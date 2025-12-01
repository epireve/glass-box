"""
Base classes for PII detectors.
Provides a unified interface for comparing different detection approaches.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import time


class EntityType(str, Enum):
    """Supported PII entity types."""
    PERSON = "PERSON"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    CREDIT_CARD = "CREDIT_CARD"
    US_SSN = "US_SSN"
    DATE_TIME = "DATE_TIME"
    LOCATION = "LOCATION"
    IBAN_CODE = "IBAN_CODE"
    US_BANK_NUMBER = "US_BANK_NUMBER"
    SALARY = "SALARY"


@dataclass
class DetectedEntity:
    """A single detected PII entity."""
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float
    source: str  # "presidio", "llama_guard", etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "source": self.source
        }

    def overlaps_with(self, other: "DetectedEntity", threshold: float = 0.5) -> bool:
        """Check if this entity overlaps with another by at least threshold."""
        if self.start >= other.end or other.start >= self.end:
            return False

        overlap_start = max(self.start, other.start)
        overlap_end = min(self.end, other.end)
        overlap_len = overlap_end - overlap_start

        # Calculate overlap ratio based on smaller entity
        min_len = min(self.end - self.start, other.end - other.start)
        return (overlap_len / min_len) >= threshold


@dataclass
class DetectionResult:
    """Result from a PII detection run."""
    entities: List[DetectedEntity]
    is_blocked: bool  # Whether the detector recommends blocking this input
    latency_ms: float
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "is_blocked": self.is_blocked,
            "latency_ms": self.latency_ms,
            "raw_response": self.raw_response,
            "error": self.error
        }

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def entity_types(self) -> List[str]:
        return [e.entity_type for e in self.entities]

    def get_entities_by_type(self, entity_type: str) -> List[DetectedEntity]:
        return [e for e in self.entities if e.entity_type == entity_type]


@dataclass
class ExpectedEntity:
    """Ground truth entity for evaluation."""
    text: str
    entity_type: str
    start: int
    end: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end
        }


@dataclass
class TestCase:
    """A single test case for evaluation."""
    id: str
    query: str
    expected_entities: List[ExpectedEntity]
    category: str = "general"
    difficulty: str = "medium"  # easy, medium, hard
    description: str = ""
    requires_rag: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "expected_entities": [e.to_dict() for e in self.expected_entities],
            "category": self.category,
            "difficulty": self.difficulty,
            "description": self.description,
            "requires_rag": self.requires_rag,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        """Create TestCase from dictionary."""
        # Extract only known fields for ExpectedEntity
        expected = []
        for e in data.get("expected_entities", []):
            if isinstance(e, dict):
                # Filter to only known ExpectedEntity fields
                filtered = {
                    k: v for k, v in e.items()
                    if k in ("text", "entity_type", "start", "end")
                }
                expected.append(ExpectedEntity(**filtered))
            else:
                expected.append(e)
        return cls(
            id=data["id"],
            query=data["query"],
            expected_entities=expected,
            category=data.get("category", "general"),
            difficulty=data.get("difficulty", "medium"),
            description=data.get("description", ""),
            requires_rag=data.get("requires_rag", False),
            tags=data.get("tags", [])
        )


class PIIDetector(ABC):
    """Abstract base class for PII detectors."""

    @abstractmethod
    def detect(self, text: str) -> DetectionResult:
        """
        Detect PII in the given text.

        Args:
            text: The text to analyze

        Returns:
            DetectionResult with detected entities and metadata
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """Return the name of this detector."""
        pass

    @property
    def supported_entities(self) -> List[str]:
        """Return list of entity types this detector supports."""
        return [e.value for e in EntityType]

    def detect_with_timing(self, text: str) -> DetectionResult:
        """Detect with explicit timing measurement."""
        start = time.perf_counter()
        result = self.detect(text)
        elapsed = (time.perf_counter() - start) * 1000

        # Update latency if not already set
        if result.latency_ms == 0:
            result.latency_ms = elapsed

        return result
