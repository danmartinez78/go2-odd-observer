"""
Base classes for agent evaluation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class EvaluationCriteria(Enum):
    """Types of evaluation criteria."""
    
    # Response quality
    SEMANTIC_MATCH = "semantic_match"  # LLM judges if response matches reference
    RUBRIC_BASED_QUALITY = "rubric_based_quality"  # Custom rubrics for quality
    
    # Tool usage
    TOOL_TRAJECTORY = "tool_trajectory"  # Exact/ordered/any-order tool call matching
    RUBRIC_BASED_TOOL_USE = "rubric_based_tool_use"  # Custom rubrics for tool usage
    
    # Safety and grounding
    HALLUCINATIONS = "hallucinations"  # Check grounding in context
    SAFETY = "safety"  # Harmful content check


@dataclass
class Rubric:
    """A single evaluation rubric."""
    
    rubric_id: str
    description: str
    importance: float = 1.0  # Weight for aggregation
    
    def __post_init__(self):
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"Importance must be in [0, 1], got {self.importance}")


@dataclass
class RubricScore:
    """Score for a single rubric evaluation."""
    
    rubric_id: str
    score: float  # 0.0 (fail) to 1.0 (pass)
    reasoning: str
    num_samples: int = 1
    votes: List[bool] = field(default_factory=list)  # Individual judge votes
    
    @property
    def passed(self) -> bool:
        """Whether this rubric passed (majority vote)."""
        return self.score >= 0.5


@dataclass
class EvaluationResult:
    """Result of evaluating an agent output."""
    
    agent_type: str
    criterion: EvaluationCriteria
    overall_score: float  # Aggregated score across all rubrics
    rubric_scores: List[RubricScore] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def passed(self) -> bool:
        """Whether evaluation passed overall."""
        return self.overall_score >= 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_type": self.agent_type,
            "criterion": self.criterion.value,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "rubric_scores": [
                {
                    "rubric_id": rs.rubric_id,
                    "score": rs.score,
                    "passed": rs.passed,
                    "reasoning": rs.reasoning,
                    "num_samples": rs.num_samples,
                }
                for rs in self.rubric_scores
            ],
            "metadata": self.metadata,
        }


class AgentEvaluator:
    """Base class for agent evaluators."""
    
    def __init__(
        self,
        agent_type: str,
        rubrics: List[Rubric],
        judge_model: str = "gemini-2.5-pro",
        num_samples: int = 5,
    ):
        """
        Initialize evaluator.
        
        Args:
            agent_type: Type of agent being evaluated
            rubrics: List of rubrics to evaluate against
            judge_model: Model to use as judge (should be different/larger than agent model)
            num_samples: Number of samples for majority voting
        """
        self.agent_type = agent_type
        self.rubrics = rubrics
        self.judge_model = judge_model
        self.num_samples = num_samples
        
        # Validate that judge model is sufficiently capable
        if "flash-lite" in judge_model.lower():
            raise ValueError(
                "Judge model should be more capable than agent model. "
                "Use gemini-2.5-pro or larger to avoid model similarity bias."
            )
    
    def evaluate(
        self,
        agent_output: Dict[str, Any],
        reference_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate agent output.
        
        Args:
            agent_output: The output produced by the agent
            reference_output: Optional reference/expected output
            context: Optional context (inputs, tool outputs, etc.)
            
        Returns:
            EvaluationResult with scores and reasoning
        """
        raise NotImplementedError("Subclasses must implement evaluate()")
    
    def _aggregate_rubric_scores(
        self,
        rubric_scores: List[RubricScore],
    ) -> float:
        """
        Aggregate rubric scores with importance weighting.
        
        Args:
            rubric_scores: List of individual rubric scores
            
        Returns:
            Weighted average score
        """
        if not rubric_scores:
            return 0.0
        
        # Get importance weights from rubrics
        rubric_weights = {r.rubric_id: r.importance for r in self.rubrics}
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for rs in rubric_scores:
            weight = rubric_weights.get(rs.rubric_id, 1.0)
            weighted_sum += rs.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
