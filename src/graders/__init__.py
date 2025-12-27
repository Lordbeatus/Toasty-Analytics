"""
Graders module - refactored grading components
"""

import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.base_grader import BaseGrader
from src.core.types import GradingDimension

# Import refactored graders
from .code_quality_grader import CodeQualityGraderV2
from .reliability_grader import ReliabilityGrader
from .speed_grader import SpeedGrader

# Import advanced graders (optional dependencies)
try:
    from .neural_grader import NeuralGrader

    NEURAL_GRADER_AVAILABLE = True
except ImportError:
    NEURAL_GRADER_AVAILABLE = False

# Import plugin system
try:
    from src.plugins.plugin_loader import get_plugin_loader

    PLUGINS_AVAILABLE = True
except ImportError:
    PLUGINS_AVAILABLE = False


def get_grader_for_dimension(
    dimension: GradingDimension,
    config: Optional[dict] = None,
    use_neural: bool = False,
    custom_grader: Optional[str] = None,
) -> BaseGrader:
    """
    Factory function to get appropriate grader for a dimension

    Args:
        dimension: The grading dimension
        config: Optional configuration for the grader
        use_neural: Whether to use neural network grader (requires PyTorch)
        custom_grader: Name of custom grader plugin to use

    Returns:
        BaseGrader instance for that dimension
    """

    # Check for custom grader first
    if custom_grader and PLUGINS_AVAILABLE:
        plugin_loader = get_plugin_loader()
        grader_class = plugin_loader.get_custom_grader(custom_grader)
        if grader_class:
            return grader_class(config)
        else:
            print(f"⚠️  Custom grader '{custom_grader}' not found, using default")

    # Check for neural grader
    if use_neural and NEURAL_GRADER_AVAILABLE:
        return NeuralGrader()

    # Default grader map
    grader_map = {
        GradingDimension.CODE_QUALITY: CodeQualityGraderV2,
        GradingDimension.READABILITY: CodeQualityGraderV2,  # Readability uses code quality grader
        GradingDimension.SPEED: SpeedGrader,
        GradingDimension.RELIABILITY: ReliabilityGrader,
    }

    grader_class = grader_map.get(dimension)
    if not grader_class:
        raise ValueError(f"No grader available for dimension: {dimension}")

    return grader_class(config)


__all__ = [
    "get_grader_for_dimension",
    "CodeQualityGraderV2",
    "SpeedGrader",
    "ReliabilityGrader",
]
