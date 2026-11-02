"""Tests for the accuracy, understanding, follow-up, efficiency, and prompt graders."""

from toastyanalytics.core.types import GradingDimension
from toastyanalytics.graders import (
    SUPPORTED_DIMENSIONS,
    AccuracyGrader,
    EfficiencyGrader,
    FollowupQualityGrader,
    PromptQualityGrader,
    PromptUnderstandingGrader,
    get_grader_for_dimension,
)


class TestRegistry:
    def test_all_dimensions_have_graders(self):
        assert len(SUPPORTED_DIMENSIONS) == len(GradingDimension)
        for dimension in GradingDimension:
            grader = get_grader_for_dimension(dimension)
            assert grader.dimension == dimension

    def test_new_graders_are_exported(self):
        assert AccuracyGrader().dimension == GradingDimension.ACCURACY
        assert (
            PromptUnderstandingGrader().dimension
            == GradingDimension.PROMPT_UNDERSTANDING
        )
        assert FollowupQualityGrader().dimension == GradingDimension.FOLLOWUP_QUALITY
        assert EfficiencyGrader().dimension == GradingDimension.EFFICIENCY
        assert PromptQualityGrader().dimension == GradingDimension.PROMPT_QUALITY


class TestAccuracyGrader:
    reference = "Paris is the capital of France and its largest city."

    def test_exact_answer_scores_high(self):
        result = AccuracyGrader().grade(code=self.reference, reference=self.reference)
        assert result.score >= 90
        assert result.metadata["coverage"] == 1.0

    def test_wrong_answer_scores_low(self):
        result = AccuracyGrader().grade(
            code="Bananas are a yellow fruit.", reference=self.reference
        )
        assert result.score < 50
        assert result.suggestions

    def test_context_reference_is_accepted(self):
        result = AccuracyGrader().grade(
            code=self.reference, context={"reference": self.reference}
        )
        assert result.metadata["reference_provided"] is True
        assert result.score >= 90

    def test_missing_reference_is_reported_not_guessed(self):
        result = AccuracyGrader().grade(code="Some answer")
        assert result.score == 50
        assert result.metadata["reference_provided"] is False
        assert result.metadata["confidence"] == "unverified"

    def test_empty_answer_scores_zero(self):
        result = AccuracyGrader().grade(code="  ", reference=self.reference)
        assert result.score == 0


class TestPromptUnderstandingGrader:
    prompt = "How do I install the package with pip?"

    def test_on_target_answer_scores_high(self):
        result = PromptUnderstandingGrader().grade(
            code="First run pip install toastyanalytics, then verify the import.",
            prompt=self.prompt,
        )
        assert result.score >= 80
        assert result.metadata["intent"] == "explains the process"

    def test_unrelated_answer_scores_low(self):
        result = PromptUnderstandingGrader().grade(code="Yes.", prompt=self.prompt)
        assert result.score < 50

    def test_unmet_format_instruction_is_flagged(self):
        result = PromptUnderstandingGrader().grade(
            code="Here is the answer.",
            prompt="Return the result as JSON.",
        )
        assert "respond in JSON" in result.metadata["unmet_instructions"]

    def test_met_format_instruction_passes(self):
        result = PromptUnderstandingGrader().grade(
            code='{"result": 42}',
            prompt="Return the result as JSON.",
        )
        assert result.metadata["unmet_instructions"] == []

    def test_missing_prompt_is_unverified(self):
        result = PromptUnderstandingGrader().grade(code="An answer")
        assert result.score == 50
        assert result.metadata["prompt_provided"] is False


class TestFollowupQualityGrader:
    prior = (
        "We are debugging the auth middleware in api.py; "
        "tokens expire after 30 minutes."
    )

    def test_specific_followup_scores_well(self):
        result = FollowupQualityGrader().grade(
            code=(
                "Update the JWT expiry in api.py to 60 minutes, then restart "
                "the server and re-run the login test."
            ),
            prior_context=self.prior,
        )
        assert result.score >= 60
        assert result.metadata["context_provided"] is True
        assert result.metadata["specificity"] > 0

    def test_vague_followup_scores_low(self):
        result = FollowupQualityGrader().grade(
            code="It depends on what you want to do.", prior_context=self.prior
        )
        assert result.score < 40

    def test_context_is_optional(self):
        result = FollowupQualityGrader().grade(
            code="Set the retry count to 3 in config.yaml."
        )
        assert result.metadata["context_provided"] is False
        assert result.score > 0

    def test_empty_followup_scores_zero(self):
        assert FollowupQualityGrader().grade(code="").score == 0


class TestEfficiencyGrader:
    dense = (
        "Graders return a score, a breakdown, and suggestions. "
        "Each grader implements grade() and declares its weights."
    )

    def test_dense_text_beats_padded_text(self):
        padded = (
            "It is important to note that basically there are many ways to do "
            "this. " * 12
        )
        dense_result = EfficiencyGrader().grade(code=self.dense)
        padded_result = EfficiencyGrader().grade(code=padded)

        assert dense_result.score > padded_result.score
        assert padded_result.metadata["filler_phrases"] > 0

    def test_empty_text_scores_zero(self):
        assert EfficiencyGrader().grade(code="").score == 0


class TestPromptQualityGrader:
    good = (
        "Add retry with backoff to the deploy poller in deploy.py. "
        "It must retry at most 3 times and avoid duplicate uploads. "
        "Return a diff."
    )

    def test_detailed_prompt_scores_high(self):
        result = PromptQualityGrader().grade(code=self.good)
        assert result.score >= 75
        assert "file reference" in result.metadata["requirements_found"]

    def test_vague_prompt_scores_low(self):
        result = PromptQualityGrader().grade(code="fix my code")
        assert result.score < 45
        assert result.suggestions

    def test_prompt_keyword_argument_is_used(self):
        result = PromptQualityGrader().grade(prompt=self.good)
        assert result.metadata["word_count"] > 10

    def test_empty_prompt_scores_zero(self):
        assert PromptQualityGrader().grade(code="").score == 0
