"""
Evaluation reporting and metrics utilities.
"""

import json
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

from .base import EvaluationResult


class EvaluationReporter:
    """Generate evaluation reports and metrics."""

    def __init__(self):
        self.results: List[EvaluationResult] = []

    def add_result(self, result: EvaluationResult):
        """Add an evaluation result to the reporter."""
        self.results.append(result)

    def generate_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics across all evaluations.

        Returns:
            Dictionary with summary metrics
        """
        if not self.results:
            return {"error": "No evaluation results"}

        # Overall metrics
        total_results = len(self.results)
        passed_results = sum(1 for r in self.results if r.passed)

        # Per-agent metrics
        agent_scores = {}
        for result in self.results:
            agent_type = result.agent_type
            if agent_type not in agent_scores:
                agent_scores[agent_type] = []
            agent_scores[agent_type].append(result.overall_score)

        agent_avg_scores = {
            agent: sum(scores) / len(scores)
            for agent, scores in agent_scores.items()
        }

        # Per-rubric metrics (across all agents)
        rubric_scores = {}
        for result in self.results:
            for rs in result.rubric_scores:
                rubric_id = rs.rubric_id
                if rubric_id not in rubric_scores:
                    rubric_scores[rubric_id] = []
                rubric_scores[rubric_id].append(rs.score)

        rubric_avg_scores = {
            rubric: sum(scores) / len(scores)
            for rubric, scores in rubric_scores.items()
        }

        # Find worst-performing rubrics
        worst_rubrics = sorted(
            rubric_avg_scores.items(),
            key=lambda x: x[1]
        )[:5]

        return {
            "summary": {
                "total_evaluations": total_results,
                "passed_evaluations": passed_results,
                "pass_rate": passed_results / total_results,
                "average_score": sum(r.overall_score for r in self.results) / total_results,
            },
            "per_agent": agent_avg_scores,
            "per_rubric": rubric_avg_scores,
            "worst_rubrics": dict(worst_rubrics),
            "timestamp": datetime.now().isoformat(),
        }

    def generate_detailed_report(self) -> str:
        """
        Generate detailed markdown report.

        Returns:
            Markdown-formatted report string
        """
        summary = self.generate_summary()

        lines = [
            "# Agent Evaluation Report",
            "",
            f"**Generated:** {summary['timestamp']}",
            f"**Total Evaluations:** {summary['summary']['total_evaluations']}",
            f"**Pass Rate:** {summary['summary']['pass_rate']:.1%}",
            f"**Average Score:** {summary['summary']['average_score']:.2f}",
            "",
            "## Per-Agent Performance",
            "",
        ]

        # Sort agents by score
        for agent, score in sorted(
            summary['per_agent'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"- **{agent}**: {score:.2f}")

        lines.extend([
            "",
            "## Worst-Performing Rubrics",
            "",
            "These rubrics had the lowest scores across all evaluations:",
            "",
        ])

        for rubric, score in summary['worst_rubrics'].items():
            lines.append(f"- **{rubric}**: {score:.2f}")

        lines.extend([
            "",
            "## Detailed Results",
            "",
        ])

        for i, result in enumerate(self.results, 1):
            status = "✓ PASSED" if result.passed else "✗ FAILED"
            lines.extend([
                f"### {i}. {result.agent_type} - {status}",
                "",
                f"**Overall Score:** {result.overall_score:.2f}",
                "",
                "**Rubric Scores:**",
                "",
            ])

            for rs in result.rubric_scores:
                status = "✓" if rs.passed else "✗"
                lines.append(f"- {status} **{rs.rubric_id}**: {rs.score:.2f}")
                lines.append(f"  - _{rs.reasoning}_")

            lines.append("")

        return "\n".join(lines)

    def save_report(self, output_path: Path):
        """
        Save detailed report to file.

        Args:
            output_path: Path to save report (markdown)
        """
        report = self.generate_detailed_report()
        output_path.write_text(report)

    def save_summary_json(self, output_path: Path):
        """
        Save summary metrics as JSON.

        Args:
            output_path: Path to save JSON summary
        """
        summary = self.generate_summary()
        output_path.write_text(json.dumps(summary, indent=2))

    def print_summary(self):
        """Print summary to console."""
        summary = self.generate_summary()

        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total Evaluations: {summary['summary']['total_evaluations']}")
        print(f"Passed: {summary['summary']['passed_evaluations']}")
        print(f"Pass Rate: {summary['summary']['pass_rate']:.1%}")
        print(f"Average Score: {summary['summary']['average_score']:.2f}")

        print("\nPer-Agent Performance:")
        for agent, score in sorted(
            summary['per_agent'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  {agent:20s}: {score:.2f}")

        print("\nWorst-Performing Rubrics:")
        for rubric, score in list(summary['worst_rubrics'].items())[:5]:
            print(f"  {rubric:40s}: {score:.2f}")
        print("=" * 60)


def compare_evaluations(
    results_before: List[EvaluationResult],
    results_after: List[EvaluationResult],
) -> Dict[str, Any]:
    """
    Compare two sets of evaluation results (e.g., before/after improvements).

    Args:
        results_before: Evaluation results before changes
        results_after: Evaluation results after changes

    Returns:
        Dictionary with comparison metrics
    """
    reporter_before = EvaluationReporter()
    for r in results_before:
        reporter_before.add_result(r)

    reporter_after = EvaluationReporter()
    for r in results_after:
        reporter_after.add_result(r)

    summary_before = reporter_before.generate_summary()
    summary_after = reporter_after.generate_summary()

    # Calculate improvements
    score_improvement = (
        summary_after['summary']['average_score'] -
        summary_before['summary']['average_score']
    )

    pass_rate_improvement = (
        summary_after['summary']['pass_rate'] -
        summary_before['summary']['pass_rate']
    )

    # Per-agent improvements
    agent_improvements = {}
    for agent in summary_before['per_agent']:
        if agent in summary_after['per_agent']:
            improvement = (
                summary_after['per_agent'][agent] -
                summary_before['per_agent'][agent]
            )
            agent_improvements[agent] = improvement

    return {
        "overall": {
            "score_improvement": score_improvement,
            "pass_rate_improvement": pass_rate_improvement,
        },
        "per_agent_improvements": agent_improvements,
        "before": summary_before,
        "after": summary_after,
    }
