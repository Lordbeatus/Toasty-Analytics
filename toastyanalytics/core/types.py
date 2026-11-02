"""
Type definitions and enums for toastyanalytics
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class GradingDimension(str, Enum):
    """Different dimensions of code/agent grading"""

    CODE_QUALITY = "code_quality"
    READABILITY = "readability"
    SPEED = "speed"
    RELIABILITY = "reliability"
    ACCURACY = "accuracy"
    PROMPT_UNDERSTANDING = "prompt_understanding"
    FOLLOWUP_QUALITY = "followup_quality"
    EFFICIENCY = "efficiency"
    PROMPT_QUALITY = "prompt_quality"


class FeedbackLevel(str, Enum):
    """Level of detail in feedback"""

    MINIMAL = "minimal"  # Just scores
    STANDARD = "standard"  # Scores + brief feedback
    DETAILED = "detailed"  # Scores + detailed feedback + suggestions
    EXPERT = "expert"  # Everything + line-by-line analysis


class LearningStrategy(str, Enum):
    """Meta-learning strategies"""

    PARAMETER_ADAPTATION = "parameter_adaptation"  # Adjust grading weights
    FEEDBACK_PERSONALIZATION = "feedback_personalization"  # Customize feedback style
    THRESHOLD_TUNING = "threshold_tuning"  # Adjust scoring thresholds
    PATTERN_RECOGNITION = "pattern_recognition"  # Learn user patterns


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a score with rationale"""

    dimension: GradingDimension
    score: float
    max_score: float
    weight: float
    weighted_score: float
    rationale: str
    line_level_feedback: Optional[Dict[int, str]] = None  # Line number -> feedback
    suggestions: Optional[List[str]] = None


@dataclass
class ImprovementSuggestion:
    """A specific improvement suggestion"""

    category: str
    priority: int  # 1=critical, 2=important, 3=nice-to-have
    description: str
    expected_impact: str
    examples: Optional[List[str]] = None


class UserProfile(TypedDict, total=False):
    """User-specific learning profile"""

    user_id: str
    preferences: Dict[str, Any]
    learning_strategies: List[str]
    adaptation_history: List[Dict[str, Any]]
    performance_trends: Dict[str, List[float]]


class AgentProfile(TypedDict, total=False):
    """Agent-specific profile for multi-agent systems"""

    agent_id: str
    agent_type: str
    capabilities: List[str]
    performance_metrics: Dict[str, float]
    specializations: List[str]
