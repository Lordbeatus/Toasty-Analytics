"""
Speed Grader - evaluates code generation/execution speed
"""

import sys
from pathlib import Path

# Add parent directory to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Any, Dict, List

from src.core.base_grader import BaseGrader, GraderResult
from src.core.types import GradingDimension, ImprovementSuggestion, ScoreBreakdown


class SpeedGrader(BaseGrader):
    """
    Grades the speed of code generation or execution
    """

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.SPEED

    def _get_default_weights(self) -> Dict[str, float]:
        return {"speed": 1.0}

    def _get_default_thresholds(self) -> Dict[str, float]:
        return {
            "excellent": 5.0,  # < 5 seconds
            "good": 15.0,  # < 15 seconds
            "acceptable": 30.0,  # < 30 seconds
            "slow": 60.0,  # < 60 seconds
        }

    def grade(self, generation_time: float, **kwargs) -> GraderResult:
        """
        Grade based on generation time

        Args:
            generation_time: Time in seconds

        Returns:
            GraderResult
        """
        # Score calculation (inverse relationship with time)
        if generation_time <= self._thresholds["excellent"]:
            score = 100
            tier = "Excellent"
        elif generation_time <= self._thresholds["good"]:
            score = 85
            tier = "Good"
        elif generation_time <= self._thresholds["acceptable"]:
            score = 70
            tier = "Acceptable"
        elif generation_time <= self._thresholds["slow"]:
            score = 55
            tier = "Slow"
        else:
            score = 40
            tier = "Very Slow"

        feedback = f"Generation speed: {tier} ({generation_time:.2f}s)"

        suggestions = []
        if score < 70:
            suggestions.append(
                ImprovementSuggestion(
                    category="Speed",
                    priority=2,
                    description="Consider optimizing for faster generation",
                    expected_impact="Reduced wait time for users",
                    examples=["Use more efficient algorithms", "Reduce complexity"],
                )
            )

        breakdown = ScoreBreakdown(
            dimension=self.dimension,
            score=score,
            max_score=100,
            weight=1.0,
            weighted_score=score,
            rationale=feedback,
        )

        return GraderResult(
            dimension=self.dimension,
            score=score,
            max_score=100,
            breakdown=breakdown,
            feedback=feedback,
            suggestions=suggestions,
            metadata={"generation_time": generation_time, "tier": tier},
        )
