"""
Base grader abstraction - all graders inherit from this
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import GradingDimension, ImprovementSuggestion, ScoreBreakdown


@dataclass
class GraderResult:
    """
    Standardized result from any grader
    """

    dimension: GradingDimension
    score: float
    max_score: float
    breakdown: ScoreBreakdown
    feedback: str
    suggestions: List[ImprovementSuggestion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def percentage(self) -> float:
        """Score as percentage"""
        return (self.score / self.max_score * 100) if self.max_score > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "breakdown": {
                "dimension": self.breakdown.dimension.value,
                "score": self.breakdown.score,
                "max_score": self.breakdown.max_score,
                "weight": self.breakdown.weight,
                "weighted_score": self.breakdown.weighted_score,
                "rationale": self.breakdown.rationale,
                "line_level_feedback": self.breakdown.line_level_feedback,
                "suggestions": self.breakdown.suggestions,
            },
            "feedback": self.feedback,
            "suggestions": [
                {
                    "category": s.category,
                    "priority": s.priority,
                    "description": s.description,
                    "expected_impact": s.expected_impact,
                    "examples": s.examples,
                }
                for s in self.suggestions
            ],
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseGrader(ABC):
    """
    Abstract base class for all graders

    All grading components inherit from this and implement the grade() method.
    This ensures consistency and makes it easy to add new graders.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize grader with optional configuration

        Args:
            config: Configuration dictionary (weights, thresholds, etc.)
        """
        self.config = config or {}
        self._weights = self._get_default_weights()
        self._thresholds = self._get_default_thresholds()

        # Override defaults with config
        if "weights" in self.config:
            self._weights.update(self.config["weights"])
        if "thresholds" in self.config:
            self._thresholds.update(self.config["thresholds"])

    @abstractmethod
    def grade(self, **kwargs) -> GraderResult:
        """
        Grade the input and return a standardized result

        Returns:
            GraderResult with score, feedback, and suggestions
        """
        pass

    @abstractmethod
    def _get_default_weights(self) -> Dict[str, float]:
        """
        Get default weights for scoring components

        Returns:
            Dictionary of component weights
        """
        pass

    @abstractmethod
    def _get_default_thresholds(self) -> Dict[str, float]:
        """
        Get default thresholds for scoring

        Returns:
            Dictionary of thresholds
        """
        pass

    def update_weights(self, weights: Dict[str, float]) -> None:
        """
        Update grader weights (used by meta-learning)

        Args:
            weights: New weights to apply
        """
        self._weights.update(weights)

    def update_thresholds(self, thresholds: Dict[str, float]) -> None:
        """
        Update grader thresholds (used by meta-learning)

        Args:
            thresholds: New thresholds to apply
        """
        self._thresholds.update(thresholds)

    def get_weights(self) -> Dict[str, float]:
        """Get current weights"""
        return self._weights.copy()

    def get_thresholds(self) -> Dict[str, float]:
        """Get current thresholds"""
        return self._thresholds.copy()

    @property
    def dimension(self) -> GradingDimension:
        """The dimension this grader evaluates"""
        raise NotImplementedError("Subclasses must define dimension property")
