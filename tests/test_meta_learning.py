"""
Tests for meta-learning engine
"""

from datetime import datetime, timedelta

from src.core.types import LearningStrategy as StrategyType
from src.database.models import GradingHistory, User
from src.meta_learning.engine import MetaLearner


class TestMetaLearner:
    """Tests for MetaLearner"""

    def test_initialization(self, db_manager):
        """Test meta-learner initialization"""
        learner = MetaLearner(db_manager)
        assert learner.db == db_manager
        assert learner.adaptation_rate == 0.1
        assert learner.min_samples == 5

    def test_learn_from_session_no_data(self, meta_learner):
        """Test learning with no grading data"""
        result = meta_learner.learn_from_session(
            user_id="test_user", session_id="session_1"
        )

        assert result["status"] == "no_data"

    def test_learn_from_session_insufficient_data(self, meta_learner, db_manager):
        """Test learning with insufficient historical data"""
        session = db_manager.get_session()

        # Create user
        user = User(id="test_user")
        session.add(user)

        # Add only 2 gradings (below min_samples of 5)
        for i in range(2):
            grading = GradingHistory(
                user_id="test_user",
                session_id="session_1",
                dimension="code_quality",
                score=75,
                max_score=100,
                percentage=75,
                breakdown={},
                feedback="Test feedback",
            )
            session.add(grading)

        session.commit()
        session.close()

        result = meta_learner.learn_from_session(
            user_id="test_user", session_id="session_1"
        )

        # Should not update strategies due to insufficient data
        assert "insights" in result

    def test_learn_from_session_with_data(self, meta_learner, db_manager):
        """Test learning with sufficient historical data"""
        session = db_manager.get_session()

        # Create user
        user = User(id="test_user2")
        session.add(user)
        session.flush()

        # Add historical gradings (>= min_samples)
        base_time = datetime.utcnow() - timedelta(days=10)
        for i in range(10):
            grading = GradingHistory(
                user_id="test_user2",
                session_id=f"session_{i}",
                dimension="code_quality",
                score=70 + i * 2,  # Improving scores
                max_score=100,
                percentage=70 + i * 2,
                breakdown={},
                feedback="Test feedback",
                timestamp=base_time + timedelta(days=i),
            )
            session.add(grading)

        # Add current session gradings
        for dim in ["code_quality", "speed"]:
            grading = GradingHistory(
                user_id="test_user2",
                session_id="current_session",
                dimension=dim,
                score=85,
                max_score=100,
                percentage=85,
                breakdown={},
                feedback="Current feedback",
            )
            session.add(grading)

        session.commit()
        session.close()

        result = meta_learner.learn_from_session(
            user_id="test_user2", session_id="current_session", user_feedback_score=8.0
        )

        assert result["status"] == "success"
        assert "insights" in result
        assert "updated_strategies" in result
        assert result["learning_applied"] is True

    def test_get_user_strategies(self, meta_learner, db_manager):
        """Test retrieving user strategies"""
        session = db_manager.get_session()

        # Create user with a strategy
        user = User(id="test_user3")
        session.add(user)
        session.flush()

        from src.database.models import LearningStrategy

        strategy = LearningStrategy(
            user_id="test_user3",
            strategy_type=StrategyType.PARAMETER_ADAPTATION.value,
            dimension="all",
            weights={"structure": 0.3, "readability": 0.3},
            thresholds={"excellent": 90},
            effectiveness_score=0.85,
            times_applied=10,
        )
        session.add(strategy)
        session.commit()
        session.close()

        strategies = meta_learner.get_user_strategies("test_user3")

        assert StrategyType.PARAMETER_ADAPTATION.value in strategies
        assert (
            strategies[StrategyType.PARAMETER_ADAPTATION.value]["effectiveness"] == 0.85
        )
        assert (
            strategies[StrategyType.PARAMETER_ADAPTATION.value]["times_applied"] == 10
        )

    def test_apply_strategies_to_grader(self, meta_learner, db_manager):
        """Test applying learned strategies to a grader"""
        from src.database.models import LearningStrategy
        from src.graders import CodeQualityGraderV2

        session = db_manager.get_session()

        # Create user with strategies
        user = User(id="test_user4")
        session.add(user)
        session.flush()

        # Add parameter adaptation strategy
        strategy = LearningStrategy(
            user_id="test_user4",
            strategy_type=StrategyType.PARAMETER_ADAPTATION.value,
            dimension="all",
            weights={"structure": 0.5, "readability": 0.3},
            thresholds={"excellent": 95},
        )
        session.add(strategy)

        # Add threshold tuning strategy
        threshold_strategy = LearningStrategy(
            user_id="test_user4",
            strategy_type=StrategyType.THRESHOLD_TUNING.value,
            dimension="all",
            thresholds={"excellent": 90, "good": 80},
        )
        session.add(threshold_strategy)

        session.commit()
        session.close()

        # Create grader and apply strategies
        grader = CodeQualityGraderV2()

        meta_learner.apply_strategies_to_grader(grader, "test_user4")

        # Check that weights were updated
        updated_weights = grader.get_weights()
        assert updated_weights["structure"] == 0.5
        assert updated_weights["readability"] == 0.3

        # Check that thresholds were updated
        updated_thresholds = grader.get_thresholds()
        assert updated_thresholds["excellent"] == 90
        assert updated_thresholds["good"] == 80


class TestSessionAnalysis:
    """Tests for session pattern analysis"""

    def test_analyze_session_patterns(self, meta_learner, db_manager):
        """Test session pattern analysis"""
        session = db_manager.get_session()

        # Create gradings for a session
        gradings = []
        for i, (dim, score) in enumerate(
            [("code_quality", 85), ("speed", 55), ("reliability", 90)]  # Low performing
        ):
            grading = GradingHistory(
                user_id="test_user",
                session_id="test_session",
                dimension=dim,
                score=score,
                max_score=100,
                percentage=score,
                breakdown={},
                feedback="Test",
            )
            session.add(grading)
            gradings.append(grading)

        session.flush()

        insights = meta_learner._analyze_session_patterns(gradings, user_feedback=8.0)

        assert "dimension_scores" in insights
        assert "avg_score" in insights
        assert "low_performing_dimensions" in insights
        assert "high_performing_dimensions" in insights

        # Speed should be in low performing (55 < 60 threshold)
        low_dims = [d["dimension"] for d in insights["low_performing_dimensions"]]
        assert "speed" in low_dims

        session.close()
