"""
Reliability Grader - evaluates consistency and error rates
"""

import sys
from pathlib import Path

# Add parent directory to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Any, Dict, List, Optional

from src.core.base_grader import BaseGrader, GraderResult
from src.core.types import GradingDimension, ImprovementSuggestion, ScoreBreakdown


class ReliabilityGrader(BaseGrader):
    """
    Grades reliability based on success/failure rates
    """

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.RELIABILITY

    def _get_default_weights(self) -> Dict[str, float]:
        return {
            "success_rate": 0.6,
            "consistency": 0.4,
        }

    def _get_default_thresholds(self) -> Dict[str, float]:
        return {
            "excellent": 95,
            "good": 85,
            "acceptable": 75,
            "poor": 60,
        }

    def grade(
        self,
        task_attempts: List[Dict[str, Any]],
        task_complexities: Optional[List[str]] = None,
        **kwargs,
    ) -> GraderResult:
        """
        Grade reliability based on task attempts

        Args:
            task_attempts: List of task results (success/failure)
            task_complexities: Optional complexity ratings

        Returns:
            GraderResult
        """
        if not task_attempts:
            return self._empty_result()

        # Calculate success rate
        successes = sum(1 for attempt in task_attempts if attempt.get("success", False))
        total = len(task_attempts)
        success_rate = (successes / total) * 100

        # Calculate consistency (variance in performance)
        if all("score" in attempt for attempt in task_attempts):
            scores = [attempt["score"] for attempt in task_attempts]
            avg_score = sum(scores) / len(scores)
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            consistency_score = max(0, 100 - variance)
        else:
            consistency_score = success_rate

        # Weighted score
        score = (
            success_rate * self._weights["success_rate"]
            + consistency_score * self._weights["consistency"]
        )

        # Generate feedback
        feedback = self._generate_feedback(
            score, success_rate, consistency_score, successes, total
        )

        # Generate suggestions
        suggestions = []
        if score < 80:
            suggestions.append(
                ImprovementSuggestion(
                    category="Reliability",
                    priority=1,
                    description="Improve success rate and consistency",
                    expected_impact="More dependable results",
                    examples=[
                        "Add error handling",
                        "Test edge cases",
                        "Validate inputs thoroughly",
                    ],
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
            metadata={
                "success_rate": success_rate,
                "consistency_score": consistency_score,
                "successes": successes,
                "total_attempts": total,
            },
        )

    def _generate_feedback(
        self,
        score: float,
        success_rate: float,
        consistency: float,
        successes: int,
        total: int,
    ) -> str:
        """Generate feedback message"""
        if score >= self._thresholds["excellent"]:
            return f"Excellent reliability! {successes}/{total} successful ({success_rate:.1f}%)"
        elif score >= self._thresholds["good"]:
            return f"Good reliability. {successes}/{total} successful ({success_rate:.1f}%)"
        elif score >= self._thresholds["acceptable"]:
            return f"Acceptable reliability. {successes}/{total} successful. Room for improvement."
        else:
            return f"Reliability needs improvement. Only {successes}/{total} successful ({success_rate:.1f}%)"

    def _empty_result(self) -> GraderResult:
        """Return result when no data available"""
        breakdown = ScoreBreakdown(
            dimension=self.dimension,
            score=0,
            max_score=100,
            weight=1.0,
            weighted_score=0,
            rationale="No task attempts data available",
        )

        return GraderResult(
            dimension=self.dimension,
            score=0,
            max_score=100,
            breakdown=breakdown,
            feedback="No reliability data available",
            suggestions=[],
            metadata={},
        )
