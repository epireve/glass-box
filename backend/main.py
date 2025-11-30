"""
FastAPI backend for PII Guardrail POC.
Implements streaming chat endpoint with Presidio anonymization and OpenRouter LLM.
"""

import json
import os
import time
import uuid
from typing import Optional, List, Dict, Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pii_service import pii_service
from retrieval_service import retrieval_service

# Load environment variables
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Check if API key is valid (not empty or placeholder)
def is_api_key_valid():
    return OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("sk-or-v1-your")

# Initialize FastAPI app
app = FastAPI(
    title="PII Guardrail API",
    description="Privacy-preserving RAG chatbot with reversible anonymization",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: Optional[str] = None


class AnalyzeRequest(BaseModel):
    text: str


class ScenarioResponse(BaseModel):
    scenarios: List[Dict[str, Any]]


# Helper function to format Vercel AI SDK stream
def format_text_chunk(text: str) -> str:
    """Format text chunk for Vercel AI SDK Data Stream Protocol (prefix 0:)"""
    # Escape the text for JSON
    escaped = json.dumps(text)
    return f"0:{escaped}\n"


def format_data_chunk(data: Dict[str, Any]) -> str:
    """Format data chunk for Vercel AI SDK Data Stream Protocol (prefix 2:)"""
    return f"2:{json.dumps([data])}\n"


async def stream_chat_response(
    messages: List[ChatMessage],
    session_id: str
):
    """
    Main streaming handler that:
    1. Retrieves relevant employee context (RAG)
    2. Anonymizes the combined input
    3. Streams response from OpenRouter
    4. Sends debug events with PII mapping
    """
    start_time = time.time()

    # Get the latest user message
    user_message = messages[-1].content if messages else ""

    # Step 1: Retrieve relevant employee context (RAG)
    retrieval_result = retrieval_service.retrieve_for_query(user_message)
    rag_context = retrieval_result["context"]
    retrieved_employees = retrieval_result["employees"]
    retrieval_type = retrieval_result["retrieval_type"]

    retrieval_time = (time.time() - start_time) * 1000

    # Build combined text for anonymization
    if rag_context:
        combined_text = f"{rag_context}\n\nUser Query: {user_message}"
    else:
        combined_text = user_message

    # Step 2: Anonymize the combined text
    anonymize_start = time.time()
    anonymized_text, mapping, analysis = pii_service.anonymize(combined_text, session_id)
    anonymize_time = (time.time() - anonymize_start) * 1000

    # Get entity statistics
    entity_stats = pii_service.get_entity_stats(analysis)

    # Step 3: Send debug event with PII analysis info
    debug_event = {
        "type": "pii_analysis",
        "session_id": session_id,
        "mapping": mapping,
        "entities_found": analysis,
        "entity_stats": entity_stats,
        "original_prompt": user_message,
        "anonymized_prompt": anonymized_text,
        "rag_context": rag_context if rag_context else None,
        "retrieved_employees": [e["name"] for e in retrieved_employees],
        "retrieval_type": retrieval_type,
        "metrics": {
            "retrieval_time_ms": round(retrieval_time, 2),
            "anonymization_time_ms": round(anonymize_time, 2)
        }
    }

    yield format_data_chunk(debug_event)

    # Step 4: Build messages for LLM
    system_prompt = """You are an HR assistant for Acme Corporation.
You help with employee inquiries, compensation questions, and HR-related tasks.
Be professional, helpful, and concise.
When employee data is provided in the context, use it to answer questions accurately."""

    llm_messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add conversation history (anonymized)
    for msg in messages[:-1]:
        # Anonymize each historical message
        anon_content, _, _ = pii_service.anonymize(msg.content, session_id)
        llm_messages.append({
            "role": msg.role,
            "content": anon_content
        })

    # Add current anonymized message
    llm_messages.append({
        "role": "user",
        "content": anonymized_text
    })

    # Step 5: Stream from OpenRouter
    if not is_api_key_valid():
        # Demo mode without API key - return mock response
        mock_response = generate_mock_response(anonymized_text, mapping)
        for chunk in mock_response:
            yield format_text_chunk(chunk)

        # Send completion event
        yield format_data_chunk({
            "type": "completion",
            "total_time_ms": round((time.time() - start_time) * 1000, 2)
        })
        return

    llm_start = time.time()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "PII Guardrail POC"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": llm_messages,
                    "stream": True
                }
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield format_text_chunk(f"Error from LLM: {response.status_code}")
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                yield format_text_chunk(content)
                        except json.JSONDecodeError:
                            continue

    except httpx.TimeoutException:
        yield format_text_chunk("Request timed out. Please try again.")
    except Exception as e:
        yield format_text_chunk(f"Error: {str(e)}")

    # Send completion event
    llm_time = (time.time() - llm_start) * 1000
    total_time = (time.time() - start_time) * 1000

    yield format_data_chunk({
        "type": "completion",
        "metrics": {
            "llm_time_ms": round(llm_time, 2),
            "total_time_ms": round(total_time, 2)
        }
    })


def generate_mock_response(anonymized_text: str, mapping: Dict[str, str]) -> List[str]:
    """
    Generate a mock response for demo mode (when no API key is configured).
    Uses the anonymized placeholders in the response.
    """
    # Detect what type of query this is
    # Use only the user query portion if present
    if "user query:" in anonymized_text.lower():
        query_part = anonymized_text.lower().split("user query:")[-1].strip()
    else:
        query_part = anonymized_text.lower()

    # Check for top earners / most salary queries FIRST
    if any(word in query_part for word in ["most", "top", "highest", "maximum", "max"]) and "salary" in query_part:
        # Top earners query
        persons = [k for k in mapping.keys() if "PERSON" in k]
        salaries = [k for k in mapping.keys() if "SALARY" in k]

        if persons and salaries:
            response = f"Based on the employee records, {persons[0]} has the highest salary at {salaries[0]}."
            if len(persons) > 1:
                response += f"\n\nTop earners:\n"
                for i, (person, salary) in enumerate(zip(persons[:3], salaries[:3]), 1):
                    response += f"{i}. {person}: {salary}\n"
        else:
            response = "Based on the employee records provided, I can identify the top earners for you."

    elif "salary" in query_part and "higher" in query_part:
        # Salary comparison query
        persons = [k for k in mapping.keys() if "PERSON" in k]
        salaries = [k for k in mapping.keys() if "SALARY" in k]

        if len(persons) >= 2:
            response = f"Based on the employee records, {persons[1]} has a higher salary than {persons[0]}."
        else:
            response = "I can see the salary information in the records. Let me compare them for you."

    elif any(phrase in query_part for phrase in ["draft email", "write email", "send email", "compose email", "draft an email", "write an email"]):
        # Email drafting query - check for explicit email writing intent
        person = next((k for k in mapping.keys() if "PERSON" in k), "the employee")
        salary = next((k for k in mapping.keys() if "SALARY" in k), "the discussed amount")

        response = f"""Subject: Compensation Update

Dear {person},

I hope this message finds you well. I am writing to inform you about an important update regarding your compensation.

After careful review, we are pleased to confirm the salary adjustment to {salary}. This change reflects our recognition of your valuable contributions to the team.

Please let me know if you have any questions.

Best regards,
HR Department"""

    elif any(word in query_part for word in ["lowest", "minimum", "min", "least"]) and "salary" in query_part:
        # Lowest salary query
        persons = [k for k in mapping.keys() if "PERSON" in k]
        salaries = [k for k in mapping.keys() if "SALARY" in k]

        if persons and salaries:
            response = f"Based on the employee records, {persons[-1] if len(persons) > 1 else persons[0]} has the lowest salary at {salaries[-1] if len(salaries) > 1 else salaries[0]}."
        else:
            response = "Based on the employee records provided, I can identify employees with lower salaries."

    else:
        # Generic response
        response = "I understand your request. Based on the employee information provided, I can help you with that. "
        if mapping:
            persons = [k for k in mapping.keys() if "PERSON" in k]
            salaries = [k for k in mapping.keys() if "SALARY" in k]
            if persons:
                response += f"\n\nI found information about: {', '.join(persons[:3])}"
            if salaries:
                response += f"\nSalary data: {', '.join(salaries[:3])}"

    # Split response into chunks for streaming effect
    words = response.split(" ")
    chunks = []
    current_chunk = ""

    for word in words:
        current_chunk += word + " "
        if len(current_chunk) > 20:  # Chunk every ~20 chars
            chunks.append(current_chunk)
            current_chunk = ""

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# API Endpoints
@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint with streaming response.
    Implements Vercel AI SDK Data Stream Protocol.
    """
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        stream_chat_response(request.messages, session_id),
        media_type="text/plain",
        headers={
            "X-Session-Id": session_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.post("/api/analyze")
async def analyze_pii(request: AnalyzeRequest):
    """
    Analyze text for PII without sending to LLM.
    Useful for debugging and understanding PII detection.
    """
    entities = pii_service.analyze(request.text)

    return {
        "text": request.text,
        "entities": entities,
        "entity_count": len(entities),
        "entity_stats": pii_service.get_entity_stats(entities)
    }


@app.get("/api/scenarios")
async def get_scenarios():
    """Get the Golden Set test scenarios."""
    from pathlib import Path
    import json

    scenarios_path = Path(__file__).parent / "data" / "test_scenarios.json"

    with open(scenarios_path, "r") as f:
        data = json.load(f)

    return {"scenarios": data.get("scenarios", [])}


@app.get("/api/employees")
async def get_employees():
    """Get list of employees (names only, for UI autocomplete)."""
    employees = retrieval_service.get_all_employees()

    return {
        "employees": [
            {
                "id": e["id"],
                "name": e["name"],
                "department": e["department"],
                "title": e["title"]
            }
            for e in employees
        ]
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "pii_service": "active",
            "retrieval_service": "active",
            "openrouter": "configured" if is_api_key_valid() else "demo_mode"
        }
    }


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """Clear PII mapping for a session."""
    pii_service.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
