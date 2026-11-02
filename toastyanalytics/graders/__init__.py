"""Grader implementations and the dimension factory."""

from typing import Dict, Optional, Type

from toastyanalytics.core.base_grader import BaseGrader
from toastyanalytics.core.types import GradingDimension

from .accuracy_grader import AccuracyGrader
from .code_quality_grader import CodeQualityGraderV2
from .efficiency_grader import EfficiencyGrader
from .followup_quality_grader import FollowupQualityGrader
from .prompt_quality_grader import PromptQualityGrader
from .prompt_understanding_grader import PromptUnderstandingGrader
from .readability_grader import ReadabilityGrader
from .reliability_grader import ReliabilityGrader
from .speed_grader import SpeedGrader

# Optional neural grader (requires PyTorch and Transformers).
try:
    from .neural_grader import NeuralGrader

    NEURAL_GRADER_AVAILABLE = True
except ImportError:
    NEURAL_GRADER_AVAILABLE = False

# Optional plugin system.
try:
    from toastyanalytics.plugins.plugin_loader import get_plugin_loader

    PLUGINS_AVAILABLE = True
except ImportError:
    PLUGINS_AVAILABLE = False


GRADER_MAP: Dict[GradingDimension, Type[BaseGrader]] = {
    GradingDimension.CODE_QUALITY: CodeQualityGraderV2,
    GradingDimension.READABILITY: ReadabilityGrader,
    GradingDimension.SPEED: SpeedGrader,
    GradingDimension.RELIABILITY: ReliabilityGrader,
    GradingDimension.ACCURACY: AccuracyGrader,
    GradingDimension.PROMPT_UNDERSTANDING: PromptUnderstandingGrader,
    GradingDimension.FOLLOWUP_QUALITY: FollowupQualityGrader,
    GradingDimension.EFFICIENCY: EfficiencyGrader,
    GradingDimension.PROMPT_QUALITY: PromptQualityGrader,
}

# Dimensions that have a concrete grader implementation.
SUPPORTED_DIMENSIONS = frozenset(GRADER_MAP)


def get_grader_for_dimension(
    dimension: GradingDimension,
    config: Optional[dict] = None,
    use_neural: bool = False,
    custom_grader: Optional[str] = None,
) -> BaseGrader:
    """
    Return a grader for ``dimension``.

    Args:
        dimension: The grading dimension.
        config: Optional weights and thresholds.
        use_neural: Use the neural grader when its dependencies are installed.
        custom_grader: Name of a grader registered by the plugin system.

    Raises:
        ValueError: If no grader is registered for the dimension.
    """
    if custom_grader and PLUGINS_AVAILABLE:
        grader_class = get_plugin_loader().get_custom_grader(custom_grader)
        if grader_class:
            return grader_class(config)
        print(f"Custom grader '{custom_grader}' not found, using default")

    if use_neural and NEURAL_GRADER_AVAILABLE:
        return NeuralGrader()

    grader_class = GRADER_MAP.get(dimension)
    if not grader_class:
        raise ValueError(f"No grader available for dimension: {dimension}")

    return grader_class(config)


__all__ = [
    "AccuracyGrader",
    "CodeQualityGraderV2",
    "EfficiencyGrader",
    "FollowupQualityGrader",
    "GRADER_MAP",
    "PromptQualityGrader",
    "PromptUnderstandingGrader",
    "ReadabilityGrader",
    "ReliabilityGrader",
    "SUPPORTED_DIMENSIONS",
    "SpeedGrader",
    "get_grader_for_dimension",
]
