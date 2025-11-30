"""
PII Service using Microsoft Presidio for detection and anonymization.
Implements reversible anonymization with placeholder mapping.
"""

from typing import Dict, List, Tuple, Any
from collections import defaultdict
import re

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import RecognizerResult, OperatorConfig


class PIIService:
    """
    Service for detecting and anonymizing PII using Microsoft Presidio.
    Supports reversible anonymization with session-based mapping storage.
    """

    # PII entity types to detect
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
        "SALARY"  # Custom entity
    ]

    def __init__(self):
        """Initialize Presidio engines and add custom recognizers."""
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self._add_custom_recognizers()

        # Session-based mapping storage: {session_id: {placeholder: original_value}}
        self.mapping_store: Dict[str, Dict[str, str]] = {}

    def _add_custom_recognizers(self):
        """Add custom pattern recognizers for entities not natively supported."""

        # SALARY recognizer - matches currency amounts like $145,000 or 145k
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

        # Bank account recognizer for masked accounts (****1234)
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

    def analyze(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze text for PII entities.

        Args:
            text: The text to analyze

        Returns:
            List of detected entities with type, value, position, and score
        """
        results = self.analyzer.analyze(
            text=text,
            entities=self.SUPPORTED_ENTITIES,
            language="en"
        )

        # Convert to dict format for JSON serialization
        entities = []
        for result in results:
            entities.append({
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score,
                "value": text[result.start:result.end]
            })

        # Sort by position for consistent ordering
        entities.sort(key=lambda x: x["start"])
        return entities

    def anonymize(
        self,
        text: str,
        session_id: str
    ) -> Tuple[str, Dict[str, str], List[Dict[str, Any]]]:
        """
        Anonymize PII in text with reversible placeholders.

        Args:
            text: The text to anonymize
            session_id: Session identifier for mapping storage

        Returns:
            Tuple of (anonymized_text, mapping, analysis_results)
        """
        # Analyze for PII entities
        results = self.analyzer.analyze(
            text=text,
            entities=self.SUPPORTED_ENTITIES,
            language="en"
        )

        if not results:
            return text, {}, []

        # Sort results by start position (descending) to replace from end
        sorted_results = sorted(results, key=lambda x: x.start, reverse=True)

        # Track entity counts for unique placeholders
        entity_counts: Dict[str, int] = defaultdict(int)

        # Build mapping and anonymized text
        mapping: Dict[str, str] = {}
        anonymized_text = text
        analysis_results = []

        for result in sorted_results:
            original_value = text[result.start:result.end]
            entity_type = result.entity_type

            # Generate unique placeholder
            entity_counts[entity_type] += 1
            placeholder = f"<{entity_type}_{entity_counts[entity_type]}>"

            # Store mapping (placeholder -> original)
            mapping[placeholder] = original_value

            # Replace in text
            anonymized_text = (
                anonymized_text[:result.start] +
                placeholder +
                anonymized_text[result.end:]
            )

            # Record analysis result
            analysis_results.append({
                "entity_type": entity_type,
                "original_value": original_value,
                "placeholder": placeholder,
                "score": result.score,
                "start": result.start,
                "end": result.end
            })

        # Reverse to get correct order (by original position)
        analysis_results.reverse()

        # Renumber placeholders to be in reading order
        mapping, anonymized_text = self._renumber_placeholders(mapping, anonymized_text)

        # Store mapping for session
        if session_id not in self.mapping_store:
            self.mapping_store[session_id] = {}
        self.mapping_store[session_id].update(mapping)

        return anonymized_text, mapping, analysis_results

    def _renumber_placeholders(
        self,
        mapping: Dict[str, str],
        text: str
    ) -> Tuple[Dict[str, str], str]:
        """
        Renumber placeholders to be in reading order (left to right).
        """
        # Find all placeholders in order of appearance
        placeholder_pattern = r"<([A-Z_]+)_(\d+)>"
        matches = list(re.finditer(placeholder_pattern, text))

        if not matches:
            return mapping, text

        # Track new numbering per entity type
        entity_order: Dict[str, int] = defaultdict(int)
        placeholder_remap: Dict[str, str] = {}

        for match in matches:
            entity_type = match.group(1)
            old_placeholder = match.group(0)

            if old_placeholder not in placeholder_remap:
                entity_order[entity_type] += 1
                new_placeholder = f"<{entity_type}_{entity_order[entity_type]}>"
                placeholder_remap[old_placeholder] = new_placeholder

        # Apply remapping to text and mapping
        new_text = text
        new_mapping: Dict[str, str] = {}

        for old_ph, new_ph in placeholder_remap.items():
            new_text = new_text.replace(old_ph, new_ph)
            if old_ph in mapping:
                new_mapping[new_ph] = mapping[old_ph]

        return new_mapping, new_text

    def deanonymize(self, text: str, session_id: str) -> str:
        """
        Restore original PII values from placeholders.

        Args:
            text: Anonymized text with placeholders
            session_id: Session identifier to retrieve mapping

        Returns:
            Text with placeholders replaced by original values
        """
        mapping = self.mapping_store.get(session_id, {})

        deanonymized_text = text
        for placeholder, original in mapping.items():
            deanonymized_text = deanonymized_text.replace(placeholder, original)

        return deanonymized_text

    def get_mapping(self, session_id: str) -> Dict[str, str]:
        """Get the current PII mapping for a session."""
        return self.mapping_store.get(session_id, {})

    def clear_session(self, session_id: str) -> None:
        """Clear mapping data for a session."""
        if session_id in self.mapping_store:
            del self.mapping_store[session_id]

    def get_entity_stats(self, analysis_results: List[Dict]) -> Dict[str, int]:
        """
        Get count of each entity type detected.

        Args:
            analysis_results: Results from analyze() or anonymize()

        Returns:
            Dict mapping entity type to count
        """
        stats: Dict[str, int] = defaultdict(int)
        for result in analysis_results:
            stats[result["entity_type"]] += 1
        return dict(stats)


# Singleton instance for use across the application
pii_service = PIIService()
