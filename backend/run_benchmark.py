#!/usr/bin/env python3
"""
Unified Benchmark Runner

Runs PII detection benchmarks with multiple detectors and generates comparison reports.

Usage:
    python run_benchmark.py --detector presidio --dataset data/golden_set.json
    python run_benchmark.py --detector llama_guard --dataset data/synthetic_dataset.json
    python run_benchmark.py --detector all --dataset data/golden_set.json --compare
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

from detectors.presidio_detector import PresidioDetector
from detectors.llama_guard_detector import LlamaGuardDetector
from detectors.gliner_detector import GLiNERDetector
from detectors.base import PIIDetector
from evaluation.runner import BenchmarkRunner


def get_detector(name: str) -> PIIDetector:
    """Get detector instance by name."""
    if name == "presidio":
        return PresidioDetector()
    elif name == "llama_guard":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            print("Error: OPENROUTER_API_KEY environment variable not set")
            print("Set it with: export OPENROUTER_API_KEY=your_key_here")
            sys.exit(1)
        return LlamaGuardDetector(api_key=api_key)
    elif name == "gliner":
        return GLiNERDetector()
    else:
        raise ValueError(f"Unknown detector: {name}")


def print_progress(current: int, total: int, result):
    """Print progress during benchmark."""
    status = "✅" if result.passed else "❌"
    print(f"  [{current:3d}/{total}] {status} {result.case_id}: {result.query[:50]}...")


def print_summary(result, show_details: bool = True):
    """Print benchmark summary."""
    print("\n" + "=" * 70)
    print(f"BENCHMARK SUMMARY: {result.detector_name.upper()}")
    print("=" * 70)

    print(f"\nDetector: {result.detector_name}")
    print(f"Dataset:  {result.dataset_name}")
    print(f"Time:     {result.timestamp}")

    print(f"\n📊 Overall Results:")
    print(f"   Total Cases:  {result.total_cases}")
    print(f"   Passed:       {result.passed_cases} ({result.passed_cases/result.total_cases*100:.1f}%)")
    print(f"   Failed:       {result.failed_cases}")

    print(f"\n📈 Detection Metrics:")
    print(f"   Precision:    {result.overall_precision*100:.1f}%")
    print(f"   Recall:       {result.overall_recall*100:.1f}%")
    print(f"   F1 Score:     {result.overall_f1*100:.1f}%")
    print(f"   Leakage Rate: {result.leakage_rate*100:.1f}%")

    print(f"\n⏱️  Latency:")
    print(f"   p50:  {result.latency_p50:.1f}ms")
    print(f"   p95:  {result.latency_p95:.1f}ms")
    print(f"   p99:  {result.latency_p99:.1f}ms")
    print(f"   mean: {result.latency_mean:.1f}ms")

    if show_details and result.entity_metrics:
        print(f"\n📋 Per-Entity Metrics:")
        print(f"   {'Entity Type':<20} {'Precision':>10} {'Recall':>10} {'F1':>10} {'TP':>5} {'FP':>5} {'FN':>5}")
        print(f"   {'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*5} {'-'*5} {'-'*5}")

        for etype, metrics in sorted(result.entity_metrics.items()):
            print(f"   {etype:<20} {metrics.precision*100:>9.1f}% {metrics.recall*100:>9.1f}% "
                  f"{metrics.f1_score*100:>9.1f}% {metrics.true_positives:>5} "
                  f"{metrics.false_positives:>5} {metrics.false_negatives:>5}")

    print("=" * 70)


def print_comparison(results: List, runner: BenchmarkRunner):
    """Print comparison between multiple detector results."""
    print("\n" + "=" * 80)
    print("DETECTOR COMPARISON")
    print("=" * 80)

    # Header
    print(f"\n{'Metric':<25}", end="")
    for r in results:
        print(f"{r.detector_name:>18}", end="")
    print()
    print("-" * (25 + 18 * len(results)))

    # Core metrics
    metrics = [
        ("Pass Rate", lambda r: f"{r.passed_cases/r.total_cases*100:.1f}%"),
        ("Precision", lambda r: f"{r.overall_precision*100:.1f}%"),
        ("Recall", lambda r: f"{r.overall_recall*100:.1f}%"),
        ("F1 Score", lambda r: f"{r.overall_f1*100:.1f}%"),
        ("Leakage Rate", lambda r: f"{r.leakage_rate*100:.1f}%"),
        ("Latency (p50)", lambda r: f"{r.latency_p50:.1f}ms"),
        ("Latency (p95)", lambda r: f"{r.latency_p95:.1f}ms"),
        ("Latency (mean)", lambda r: f"{r.latency_mean:.1f}ms"),
    ]

    for name, getter in metrics:
        print(f"{name:<25}", end="")
        for r in results:
            print(f"{getter(r):>18}", end="")
        print()

    # Per-entity comparison
    all_entity_types = set()
    for r in results:
        all_entity_types.update(r.entity_metrics.keys())

    if all_entity_types:
        print(f"\n{'Entity F1 Scores':<25}", end="")
        for r in results:
            print(f"{r.detector_name:>18}", end="")
        print()
        print("-" * (25 + 18 * len(results)))

        for etype in sorted(all_entity_types):
            print(f"{etype:<25}", end="")
            for r in results:
                if etype in r.entity_metrics:
                    f1 = r.entity_metrics[etype].f1_score * 100
                    print(f"{f1:>17.1f}%", end="")
                else:
                    print(f"{'N/A':>18}", end="")
            print()

    # Winner summary
    print("\n" + "-" * 80)
    print("WINNER BY METRIC:")
    print("-" * 80)

    metric_comparisons = [
        ("Highest F1 Score", lambda r: r.overall_f1, True),
        ("Lowest Leakage Rate", lambda r: r.leakage_rate, False),
        ("Best Precision", lambda r: r.overall_precision, True),
        ("Best Recall", lambda r: r.overall_recall, True),
        ("Fastest (p50)", lambda r: r.latency_p50, False),
    ]

    for name, getter, higher_is_better in metric_comparisons:
        if higher_is_better:
            winner = max(results, key=getter)
        else:
            winner = min(results, key=getter)
        value = getter(winner)
        if "Latency" in name or "Fastest" in name:
            value_str = f"{value:.1f}ms"
        elif "Leakage" in name:
            value_str = f"{value*100:.1f}%"
        else:
            value_str = f"{value*100:.1f}%"
        print(f"  {name:<25} {winner.detector_name:<15} ({value_str})")

    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Run PII detection benchmarks")
    parser.add_argument(
        "--detector",
        type=str,
        choices=["presidio", "llama_guard", "gliner", "all"],
        default="presidio",
        help="Detector to benchmark (default: presidio)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/golden_set.json",
        help="Path to test dataset JSON file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save results (default: auto-generated)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run comparison mode (when --detector=all)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of test cases (useful for testing)"
    )

    args = parser.parse_args()

    # Check dataset exists
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset not found: {dataset_path}")
        sys.exit(1)

    runner = BenchmarkRunner()
    results = []

    # Determine which detectors to run
    if args.detector == "all":
        detector_names = ["presidio", "gliner", "llama_guard"]
    else:
        detector_names = [args.detector]

    # Load test cases once
    print(f"Loading test cases from {dataset_path}...")
    test_cases = runner.load_test_cases(str(dataset_path))

    if args.limit:
        test_cases = test_cases[:args.limit]

    print(f"Loaded {len(test_cases)} test cases\n")

    # Run benchmarks
    for detector_name in detector_names:
        print(f"\n{'='*70}")
        print(f"Running benchmark with {detector_name.upper()} detector...")
        print(f"{'='*70}\n")

        try:
            detector = get_detector(detector_name)
        except Exception as e:
            print(f"Error initializing {detector_name}: {e}")
            continue

        progress_cb = None if args.quiet else print_progress

        result = runner.run_benchmark(
            detector=detector,
            test_cases=test_cases,
            dataset_name=dataset_path.stem,
            progress_callback=progress_cb
        )

        results.append(result)

        # Save individual result
        saved_path = runner.save_result(result)
        print(f"\n💾 Results saved to: {saved_path}")

        # Print summary
        print_summary(result, show_details=not args.compare)

        # Clean up if needed
        if hasattr(detector, 'close'):
            detector.close()

    # Print comparison if multiple detectors
    if len(results) > 1 and args.compare:
        print_comparison(results, runner)

        # Save comparison
        comparison = runner.compare_results(results[0], results[1])
        comparison_path = Path("data/benchmark_results") / f"comparison_{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.json"
        comparison_path.parent.mkdir(parents=True, exist_ok=True)
        with open(comparison_path, 'w') as f:
            json.dump(comparison, f, indent=2)
        print(f"\n📊 Comparison saved to: {comparison_path}")


if __name__ == "__main__":
    main()
