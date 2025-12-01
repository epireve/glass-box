"""
Presidio-based PII detector.
Wraps the existing PIIService to implement the unified detector interface.
"""

import time
from typing import List, Dict, Any

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern

from detectors.base import PIIDetector, DetectedEntity, DetectionResult


class PresidioDetector(PIIDetector):
    """
    PII detector using Microsoft Presidio.

    Uses NER (spaCy) + regex patterns for detection.
    High precision, fast inference, no API calls required.
    """

    SUPPORTED_ENTITIES = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "CREDIT_CARD",
        "US_SSN",
        "DATE_TIME",
        "LOCATION",
        "IBAN_CODE",
        "US_BANK_NUMBER",
        "SALARY"
    ]

    def __init__(self):
        """Initialize Presidio analyzer with custom recognizers."""
        self.analyzer = AnalyzerEngine()
        self._add_custom_recognizers()

    def _add_custom_recognizers(self):
        """Add custom pattern recognizers for domain-specific entities."""

        # SALARY recognizer - matches currency amounts
        salary_patterns = [
            Pattern(
                name="salary_dollar_amount",
                regex=r"\$[\d,]+(?:\.\d{2})?",
                score=0.85
            ),
            Pattern(
                name="salary_k_format",
                regex=r"\$?\d+[kK]\b",
                score=0.7
            ),
            Pattern(
                name="salary_annual",
                regex=r"\$[\d,]+ (?:per year|annually|/year|per annum)",
                score=0.9
            )
        ]

        salary_recognizer = PatternRecognizer(
            supported_entity="SALARY",
            patterns=salary_patterns,
            name="SalaryRecognizer"
        )
        self.analyzer.registry.add_recognizer(salary_recognizer)

        # Bank account recognizer for masked accounts
        bank_patterns = [
            Pattern(
                name="masked_bank_account",
                regex=r"\*{3,4}\d{4}",
                score=0.8
            ),
            Pattern(
                name="account_ending",
                regex=r"account (?:ending |ending in |#)?\d{4}",
                score=0.75
            )
        ]

        bank_recognizer = PatternRecognizer(
            supported_entity="US_BANK_NUMBER",
            patterns=bank_patterns,
            name="BankAccountRecognizer"
        )
        self.analyzer.registry.add_recognizer(bank_recognizer)

    def name(self) -> str:
        return "presidio"

    def detect(self, text: str) -> DetectionResult:
        """
        Detect PII entities in text using Presidio.

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with all detected entities
        """
        start_time = time.perf_counter()

        try:
            results = self.analyzer.analyze(
                text=text,
                entities=self.SUPPORTED_ENTITIES,
                language="en"
            )

            entities = []
            for result in results:
                entities.append(DetectedEntity(
                    text=text[result.start:result.end],
                    entity_type=result.entity_type,
                    start=result.start,
                    end=result.end,
                    confidence=result.score,
                    source="presidio"
                ))

            # Sort by position
            entities.sort(key=lambda x: x.start)

            latency = (time.perf_counter() - start_time) * 1000

            return DetectionResult(
                entities=entities,
                is_blocked=len(entities) > 0,
                latency_ms=latency,
                raw_response={
                    "entity_count": len(entities),
                    "entity_types": list(set(e.entity_type for e in entities))
                }
            )

        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return DetectionResult(
                entities=[],
                is_blocked=False,
                latency_ms=latency,
                error=str(e)
            )

    @property
    def supported_entities(self) -> List[str]:
        return self.SUPPORTED_ENTITIES
