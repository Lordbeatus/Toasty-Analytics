"""Prompt-understanding grader - does the answer address what was asked?"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from toastyanalytics.core.base_grader import BaseGrader, GraderResult
from toastyanalytics.core.types import (
    GradingDimension,
    ImprovementSuggestion,
    ScoreBreakdown,
)
from toastyanalytics.graders.text_utils import (
    CAUSAL_MARKERS,
    COMPARISON_MARKERS,
    PROCESS_MARKERS,
    has_bullet_structure,
    has_code_block,
    keyword_coverage,
    sentences,
    words,
)

_WORD_LIMIT_RE = re.compile(
    r"(?:under|at most|within|max(?:imum)? of?)\s+(\d+)\s+words?", re.I
)


class PromptUnderstandingGrader(BaseGrader):
    """
    Grades how well a response answers a prompt.

    Scores keyword coverage of the prompt, alignment with the question type
    (how/why/compare/define), and compliance with explicit output instructions.
    """

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.PROMPT_UNDERSTANDING

    def _get_default_weights(self) -> Dict[str, float]:
        return {"relevance": 0.5, "intent": 0.25, "compliance": 0.25}

    def _get_default_thresholds(self) -> Dict[str, float]:
        return {"excellent": 85.0, "good": 70.0, "acceptable": 55.0}

    def grade(
        self,
        code: str = "",
        language: str = "text",
        prompt: Optional[str] = None,
        question: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> GraderResult:
        response = code or kwargs.get("response") or ""
        prompt = prompt or question or (context or {}).get("prompt")

        if not prompt:
            return self._unverified(response, "prompt")
        if not response.strip():
            return self._empty("response")

        relevance = keyword_coverage(prompt, response)
        intent_score, intent_label = self._intent_alignment(prompt, response)
        compliance, requested, unmet = self._instruction_compliance(prompt, response)

        score = 100.0 * (
            self._weights["relevance"] * min(1.0, relevance * 1.5)
            + self._weights["intent"] * intent_score
            + self._weights["compliance"] * compliance
        )
        score = round(min(100.0, max(0.0, score)), 2)
        tier = self._tier_for(score)

        feedback = (
            f"Prompt keyword coverage: {relevance:.0%}; "
            f"{intent_label}; instruction compliance: {compliance:.0%} ({tier})"
        )

        suggestions: List[ImprovementSuggestion] = []
        if relevance < 0.5:
            suggestions.append(
                ImprovementSuggestion(
                    category="Relevance",
                    priority=2,
                    description="Address more of the concepts named in the prompt",
                    expected_impact="Higher relevance and fewer unanswered parts",
                )
            )
        if intent_score < 1.0:
            suggestions.append(
                ImprovementSuggestion(
                    category="Intent",
                    priority=2,
                    description=f"Answer the question type directly ({intent_label})",
                    expected_impact="Response matches what was actually asked",
                )
            )
        if unmet:
            suggestions.append(
                ImprovementSuggestion(
                    category="Instructions",
                    priority=1,
                    description="Follow the explicit output instructions: "
                    + ", ".join(unmet),
                    expected_impact="Response satisfies the requested format",
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
                "prompt_provided": True,
                "relevance": round(relevance, 3),
                "intent": intent_label,
                "requested_instructions": requested,
                "unmet_instructions": unmet,
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

    def _intent_alignment(self, prompt: str, response: str) -> Tuple[float, str]:
        lowered = prompt.lower()
        response_lower = response.lower()

        if "how" in lowered.split():
            label = "explains the process"
            return (
                1.0 if any(m in response_lower for m in PROCESS_MARKERS) else 0.4
            ), label
        if "why" in lowered.split():
            label = "explains the cause"
            return (
                1.0 if any(m in response_lower for m in CAUSAL_MARKERS) else 0.4
            ), label
        if any(word in lowered for word in ("compare", "difference", "versus", " vs ")):
            label = "compares the options"
            return (
                1.0 if any(m in response_lower for m in COMPARISON_MARKERS) else 0.4
            ), label
        if any(word in lowered for word in ("what is", "what are", "define")):
            markers = ("is a", "is an", "refers to", "means", "defined as")
            label = "defines the term"
            return (1.0 if any(m in response_lower for m in markers) else 0.5), label

        return 1.0, "answers the prompt"

    def _instruction_compliance(
        self, prompt: str, response: str
    ) -> Tuple[float, List[str], List[str]]:
        lowered = prompt.lower()
        requested: List[str] = []
        unmet: List[str] = []

        if "json" in lowered:
            requested.append("respond in JSON")
            try:
                json.loads(response)
            except (ValueError, TypeError):
                unmet.append("respond in JSON")

        if any(word in lowered for word in ("bullet", "bulleted", "list")):
            requested.append("use a list")
            if not has_bullet_structure(response):
                unmet.append("use a list")

        if any(word in lowered for word in ("code block", "code snippet", "snippet")):
            requested.append("include code")
            if not has_code_block(response):
                unmet.append("include code")

        if any(word in lowered for word in ("concise", "brief", "short answer")):
            requested.append("keep it concise")
            if len(words(response)) > 80:
                unmet.append("keep it concise")

        if "one sentence" in lowered or "single sentence" in lowered:
            requested.append("use one sentence")
            if len(sentences(response)) != 1:
                unmet.append("use one sentence")

        limit_match = _WORD_LIMIT_RE.search(prompt)
        if limit_match:
            limit = int(limit_match.group(1))
            requested.append(f"stay under {limit} words")
            if len(words(response)) > limit:
                unmet.append(f"stay under {limit} words")

        compliance = (
            1.0 if not requested else (len(requested) - len(unmet)) / len(requested)
        )
        return compliance, requested, unmet

    def _unverified(self, response: str, missing: str) -> GraderResult:
        feedback = (
            f"No {missing} was supplied, so understanding cannot be verified. "
            f'Pass it as {{"{missing}": "..."}} in the request context.'
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
            metadata={"prompt_provided": False, "confidence": "unverified"},
        )

    def _empty(self, missing: str) -> GraderResult:
        feedback = f"The {missing} is empty, so there is nothing to grade."
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
            metadata={"prompt_provided": True, "confidence": "empty"},
        )
