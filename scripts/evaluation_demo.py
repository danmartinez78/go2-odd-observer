#!/usr/bin/env python3
"""
Demo script for LLM-as-judge evaluation framework.

This demonstrates how to evaluate agent outputs using the LLM-as-judge
pattern with majority voting and custom rubrics.
"""

import json
from pathlib import Path

from odd_agents.evaluation import (
    LLMJudge,
    EvaluationReporter,
    PERCEPTION_RUBRICS,
    MOTION_RUBRICS,
    COLLISION_RUBRICS,
)


def main():
    print("=" * 70)
    print("LLM-AS-JUDGE EVALUATION DEMO")
    print("=" * 70)
    print("\nThis demo shows how to use LLM-as-judge evaluation to assess")
    print("agent output quality using a more capable model (gemini-2.5-pro)")
    print("to avoid model similarity bias.\n")

    # Sample outputs (from test fixtures)
    perception_output = {
        "environment_type": "indoor",
        "lighting": "moderate",
        "obstacles": {
            "count": 12,
            "types": ["furniture", "walls", "decorative items"],
            "density": 0.45,
        },
        "terrain_type": "smooth",
        "traversability_score": 0.72,
        "summary": (
            "Indoor office environment with moderate lighting. "
            "Moderate obstacle density (12 objects, density=0.45) from furniture "
            "and walls. Smooth floor with good traversability (0.72)."
        ),
    }

    motion_output = {
        "velocity": {
            "mean": 0.05,
            "max": 0.12,
            "variance": 0.001,
        },
        "rotation": {
            "mean": 2.1,
            "max": 8.3,
            "variance": 3.2,
        },
        "platform_stability": 0.92,
        "summary": (
            "Robot is predominantly stationary with minimal translation "
            "(mean velocity 0.05 m/s, max 0.12 m/s). Small rotational adjustments "
            "observed (mean 2.1 deg/s). Platform is highly stable (0.92)."
        ),
    }

    collision_output = {
        "collision_risk": 0.38,
        "closest_obstacle_distance": 0.85,
        "risk_factors": [
            "Moderate obstacle density (0.45)",
            "Closest obstacle at 0.85m (within 1m threshold)",
        ],
        "summary": (
            "Low-moderate collision risk (0.38). Robot positioned in close "
            "proximity to static obstacles (closest at 0.85m). Low velocity "
            "reduces immediate risk. Recommend maintaining current speed and "
            "monitoring obstacle proximity."
        ),
    }

    # Initialize reporter
    reporter = EvaluationReporter()

    # Evaluate Perception Agent
    print("\n" + "-" * 70)
    print("Evaluating Perception Agent...")
    print("-" * 70)

    perception_judge = LLMJudge(
        agent_type="perception",
        rubrics=PERCEPTION_RUBRICS,
        num_samples=3,  # Reduced for demo speed
    )

    perception_result = perception_judge.evaluate(
        agent_output=perception_output,
        reference_output=perception_output,  # Perfect match for demo
    )

    reporter.add_result(perception_result)

    print(f"Overall Score: {perception_result.overall_score:.2f}")
    print(f"Passed: {perception_result.passed}\n")
    print("Rubric Scores:")
    for rs in perception_result.rubric_scores:
        status = "✓" if rs.passed else "✗"
        print(f"  {status} {rs.rubric_id:30s} {rs.score:.2f}")

    # Evaluate Motion Agent
    print("\n" + "-" * 70)
    print("Evaluating Motion Agent...")
    print("-" * 70)

    motion_judge = LLMJudge(
        agent_type="motion",
        rubrics=MOTION_RUBRICS,
        num_samples=3,
    )

    motion_result = motion_judge.evaluate(
        agent_output=motion_output,
        reference_output=motion_output,
    )

    reporter.add_result(motion_result)

    print(f"Overall Score: {motion_result.overall_score:.2f}")
    print(f"Passed: {motion_result.passed}\n")
    print("Rubric Scores:")
    for rs in motion_result.rubric_scores:
        status = "✓" if rs.passed else "✗"
        print(f"  {status} {rs.rubric_id:30s} {rs.score:.2f}")

    # Evaluate Collision Agent (with context)
    print("\n" + "-" * 70)
    print("Evaluating Collision Agent (with multimodal context)...")
    print("-" * 70)

    collision_judge = LLMJudge(
        agent_type="collision",
        rubrics=COLLISION_RUBRICS,
        num_samples=3,
    )

    collision_result = collision_judge.evaluate(
        agent_output=collision_output,
        reference_output=collision_output,
        context={
            "perception": perception_output,
            "motion": motion_output,
        },
    )

    reporter.add_result(collision_result)

    print(f"Overall Score: {collision_result.overall_score:.2f}")
    print(f"Passed: {collision_result.passed}\n")
    print("Rubric Scores:")
    for rs in collision_result.rubric_scores:
        status = "✓" if rs.passed else "✗"
        print(f"  {status} {rs.rubric_id:30s} {rs.score:.2f}")

    # Generate Summary Report
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    reporter.print_summary()

    # Save reports
    output_dir = Path("data/examples")
    output_dir.mkdir(parents=True, exist_ok=True)

    reporter.save_report(output_dir / "evaluation_demo_report.md")
    reporter.save_summary_json(output_dir / "evaluation_demo_summary.json")

    print(f"\nReports saved to {output_dir}/")
    print(f"  - evaluation_demo_report.md")
    print(f"  - evaluation_demo_summary.json")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  ✓ Used gemini-2.5-pro as judge (different from agent models)")
    print("  ✓ Majority voting across 3 samples for robustness")
    print("  ✓ Custom rubrics for each agent type")
    print("  ✓ Multimodal context for collision evaluation")
    print("  ✓ Detailed per-rubric reasoning")
    print("\nSee odd_agents/evaluation/README.md for full documentation.")


if __name__ == "__main__":
    main()
