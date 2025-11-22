"""
Test LLM-as-judge evaluation framework.
"""

import pytest
import json
from odd_agents.evaluation import (
    LLMJudge,
    PERCEPTION_RUBRICS,
    MOTION_RUBRICS,
    COLLISION_RUBRICS,
)


# ============================================================================
# GOLDEN OUTPUTS (Reference examples for evaluation)
# ============================================================================

GOLDEN_PERCEPTION_OUTPUT = {
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

GOLDEN_MOTION_OUTPUT = {
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

GOLDEN_COLLISION_OUTPUT = {
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


# ============================================================================
# TEST CASES
# ============================================================================

class TestLLMJudge:
    """Test LLM-as-judge evaluation framework."""

    @pytest.mark.slow  # Mark as slow since it calls LLM
    def test_perception_evaluation_perfect_output(self):
        """Test evaluation of perfect perception output."""
        judge = LLMJudge(
            agent_type="perception",
            rubrics=PERCEPTION_RUBRICS,
            num_samples=3,  # Reduced for faster testing
        )

        # Evaluate golden output against itself (should pass all rubrics)
        result = judge.evaluate(
            agent_output=GOLDEN_PERCEPTION_OUTPUT,
            reference_output=GOLDEN_PERCEPTION_OUTPUT,
        )

        # Overall score should be very high
        assert result.overall_score >= 0.8, (
            f"Perfect output should score ≥0.8, got {result.overall_score}"
        )
        assert result.passed

        # Most rubrics should pass
        passed_rubrics = sum(1 for rs in result.rubric_scores if rs.passed)
        assert passed_rubrics >= len(PERCEPTION_RUBRICS) * 0.7, (
            f"Expected ≥70% rubrics to pass, got {passed_rubrics}/{len(PERCEPTION_RUBRICS)}"
        )

        # Print detailed results
        print("\n" + "=" * 60)
        print("PERCEPTION EVALUATION - Perfect Output")
        print("=" * 60)
        print(f"Overall Score: {result.overall_score:.2f}")
        print(f"Passed: {result.passed}")
        print("\nPer-Rubric Scores:")
        for rs in result.rubric_scores:
            status = "✓ PASS" if rs.passed else "✗ FAIL"
            print(f"  {status} {rs.rubric_id}: {rs.score:.2f}")
            print(f"    └─ {rs.reasoning}")

    @pytest.mark.slow
    def test_perception_evaluation_flawed_output(self):
        """Test evaluation of flawed perception output."""
        judge = LLMJudge(
            agent_type="perception",
            rubrics=PERCEPTION_RUBRICS,
            num_samples=3,
        )

        # Create flawed output (inconsistencies, missing fields)
        flawed_output = {
            "environment_type": "indoor",
            "lighting": "moderate",
            "obstacles": {
                "count": 50,  # Very high count
                "types": ["furniture"],
                "density": 0.15,  # But low density (inconsistent!)
            },
            "terrain_type": "smooth",
            # Low traversability on smooth terrain (inconsistent!)
            "traversability_score": 0.2,
            # Missing summary!
        }

        result = judge.evaluate(
            agent_output=flawed_output,
            reference_output=GOLDEN_PERCEPTION_OUTPUT,
        )

        # Score should be lower due to inconsistencies
        assert result.overall_score < 0.8, (
            f"Flawed output should score <0.8, got {result.overall_score}"
        )

        # At least some rubrics should fail
        failed_rubrics = sum(1 for rs in result.rubric_scores if not rs.passed)
        assert failed_rubrics > 0, "Expected at least one rubric to fail"

        # Print detailed results
        print("\n" + "=" * 60)
        print("PERCEPTION EVALUATION - Flawed Output")
        print("=" * 60)
        print(f"Overall Score: {result.overall_score:.2f}")
        print(f"Passed: {result.passed}")
        print("\nPer-Rubric Scores:")
        for rs in result.rubric_scores:
            status = "✓ PASS" if rs.passed else "✗ FAIL"
            print(f"  {status} {rs.rubric_id}: {rs.score:.2f}")
            print(f"    └─ {rs.reasoning}")

    @pytest.mark.slow
    def test_motion_evaluation_stationary_robot(self):
        """Test evaluation of motion output for stationary robot."""
        judge = LLMJudge(
            agent_type="motion",
            rubrics=MOTION_RUBRICS,
            num_samples=3,
        )

        result = judge.evaluate(
            agent_output=GOLDEN_MOTION_OUTPUT,
            reference_output=GOLDEN_MOTION_OUTPUT,
        )

        # Should correctly identify stationary detection
        stationary_rubric = next(
            rs for rs in result.rubric_scores
            if rs.rubric_id == "stationary_detection"
        )
        assert stationary_rubric.passed, (
            "Should correctly identify stationary robot"
        )

        print("\n" + "=" * 60)
        print("MOTION EVALUATION - Stationary Robot")
        print("=" * 60)
        print(f"Overall Score: {result.overall_score:.2f}")
        print(f"\nStationary Detection Rubric:")
        print(f"  Score: {stationary_rubric.score:.2f}")
        print(f"  Reasoning: {stationary_rubric.reasoning}")

    @pytest.mark.slow
    def test_collision_evaluation_with_context(self):
        """Test collision evaluation with perception/motion context."""
        judge = LLMJudge(
            agent_type="collision",
            rubrics=COLLISION_RUBRICS,
            num_samples=3,
        )

        # Provide context from upstream agents
        context = {
            "perception": GOLDEN_PERCEPTION_OUTPUT,
            "motion": GOLDEN_MOTION_OUTPUT,
        }

        result = judge.evaluate(
            agent_output=GOLDEN_COLLISION_OUTPUT,
            reference_output=GOLDEN_COLLISION_OUTPUT,
            context=context,
        )

        # Should correctly assess multimodal fusion
        fusion_rubric = next(
            rs for rs in result.rubric_scores
            if rs.rubric_id == "multimodal_fusion"
        )
        assert fusion_rubric.score > 0.5, (
            "Should recognize proper multimodal fusion"
        )

        print("\n" + "=" * 60)
        print("COLLISION EVALUATION - With Context")
        print("=" * 60)
        print(f"Overall Score: {result.overall_score:.2f}")
        print(f"\nMultimodal Fusion Rubric:")
        print(f"  Score: {fusion_rubric.score:.2f}")
        print(f"  Reasoning: {fusion_rubric.reasoning}")

    def test_majority_voting_consistency(self):
        """Test that majority voting provides consistent results."""
        judge = LLMJudge(
            agent_type="perception",
            rubrics=PERCEPTION_RUBRICS[:2],  # Just test 2 rubrics
            num_samples=5,
        )

        # Run evaluation twice on same input
        result1 = judge.evaluate(
            agent_output=GOLDEN_PERCEPTION_OUTPUT,
            reference_output=GOLDEN_PERCEPTION_OUTPUT,
        )

        result2 = judge.evaluate(
            agent_output=GOLDEN_PERCEPTION_OUTPUT,
            reference_output=GOLDEN_PERCEPTION_OUTPUT,
        )

        # Scores should be similar (within 0.2)
        score_diff = abs(result1.overall_score - result2.overall_score)
        assert score_diff < 0.2, (
            f"Majority voting should be consistent, score diff: {score_diff}"
        )


if __name__ == "__main__":
    # Run a quick demo
    print("=" * 60)
    print("LLM-AS-JUDGE EVALUATION DEMO")
    print("=" * 60)

    judge = LLMJudge(
        agent_type="perception",
        rubrics=PERCEPTION_RUBRICS,
        num_samples=3,
    )

    result = judge.evaluate(
        agent_output=GOLDEN_PERCEPTION_OUTPUT,
        reference_output=GOLDEN_PERCEPTION_OUTPUT,
    )

    print(f"\nOverall Score: {result.overall_score:.2f}")
    print(f"Passed: {result.passed}")
    print(f"\nDetailed Scores:")
    print(json.dumps(result.to_dict(), indent=2))
