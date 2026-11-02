"""ToastyAnalytics: multi-dimensional code grading with feedback-driven adaptation."""

from toastyanalytics.core.types import GradingDimension
from toastyanalytics.database.models import DatabaseManager
from toastyanalytics.graders import get_grader_for_dimension
from toastyanalytics.meta_learning.engine import MetaLearner

__version__ = "2.0.0"

__all__ = [
    "DatabaseManager",
    "GradingDimension",
    "MetaLearner",
    "get_grader_for_dimension",
]
