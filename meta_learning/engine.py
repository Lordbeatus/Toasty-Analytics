"""
Meta-learning engine for self-improving graders
"""

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Add parent directory to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from core.types import GradingDimension
from core.types import LearningStrategy as StrategyType
from database.models import DatabaseManager, GradingHistory, LearningStrategy, User


class MetaLearner:
    """
    Meta-learning engine that learns how to improve grading over time.

    This class implements a sophisticated meta-learning system that adapts grading
    behavior based on user feedback and performance patterns. It uses multiple
    learning strategies to continuously improve grading accuracy and relevance.

    Key capabilities:
    - Adapts grading parameters based on user feedback and performance trends
    - Personalizes feedback style based on individual user learning patterns
    - Identifies effective strategies and applies them automatically
    - Learns from collective data across all users for pattern recognition
    - Maintains session history for cross-session improvement

    Learning Strategies:
    1. Parameter Adaptation: Adjusts grading weights based on feedback trends
    2. Feedback Personalization: Learns preferred feedback verbosity/style
    3. Threshold Tuning: Adapts scoring thresholds to user skill level
    4. Pattern Recognition: Identifies common issues from collective data

    Example:
        >>> db = DatabaseManager()
        >>> learner = MetaLearner(db)
        >>> grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
        >>> learner.apply_strategies_to_grader(grader, 'user_123')
        >>> # Grader now uses personalized parameters for user_123
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize meta-learner with database connection.

        Args:
            db_manager: Database manager for persistent storage of learning data,
                       user profiles, grading history, and strategies.

        Attributes:
            adaptation_rate (float): Learning rate for parameter updates (0-1).
                                    Higher = faster adaptation, lower = more stable.
                                    Default: 0.1 for balanced learning.
            min_samples (int): Minimum number of feedback samples required before
                              adapting strategies. Prevents overfitting to noise.
                              Default: 5 samples.
        """
        self.db = db_manager
        # Learning rate: controls how aggressively we adapt to new feedback
        # 0.1 means we adjust 10% toward new feedback each time
        self.adaptation_rate = 0.1
        # Require at least 5 samples to avoid knee-jerk reactions to single feedbacks
        self.min_samples = 5

    def learn_from_session(
        self,
        user_id: str,
        session_id: str,
        user_feedback_score: Optional[float] = None,
        explicit_feedback: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Learn from a completed grading session

        Args:
            user_id: User identifier
            session_id: Session identifier
            user_feedback_score: Optional user rating (0-10)
            explicit_feedback: Optional structured feedback from user

        Returns:
            Learning results and updated strategies
        """
        session = self.db.get_session()

        try:
            # Get all gradings from this session
            gradings = (
                session.query(GradingHistory)
                .filter(
                    GradingHistory.session_id == session_id,
                    GradingHistory.user_id == user_id,
                )
                .all()
            )

            if not gradings:
                return {"status": "no_data", "message": "No gradings found for session"}

            # Analyze patterns
            insights = self._analyze_session_patterns(gradings, user_feedback_score)

            # Update user-specific strategies
            updated_strategies = self._update_user_strategies(
                session,
                user_id,
                gradings,
                insights,
                user_feedback_score,
                explicit_feedback,
            )

            # Contribute to collective learning
            self._contribute_to_collective_learning(session, gradings, insights)

            session.commit()

            return {
                "status": "success",
                "insights": insights,
                "updated_strategies": updated_strategies,
                "learning_applied": True,
            }

        finally:
            session.close()

    def _analyze_session_patterns(
        self, gradings: List[GradingHistory], user_feedback: Optional[float]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in a grading session

        Args:
            gradings: List of gradings from the session
            user_feedback: Optional user feedback score

        Returns:
            Dictionary of insights
        """
        insights = {
            "dimension_scores": {},
            "avg_score": 0.0,
            "low_performing_dimensions": [],
            "high_performing_dimensions": [],
            "user_satisfaction": user_feedback,
            "score_variance": 0.0,
        }

        if not gradings:
            return insights

        # Calculate dimension-wise scores
        dimension_scores = defaultdict(list)
        for grading in gradings:
            if grading.percentage is not None:  # Safety check
                dimension_scores[grading.dimension].append(grading.percentage)

        insights["dimension_scores"] = {
            dim: np.mean(scores) for dim, scores in dimension_scores.items() if scores
        }

        # Calculate overall stats
        all_scores = [g.percentage for g in gradings if g.percentage is not None]
        if not all_scores:
            return insights  # Safety check
        insights["avg_score"] = np.mean(all_scores)
        insights["score_variance"] = np.var(all_scores)

        # Identify low/high performing dimensions
        threshold_low = 60.0
        threshold_high = 85.0

        for dim, avg_score in insights["dimension_scores"].items():
            if avg_score < threshold_low:
                insights["low_performing_dimensions"].append(
                    {
                        "dimension": dim,
                        "score": avg_score,
                        "gap": threshold_low - avg_score,
                    }
                )
            elif avg_score > threshold_high:
                insights["high_performing_dimensions"].append(
                    {"dimension": dim, "score": avg_score}
                )

        return insights

    def _update_user_strategies(
        self,
        session,
        user_id: str,
        gradings: List[GradingHistory],
        insights: Dict[str, Any],
        user_feedback: Optional[float],
        explicit_feedback: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Update user-specific learning strategies

        Args:
            session: Database session
            user_id: User identifier
            gradings: Gradings from session
            insights: Session insights
            user_feedback: User feedback score
            explicit_feedback: Structured user feedback

        Returns:
            List of updated strategies
        """
        updated = []

        # Get user's historical data
        historical_gradings = (
            session.query(GradingHistory)
            .filter(GradingHistory.user_id == user_id)
            .order_by(GradingHistory.timestamp.desc())
            .limit(100)
            .all()
        )

        if len(historical_gradings) < self.min_samples:
            return updated  # Not enough data yet

        # Strategy 1: Adapt grading weights based on user patterns
        weight_strategy = self._adapt_grading_weights(
            session, user_id, historical_gradings, insights
        )
        if weight_strategy:
            updated.append(weight_strategy)

        # Strategy 2: Personalize feedback based on what helps user improve
        feedback_strategy = self._personalize_feedback(
            session, user_id, historical_gradings, user_feedback, explicit_feedback
        )
        if feedback_strategy:
            updated.append(feedback_strategy)

        # Strategy 3: Adjust thresholds based on user skill level
        threshold_strategy = self._adapt_thresholds(
            session, user_id, historical_gradings, insights
        )
        if threshold_strategy:
            updated.append(threshold_strategy)

        return updated

    def _adapt_grading_weights(
        self,
        session,
        user_id: str,
        historical_gradings: List[GradingHistory],
        insights: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Adapt grading weights based on user improvement patterns

        This implements meta-learning by analyzing which dimensions
        the user improves in and adjusting weights accordingly.
        """
        # Calculate improvement trends per dimension
        dimension_trends = defaultdict(list)

        for grading in historical_gradings:
            if grading.percentage is not None:  # Filter None values
                dimension_trends[grading.dimension].append(
                    {"score": grading.percentage, "timestamp": grading.timestamp}
                )

        # Calculate improvement rates
        improvement_rates = {}
        for dim, scores_data in dimension_trends.items():
            if len(scores_data) < 3:
                continue

            # Sort by timestamp
            scores_data.sort(key=lambda x: x["timestamp"])
            scores = [s["score"] for s in scores_data if s["score"] is not None]

            # Simple linear trend
            if len(scores) >= 3:
                recent_avg = np.mean(scores[-3:])
                older_avg = np.mean(scores[:3])
                improvement_rates[dim] = recent_avg - older_avg

        if not improvement_rates:
            return None

        # Find or create weight adaptation strategy
        strategy = (
            session.query(LearningStrategy)
            .filter(
                LearningStrategy.user_id == user_id,
                LearningStrategy.strategy_type
                == StrategyType.PARAMETER_ADAPTATION.value,
                LearningStrategy.active == True,
            )
            .first()
        )

        if not strategy:
            strategy = LearningStrategy(
                user_id=user_id,
                strategy_type=StrategyType.PARAMETER_ADAPTATION.value,
                dimension="all",
                weights={},
                thresholds={},
            )
            session.add(strategy)

        # Update weights: dimensions with low improvement get higher weight
        # (to focus more attention there)
        new_weights = {}
        for dim, improvement in improvement_rates.items():
            current_weight = strategy.weights.get(dim, 1.0)

            # If improvement is negative or low, increase weight
            if improvement < 5.0:
                new_weight = min(2.0, current_weight + self.adaptation_rate * 0.2)
            else:
                # Good improvement, can reduce weight slightly
                new_weight = max(0.5, current_weight - self.adaptation_rate * 0.1)

            new_weights[dim] = new_weight

        strategy.weights = new_weights
        strategy.times_applied = (strategy.times_applied or 0) + 1
        strategy.updated_at = datetime.utcnow()

        return {
            "strategy_type": "parameter_adaptation",
            "weights": new_weights,
            "improvement_rates": improvement_rates,
        }

    def _personalize_feedback(
        self,
        session,
        user_id: str,
        historical_gradings: List[GradingHistory],
        user_feedback: Optional[float],
        explicit_feedback: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Personalize feedback style based on what helps the user improve

        Meta-learning: learn which feedback style is most effective
        """
        # Find or create feedback personalization strategy
        strategy = (
            session.query(LearningStrategy)
            .filter(
                LearningStrategy.user_id == user_id,
                LearningStrategy.strategy_type
                == StrategyType.FEEDBACK_PERSONALIZATION.value,
                LearningStrategy.active == True,
            )
            .first()
        )

        if not strategy:
            strategy = LearningStrategy(
                user_id=user_id,
                strategy_type=StrategyType.FEEDBACK_PERSONALIZATION.value,
                dimension="all",
                feedback_template="standard",
            )
            session.add(strategy)

        # Analyze user response to different feedback styles
        if user_feedback is not None:
            # Update effectiveness score
            strategy.times_applied = (strategy.times_applied or 0) + 1
            if user_feedback >= 7.0:
                strategy.success_count = (strategy.success_count or 0) + 1

            times_applied = strategy.times_applied or 1
            success_count = strategy.success_count or 0
            strategy.effectiveness_score = (
                success_count / times_applied if times_applied > 0 else 0.0
            )

        # Adjust feedback style based on user preference signals
        if explicit_feedback:
            if explicit_feedback.get("too_detailed"):
                strategy.feedback_template = "standard"
            elif explicit_feedback.get("want_more_detail"):
                strategy.feedback_template = "detailed"
            elif explicit_feedback.get("want_expert_analysis"):
                strategy.feedback_template = "expert"

        strategy.updated_at = datetime.utcnow()

        return {
            "strategy_type": "feedback_personalization",
            "feedback_style": strategy.feedback_template,
            "effectiveness": strategy.effectiveness_score,
        }

    def _adapt_thresholds(
        self,
        session,
        user_id: str,
        historical_gradings: List[GradingHistory],
        insights: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Adapt scoring thresholds based on user skill level

        Meta-learning: adjust thresholds to keep user challenged but not frustrated
        """
        if len(historical_gradings) < self.min_samples:
            return None

        # Calculate user's average performance over time
        recent_scores = [
            g.percentage for g in historical_gradings[:20] if g.percentage is not None
        ]
        if not recent_scores:
            return None  # Safety check
        avg_recent = np.mean(recent_scores)

        # Find or create threshold adaptation strategy
        strategy = (
            session.query(LearningStrategy)
            .filter(
                LearningStrategy.user_id == user_id,
                LearningStrategy.strategy_type == StrategyType.THRESHOLD_TUNING.value,
                LearningStrategy.active == True,
            )
            .first()
        )

        if not strategy:
            strategy = LearningStrategy(
                user_id=user_id,
                strategy_type=StrategyType.THRESHOLD_TUNING.value,
                dimension="all",
                thresholds={},
            )
            session.add(strategy)

        # Adapt thresholds: if user consistently scores high, raise the bar slightly
        # If struggling, lower it slightly (growth mindset)
        new_thresholds = {}

        if avg_recent > 85:
            # User is excelling, can raise standards
            new_thresholds["excellent"] = 90
            new_thresholds["good"] = 80
            new_thresholds["acceptable"] = 70
        elif avg_recent > 70:
            # User is doing well
            new_thresholds["excellent"] = 85
            new_thresholds["good"] = 75
            new_thresholds["acceptable"] = 65
        else:
            # User needs encouragement, slightly lower thresholds
            new_thresholds["excellent"] = 80
            new_thresholds["good"] = 70
            new_thresholds["acceptable"] = 60

        strategy.thresholds = new_thresholds
        strategy.times_applied = (strategy.times_applied or 0) + 1
        strategy.updated_at = datetime.utcnow()

        return {
            "strategy_type": "threshold_tuning",
            "thresholds": new_thresholds,
            "user_avg_score": avg_recent,
        }

    def _contribute_to_collective_learning(
        self, session, gradings: List[GradingHistory], insights: Dict[str, Any]
    ) -> None:
        """
        Contribute session insights to collective learning pool

        This enables global learning across all users
        """
        # This would be more sophisticated in production
        # For now, we're just tracking common patterns

        from database.models import CollectiveLearning

        # Example: Track common low-performing dimensions
        for dim_info in insights.get("low_performing_dimensions", []):
            pattern = (
                session.query(CollectiveLearning)
                .filter(
                    CollectiveLearning.pattern_type == "common_struggle",
                    CollectiveLearning.dimension == dim_info["dimension"],
                )
                .first()
            )

            if pattern:
                pattern.occurrence_count += 1
                pattern.last_seen = datetime.utcnow()
            else:
                pattern = CollectiveLearning(
                    pattern_type="common_struggle",
                    dimension=dim_info["dimension"],
                    pattern_data={"avg_gap": dim_info["gap"]},
                    occurrence_count=1,
                )
                session.add(pattern)

    def get_user_strategies(self, user_id: str) -> Dict[str, Any]:
        """
        Get all active learning strategies for a user

        Args:
            user_id: User identifier

        Returns:
            Dictionary of strategies by type
        """
        session = self.db.get_session()

        try:
            strategies = (
                session.query(LearningStrategy)
                .filter(
                    LearningStrategy.user_id == user_id, LearningStrategy.active == True
                )
                .all()
            )

            result = {}
            for strategy in strategies:
                result[strategy.strategy_type] = {
                    "weights": strategy.weights,
                    "thresholds": strategy.thresholds,
                    "feedback_template": strategy.feedback_template,
                    "effectiveness": strategy.effectiveness_score,
                    "times_applied": strategy.times_applied,
                }

            return result

        finally:
            session.close()

    def update_from_feedback(
        self,
        user_id: str,
        grading_id: str,
        rating: Optional[int] = None,
        comments: Optional[str] = None,
        helpful_suggestions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update meta-learning strategies based on user feedback

        Args:
            user_id: User identifier
            grading_id: The grading session being reviewed
            rating: User rating 1-5 (optional)
            comments: User comments (optional)
            helpful_suggestions: List of helpful suggestion IDs (optional)

        Returns:
            Status of the update
        """
        # Convert rating to feedback score (1-5 -> 2-10 scale)
        feedback_score = (rating * 2) if (rating is not None) else None

        # For now, just trigger learning from the session
        # In a full implementation, this would weight feedback more heavily
        return self.learn_from_session(
            user_id=user_id,
            session_id=grading_id,
            user_feedback_score=feedback_score,
            explicit_feedback={
                "comments": comments,
                "helpful_suggestions": helpful_suggestions or [],
            },
        )

    def apply_strategies_to_grader(self, grader, user_id: str) -> None:
        """
        Apply learned strategies to a grader instance

        Args:
            grader: BaseGrader instance
            user_id: User identifier
        """
        strategies = self.get_user_strategies(user_id)

        # Apply parameter adaptations
        if StrategyType.PARAMETER_ADAPTATION.value in strategies:
            weights = strategies[StrategyType.PARAMETER_ADAPTATION.value]["weights"]
            grader.update_weights(weights)

        # Apply threshold adaptations
        if StrategyType.THRESHOLD_TUNING.value in strategies:
            thresholds = strategies[StrategyType.THRESHOLD_TUNING.value]["thresholds"]
            grader.update_thresholds(thresholds)
