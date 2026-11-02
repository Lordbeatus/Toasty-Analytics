"""Efficiency grader - information density and concision of generated text."""

from typing import Dict, List

from toastyanalytics.core.base_grader import BaseGrader, GraderResult
from toastyanalytics.core.types import (
    GradingDimension,
    ImprovementSuggestion,
    ScoreBreakdown,
)
from toastyanalytics.graders.text_utils import (
    FILLER_PHRASES,
    content_words,
    count_ngram_repetition,
    count_phrases,
    sentences,
    unique_ratio,
    words,
)


class EfficiencyGrader(BaseGrader):
    """
    Grades how much useful information a response carries per unit of length.

    Scores content density, redundancy, and length appropriateness, then applies
    a penalty for filler phrasing.
    """

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.EFFICIENCY

    def _get_default_weights(self) -> Dict[str, float]:
        return {"density": 0.4, "redundancy": 0.35, "concision": 0.25}

    def _get_default_thresholds(self) -> Dict[str, float]:
        return {"excellent": 85.0, "good": 70.0, "acceptable": 55.0}

    def grade(self, code: str = "", language: str = "text", **kwargs) -> GraderResult:
        text = code or kwargs.get("response") or ""
        if not text.strip():
            return self._empty()

        tokens = words(text)
        total_words = len(tokens)
        density = len(content_words(text)) / max(1, total_words)
        uniqueness = unique_ratio(tokens)
        repetition = count_ngram_repetition(text, size=3)
        filler_count = count_phrases(text, FILLER_PHRASES)

        density_score = min(1.0, density / 0.6)
        redundancy_score = max(0.0, 1.0 - max(repetition, 1.0 - uniqueness))
        concision_score = self._concision_score(total_words, len(sentences(text)))

        weighted = (
            self._weights["density"] * density_score
            + self._weights["redundancy"] * redundancy_score
            + self._weights["concision"] * concision_score
        )
        penalty = min(0.25, filler_count * 0.1)
        score = round(max(0.0, 100.0 * weighted * (1.0 - penalty)), 2)
        tier = self._tier_for(score)

        feedback = (
            f"{total_words} words, content density {density:.0%}, "
            f"repetition {repetition:.0%} ({tier})"
        )
        if filler_count:
            feedback += f"; {filler_count} filler phrase(s)"

        suggestions = self._suggestions(
            total_words, density, repetition, filler_count, score
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
                "word_count": total_words,
                "density": round(density, 3),
                "repetition": round(repetition, 3),
                "filler_phrases": filler_count,
                "tier": tier,
            },
        )

    def _concision_score(self, word_count: int, sentence_count: int) -> float:
        if word_count < 15:
            return 0.4
        if word_count <= 300:
            score = 1.0
        elif word_count <= 600:
            score = 0.75
        else:
            score = 0.5

        if sentence_count and word_count / sentence_count > 45:
            score -= 0.2
        return max(0.0, min(1.0, score))

    def _suggestions(
        self,
        word_count: int,
        density: float,
        repetition: float,
        filler_count: int,
        score: float,
    ) -> List[ImprovementSuggestion]:
        if score >= self._thresholds["good"]:
            return []

        suggestions: List[ImprovementSuggestion] = []
        if density < 0.45:
            suggestions.append(
                ImprovementSuggestion(
                    category="Density",
                    priority=2,
                    description="Replace connective and hedging language with concrete detail",
                    expected_impact="More information per sentence",
                )
            )
        if repetition > 0.2:
            suggestions.append(
                ImprovementSuggestion(
                    category="Redundancy",
                    priority=2,
                    description="Remove repeated points and restated conclusions",
                    expected_impact="Shorter response with the same content",
                )
            )
        if word_count > 300:
            suggestions.append(
                ImprovementSuggestion(
                    category="Length",
                    priority=2,
                    description="Trim to the parts that change the reader's next action",
                    expected_impact="Easier to scan and act on",
                )
            )
        if filler_count:
            suggestions.append(
                ImprovementSuggestion(
                    category="Filler",
                    priority=3,
                    description="Drop generic filler phrases",
                    expected_impact="Tighter prose",
                )
            )
        return suggestions

    def _tier_for(self, score: float) -> str:
        if score >= self._thresholds["excellent"]:
            return "Excellent"
        if score >= self._thresholds["good"]:
            return "Good"
        if score >= self._thresholds["acceptable"]:
            return "Acceptable"
        return "Needs work"

    def _empty(self) -> GraderResult:
        feedback = "The text is empty, so there is nothing to grade."
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
            metadata={"confidence": "empty"},
        )
