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
from pii_detector_factory import PIIDetectorFactory
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
    session_id: str,
    detector: str = "presidio"
):
    """
    Main streaming handler that:
    1. Retrieves relevant employee context (RAG)
    2. Anonymizes the combined input using specified detector
    3. Streams response from OpenRouter
    4. Sends debug events with PII mapping

    Args:
        messages: Chat messages
        session_id: Session ID for mapping persistence
        detector: PII detector to use ("presidio" or "gliner")
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

    # Step 2: Anonymize the combined text using selected detector
    anonymize_start = time.time()
    detector_service = None
    detector_error = None
    try:
        detector_service = PIIDetectorFactory.get_detector(detector)
        anonymized_text, mapping, analysis = detector_service.anonymize(combined_text, session_id)
    except Exception as e:
        # If detector fails, fall back to no anonymization and report error
        detector_error = str(e)
        print(f"Error with {detector} detector: {e}")
        import traceback
        traceback.print_exc()
        anonymized_text = combined_text
        mapping = {}
        analysis = []
    anonymize_time = (time.time() - anonymize_start) * 1000

    # Get entity statistics
    if detector_service and analysis:
        try:
            entity_stats = detector_service.get_entity_stats(analysis)
        except:
            entity_stats = {}
    else:
        entity_stats = {}

    # Step 3: Send debug event with PII analysis info
    debug_event = {
        "type": "pii_analysis",
        "session_id": session_id,
        "detector": detector,
        "detector_error": detector_error,
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
        # Anonymize each historical message using selected detector
        if detector_service:
            try:
                anon_content, _, _ = detector_service.anonymize(msg.content, session_id)
            except:
                anon_content = msg.content
        else:
            anon_content = msg.content
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

    elif any(word in query_part for word in ["direct deposit", "bank", "account", "routing"]):
        # Banking / direct deposit update
        ssns = [k for k in mapping.keys() if "US_SSN" in k]
        bank_accounts = [k for k in mapping.keys() if "US_BANK_NUMBER" in k]
        persons = [k for k in mapping.keys() if "PERSON" in k]

        response = "I'll help you update the direct deposit information.\n\n"
        response += "**Request Details:**\n"
        if ssns:
            response += f"- Employee SSN: {ssns[0]}\n"
        if bank_accounts:
            response += f"- New Account: {bank_accounts[0]}\n"
        if persons:
            response += f"- Employee: {persons[0]}\n"
        response += "\n⚠️ **Note:** For security, direct deposit changes require employee verification. A confirmation email will be sent to the employee on file."

    elif any(word in query_part for word in ["meeting", "invite", "schedule", "call", "contact"]):
        # Meeting / contact request
        emails = [k for k in mapping.keys() if "EMAIL" in k]
        phones = [k for k in mapping.keys() if "PHONE" in k]
        persons = [k for k in mapping.keys() if "PERSON" in k]

        response = "I'll help you with this communication request.\n\n"
        response += "**Contact Details:**\n"
        if persons:
            response += f"- Name: {persons[0]}\n"
        if emails:
            response += f"- Email: {emails[0]}\n"
        if phones:
            response += f"- Phone: {phones[0]}\n"
        response += "\n✅ Meeting invite will be sent to the specified contacts."

    elif any(word in query_part for word in ["find", "lookup", "search", "get", "show", "what is", "who is"]):
        # Lookup / search query
        persons = [k for k in mapping.keys() if "PERSON" in k]
        emails = [k for k in mapping.keys() if "EMAIL" in k]
        phones = [k for k in mapping.keys() if "PHONE" in k]
        salaries = [k for k in mapping.keys() if "SALARY" in k]

        response = "Here's the information I found:\n\n"
        if persons:
            for person in persons[:3]:
                response += f"**{person}**\n"
        if emails:
            response += f"- Email: {', '.join(emails[:2])}\n"
        if phones:
            response += f"- Phone: {', '.join(phones[:2])}\n"
        if salaries:
            response += f"- Salary: {', '.join(salaries[:2])}\n"

    else:
        # Generic response - build based on what PII was detected
        pii_types = {
            "PERSON": [k for k in mapping.keys() if "PERSON" in k],
            "EMAIL": [k for k in mapping.keys() if "EMAIL" in k],
            "PHONE": [k for k in mapping.keys() if "PHONE" in k],
            "SSN": [k for k in mapping.keys() if "US_SSN" in k],
            "SALARY": [k for k in mapping.keys() if "SALARY" in k],
            "BANK": [k for k in mapping.keys() if "US_BANK" in k],
            "CREDIT_CARD": [k for k in mapping.keys() if "CREDIT_CARD" in k],
        }

        response = "I've processed your request. Here's a summary of the information involved:\n\n"

        has_data = False
        for pii_type, values in pii_types.items():
            if values:
                has_data = True
                response += f"**{pii_type}:** {', '.join(values[:3])}\n"

        if not has_data:
            response = "I understand your request. No sensitive PII was detected in this query."

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
async def chat(request: ChatRequest, detector: str = "presidio"):
    """
    Main chat endpoint with streaming response.
    Implements Vercel AI SDK Data Stream Protocol.

    Args:
        request: Chat request with messages
        detector: PII detector to use ("presidio" or "gliner")
    """
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        stream_chat_response(request.messages, session_id, detector),
        media_type="text/plain",
        headers={
            "X-Session-Id": session_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.post("/api/analyze")
async def analyze_pii(request: AnalyzeRequest, detector: str = "presidio"):
    """
    Analyze text for PII without sending to LLM.
    Useful for debugging and understanding PII detection.

    Args:
        request: Text to analyze
        detector: PII detector to use ("presidio" or "gliner")
    """
    detector_service = PIIDetectorFactory.get_detector(detector)
    entities = detector_service.analyze(request.text)

    return {
        "text": request.text,
        "detector": detector,
        "entities": entities,
        "entity_count": len(entities),
        "entity_stats": detector_service.get_entity_stats(entities)
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
        },
        "detectors": {
            "presidio": "available",
            "gliner": "available"
        }
    }


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """Clear PII mapping for a session from all detectors."""
    # Clear from both detectors to ensure complete cleanup
    pii_service.clear_session(session_id)
    gliner_service = PIIDetectorFactory.get_detector("gliner")
    gliner_service.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


# =============================================================================
# Benchmark API Endpoints
# =============================================================================

from pathlib import Path
from detectors.presidio_detector import PresidioDetector
from evaluation.runner import BenchmarkRunner

# Lazy initialization of benchmark components
_benchmark_runner = None
_presidio_detector = None


def get_benchmark_runner() -> BenchmarkRunner:
    global _benchmark_runner
    if _benchmark_runner is None:
        _benchmark_runner = BenchmarkRunner()
    return _benchmark_runner


def get_presidio_detector() -> PresidioDetector:
    global _presidio_detector
    if _presidio_detector is None:
        _presidio_detector = PresidioDetector()
    return _presidio_detector


class BenchmarkRequest(BaseModel):
    detector: str = "presidio"  # presidio or llama_guard
    dataset: str = "golden_set"  # Dataset name without extension
    limit: Optional[int] = None  # Limit test cases (for quick testing)


class CompareRequest(BaseModel):
    run_id_1: str
    run_id_2: str


@app.get("/api/benchmark/datasets")
async def list_datasets():
    """List available benchmark datasets."""
    data_dir = Path(__file__).parent / "data"
    datasets = []

    for f in data_dir.glob("*.json"):
        if f.name.startswith("_") or f.name == "employees.json":
            continue

        # Load metadata if available
        try:
            with open(f, "r") as file:
                data = json.load(file)
                if "test_cases" in data:
                    count = len(data["test_cases"])
                    metadata = data.get("metadata", {})
                elif "scenarios" in data:
                    count = len(data["scenarios"])
                    metadata = {}
                else:
                    count = 0
                    metadata = {}

                datasets.append({
                    "name": f.stem,
                    "filename": f.name,
                    "test_case_count": count,
                    "description": metadata.get("description", ""),
                    "categories": metadata.get("categories", [])
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return {"datasets": datasets}


@app.get("/api/benchmark/results")
async def list_benchmark_results():
    """List all benchmark run results."""
    results_dir = Path(__file__).parent / "data" / "benchmark_results" / "runs"

    if not results_dir.exists():
        return {"results": [], "index": None}

    results = []
    for f in sorted(results_dir.glob("*.json"), reverse=True):
        try:
            with open(f, "r") as file:
                data = json.load(file)
                # Handle nested structure
                summary = data.get("summary", {})
                metrics = data.get("overall_metrics", {})
                latency = data.get("latency", {})

                results.append({
                    "run_id": f.stem,
                    "filename": f.name,
                    "detector": data.get("detector_name", "unknown"),
                    "dataset": data.get("dataset_name", "unknown"),
                    "timestamp": data.get("timestamp", ""),
                    "total_cases": summary.get("total_cases", 0),
                    "passed_cases": summary.get("passed_cases", 0),
                    "overall_f1": metrics.get("f1_score", 0),
                    "leakage_rate": metrics.get("leakage_rate", 0),
                    "latency_p50": latency.get("p50_ms", 0),
                })
        except (json.JSONDecodeError, KeyError):
            continue

    # Load index if available
    index_path = Path(__file__).parent / "data" / "benchmark_results" / "index.json"
    index = None
    if index_path.exists():
        try:
            with open(index_path, "r") as f:
                index = json.load(f)
        except json.JSONDecodeError:
            pass

    return {"results": results, "index": index}


@app.get("/api/benchmark/results/{run_id}")
async def get_benchmark_result(run_id: str):
    """Get detailed benchmark result by run ID."""
    results_dir = Path(__file__).parent / "data" / "benchmark_results" / "runs"
    result_path = results_dir / f"{run_id}.json"

    if not result_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark result not found: {run_id}")

    with open(result_path, "r") as f:
        data = json.load(f)

    return data


@app.post("/api/benchmark/run")
async def run_benchmark(request: BenchmarkRequest):
    """
    Run a benchmark with specified detector and dataset.
    Returns the benchmark results.
    """
    # Validate detector
    if request.detector not in ["presidio", "llama_guard", "gliner"]:
        raise HTTPException(status_code=400, detail=f"Unknown detector: {request.detector}")

    # Find dataset
    data_dir = Path(__file__).parent / "data"
    dataset_path = data_dir / f"{request.dataset}.json"

    if not dataset_path.exists():
        # Try with different extensions
        for ext in [".json"]:
            alt_path = data_dir / f"{request.dataset}{ext}"
            if alt_path.exists():
                dataset_path = alt_path
                break
        else:
            raise HTTPException(status_code=404, detail=f"Dataset not found: {request.dataset}")

    # Initialize detector
    if request.detector == "presidio":
        detector = get_presidio_detector()
    elif request.detector == "gliner":
        from detectors.gliner_detector import GLiNERDetector
        detector = GLiNERDetector()
    else:
        # Llama Guard requires API key
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key or api_key.startswith("sk-or-v1-your"):
            raise HTTPException(
                status_code=400,
                detail="OPENROUTER_API_KEY not configured for Llama Guard detector"
            )
        from detectors.llama_guard_detector import LlamaGuardDetector
        detector = LlamaGuardDetector(api_key=api_key)

    # Load test cases
    runner = get_benchmark_runner()
    test_cases = runner.load_test_cases(str(dataset_path))

    if request.limit:
        test_cases = test_cases[:request.limit]

    # Run benchmark
    result = runner.run_benchmark(
        detector=detector,
        test_cases=test_cases,
        dataset_name=request.dataset
    )

    # Save result
    saved_path = runner.save_result(result)

    # Clean up if needed
    if hasattr(detector, 'close'):
        detector.close()

    return {
        "status": "completed",
        "run_id": Path(saved_path).stem,
        "saved_path": saved_path,
        "summary": {
            "detector": result.detector_name,
            "dataset": result.dataset_name,
            "total_cases": result.total_cases,
            "passed_cases": result.passed_cases,
            "pass_rate": result.passed_cases / result.total_cases if result.total_cases > 0 else 0,
            "precision": result.overall_precision,
            "recall": result.overall_recall,
            "f1_score": result.overall_f1,
            "leakage_rate": result.leakage_rate,
            "latency_p50_ms": result.latency_p50,
            "latency_p95_ms": result.latency_p95,
        },
        "entity_metrics": {
            etype: {
                "precision": m.precision,
                "recall": m.recall,
                "f1_score": m.f1_score,
                "true_positives": m.true_positives,
                "false_positives": m.false_positives,
                "false_negatives": m.false_negatives,
            }
            for etype, m in result.entity_metrics.items()
        }
    }


@app.post("/api/benchmark/compare")
async def compare_benchmark_runs(request: CompareRequest):
    """Compare two benchmark runs."""
    results_dir = Path(__file__).parent / "data" / "benchmark_results" / "runs"

    # Load both results
    path1 = results_dir / f"{request.run_id_1}.json"
    path2 = results_dir / f"{request.run_id_2}.json"

    if not path1.exists():
        raise HTTPException(status_code=404, detail=f"Result not found: {request.run_id_1}")
    if not path2.exists():
        raise HTTPException(status_code=404, detail=f"Result not found: {request.run_id_2}")

    with open(path1) as f:
        result1 = json.load(f)
    with open(path2) as f:
        result2 = json.load(f)

    # Extract nested metrics
    def get_metrics(data):
        metrics = data.get("overall_metrics", {})
        latency = data.get("latency", {})
        return {
            "precision": metrics.get("precision", 0),
            "recall": metrics.get("recall", 0),
            "f1_score": metrics.get("f1_score", 0),
            "leakage_rate": metrics.get("leakage_rate", 0),
            "latency_p50": latency.get("p50_ms", 0),
        }

    m1 = get_metrics(result1)
    m2 = get_metrics(result2)

    # Build comparison
    comparison = {
        "run_1": {
            "run_id": request.run_id_1,
            "detector": result1.get("detector_name"),
            "dataset": result1.get("dataset_name"),
        },
        "run_2": {
            "run_id": request.run_id_2,
            "detector": result2.get("detector_name"),
            "dataset": result2.get("dataset_name"),
        },
        "metrics_comparison": {
            "precision": {
                "run_1": m1["precision"],
                "run_2": m2["precision"],
                "delta": m2["precision"] - m1["precision"],
            },
            "recall": {
                "run_1": m1["recall"],
                "run_2": m2["recall"],
                "delta": m2["recall"] - m1["recall"],
            },
            "f1_score": {
                "run_1": m1["f1_score"],
                "run_2": m2["f1_score"],
                "delta": m2["f1_score"] - m1["f1_score"],
            },
            "leakage_rate": {
                "run_1": m1["leakage_rate"],
                "run_2": m2["leakage_rate"],
                "delta": m2["leakage_rate"] - m1["leakage_rate"],
            },
            "latency_p50": {
                "run_1": m1["latency_p50"],
                "run_2": m2["latency_p50"],
                "delta": m2["latency_p50"] - m1["latency_p50"],
            },
        },
        "winner": {
            "f1_score": request.run_id_1 if m1["f1_score"] > m2["f1_score"] else request.run_id_2,
            "leakage_rate": request.run_id_1 if m1["leakage_rate"] < m2["leakage_rate"] else request.run_id_2,
            "latency": request.run_id_1 if m1["latency_p50"] < m2["latency_p50"] else request.run_id_2,
        }
    }

    return comparison


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
