"""Readability grader - the readability view of the code-quality analysis."""

from toastyanalytics.core.types import GradingDimension

from .code_quality_grader import CodeQualityGraderV2


class ReadabilityGrader(CodeQualityGraderV2):
    """Scores code readability and reports it under its own dimension."""

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.READABILITY
