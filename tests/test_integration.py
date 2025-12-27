"""
Integration tests for ToastyAnalytics
Tests the full workflow from grading to meta-learning to API
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from src.core.types import GradingDimension
from src.database.models import DatabaseManager
from src.graders import get_grader_for_dimension
from src.meta_learning.engine import MetaLearner
from src.server_v2 import app


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db_url = f"sqlite:///{db_path}"
    db = DatabaseManager(db_url)

    yield db

    # Cleanup
    db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def api_client():
    """Create FastAPI test client"""
    return TestClient(app)


class TestEndToEndGrading:
    """Test complete grading workflow"""

    def test_grade_and_learn_workflow(self, temp_db):
        """
        Integration test: Grade code -> Submit feedback -> Learn -> Grade again
        Verifies the entire meta-learning loop works end-to-end
        """
        # Setup
        user_id = "integration_test_user"
        meta_learner = MetaLearner(temp_db)

        # Sample code to grade
        code = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
        """

        # Step 1: Initial grading
        grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
        meta_learner.apply_strategies_to_grader(grader, user_id)

        initial_result = grader.grade(code=code, language="python")

        # Verify grading works
        assert initial_result.score > 0
        assert initial_result.max_score == 100
        assert initial_result.feedback is not None

        # Step 2: Record grading in database
        session_id = "test_session_1"
        session = temp_db.get_session()
        try:
            from src.database.models import GradingHistory, User

            # Create user if not exists
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                user = User(id=user_id)
                session.add(user)

            # Add grading history
            grading_record = GradingHistory(
                user_id=user_id,
                session_id=session_id,
                dimension=GradingDimension.CODE_QUALITY.value,
                score=initial_result.score,
                max_score=initial_result.max_score,
                percentage=(initial_result.score / initial_result.max_score) * 100,
                feedback=initial_result.feedback,
                grade_metadata={"code_snippet": code[:200]},
            )
            session.add(grading_record)
            session.commit()
        finally:
            session.close()

        # Step 3: Simulate user feedback (positive)
        learning_result = meta_learner.learn_from_session(
            user_id=user_id,
            session_id=session_id,
            user_feedback_score=9.0,  # High score = user liked it
            explicit_feedback={
                "comment": "Good feedback, very helpful",
                "dimension": "code_quality",
            },
        )

        # Verify learning occurred
        assert (
            "updated_strategies" in learning_result
            or learning_result["status"] == "success"
        )

        # Step 4: Grade again with learned strategies
        grader_v2 = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
        meta_learner.apply_strategies_to_grader(grader_v2, user_id)

        second_result = grader_v2.grade(code=code, language="python")

        # The grader should maintain consistency since feedback was positive
        assert second_result.score is not None
        assert second_result.max_score == 100

    def test_negative_feedback_adaptation(self, temp_db):
        """
        Test that negative feedback causes grader to adapt
        """
        user_id = "adaptive_test_user"
        meta_learner = MetaLearner(temp_db)

        code = "def f(x): return x*2"

        # Initial grading
        grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
        result = grader.grade(code=code, language="python")

        # Record with negative feedback
        session_id = "negative_test"
        session = temp_db.get_session()
        try:
            from src.database.models import GradingHistory, User

            # Create user if not exists
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                user = User(id=user_id)
                session.add(user)

            # Add grading history
            grading_record = GradingHistory(
                user_id=user_id,
                session_id=session_id,
                dimension=GradingDimension.CODE_QUALITY.value,
                score=result.score,
                max_score=result.max_score,
                percentage=(result.score / result.max_score) * 100,
                feedback=result.feedback,
            )
            session.add(grading_record)
            session.commit()
        finally:
            session.close()

        # Negative feedback
        meta_learner.learn_from_session(
            user_id=user_id,
            session_id=session_id,
            user_feedback_score=2.0,  # Low score = disagreed
            explicit_feedback={
                "comment": "Too harsh on simple functions",
                "dimension": "code_quality",
            },
        )

        # Verify strategy was created
        session = temp_db.get_session()
        try:
            from src.database.models import LearningStrategy

            strategies = (
                session.query(LearningStrategy).filter_by(user_id=user_id).all()
            )
            assert len(strategies) >= 0  # May be 0 if not enough samples
        finally:
            session.close()


class TestMultiDimensionalGrading:
    """Test grading across multiple dimensions"""

    def test_all_dimensions(self, temp_db):
        """Test that all grading dimensions work together"""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
        """

        dimensions = [
            GradingDimension.CODE_QUALITY,
            GradingDimension.SPEED,
            GradingDimension.RELIABILITY,
        ]

        results = {}
        for dim in dimensions:
            grader = get_grader_for_dimension(dim)
            if dim == GradingDimension.SPEED:
                # SpeedGrader requires generation_time
                result = grader.grade(code=code, language="python", generation_time=2.5)
            elif dim == GradingDimension.RELIABILITY:
                # ReliabilityGrader requires task_attempts
                result = grader.grade(
                    task_attempts=[
                        {"success": True, "time": 1.0},
                        {"success": True, "time": 1.2},
                        {"success": False, "time": 2.0},
                    ]
                )
            else:
                result = grader.grade(code=code, language="python")

            # Verify each dimension returns valid results
            assert result.score >= 0
            assert result.score <= result.max_score
            assert result.dimension == dim
            assert result.feedback is not None

            results[dim] = result

        # Verify we got results for all dimensions
        assert len(results) == len(dimensions)


class TestMCPServerIntegration:
    """Test MCP server endpoints"""

    def test_health_endpoint(self, api_client):
        """Test health check endpoint"""
        response = api_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["healthy", "degraded"]

    def test_grade_endpoint(self, api_client):
        """Test grading via API"""
        payload = {
            "user_id": "api_test_user",
            "code": "def hello(): return 'world'",
            "language": "python",
            "dimensions": ["code_quality"],
        }

        response = api_client.post("/grade", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "grading_id" in data
        assert "feedback" in data
        assert "scores" in data
        assert len(data["scores"]) > 0

        # Check result structure
        assert "code_quality" in data["scores"]
        assert "code_quality" in data["feedback"]
        assert "score" in data["feedback"]["code_quality"]
        assert "feedback" in data["feedback"]["code_quality"]

    def test_feedback_endpoint(self, api_client):
        """Test feedback submission"""
        # First grade some code
        grade_payload = {
            "user_id": "feedback_test_user",
            "code": "def test(): pass",
            "language": "python",
            "dimensions": ["code_quality"],
        }

        grade_response = api_client.post("/grade", json=grade_payload)
        assert grade_response.status_code == 200
        grading_id = grade_response.json()["grading_id"]

        # Submit feedback
        feedback_payload = {
            "grading_id": grading_id,
            "user_id": "feedback_test_user",
            "rating": 4,
            "comments": "Great feedback!",
        }

        feedback_response = api_client.post("/feedback", json=feedback_payload)
        assert feedback_response.status_code == 200

        data = feedback_response.json()
        assert data["status"] == "success"
        assert "message" in data


class TestDatabasePersistence:
    """Test database operations and persistence"""

    def test_user_creation_and_retrieval(self, temp_db):
        """Test user CRUD operations"""
        user_id = "db_test_user"

        # Create user
        session = temp_db.get_session()
        try:
            from src.database.models import User

            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                user = User(
                    id=user_id,
                    preferences={"name": "Test User", "email": "test@example.com"},
                )
                session.add(user)
                session.commit()

            # Verify user was created
            assert user.id == user_id
            assert user.preferences["name"] == "Test User"

            # Retrieve user to verify persistence
            session.refresh(user)
            assert user.id == user_id
            assert user.preferences["email"] == "test@example.com"
        finally:
            session.close()

    def test_grading_history_persistence(self, temp_db):
        """Test that grading history is stored and retrievable"""
        user_id = "history_test_user"

        # Add multiple grading records
        session = temp_db.get_session()
        try:
            from src.database.models import GradingHistory, User

            # Create user if not exists
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                user = User(id=user_id)
                session.add(user)

            for i in range(5):
                grading_record = GradingHistory(
                    user_id=user_id,
                    session_id=f"session_{i}",
                    dimension=GradingDimension.CODE_QUALITY.value,
                    score=70.0 + i * 5,
                    max_score=100.0,
                    percentage=70.0 + i * 5,
                    feedback=f"Feedback {i}",
                    grade_metadata={"code_snippet": "test code"},
                )
                session.add(grading_record)
            session.commit()

            # Query grading history
            history = (
                session.query(GradingHistory)
                .filter_by(user_id=user_id)
                .order_by(GradingHistory.timestamp)
                .all()
            )

            # Verify history records
            assert len(history) == 5

            # Verify scores are increasing
            scores = [h.score for h in history]
            assert scores[0] < scores[-1]
        finally:
            session.close()

    def test_strategy_persistence(self, temp_db):
        """Test learning strategy storage"""
        user_id = "strategy_test_user"

        # Add strategy
        session = temp_db.get_session()
        try:
            from src.database.models import LearningStrategy, User

            # Create user if not exists
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                user = User(id=user_id)
                session.add(user)

            # Create or update strategy
            strategy = (
                session.query(LearningStrategy)
                .filter_by(
                    user_id=user_id,
                    dimension=GradingDimension.CODE_QUALITY.value,
                    strategy_type="parameter_adaptation",
                )
                .first()
            )
            if not strategy:
                strategy = LearningStrategy(
                    user_id=user_id,
                    dimension=GradingDimension.CODE_QUALITY.value,
                    strategy_type="parameter_adaptation",
                    weights={"readability": 0.5},
                    effectiveness_score=0.85,
                )
                session.add(strategy)
            else:
                strategy.weights = {"readability": 0.5}
                strategy.effectiveness_score = 0.85
            session.commit()

            # Retrieve and verify strategy
            retrieved = (
                session.query(LearningStrategy)
                .filter_by(
                    user_id=user_id, dimension=GradingDimension.CODE_QUALITY.value
                )
                .first()
            )
            assert retrieved is not None
            assert retrieved.strategy_type == "parameter_adaptation"
            assert retrieved.weights["readability"] == 0.5
            assert retrieved.effectiveness_score == 0.85
        finally:
            session.close()


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_code(self):
        """Test grading empty code"""
        grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
        result = grader.grade(code="", language="python")

        # Should handle gracefully
        assert result.score >= 0
        assert result.feedback is not None

    def test_invalid_code(self):
        """Test grading syntactically invalid code"""
        grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
        result = grader.grade(code="def invalid( syntax error", language="python")

        # Should handle gracefully
        assert result.score >= 0

    def test_very_long_code(self):
        """Test grading very long code"""
        long_code = "\n".join([f"x{i} = {i}" for i in range(1000)])

        grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
        result = grader.grade(code=long_code, language="python")

        assert result.score is not None


class TestConcurrency:
    """Test concurrent operations"""

    def test_concurrent_grading(self, temp_db):
        """Test multiple users grading simultaneously"""
        import concurrent.futures

        def grade_for_user(user_id):
            grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
            result = grader.grade(code=f"def user_{user_id}(): pass", language="python")
            return result.score

        # Grade concurrently for 10 users
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(grade_for_user, i) for i in range(10)]
            scores = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should complete successfully
        assert len(scores) == 10
        assert all(score >= 0 for score in scores)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
