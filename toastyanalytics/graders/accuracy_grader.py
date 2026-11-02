"""Accuracy grader - compares an answer against a reference answer."""

from difflib import SequenceMatcher
from typing import Any, Dict, Optional

from toastyanalytics.core.base_grader import BaseGrader, GraderResult
from toastyanalytics.core.types import (
    GradingDimension,
    ImprovementSuggestion,
    ScoreBreakdown,
)
from toastyanalytics.graders.text_utils import content_words, keyword_coverage


class AccuracyGrader(BaseGrader):
    """
    Grades factual correctness against a reference answer.

    Accuracy cannot be measured without ground truth, so the caller supplies one
    through ``reference`` (or ``context["reference"]``). Without a reference the
    grader returns an explicit unverified score instead of guessing.
    """

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.ACCURACY

    def _get_default_weights(self) -> Dict[str, float]:
        return {"similarity": 0.55, "coverage": 0.45}

    def _get_default_thresholds(self) -> Dict[str, float]:
        return {"excellent": 85.0, "good": 70.0, "acceptable": 55.0}

    def grade(
        self,
        code: str = "",
        language: str = "text",
        reference: Optional[str] = None,
        expected: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> GraderResult:
        """Grade ``code`` (the answer) against a reference answer."""
        answer = code or kwargs.get("answer") or ""
        reference = reference or expected or (context or {}).get("reference")

        if not reference:
            return self._unverified(answer)

        if not answer.strip():
            return self._empty(answer)

        similarity = SequenceMatcher(
            None, reference.lower().strip(), answer.lower().strip()
        ).ratio()
        coverage = keyword_coverage(reference, answer)

        score = 100.0 * (
            self._weights["similarity"] * similarity
            + self._weights["coverage"] * coverage
        )
        score = round(min(100.0, max(0.0, score)), 2)

        tier = self._tier_for(score)
        feedback = (
            f"Reference similarity: {similarity:.0%}; "
            f"reference concepts covered: {coverage:.0%} ({tier})"
        )

        suggestions = self._suggestions(reference, answer, score)

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
                "reference_provided": True,
                "similarity": round(similarity, 3),
                "coverage": round(coverage, 3),
                "tier": tier,
            },
        )

    def _tier_for(self, score: float) -> str:
        if score >= self._thresholds["excellent"]:
            return "Excellent"
        if score >= self._thresholds["good"]:
            return "Good"
        if score >= self._thresholds["acceptable"]:
            return "Acceptable"
        return "Needs work"

    def _suggestions(
        self, reference: str, answer: str, score: float
    ) -> list[ImprovementSuggestion]:
        if score >= self._thresholds["good"]:
            return []

        missing = sorted(content_words(reference) - content_words(answer))[:5]
        description = "Align the answer with the reference"
        if missing:
            description += f"; missing concepts: {', '.join(missing)}"

        return [
            ImprovementSuggestion(
                category="Accuracy",
                priority=1 if score < self._thresholds["acceptable"] else 2,
                description=description,
                expected_impact="Closer agreement with the expected answer",
            )
        ]

    def _unverified(self, answer: str) -> GraderResult:
        feedback = (
            "No reference answer was supplied, so accuracy cannot be verified. "
            'Pass a reference with {"reference": "..."} in the request context.'
        )
        breakdown = ScoreBreakdown(
            dimension=self.dimension,
            score=50.0,
            max_score=100,
            weight=1.0,
            weighted_score=50.0,
            rationale=feedback,
        )
        return GraderResult(
            dimension=self.dimension,
            score=50.0,
            max_score=100,
            breakdown=breakdown,
            feedback=feedback,
            suggestions=[
                ImprovementSuggestion(
                    category="Accuracy",
                    priority=2,
                    description="Provide a reference answer to enable accuracy scoring",
                    expected_impact="Accuracy becomes measurable instead of assumed",
                )
            ],
            metadata={"reference_provided": False, "confidence": "unverified"},
        )

    def _empty(self, answer: str) -> GraderResult:
        feedback = (
            "The answer is empty, so there is nothing to compare to the reference."
        )
        breakdown = ScoreBreakdown(
            dimension=self.dimension,
            score=0.0,
            max_score=100,
            weight=1.0,
            weighted_score=0.0,
            rationale=feedback,
        )
        return GraderResult(
            dimension=self.dimension,
            score=0.0,
            max_score=100,
            breakdown=breakdown,
            feedback=feedback,
            metadata={"reference_provided": True, "confidence": "empty"},
        )
