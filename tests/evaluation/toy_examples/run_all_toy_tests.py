#!/usr/bin/env python3
"""
Sequential test runner for toy examples.

Runs each test in isolation to avoid pytest-asyncio event loop conflicts.
Captures all results and generates a summary report.

Usage:
    python tests/evaluation/toy_examples/run_all_toy_tests.py
    python tests/evaluation/toy_examples/run_all_toy_tests.py --include-slow
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import argparse


def run_test(test_name: str) -> dict:
    """Run a single test and capture results."""
    print(f"\n{'='*60}")
    print(f"Running: {test_name}")
    print(f"{'='*60}")

    cmd = [
        "pytest",
        f"tests/evaluation/toy_examples/test_toy_evaluation.py::{test_name}",
        "-v",
        "--tb=short",
    ]

    start = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = (datetime.now() - start).total_seconds()

    # Parse result
    passed = result.returncode == 0
    output = result.stdout + result.stderr

    # Extract key info
    if passed:
        print(f"✅ PASSED in {duration:.2f}s")
    else:
        print(f"❌ FAILED in {duration:.2f}s")
        # Show last 20 lines of error
        error_lines = output.split('\n')[-20:]
        print("\n".join(error_lines))

    return {
        "test": test_name,
        "passed": passed,
        "duration": duration,
        "returncode": result.returncode,
        "output_lines": len(output.split('\n')),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run all toy evaluation tests sequentially")
    parser.add_argument("--include-slow", action="store_true",
                        help="Include slow tests (LLM judging)")
    parser.add_argument(
        "--output", default="toy_test_results.json", help="Output file for results")
    args = parser.parse_args()

    # Define test suite
    fast_tests = [
        "test_simple_greeting",
        "test_tool_trajectory",
        "test_response_similarity",
    ]

    slow_tests = [
        "test_rubric_quality",
        "test_comprehensive",
    ]

    tests = fast_tests + (slow_tests if args.include_slow else [])

    print(f"🧪 Running {len(tests)} toy evaluation tests sequentially")
    print(f"📊 Results will be saved to: {args.output}")

    # Run all tests
    results = []
    for test_name in tests:
        result = run_test(test_name)
        results.append(result)

    # Generate summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    total_duration = sum(r["duration"] for r in results)

    print(f"\nTotal: {len(results)} tests")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total time: {total_duration:.2f}s")
    print(f"⏱️  Average time: {total_duration/len(results):.2f}s per test")

    # Detailed results
    print(f"\nDetailed Results:")
    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"  {status} {r['test']:30s} ({r['duration']:5.2f}s)")

    # Save results
    output_path = Path(args.output)
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed": passed,
        "failed": failed,
        "total_duration": total_duration,
        "include_slow": args.include_slow,
        "results": results,
    }

    output_path.write_text(json.dumps(report, indent=2))
    print(f"\n📄 Full results saved to: {output_path}")

    # Exit with error if any failed
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
