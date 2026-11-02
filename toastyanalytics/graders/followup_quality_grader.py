"""Follow-up quality grader - continuity, specificity, and actionability."""

import re
from typing import Any, Dict, List, Optional, Sequence, Union

from toastyanalytics.core.base_grader import BaseGrader, GraderResult
from toastyanalytics.core.types import (
    GradingDimension,
    ImprovementSuggestion,
    ScoreBreakdown,
)
from toastyanalytics.graders.text_utils import (
    ACTION_MARKERS,
    FILLER_PHRASES,
    SEQUENCE_MARKERS,
    count_any,
    count_phrases,
    has_code_block,
    keyword_coverage,
)

_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_IDENTIFIER_RE = re.compile(
    r"\b[a-z]+_[a-z0-9_]+\b|\b[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*\b"
)
_PATH_RE = re.compile(r"\b[\w-]+/[\w./-]+\b|\b\w+\.(?:py|js|ts|json|yaml|yml|md)\b")


class FollowupQualityGrader(BaseGrader):
    """
    Grades a follow-up message in the context of the conversation so far.

    Rewards concrete detail and next actions, and penalises context-free or
    filler-heavy replies.
    """

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.FOLLOWUP_QUALITY

    def _get_default_weights(self) -> Dict[str, float]:
        return {"continuity": 0.35, "specificity": 0.35, "actionability": 0.3}

    def _get_default_thresholds(self) -> Dict[str, float]:
        return {"excellent": 85.0, "good": 70.0, "acceptable": 55.0}

    def grade(
        self,
        code: str = "",
        language: str = "text",
        prior_context: Optional[Union[str, Sequence[str]]] = None,
        history: Optional[Union[str, Sequence[str]]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> GraderResult:
        followup = code or kwargs.get("response") or ""
        prior = prior_context or history or (context or {}).get("prior_context")

        if not followup.strip():
            return self._empty()

        prior_text = self._normalize_context(prior)
        specificity = self._specificity(followup)
        actionability = self._actionability(followup)
        filler_count = count_phrases(followup, FILLER_PHRASES)

        weights = dict(self._weights)
        continuity: Optional[float] = None
        if prior_text:
            continuity = keyword_coverage(prior_text, followup)
            # A follow-up rarely reuses all prior keywords.
            continuity = min(1.0, continuity * 2.0)
        else:
            weights.pop("continuity")

        total_weight = sum(weights.values())
        weighted = (
            (weights.get("continuity", 0.0) * (continuity or 0.0))
            + weights["specificity"] * specificity
            + weights["actionability"] * actionability
        ) / total_weight

        penalty = min(0.3, filler_count * 0.1)
        score = round(max(0.0, 100.0 * weighted * (1.0 - penalty)), 2)
        tier = self._tier_for(score)

        parts = []
        if continuity is not None:
            parts.append(f"context continuity: {continuity:.0%}")
        parts.append(f"specificity: {specificity:.0%}")
        parts.append(f"actionability: {actionability:.0%}")
        if filler_count:
            parts.append(f"filler phrases: {filler_count}")
        feedback = ", ".join(parts) + f" ({tier})"

        suggestions: List[ImprovementSuggestion] = []
        if continuity is not None and continuity < 0.4:
            suggestions.append(
                ImprovementSuggestion(
                    category="Continuity",
                    priority=2,
                    description="Reference the earlier context explicitly",
                    expected_impact="Follow-up reads as a continuation, not a restart",
                )
            )
        if specificity < 0.5:
            suggestions.append(
                ImprovementSuggestion(
                    category="Specificity",
                    priority=2,
                    description="Name the concrete file, value, or identifier involved",
                    expected_impact="Recommendation is unambiguous and checkable",
                )
            )
        if actionability < 0.5:
            suggestions.append(
                ImprovementSuggestion(
                    category="Actionability",
                    priority=1,
                    description="State the next action, ideally as ordered steps",
                    expected_impact="Reader knows exactly what to do next",
                )
            )
        if filler_count:
            suggestions.append(
                ImprovementSuggestion(
                    category="Concision",
                    priority=3,
                    description="Remove generic filler phrasing",
                    expected_impact="Denser, more useful response",
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
                "context_provided": bool(prior_text),
                "continuity": round(continuity, 3) if continuity is not None else None,
                "specificity": round(specificity, 3),
                "actionability": round(actionability, 3),
                "filler_phrases": filler_count,
                "tier": tier,
            },
        )

    def _normalize_context(self, prior: Optional[Union[str, Sequence[str]]]) -> str:
        if not prior:
            return ""
        if isinstance(prior, str):
            return prior
        return "\n".join(str(item) for item in prior)

    def _specificity(self, text: str) -> float:
        signals = 0
        signals += min(2, len(_NUMBER_RE.findall(text)))
        signals += min(2, len(_IDENTIFIER_RE.findall(text)))
        signals += min(2, len(_PATH_RE.findall(text)))
        if has_code_block(text):
            signals += 2
        return min(1.0, signals / 6.0)

    def _actionability(self, text: str) -> float:
        actions = count_any(text, ACTION_MARKERS)
        steps = count_any(text, SEQUENCE_MARKERS)
        return min(1.0, (actions + 2 * steps) / 5.0)

    def _tier_for(self, score: float) -> str:
        if score >= self._thresholds["excellent"]:
            return "Excellent"
        if score >= self._thresholds["good"]:
            return "Good"
        if score >= self._thresholds["acceptable"]:
            return "Acceptable"
        return "Needs work"

    def _empty(self) -> GraderResult:
        feedback = "The follow-up is empty, so there is nothing to grade."
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
