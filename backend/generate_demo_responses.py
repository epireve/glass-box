#!/usr/bin/env python3
"""
Generate demo responses by calling the actual backend API.
This creates authentic PII detection results for demo mode.
"""

import json
import httpx
import asyncio
from pathlib import Path


# Test scenarios from test-scenarios.json
SCENARIOS = [
    {"id": "HR-001", "prompt": "Draft an email to Alice Chen about her salary increase from $145,000 to $165,000"},
    {"id": "HR-002", "prompt": "Whose salary is higher, Alice or David?"},
    {"id": "HR-003", "prompt": "Update direct deposit for employee SSN 123-45-6789 to account ending 4521"},
    {"id": "HR-004", "prompt": "Send meeting invite to maria.garcia@acmecorp.com and call (555) 345-6789 to confirm"},
    {"id": "HR-005", "prompt": "Process new hire paperwork for Raj Patel, born April 18, 1988, SSN 345-67-8901"},
    {"id": "HR-006", "prompt": "Calculate bonus for Jennifer Williams earning $250,000 with 15% target"},
    {"id": "HR-007", "prompt": "Send tax documents to Michael Johnson at 1100 Main Street, Austin, TX 78701"},
    {"id": "HR-008", "prompt": "Compare the salaries of all employees in the Engineering department"},
    {"id": "HR-009", "prompt": "Enroll Yuki Tanaka in health insurance, DOB August 14, 1992"},
    {"id": "HR-010", "prompt": "Set up direct deposit for Sarah Thompson to bank account ending in 7890"},
    {"id": "HR-011", "prompt": "Update contact info: ahmed.hassan@acmecorp.com, phone (555) 901-2345, address 2800 Research Blvd"},
    {"id": "HR-012", "prompt": "Who are the top 3 highest paid employees?"},
    {"id": "HR-013", "prompt": "Process final paycheck for Emily Rodriguez, SSN 901-23-4567, at $75,000 annual"},
    {"id": "HR-014", "prompt": "Prepare promotion letter for James Kim with new salary of $175,000"},
    {"id": "HR-015", "prompt": "Verify employment for Priya Sharma at (555) 234-5679 or priya.sharma@acmecorp.com"},
    {"id": "HR-016", "prompt": "What is the salary difference between Robert Taylor and Marcus Brown?"},
    {"id": "HR-017", "prompt": "Process relocation package for Lisa Nguyen moving from 2100 Guadalupe Street to 500 East 7th Street"},
    {"id": "HR-018", "prompt": "Issue emergency payment of $5,000 to account ****4567 for Marcus Brown"},
    {"id": "HR-019", "prompt": "Call David Okonkwo at (555) 876-5432 regarding the budget meeting"},
    {"id": "HR-020", "prompt": "Send offer letter to new hire: John Smith, SSN 111-22-3333, starting salary $95,000, DOB Jan 15, 1990, address 123 New Street Austin TX, email john.smith@email.com, phone (555) 999-8888"},
]

API_URL = "http://localhost:8000/api/chat"


async def call_api(client: httpx.AsyncClient, scenario: dict, detector: str) -> dict:
    """Call the API and parse the streaming response."""
    url = f"{API_URL}?detector={detector}"
    payload = {
        "messages": [{"role": "user", "content": scenario["prompt"]}]
    }

    print(f"  Calling API for {scenario['id']} with {detector}...")

    try:
        response = await client.post(url, json=payload, timeout=60.0)
        response.raise_for_status()

        # Parse the streaming response
        content = response.text
        lines = content.strip().split('\n')

        pii_analysis = None
        llm_response_parts = []
        completion_metrics = None

        for line in lines:
            if not line.strip():
                continue

            # Parse Vercel AI SDK data stream format
            if line.startswith('2:'):
                # JSON data (pii_analysis or completion)
                try:
                    data = json.loads(line[2:])
                    if isinstance(data, list) and len(data) > 0:
                        item = data[0]
                        if item.get('type') == 'pii_analysis':
                            pii_analysis = item
                        elif item.get('type') == 'completion':
                            completion_metrics = item
                except json.JSONDecodeError:
                    pass
            elif line.startswith('0:'):
                # Text content
                try:
                    text = json.loads(line[2:])
                    llm_response_parts.append(text)
                except json.JSONDecodeError:
                    pass

        llm_response = ''.join(llm_response_parts)

        return {
            "pii_analysis": pii_analysis,
            "response": llm_response,
            "completion_metrics": completion_metrics
        }

    except Exception as e:
        print(f"  Error for {scenario['id']}: {e}")
        return None


async def generate_responses(detector: str = "presidio") -> dict:
    """Generate responses for all scenarios."""
    responses = {}

    async with httpx.AsyncClient() as client:
        for scenario in SCENARIOS:
            result = await call_api(client, scenario, detector)
            if result and result["pii_analysis"]:
                responses[scenario["id"]] = {
                    "pii_analysis": result["pii_analysis"],
                    "response": result["response"]
                }
                print(f"  ✓ {scenario['id']}: {len(result['pii_analysis'].get('entities_found', []))} entities detected")
            else:
                print(f"  ✗ {scenario['id']}: Failed to get response")

            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.5)

    return responses


async def main():
    print("=" * 60)
    print("Generating Demo Responses from Actual Backend API")
    print("=" * 60)

    # Generate with Presidio detector
    print("\n[1/2] Generating responses with Presidio detector...")
    presidio_responses = await generate_responses("presidio")

    # Create the demo-responses.json structure
    demo_data = {
        "responses": presidio_responses,
        "detectors": {
            "presidio": {
                "name": "Presidio",
                "description": "Microsoft's Regex + NER based detector",
                "color": "blue"
            },
            "gliner": {
                "name": "GLiNER",
                "description": "Transformer-based zero-shot NER",
                "color": "green"
            }
        }
    }

    # Save to frontend public folder
    output_path = Path(__file__).parent.parent / "frontend" / "public" / "demo-responses.json"
    with open(output_path, 'w') as f:
        json.dump(demo_data, f, indent=2)

    print(f"\n✓ Saved {len(presidio_responses)} responses to {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
