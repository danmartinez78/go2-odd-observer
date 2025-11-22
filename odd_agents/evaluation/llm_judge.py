"""
LLM-as-judge evaluator using a larger/different model for unbiased evaluation.

This module implements the core evaluation logic using an LLM to judge
agent outputs against rubrics, with majority voting for robustness.
"""

import json
import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai

from .base import (
    AgentEvaluator,
    EvaluationResult,
    EvaluationCriteria,
    Rubric,
    RubricScore,
)

load_dotenv()


class LLMJudge(AgentEvaluator):
    """
    Evaluator using LLM-as-judge pattern.

    Uses a more capable model (gemini-2.5-pro) to judge agent outputs
    produced by smaller models (gemini-flash-lite) to avoid model similarity bias.
    """

    def __init__(
        self,
        agent_type: str,
        rubrics: List[Rubric],
        judge_model: str = "gemini-2.5-pro",
        num_samples: int = 5,
        api_key: Optional[str] = None,
    ):
        """
        Initialize LLM judge.

        Args:
            agent_type: Type of agent being evaluated
            rubrics: List of rubrics to evaluate against
            judge_model: Model to use as judge (default: gemini-2.5-pro)
            num_samples: Number of samples for majority voting (default: 5)
            api_key: Optional API key (uses GOOGLE_API_KEY env var if not provided)
        """
        super().__init__(agent_type, rubrics, judge_model, num_samples)

        # Configure Gemini API
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. Set in .env or pass as argument."
            )

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(judge_model)

    def evaluate(
        self,
        agent_output: Dict[str, Any],
        reference_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate agent output using LLM-as-judge.

        Args:
            agent_output: The output produced by the agent
            reference_output: Optional reference/expected output
            context: Optional context (inputs, tool outputs, etc.)

        Returns:
            EvaluationResult with scores and reasoning
        """
        rubric_scores = []

        for rubric in self.rubrics:
            score = self._evaluate_rubric(
                rubric=rubric,
                agent_output=agent_output,
                reference_output=reference_output,
                context=context,
            )
            rubric_scores.append(score)

        # Aggregate scores
        overall_score = self._aggregate_rubric_scores(rubric_scores)

        return EvaluationResult(
            agent_type=self.agent_type,
            criterion=EvaluationCriteria.RUBRIC_BASED_QUALITY,
            overall_score=overall_score,
            rubric_scores=rubric_scores,
            metadata={
                "judge_model": self.judge_model,
                "num_samples": self.num_samples,
            },
        )

    def _evaluate_rubric(
        self,
        rubric: Rubric,
        agent_output: Dict[str, Any],
        reference_output: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> RubricScore:
        """
        Evaluate a single rubric with majority voting.

        Args:
            rubric: The rubric to evaluate
            agent_output: Agent's output
            reference_output: Optional reference output
            context: Optional context

        Returns:
            RubricScore with majority vote and reasoning
        """
        votes = []
        reasonings = []

        # Sample multiple times for majority voting
        for _ in range(self.num_samples):
            vote, reasoning = self._judge_rubric(
                rubric=rubric,
                agent_output=agent_output,
                reference_output=reference_output,
                context=context,
            )
            votes.append(vote)
            reasonings.append(reasoning)

        # Majority vote
        num_passed = sum(votes)
        score = num_passed / len(votes)

        # Use reasoning from majority (or first if tie)
        majority_reasoning = reasonings[0]
        if num_passed > len(votes) / 2:
            # Find first "pass" reasoning
            for i, vote in enumerate(votes):
                if vote:
                    majority_reasoning = reasonings[i]
                    break
        else:
            # Find first "fail" reasoning
            for i, vote in enumerate(votes):
                if not vote:
                    majority_reasoning = reasonings[i]
                    break

        return RubricScore(
            rubric_id=rubric.rubric_id,
            score=score,
            reasoning=majority_reasoning,
            num_samples=self.num_samples,
            votes=votes,
        )

    def _judge_rubric(
        self,
        rubric: Rubric,
        agent_output: Dict[str, Any],
        reference_output: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> tuple[bool, str]:
        """
        Single judge evaluation of a rubric.

        Args:
            rubric: The rubric to evaluate
            agent_output: Agent's output
            reference_output: Optional reference output
            context: Optional context

        Returns:
            Tuple of (pass/fail, reasoning)
        """
        prompt = self._build_judge_prompt(
            rubric=rubric,
            agent_output=agent_output,
            reference_output=reference_output,
            context=context,
        )

        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)

            return result["passed"], result["reasoning"]

        except Exception as e:
            # If LLM fails, default to fail with error message
            return False, f"Evaluation failed: {str(e)}"

    def _build_judge_prompt(
        self,
        rubric: Rubric,
        agent_output: Dict[str, Any],
        reference_output: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """
        Build prompt for LLM judge.

        Args:
            rubric: The rubric to evaluate
            agent_output: Agent's output
            reference_output: Optional reference output
            context: Optional context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "You are an expert evaluator assessing the quality of an AI agent's output.",
            f"\nAgent Type: {self.agent_type}",
            f"\nEvaluation Rubric: {rubric.description}",
            "\n\nYour task is to determine whether the agent's output satisfies this rubric.",
            "Respond with a JSON object containing:",
            '- "passed": true/false',
            '- "reasoning": brief explanation of your judgment',
            "\n\nAgent Output:",
            json.dumps(agent_output, indent=2),
        ]

        if reference_output:
            prompt_parts.extend([
                "\n\nReference/Expected Output:",
                json.dumps(reference_output, indent=2),
            ])

        if context:
            prompt_parts.extend([
                "\n\nContext (inputs, tool outputs, etc.):",
                json.dumps(context, indent=2),
            ])

        prompt_parts.extend([
            "\n\nProvide your evaluation as valid JSON only (no markdown, no extra text):",
            '{"passed": true/false, "reasoning": "..."}',
        ])

        return "\n".join(prompt_parts)
