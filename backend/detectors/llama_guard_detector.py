"""
Llama Guard PII Detector via OpenRouter API.

Uses Meta's Llama Guard 4 model for PII detection through OpenRouter.
Llama Guard is designed for safety classification but can be prompted
to detect and classify PII entities.
"""

import os
import re
import time
import json
from typing import List, Dict, Any, Optional, Tuple
import httpx

from .base import PIIDetector, DetectionResult, DetectedEntity


class LlamaGuardDetector(PIIDetector):
    """
    PII detector using Llama Guard via OpenRouter API.

    Llama Guard is prompted to identify PII entities in text and
    return structured detection results.
    """

    MODEL = "meta-llama/llama-guard-4-12b"
    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    # Mapping from Llama Guard category hints to our entity types
    ENTITY_MAPPING = {
        "name": "PERSON",
        "person": "PERSON",
        "full name": "PERSON",
        "email": "EMAIL_ADDRESS",
        "email address": "EMAIL_ADDRESS",
        "phone": "PHONE_NUMBER",
        "phone number": "PHONE_NUMBER",
        "telephone": "PHONE_NUMBER",
        "ssn": "US_SSN",
        "social security": "US_SSN",
        "social security number": "US_SSN",
        "credit card": "CREDIT_CARD",
        "card number": "CREDIT_CARD",
        "date": "DATE_TIME",
        "date of birth": "DATE_TIME",
        "dob": "DATE_TIME",
        "birthday": "DATE_TIME",
        "location": "LOCATION",
        "address": "LOCATION",
        "city": "LOCATION",
        "bank account": "US_BANK_NUMBER",
        "account number": "US_BANK_NUMBER",
        "routing number": "US_BANK_NUMBER",
        "salary": "SALARY",
        "compensation": "SALARY",
        "income": "SALARY",
        "wage": "SALARY",
        "iban": "IBAN_CODE",
    }

    SUPPORTED_ENTITIES = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "CREDIT_CARD",
        "US_SSN",
        "DATE_TIME",
        "LOCATION",
        "US_BANK_NUMBER",
        "SALARY",
        "IBAN_CODE",
    ]

    # System prompt for PII detection
    SYSTEM_PROMPT = """You are a PII (Personally Identifiable Information) detection system.
Analyze the user's text and identify all PII entities present.

For each PII found, output a JSON array with objects containing:
- "text": the exact text that contains PII
- "type": the category (one of: name, email, phone, ssn, credit_card, date, location, bank_account, salary, iban)
- "confidence": your confidence level (0.0 to 1.0)

If no PII is found, output an empty array: []

Output ONLY valid JSON, no other text.

Example input: "Contact John Smith at john@email.com or 555-123-4567"
Example output: [{"text": "John Smith", "type": "name", "confidence": 0.95}, {"text": "john@email.com", "type": "email", "confidence": 0.99}, {"text": "555-123-4567", "type": "phone", "confidence": 0.95}]"""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize Llama Guard detector.

        Args:
            api_key: OpenRouter API key. If not provided, reads from OPENROUTER_API_KEY env var.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.timeout = timeout
        self._client = None

    @property
    def client(self) -> httpx.Client:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def name(self) -> str:
        return "llama_guard"

    @property
    def supported_entities(self) -> List[str]:
        return self.SUPPORTED_ENTITIES

    def _map_entity_type(self, llama_type: str) -> str:
        """Map Llama Guard entity type to our standard type."""
        normalized = llama_type.lower().strip()
        return self.ENTITY_MAPPING.get(normalized, "PERSON")

    def _find_entity_position(self, text: str, entity_text: str,
                               start_from: int = 0) -> Tuple[int, int]:
        """Find exact position of entity in text."""
        # Try exact match first
        start = text.find(entity_text, start_from)
        if start != -1:
            return start, start + len(entity_text)

        # Try case-insensitive match
        lower_text = text.lower()
        lower_entity = entity_text.lower()
        start = lower_text.find(lower_entity, start_from)
        if start != -1:
            return start, start + len(entity_text)

        # Entity not found - use approximate positions
        return -1, -1

    def _parse_response(self, response_text: str, original_text: str) -> List[DetectedEntity]:
        """Parse Llama Guard response into DetectedEntity list."""
        entities = []

        # Try to extract JSON from response
        try:
            # Look for JSON array in response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Try parsing entire response as JSON
                data = json.loads(response_text)

            if not isinstance(data, list):
                data = [data] if data else []

            # Track positions to avoid duplicates
            used_positions = set()

            for item in data:
                if not isinstance(item, dict):
                    continue

                entity_text = item.get("text", "")
                entity_type = self._map_entity_type(item.get("type", "unknown"))
                confidence = float(item.get("confidence", 0.8))

                if not entity_text:
                    continue

                # Find position in original text
                start, end = self._find_entity_position(original_text, entity_text)

                # Skip if we couldn't find the entity
                if start == -1:
                    # Still include with approximate position at 0
                    start, end = 0, len(entity_text)

                # Skip duplicates at same position
                pos_key = (start, end)
                if pos_key in used_positions:
                    continue
                used_positions.add(pos_key)

                entities.append(DetectedEntity(
                    text=entity_text,
                    entity_type=entity_type,
                    start=start,
                    end=end,
                    confidence=confidence,
                    source="llama_guard"
                ))

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # If JSON parsing fails, try to extract entities from text
            # This handles cases where Llama Guard outputs natural language
            pass

        return entities

    def detect(self, text: str) -> DetectionResult:
        """
        Detect PII in text using Llama Guard.

        Args:
            text: Text to analyze for PII.

        Returns:
            DetectionResult with detected entities.
        """
        start_time = time.perf_counter()

        try:
            response = self.client.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/pii-guardrail-poc",
                    "X-Title": "PII Guardrail POC"
                },
                json={
                    "model": self.MODEL,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.0,  # Deterministic output
                    "max_tokens": 1024,
                }
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code != 200:
                return DetectionResult(
                    entities=[],
                    is_blocked=False,
                    latency_ms=elapsed_ms,
                    error=f"API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            entities = self._parse_response(content, text)

            # Determine if should be blocked (has any high-confidence PII)
            is_blocked = any(e.confidence >= 0.7 for e in entities)

            return DetectionResult(
                entities=entities,
                is_blocked=is_blocked,
                latency_ms=elapsed_ms,
                raw_response={"model": self.MODEL, "content": content}
            )

        except httpx.TimeoutException:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return DetectionResult(
                entities=[],
                is_blocked=False,
                latency_ms=elapsed_ms,
                error="Request timed out"
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return DetectionResult(
                entities=[],
                is_blocked=False,
                latency_ms=elapsed_ms,
                error=str(e)
            )

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class LlamaGuardDetectorAsync:
    """
    Async version of Llama Guard detector for batch processing.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key required")
        self.timeout = timeout
        self._sync_detector = LlamaGuardDetector(api_key=self.api_key, timeout=timeout)

    async def detect(self, text: str) -> DetectionResult:
        """Async detection using httpx.AsyncClient."""
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    LlamaGuardDetector.API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/pii-guardrail-poc",
                        "X-Title": "PII Guardrail POC"
                    },
                    json={
                        "model": LlamaGuardDetector.MODEL,
                        "messages": [
                            {"role": "system", "content": LlamaGuardDetector.SYSTEM_PROMPT},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.0,
                        "max_tokens": 1024,
                    }
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code != 200:
                return DetectionResult(
                    entities=[],
                    is_blocked=False,
                    latency_ms=elapsed_ms,
                    error=f"API error: {response.status_code}"
                )

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            entities = self._sync_detector._parse_response(content, text)
            is_blocked = any(e.confidence >= 0.7 for e in entities)

            return DetectionResult(
                entities=entities,
                is_blocked=is_blocked,
                latency_ms=elapsed_ms,
                raw_response={"model": LlamaGuardDetector.MODEL, "content": content}
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return DetectionResult(
                entities=[],
                is_blocked=False,
                latency_ms=elapsed_ms,
                error=str(e)
            )
