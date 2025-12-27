"""
Tests for core graders
"""

from src.core.types import GradingDimension
from src.graders import CodeQualityGraderV2, ReliabilityGrader, SpeedGrader


class TestCodeQualityGrader:
    """Tests for CodeQualityGraderV2"""

    def test_grade_good_code(self, sample_code):
        """Test grading of well-written code"""
        grader = CodeQualityGraderV2()
        result = grader.grade(code=sample_code, language="python")

        assert result.dimension == GradingDimension.CODE_QUALITY
        assert result.score > 70  # Should score reasonably well
        assert result.max_score == 100
        assert result.feedback is not None
        assert len(result.suggestions) >= 0

    def test_grade_bad_code(self, bad_code):
        """Test grading of poorly written code"""
        grader = CodeQualityGraderV2()
        result = grader.grade(code=bad_code, language="python")

        assert result.dimension == GradingDimension.CODE_QUALITY
        assert result.score < 70  # Should score poorly
        assert len(result.suggestions) > 0  # Should have suggestions
        assert "improvement" in result.feedback.lower()

    def test_weight_updates(self):
        """Test that grader weights can be updated"""
        grader = CodeQualityGraderV2()

        original_weights = grader.get_weights()
        assert "structure" in original_weights

        new_weights = {"structure": 0.5}
        grader.update_weights(new_weights)

        updated_weights = grader.get_weights()
        assert updated_weights["structure"] == 0.5

    def test_threshold_updates(self):
        """Test that grader thresholds can be updated"""
        grader = CodeQualityGraderV2()

        original_thresholds = grader.get_thresholds()
        assert "excellent" in original_thresholds

        new_thresholds = {"excellent": 95}
        grader.update_thresholds(new_thresholds)

        updated_thresholds = grader.get_thresholds()
        assert updated_thresholds["excellent"] == 95

    def test_line_level_feedback(self, bad_code):
        """Test that line-level feedback is generated"""
        grader = CodeQualityGraderV2()
        result = grader.grade(code=bad_code, language="python")

        assert result.breakdown.line_level_feedback is not None
        # Bad code should have some line-level feedback
        assert len(result.breakdown.line_level_feedback) > 0


class TestSpeedGrader:
    """Tests for SpeedGrader"""

    def test_excellent_speed(self):
        """Test grading of excellent speed"""
        grader = SpeedGrader()
        result = grader.grade(generation_time=3.0)

        assert result.dimension == GradingDimension.SPEED
        assert result.score == 100
        assert "Excellent" in result.feedback

    def test_slow_speed(self):
        """Test grading of slow generation"""
        grader = SpeedGrader()
        result = grader.grade(generation_time=45.0)

        assert result.dimension == GradingDimension.SPEED
        assert result.score < 70
        assert len(result.suggestions) > 0

    def test_very_slow_speed(self):
        """Test grading of very slow generation"""
        grader = SpeedGrader()
        result = grader.grade(generation_time=120.0)

        assert result.score <= 40
        assert "Slow" in result.metadata["tier"]


class TestReliabilityGrader:
    """Tests for ReliabilityGrader"""

    def test_perfect_reliability(self):
        """Test grading of perfect reliability"""
        attempts = [
            {"success": True, "score": 95},
            {"success": True, "score": 93},
            {"success": True, "score": 97},
        ]

        grader = ReliabilityGrader()
        result = grader.grade(task_attempts=attempts)

        assert result.dimension == GradingDimension.RELIABILITY
        assert result.score > 90  # Should be very high
        assert result.metadata["success_rate"] == 100

    def test_poor_reliability(self):
        """Test grading of poor reliability"""
        attempts = [
            {"success": True, "score": 80},
            {"success": False, "score": 20},
            {"success": False, "score": 30},
            {"success": True, "score": 75},
        ]

        grader = ReliabilityGrader()
        result = grader.grade(task_attempts=attempts)

        assert result.score < 80  # Should be lower
        assert result.metadata["success_rate"] == 50  # 2/4
        assert len(result.suggestions) > 0

    def test_empty_attempts(self):
        """Test grading with no attempts"""
        grader = ReliabilityGrader()
        result = grader.grade(task_attempts=[])

        assert result.score == 0
        assert "No" in result.feedback

    def test_consistency_scoring(self):
        """Test that consistency affects score"""
        # High variance attempts
        inconsistent_attempts = [
            {"success": True, "score": 100},
            {"success": True, "score": 20},
            {"success": True, "score": 90},
            {"success": True, "score": 30},
        ]

        # Low variance attempts
        consistent_attempts = [
            {"success": True, "score": 85},
            {"success": True, "score": 87},
            {"success": True, "score": 86},
            {"success": True, "score": 88},
        ]

        grader = ReliabilityGrader()
        inconsistent_result = grader.grade(task_attempts=inconsistent_attempts)
        consistent_result = grader.grade(task_attempts=consistent_attempts)

        # Consistent attempts should score higher
        assert consistent_result.score > inconsistent_result.score
