"""
ToastyAnalytics - AI Agent Self-Improvement & Grading System with Meta-Learning

A production-grade platform for evaluating and improving AI coding agents through
personalized feedback, adaptive grading, and collective learning.
"""

__version__ = "2.0.0"
__author__ = "ToastyAnalytics Team"

# Core exports
from src.core import (
    BaseGrader,
    FeedbackLevel,
    GraderResult,
    GradingDimension,
    ScoreBreakdown,
)
from src.database.models import DatabaseManager
from src.graders import get_grader_for_dimension
from src.meta_learning.engine import MetaLearner

__all__ = [
    # Core classes
    "BaseGrader",
    "GraderResult",
    "GradingDimension",
    "FeedbackLevel",
    "ScoreBreakdown",
    # Database
    "DatabaseManager",
    # Meta-learning
    "MetaLearner",
    # Graders
    "get_grader_for_dimension",
]
