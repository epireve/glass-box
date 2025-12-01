"""
Benchmark runner for PII detection evaluation.
Executes test cases against detectors and generates results.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator, Callable

from detectors.base import PIIDetector, TestCase, ExpectedEntity
from evaluation.metrics import MetricsCalculator, TestCaseResult, BenchmarkResult


class BenchmarkRunner:
    """Runs benchmarks against PII detectors."""

    def __init__(
        self,
        results_dir: str = "data/benchmark_results/runs",
        overlap_threshold: float = 0.5
    ):
        """
        Args:
            results_dir: Directory to save benchmark results
            overlap_threshold: Minimum overlap for entity matching
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_calc = MetricsCalculator(overlap_threshold)

    def load_test_cases(self, dataset_path: str) -> List[TestCase]:
        """
        Load test cases from a JSON file.

        Supports both old format (expected_pii as list of types) and
        new format (expected_entities with positions).
        """
        with open(dataset_path, 'r') as f:
            data = json.load(f)

        test_cases = []

        # Handle scenarios format (old) or test_cases format (new)
        items = data.get("test_cases", data.get("scenarios", []))

        for item in items:
            # Check if using new format with expected_entities
            if "expected_entities" in item:
                test_cases.append(TestCase.from_dict(item))
            else:
                # Convert old format: expected_pii is just a list of types
                # We need to extract actual positions from the text
                expected_entities = self._extract_expected_entities(
                    item.get("prompt", item.get("query", "")),
                    item.get("expected_pii", [])
                )

                test_cases.append(TestCase(
                    id=item.get("id", f"TC-{len(test_cases)+1:03d}"),
                    query=item.get("prompt", item.get("query", "")),
                    expected_entities=expected_entities,
                    category=item.get("category", "general"),
                    difficulty=item.get("difficulty", "medium"),
                    description=item.get("description", ""),
                    requires_rag=item.get("requires_rag", False),
                    tags=item.get("tags", [])
                ))

        return test_cases

    def _extract_expected_entities(
        self,
        text: str,
        expected_types: List[str]
    ) -> List[ExpectedEntity]:
        """
        Extract entity positions from text based on expected types.

        This is a helper for converting old format test cases.
        Uses heuristics to find likely entity spans.
        """
        # For accurate evaluation, test cases should use the new format
        # with explicit positions. This is a best-effort conversion.
        entities = []

        # Import Presidio to help identify positions
        try:
            from presidio_analyzer import AnalyzerEngine
            analyzer = AnalyzerEngine()

            results = analyzer.analyze(
                text=text,
                entities=expected_types,
                language="en"
            )

            # Match results to expected types
            type_counts: Dict[str, int] = {}
            for expected_type in expected_types:
                type_counts[expected_type] = type_counts.get(expected_type, 0) + 1

            for result in sorted(results, key=lambda x: x.start):
                if type_counts.get(result.entity_type, 0) > 0:
                    entities.append(ExpectedEntity(
                        text=text[result.start:result.end],
                        entity_type=result.entity_type,
                        start=result.start,
                        end=result.end
                    ))
                    type_counts[result.entity_type] -= 1

        except Exception:
            # If Presidio fails, create placeholder entities
            for i, etype in enumerate(expected_types):
                entities.append(ExpectedEntity(
                    text=f"[{etype}]",
                    entity_type=etype,
                    start=-1,  # Unknown position
                    end=-1
                ))

        return entities

    def run_single_case(
        self,
        detector: PIIDetector,
        test_case: TestCase
    ) -> TestCaseResult:
        """Run a single test case against a detector."""
        result = detector.detect_with_timing(test_case.query)
        return self.metrics_calc.evaluate_test_case(test_case, result)

    def run_benchmark(
        self,
        detector: PIIDetector,
        test_cases: List[TestCase],
        dataset_name: str = "custom",
        progress_callback: Optional[Callable[[int, int, TestCaseResult], None]] = None
    ) -> BenchmarkResult:
        """
        Run full benchmark against a detector.

        Args:
            detector: The PII detector to evaluate
            test_cases: List of test cases to run
            dataset_name: Name of the dataset for reporting
            progress_callback: Optional callback(current, total, result) for progress updates

        Returns:
            BenchmarkResult with all metrics
        """
        test_results = []
        total = len(test_cases)

        for i, test_case in enumerate(test_cases):
            result = self.run_single_case(detector, test_case)
            test_results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, result)

        timestamp = datetime.now().isoformat()

        benchmark_result = self.metrics_calc.aggregate_results(
            test_results=test_results,
            detector_name=detector.name(),
            dataset_name=dataset_name,
            timestamp=timestamp
        )

        return benchmark_result

    def run_benchmark_streaming(
        self,
        detector: PIIDetector,
        test_cases: List[TestCase],
        dataset_name: str = "custom"
    ) -> Generator[Dict[str, Any], None, BenchmarkResult]:
        """
        Run benchmark with streaming results.

        Yields progress updates and individual results.
        Returns final BenchmarkResult.
        """
        test_results = []
        total = len(test_cases)

        for i, test_case in enumerate(test_cases):
            result = self.run_single_case(detector, test_case)
            test_results.append(result)

            yield {
                "type": "progress",
                "current": i + 1,
                "total": total,
                "percentage": (i + 1) / total * 100,
                "result": result.to_dict()
            }

        timestamp = datetime.now().isoformat()

        benchmark_result = self.metrics_calc.aggregate_results(
            test_results=test_results,
            detector_name=detector.name(),
            dataset_name=dataset_name,
            timestamp=timestamp
        )

        yield {
            "type": "complete",
            "benchmark": benchmark_result.to_dict()
        }

        return benchmark_result

    def save_result(self, result: BenchmarkResult) -> str:
        """Save benchmark result to JSON file."""
        filename = f"{result.timestamp.replace(':', '-')}_{result.detector_name}_{result.dataset_name}.json"
        filepath = self.results_dir / filename

        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        # Update index
        self._update_index(result, filename)

        return str(filepath)

    def _update_index(self, result: BenchmarkResult, filename: str):
        """Update the results index file."""
        index_path = self.results_dir.parent / "index.json"

        if index_path.exists():
            with open(index_path, 'r') as f:
                index = json.load(f)
        else:
            index = {"runs": []}

        index["runs"].append({
            "filename": filename,
            "detector": result.detector_name,
            "dataset": result.dataset_name,
            "timestamp": result.timestamp,
            "summary": {
                "precision": round(result.overall_precision, 4),
                "recall": round(result.overall_recall, 4),
                "f1": round(result.overall_f1, 4),
                "total_cases": result.total_cases,
                "passed_cases": result.passed_cases
            }
        })

        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)

    def load_result(self, filename: str) -> Dict[str, Any]:
        """Load a saved benchmark result."""
        filepath = self.results_dir / filename
        with open(filepath, 'r') as f:
            return json.load(f)

    def list_results(self) -> List[Dict[str, Any]]:
        """List all saved benchmark results."""
        index_path = self.results_dir.parent / "index.json"

        if index_path.exists():
            with open(index_path, 'r') as f:
                return json.load(f).get("runs", [])

        return []

    def compare_results(
        self,
        result1: BenchmarkResult,
        result2: BenchmarkResult
    ) -> Dict[str, Any]:
        """Compare two benchmark results."""
        comparison = {
            "detector1": result1.detector_name,
            "detector2": result2.detector_name,
            "dataset1": result1.dataset_name,
            "dataset2": result2.dataset_name,
            "overall": {
                "precision": {
                    "detector1": result1.overall_precision,
                    "detector2": result2.overall_precision,
                    "diff": result2.overall_precision - result1.overall_precision,
                    "winner": result1.detector_name if result1.overall_precision > result2.overall_precision else result2.detector_name
                },
                "recall": {
                    "detector1": result1.overall_recall,
                    "detector2": result2.overall_recall,
                    "diff": result2.overall_recall - result1.overall_recall,
                    "winner": result1.detector_name if result1.overall_recall > result2.overall_recall else result2.detector_name
                },
                "f1": {
                    "detector1": result1.overall_f1,
                    "detector2": result2.overall_f1,
                    "diff": result2.overall_f1 - result1.overall_f1,
                    "winner": result1.detector_name if result1.overall_f1 > result2.overall_f1 else result2.detector_name
                },
                "latency_p50": {
                    "detector1": result1.latency_p50,
                    "detector2": result2.latency_p50,
                    "diff": result2.latency_p50 - result1.latency_p50,
                    "winner": result1.detector_name if result1.latency_p50 < result2.latency_p50 else result2.detector_name
                },
                "leakage_rate": {
                    "detector1": result1.leakage_rate,
                    "detector2": result2.leakage_rate,
                    "diff": result2.leakage_rate - result1.leakage_rate,
                    "winner": result1.detector_name if result1.leakage_rate < result2.leakage_rate else result2.detector_name
                }
            },
            "by_entity_type": {}
        }

        # Compare per entity type
        all_types = set(result1.entity_metrics.keys()) | set(result2.entity_metrics.keys())

        for etype in all_types:
            m1 = result1.entity_metrics.get(etype)
            m2 = result2.entity_metrics.get(etype)

            comparison["by_entity_type"][etype] = {
                "f1": {
                    "detector1": m1.f1_score if m1 else 0,
                    "detector2": m2.f1_score if m2 else 0,
                    "winner": (
                        result1.detector_name
                        if (m1 and m2 and m1.f1_score > m2.f1_score)
                        else result2.detector_name
                    )
                }
            }

        return comparison
