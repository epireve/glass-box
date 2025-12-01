"""
Evaluation metrics for PII detection benchmarking.
Calculates precision, recall, F1, and other metrics per entity type and overall.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
import statistics

from detectors.base import DetectedEntity, ExpectedEntity, DetectionResult, TestCase


@dataclass
class EntityMetrics:
    """Metrics for a single entity type."""
    entity_type: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    total_expected: int = 0
    total_detected: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    latencies_ms: List[float] = field(default_factory=list)

    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP)"""
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN)"""
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1_score(self) -> float:
        """F1 = 2 * (P * R) / (P + R)"""
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    @property
    def avg_confidence(self) -> float:
        if not self.confidence_scores:
            return 0.0
        return statistics.mean(self.confidence_scores)

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.mean(self.latencies_ms)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "total_expected": self.total_expected,
            "total_detected": self.total_detected,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2)
        }


@dataclass
class TestCaseResult:
    """Result of running a single test case."""
    case_id: str
    query: str
    detected_entities: List[DetectedEntity]
    expected_entities: List[ExpectedEntity]
    true_positives: List[Tuple[DetectedEntity, ExpectedEntity]]
    false_positives: List[DetectedEntity]
    false_negatives: List[ExpectedEntity]
    latency_ms: float
    passed: bool
    error: Optional[str] = None

    @property
    def precision(self) -> float:
        tp = len(self.true_positives)
        fp = len(self.false_positives)
        if tp + fp == 0:
            return 1.0 if len(self.expected_entities) == 0 else 0.0
        return tp / (tp + fp)

    @property
    def recall(self) -> float:
        tp = len(self.true_positives)
        fn = len(self.false_negatives)
        if tp + fn == 0:
            return 1.0
        return tp / (tp + fn)

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "query": self.query,
            "detected_entities": [e.to_dict() for e in self.detected_entities],
            "expected_entities": [e.to_dict() for e in self.expected_entities],
            "true_positives": [
                {"detected": d.to_dict(), "expected": e.to_dict()}
                for d, e in self.true_positives
            ],
            "false_positives": [e.to_dict() for e in self.false_positives],
            "false_negatives": [e.to_dict() for e in self.false_negatives],
            "latency_ms": round(self.latency_ms, 2),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "passed": self.passed,
            "error": self.error
        }


@dataclass
class BenchmarkResult:
    """Complete benchmark results."""
    detector_name: str
    dataset_name: str
    timestamp: str
    total_cases: int
    passed_cases: int
    failed_cases: int

    # Overall metrics
    overall_precision: float
    overall_recall: float
    overall_f1: float
    leakage_rate: float  # FN / (TP + FN) - PII that slipped through
    false_refusal_rate: float  # FP / total_safe_queries

    # Per-entity metrics
    entity_metrics: Dict[str, EntityMetrics]

    # Latency distribution
    latency_p50: float
    latency_p95: float
    latency_p99: float
    latency_mean: float

    # Confidence distribution (10 buckets: 0-0.1, 0.1-0.2, ...)
    confidence_histogram: List[int]

    # Individual test results
    test_results: List[TestCaseResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detector_name": self.detector_name,
            "dataset_name": self.dataset_name,
            "timestamp": self.timestamp,
            "summary": {
                "total_cases": self.total_cases,
                "passed_cases": self.passed_cases,
                "failed_cases": self.failed_cases,
                "pass_rate": round(self.passed_cases / max(self.total_cases, 1), 4)
            },
            "overall_metrics": {
                "precision": round(self.overall_precision, 4),
                "recall": round(self.overall_recall, 4),
                "f1_score": round(self.overall_f1, 4),
                "leakage_rate": round(self.leakage_rate, 4),
                "false_refusal_rate": round(self.false_refusal_rate, 4)
            },
            "latency": {
                "p50_ms": round(self.latency_p50, 2),
                "p95_ms": round(self.latency_p95, 2),
                "p99_ms": round(self.latency_p99, 2),
                "mean_ms": round(self.latency_mean, 2)
            },
            "entity_metrics": {
                k: v.to_dict() for k, v in self.entity_metrics.items()
            },
            "confidence_histogram": self.confidence_histogram,
            "test_results": [r.to_dict() for r in self.test_results]
        }


class MetricsCalculator:
    """Calculates evaluation metrics from detection results."""

    def __init__(self, overlap_threshold: float = 0.5):
        """
        Args:
            overlap_threshold: Minimum overlap ratio to consider a match
        """
        self.overlap_threshold = overlap_threshold

    def compare_entities(
        self,
        detected: List[DetectedEntity],
        expected: List[ExpectedEntity]
    ) -> Tuple[List[Tuple[DetectedEntity, ExpectedEntity]], List[DetectedEntity], List[ExpectedEntity]]:
        """
        Compare detected entities against expected ground truth.

        Uses position-based matching with type checking.

        Returns:
            Tuple of (true_positives, false_positives, false_negatives)
        """
        true_positives = []
        false_positives = list(detected)
        false_negatives = list(expected)

        # Match detected to expected
        for det in detected:
            best_match = None
            best_overlap = 0

            for exp in false_negatives:
                # Must be same entity type
                if det.entity_type != exp.entity_type:
                    continue

                # Calculate overlap
                if det.start >= exp.end or exp.start >= det.end:
                    continue

                overlap_start = max(det.start, exp.start)
                overlap_end = min(det.end, exp.end)
                overlap_len = overlap_end - overlap_start

                min_len = min(det.end - det.start, exp.end - exp.start)
                overlap_ratio = overlap_len / min_len

                if overlap_ratio >= self.overlap_threshold and overlap_ratio > best_overlap:
                    best_match = exp
                    best_overlap = overlap_ratio

            if best_match:
                true_positives.append((det, best_match))
                false_positives.remove(det)
                false_negatives.remove(best_match)

        return true_positives, false_positives, false_negatives

    def evaluate_test_case(
        self,
        test_case: TestCase,
        result: DetectionResult
    ) -> TestCaseResult:
        """Evaluate a single test case."""
        tp, fp, fn = self.compare_entities(
            result.entities,
            test_case.expected_entities
        )

        # A test passes if recall is 100% (no false negatives)
        passed = len(fn) == 0

        return TestCaseResult(
            case_id=test_case.id,
            query=test_case.query,
            detected_entities=result.entities,
            expected_entities=test_case.expected_entities,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            latency_ms=result.latency_ms,
            passed=passed,
            error=result.error
        )

    def aggregate_results(
        self,
        test_results: List[TestCaseResult],
        detector_name: str,
        dataset_name: str,
        timestamp: str
    ) -> BenchmarkResult:
        """Aggregate individual test results into benchmark summary."""

        # Count totals
        total_tp = 0
        total_fp = 0
        total_fn = 0

        # Per-entity metrics
        entity_metrics: Dict[str, EntityMetrics] = defaultdict(
            lambda: EntityMetrics(entity_type="")
        )

        # Collect all latencies and confidences
        all_latencies = []
        all_confidences = []

        passed_cases = 0
        safe_queries = 0  # Queries with no expected PII
        false_refusals = 0  # Safe queries that got false positives

        for result in test_results:
            if result.passed:
                passed_cases += 1

            all_latencies.append(result.latency_ms)

            # Track safe queries and false refusals
            if len(result.expected_entities) == 0:
                safe_queries += 1
                if len(result.false_positives) > 0:
                    false_refusals += 1

            # Aggregate by entity type
            for det, exp in result.true_positives:
                total_tp += 1
                etype = det.entity_type
                if entity_metrics[etype].entity_type == "":
                    entity_metrics[etype].entity_type = etype
                entity_metrics[etype].true_positives += 1
                entity_metrics[etype].confidence_scores.append(det.confidence)
                entity_metrics[etype].latencies_ms.append(result.latency_ms)
                all_confidences.append(det.confidence)

            for det in result.false_positives:
                total_fp += 1
                etype = det.entity_type
                if entity_metrics[etype].entity_type == "":
                    entity_metrics[etype].entity_type = etype
                entity_metrics[etype].false_positives += 1
                all_confidences.append(det.confidence)

            for exp in result.false_negatives:
                total_fn += 1
                etype = exp.entity_type
                if entity_metrics[etype].entity_type == "":
                    entity_metrics[etype].entity_type = etype
                entity_metrics[etype].false_negatives += 1

            # Count expected per type
            for exp in result.expected_entities:
                etype = exp.entity_type
                if entity_metrics[etype].entity_type == "":
                    entity_metrics[etype].entity_type = etype
                entity_metrics[etype].total_expected += 1

            # Count detected per type
            for det in result.detected_entities:
                etype = det.entity_type
                if entity_metrics[etype].entity_type == "":
                    entity_metrics[etype].entity_type = etype
                entity_metrics[etype].total_detected += 1

        # Calculate overall metrics
        overall_precision = total_tp / max(total_tp + total_fp, 1)
        overall_recall = total_tp / max(total_tp + total_fn, 1)
        overall_f1 = (
            2 * overall_precision * overall_recall /
            max(overall_precision + overall_recall, 0.0001)
        )
        leakage_rate = total_fn / max(total_tp + total_fn, 1)
        false_refusal_rate = false_refusals / max(safe_queries, 1)

        # Calculate latency percentiles
        sorted_latencies = sorted(all_latencies) if all_latencies else [0]

        def percentile(data: List[float], p: int) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * (p / 100)
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f])

        # Build confidence histogram (10 buckets)
        confidence_histogram = [0] * 10
        for conf in all_confidences:
            bucket = min(int(conf * 10), 9)
            confidence_histogram[bucket] += 1

        return BenchmarkResult(
            detector_name=detector_name,
            dataset_name=dataset_name,
            timestamp=timestamp,
            total_cases=len(test_results),
            passed_cases=passed_cases,
            failed_cases=len(test_results) - passed_cases,
            overall_precision=overall_precision,
            overall_recall=overall_recall,
            overall_f1=overall_f1,
            leakage_rate=leakage_rate,
            false_refusal_rate=false_refusal_rate,
            entity_metrics=dict(entity_metrics),
            latency_p50=percentile(sorted_latencies, 50),
            latency_p95=percentile(sorted_latencies, 95),
            latency_p99=percentile(sorted_latencies, 99),
            latency_mean=statistics.mean(all_latencies) if all_latencies else 0,
            confidence_histogram=confidence_histogram,
            test_results=test_results
        )
