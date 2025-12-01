#!/usr/bin/env python3
"""
Baseline Benchmark Runner

Runs the current test scenarios against the Presidio detector
and generates baseline metrics for comparison.

Usage:
    python run_baseline.py
    python run_baseline.py --dataset data/test_scenarios.json
    python run_baseline.py --output results/baseline.json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from detectors.presidio_detector import PresidioDetector
from evaluation.runner import BenchmarkRunner


def print_progress(current: int, total: int, result):
    """Print progress during benchmark."""
    status = "✅" if result.passed else "❌"
    print(f"  [{current:3d}/{total}] {status} {result.case_id}: {result.query[:50]}...")


def print_summary(result):
    """Print benchmark summary."""
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

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

    if result.entity_metrics:
        print(f"\n📋 Per-Entity Metrics:")
        print(f"   {'Entity Type':<20} {'Precision':>10} {'Recall':>10} {'F1':>10} {'TP':>5} {'FP':>5} {'FN':>5}")
        print(f"   {'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*5} {'-'*5} {'-'*5}")

        for etype, metrics in sorted(result.entity_metrics.items()):
            print(f"   {etype:<20} {metrics.precision*100:>9.1f}% {metrics.recall*100:>9.1f}% {metrics.f1_score*100:>9.1f}% {metrics.true_positives:>5} {metrics.false_positives:>5} {metrics.false_negatives:>5}")

    # Show failed cases
    failed = [r for r in result.test_results if not r.passed]
    if failed:
        print(f"\n❌ Failed Cases ({len(failed)}):")
        for r in failed[:10]:  # Show first 10
            print(f"   {r.case_id}: {r.query[:60]}...")
            if r.false_negatives:
                missed = [f"{e.entity_type}({e.text})" for e in r.false_negatives]
                print(f"      Missed: {', '.join(missed)}")
        if len(failed) > 10:
            print(f"   ... and {len(failed)-10} more")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run PII detection baseline benchmark")
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/test_scenarios.json",
        help="Path to test dataset JSON file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save results (default: auto-generated in data/benchmark_results/)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output only JSON result (for piping)"
    )

    args = parser.parse_args()

    # Check dataset exists
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset not found: {dataset_path}")
        sys.exit(1)

    # Initialize
    detector = PresidioDetector()
    runner = BenchmarkRunner()

    # Load test cases
    if not args.json_only:
        print(f"Loading test cases from {dataset_path}...")
    test_cases = runner.load_test_cases(str(dataset_path))

    if not args.json_only:
        print(f"Loaded {len(test_cases)} test cases")
        print(f"\nRunning benchmark with {detector.name()} detector...\n")

    # Run benchmark
    progress_cb = None if args.quiet or args.json_only else print_progress

    result = runner.run_benchmark(
        detector=detector,
        test_cases=test_cases,
        dataset_name=dataset_path.stem,
        progress_callback=progress_cb
    )

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        saved_path = str(output_path)
    else:
        saved_path = runner.save_result(result)

    # Output
    if args.json_only:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print_summary(result)
        print(f"\n💾 Results saved to: {saved_path}")


if __name__ == "__main__":
    main()
