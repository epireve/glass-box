"""
PII Detector Factory for switching between different detectors.
Supports Presidio and GLiNER detectors.
"""

from typing import Dict, List, Tuple, Any
from collections import defaultdict
import re


class PIIDetectorFactory:
    """
    Factory for getting the appropriate PII detector based on name.
    """

    _presidio_service = None
    _gliner_service = None

    @classmethod
    def get_detector(cls, detector_name: str):
        """
        Get a PII detector by name.

        Args:
            detector_name: Either "presidio" or "gliner"

        Returns:
            PIIService compatible interface
        """
        if detector_name == "gliner":
            return cls._get_gliner_service()
        else:
            return cls._get_presidio_service()

    @classmethod
    def _get_presidio_service(cls):
        """Get or create Presidio service."""
        if cls._presidio_service is None:
            from pii_service import pii_service
            cls._presidio_service = pii_service
        return cls._presidio_service

    @classmethod
    def _get_gliner_service(cls):
        """Get or create GLiNER service wrapper."""
        if cls._gliner_service is None:
            cls._gliner_service = GLiNERServiceWrapper()
        return cls._gliner_service


class GLiNERServiceWrapper:
    """
    Wrapper around GLiNER detector to match PIIService interface.
    """

    def __init__(self):
        """Initialize the GLiNER detector lazily."""
        self._detector = None
        # Session-based mapping storage: {session_id: {placeholder: original_value}}
        self.mapping_store: Dict[str, Dict[str, str]] = {}

    @property
    def detector(self):
        """Lazy load the GLiNER detector."""
        if self._detector is None:
            from detectors.gliner_detector import GLiNERDetector
            self._detector = GLiNERDetector()
        return self._detector

    def analyze(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze text for PII entities using GLiNER.

        Args:
            text: The text to analyze

        Returns:
            List of detected entities with type, value, position, and score
        """
        result = self.detector.detect(text)

        # Convert to dict format matching PIIService
        entities = []
        for entity in result.entities:
            entities.append({
                "entity_type": entity.entity_type,
                "start": entity.start,
                "end": entity.end,
                "score": entity.confidence,  # DetectedEntity uses 'confidence' not 'score'
                "value": entity.text
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
        # Detect PII entities
        result = self.detector.detect(text)

        if not result.entities:
            return text, {}, []

        # Sort results by start position (descending) to replace from end
        sorted_entities = sorted(result.entities, key=lambda x: x.start, reverse=True)

        # Track entity counts for unique placeholders
        entity_counts: Dict[str, int] = defaultdict(int)

        # Build mapping and anonymized text
        mapping: Dict[str, str] = {}
        anonymized_text = text
        analysis_results = []

        for entity in sorted_entities:
            original_value = entity.text
            entity_type = entity.entity_type

            # Generate unique placeholder
            entity_counts[entity_type] += 1
            placeholder = f"<{entity_type}_{entity_counts[entity_type]}>"

            # Store mapping (placeholder -> original)
            mapping[placeholder] = original_value

            # Replace in text
            anonymized_text = (
                anonymized_text[:entity.start] +
                placeholder +
                anonymized_text[entity.end:]
            )

            # Record analysis result
            analysis_results.append({
                "entity_type": entity_type,
                "original_value": original_value,
                "placeholder": placeholder,
                "score": entity.confidence,  # DetectedEntity uses 'confidence' not 'score'
                "start": entity.start,
                "end": entity.end
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
