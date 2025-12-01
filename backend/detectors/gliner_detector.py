"""
GLiNER-based PII detector.
Uses the GLiNER transformer model for zero-shot NER-based PII detection.
"""

import time
from typing import List, Dict, Any, Optional

from detectors.base import PIIDetector, DetectedEntity, DetectionResult


class GLiNERDetector(PIIDetector):
    """
    PII detector using GLiNER (Generalist and Lightweight Named Entity Recognition).

    Uses a transformer-based model for zero-shot entity recognition.
    Runs locally, no API calls required.

    Available models:
    - urchade/gliner_multi_pii-v1 (general PII)
    - knowledgator/gliner-pii-base-v1.0 (highest F1: 80.99%)
    - knowledgator/gliner-pii-edge-v1.0 (optimized for speed)
    """

    # Map GLiNER entity labels to our standard entity types
    ENTITY_MAPPING = {
        # Person names
        "person": "PERSON",
        "name": "PERSON",
        "full name": "PERSON",
        "first name": "PERSON",
        "last name": "PERSON",

        # Contact info
        "email": "EMAIL_ADDRESS",
        "email address": "EMAIL_ADDRESS",
        "phone number": "PHONE_NUMBER",
        "phone": "PHONE_NUMBER",
        "mobile phone number": "PHONE_NUMBER",

        # Financial
        "credit card number": "CREDIT_CARD",
        "credit card": "CREDIT_CARD",
        "bank account number": "US_BANK_NUMBER",
        "bank account": "US_BANK_NUMBER",
        "iban": "IBAN_CODE",

        # Government IDs
        "social security number": "US_SSN",
        "ssn": "US_SSN",
        "passport number": "PASSPORT",
        "driver's license number": "DRIVERS_LICENSE",
        "driver license": "DRIVERS_LICENSE",
        "tax identification number": "TAX_ID",

        # Dates/Times
        "date of birth": "DATE_TIME",
        "date": "DATE_TIME",
        "dob": "DATE_TIME",

        # Locations
        "address": "LOCATION",
        "location": "LOCATION",
        "city": "LOCATION",
        "country": "LOCATION",
        "zip code": "LOCATION",

        # Other
        "ip address": "IP_ADDRESS",
        "username": "USERNAME",
        "password": "PASSWORD",
        "organization": "ORGANIZATION",
        "company": "ORGANIZATION",
    }

    # Labels to request from GLiNER
    PII_LABELS = [
        "person",
        "email address",
        "phone number",
        "credit card number",
        "social security number",
        "date of birth",
        "address",
        "bank account number",
        "passport number",
        "driver's license number",
        "ip address",
        "organization",
    ]

    SUPPORTED_ENTITIES = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "CREDIT_CARD",
        "US_SSN",
        "DATE_TIME",
        "LOCATION",
        "US_BANK_NUMBER",
        "PASSPORT",
        "DRIVERS_LICENSE",
        "IP_ADDRESS",
        "ORGANIZATION",
    ]

    def __init__(
        self,
        model_name: str = "urchade/gliner_multi_pii-v1",
        threshold: float = 0.4,
        device: Optional[str] = None
    ):
        """
        Initialize GLiNER detector.

        Args:
            model_name: HuggingFace model ID for GLiNER
            threshold: Confidence threshold for entity detection (0.0-1.0)
            device: Device to run on ('cpu', 'cuda', 'mps'). Auto-detected if None.
        """
        self.model_name = model_name
        self.threshold = threshold
        self._model = None
        self._device = device

    def _get_model(self):
        """Lazy load the GLiNER model."""
        if self._model is None:
            try:
                from gliner import GLiNER

                # Auto-detect device if not specified
                if self._device is None:
                    import torch
                    if torch.cuda.is_available():
                        self._device = "cuda"
                    elif torch.backends.mps.is_available():
                        self._device = "mps"
                    else:
                        self._device = "cpu"

                print(f"Loading GLiNER model: {self.model_name} on {self._device}")
                self._model = GLiNER.from_pretrained(self.model_name)
                self._model = self._model.to(self._device)
                print(f"GLiNER model loaded successfully")

            except Exception as e:
                raise RuntimeError(f"Failed to load GLiNER model: {e}")

        return self._model

    def name(self) -> str:
        return "gliner"

    def detect(self, text: str) -> DetectionResult:
        """
        Detect PII entities in text using GLiNER.

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with all detected entities
        """
        start_time = time.perf_counter()

        try:
            model = self._get_model()

            # Run prediction
            predictions = model.predict_entities(
                text,
                self.PII_LABELS,
                threshold=self.threshold
            )

            entities = []
            for pred in predictions:
                # Map GLiNER label to our standard entity type
                gliner_label = pred["label"].lower()
                entity_type = self.ENTITY_MAPPING.get(gliner_label, gliner_label.upper())

                entities.append(DetectedEntity(
                    text=pred["text"],
                    entity_type=entity_type,
                    start=pred["start"],
                    end=pred["end"],
                    confidence=pred["score"],
                    source="gliner"
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
                    "entity_types": list(set(e.entity_type for e in entities)),
                    "model": self.model_name,
                    "threshold": self.threshold
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

    def close(self):
        """Release model resources."""
        if self._model is not None:
            del self._model
            self._model = None

            # Clear CUDA cache if applicable
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
