"""Prompt-quality grader - how actionable is a request to an AI system?"""

import re
from typing import Dict, List, Optional

from toastyanalytics.core.base_grader import BaseGrader, GraderResult
from toastyanalytics.core.types import (
    GradingDimension,
    ImprovementSuggestion,
    ScoreBreakdown,
)
from toastyanalytics.graders.text_utils import (
    has_bullet_structure,
    has_code_block,
    sentences,
    words,
)

_REQUIREMENT_MARKERS = (
    "must",
    "should",
    "need",
    "avoid",
    "without",
    "within",
    "at most",
    "at least",
    "using",
    "only",
    "return",
    "output",
    "format",
)

_EXAMPLE_MARKERS = ("for example", "e.g.", "such as", "example:")

_VAGUE_WORDS = (
    "stuff",
    "things",
    "something",
    "anything",
    "whatever",
    "somehow",
    "etc",
    "maybe",
    "probably",
    "fix it",
    "make it better",
    "do the thing",
)

_GOAL_VERBS = (
    "add",
    "build",
    "change",
    "create",
    "debug",
    "explain",
    "fix",
    "generate",
    "implement",
    "improve",
    "optimize",
    "refactor",
    "remove",
    "review",
    "rewrite",
    "test",
    "update",
    "write",
)

_FILE_RE = re.compile(r"\b\w+\.(?:py|js|ts|tsx|json|yaml|yml|md|sql|sh)\b")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


class PromptQualityGrader(BaseGrader):
    """
    Grades the quality of a prompt: specificity, clarity, and structure.

    A good prompt names the goal, supplies constraints, and gives enough context
    to act without guessing.
    """

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.PROMPT_QUALITY

    def _get_default_weights(self) -> Dict[str, float]:
        return {"specificity": 0.45, "clarity": 0.35, "structure": 0.2}

    def _get_default_thresholds(self) -> Dict[str, float]:
        return {"excellent": 85.0, "good": 70.0, "acceptable": 55.0}

    def grade(
        self,
        code: str = "",
        language: str = "text",
        prompt: Optional[str] = None,
        **kwargs,
    ) -> GraderResult:
        text = prompt or code or ""
        if not text.strip():
            return self._empty()

        token_count = len(words(text))
        requirements = self._requirement_signals(text)
        specificity = self._specificity(text, token_count, requirements)
        clarity = self._clarity(text, token_count)
        structure = self._structure(text)

        weighted = (
            self._weights["specificity"] * specificity
            + self._weights["clarity"] * clarity
            + self._weights["structure"] * structure
        )
        score = round(max(0.0, min(100.0, 100.0 * weighted)), 2)
        tier = self._tier_for(score)

        feedback = (
            f"{token_count} words, specificity {specificity:.0%}, "
            f"clarity {clarity:.0%}, structure {structure:.0%} ({tier})"
        )

        suggestions = self._suggestions(specificity, clarity, structure, token_count)

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
                "word_count": token_count,
                "specificity": round(specificity, 3),
                "clarity": round(clarity, 3),
                "structure": round(structure, 3),
                "requirements_found": requirements,
                "tier": tier,
            },
        )

    def _requirement_signals(self, text: str) -> List[str]:
        lowered = text.lower()
        found = [marker for marker in _REQUIREMENT_MARKERS if marker in lowered]
        if _FILE_RE.search(text):
            found.append("file reference")
        if _NUMBER_RE.search(text):
            found.append("numeric constraint")
        if any(marker in lowered for marker in _EXAMPLE_MARKERS):
            found.append("example")
        return found

    def _specificity(
        self, text: str, token_count: int, requirements: List[str]
    ) -> float:
        signals = len(requirements)
        if 15 <= token_count <= 200:
            signals += 1
        return min(1.0, signals / 5.0)

    def _clarity(self, text: str, token_count: int) -> float:
        lowered = text.lower()
        vague = sum(1 for word in _VAGUE_WORDS if word in lowered)
        score = 1.0 - min(0.6, vague * 0.2)

        if token_count < 6:
            score -= 0.4
        elif token_count > 600:
            score -= 0.2

        if not any(verb in lowered.split() for verb in _GOAL_VERBS):
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _structure(self, text: str) -> float:
        score = 0.4
        if len(sentences(text)) >= 2:
            score += 0.3
        if has_bullet_structure(text):
            score += 0.2
        if has_code_block(text):
            score += 0.1
        if "?" in text:
            score += 0.1
        return min(1.0, score)

    def _suggestions(
        self, specificity: float, clarity: float, structure: float, token_count: int
    ) -> List[ImprovementSuggestion]:
        suggestions: List[ImprovementSuggestion] = []
        if specificity < 0.6:
            suggestions.append(
                ImprovementSuggestion(
                    category="Specificity",
                    priority=1,
                    description="Name the goal, inputs, and constraints explicitly",
                    expected_impact="Fewer clarifying round-trips",
                )
            )
        if clarity < 0.7:
            suggestions.append(
                ImprovementSuggestion(
                    category="Clarity",
                    priority=2,
                    description="Replace vague wording with concrete requirements",
                    expected_impact="Unambiguous interpretation",
                )
            )
        if structure < 0.5:
            suggestions.append(
                ImprovementSuggestion(
                    category="Structure",
                    priority=2,
                    description="Split the request into goal, context, and expected output",
                    expected_impact="Easier to follow and answer",
                )
            )
        if token_count < 6:
            suggestions.append(
                ImprovementSuggestion(
                    category="Context",
                    priority=1,
                    description="Add background and success criteria",
                    expected_impact="Enough context to produce a useful answer",
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
        feedback = "The prompt is empty, so there is nothing to grade."
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
