"""
Basic Usage Examples for ToastyAnalytics
"""

from toastyanalytics import (
    DatabaseManager,
    GradingDimension,
    MetaLearner,
    get_grader_for_dimension,
)


def example_1_basic_grading():
    """Example 1: Basic code grading"""
    print("=" * 60)
    print("Example 1: Basic Code Grading")
    print("=" * 60)

    # Sample code to grade
    code = """
def calculate_average(numbers):
    '''Calculate the average of a list of numbers'''
    if not numbers:
        return 0
    total = sum(numbers)
    count = len(numbers)
    return total / count

# Test
data = [10, 20, 30, 40, 50]
result = calculate_average(data)
print(f"Average: {result}")
    """

    # Get a grader
    grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)

    # Grade the code
    result = grader.grade(code=code, language="python")

    # Display results
    print(f"\nScore: {result.score}/{result.max_score} ({result.percentage:.1f}%)")
    print(f"Feedback: {result.feedback}")
    print(f"\nSuggestions:")
    for i, suggestion in enumerate(result.suggestions, 1):
        print(f"  {i}. [{suggestion.category}] {suggestion.description}")


def example_2_meta_learning():
    """Example 2: Using meta-learning to improve grading"""
    print("\n" + "=" * 60)
    print("Example 2: Meta-Learning")
    print("=" * 60)

    # Initialize database and meta-learner
    db = DatabaseManager()
    meta_learner = MetaLearner(db)

    # Sample code
    code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
    """

    # Get grader and apply learned strategies for this user
    user_id = "demo_user"
    grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
    meta_learner.apply_strategies_to_grader(grader, user_id)

    # Grade
    result = grader.grade(code=code, language="python")
    session_id = "demo_session_1"

    print(f"\nInitial Score: {result.score}/{result.max_score}")

    # Simulate user feedback (they thought it was too harsh)
    meta_learner.learn_from_session(
        user_id=user_id,
        session_id=session_id,
        user_feedback_score=3.0,  # Low score = user disagreed with grading
        explicit_feedback={
            "comment": "Too harsh on simple recursive functions",
            "dimension": "code_quality",
        },
    )

    print("\n✓ Meta-learner adapted based on feedback!")
    print("  Next grading for this user will be less harsh on recursion.")


def example_3_multiple_dimensions():
    """Example 3: Grade across multiple dimensions"""
    print("\n" + "=" * 60)
    print("Example 3: Multiple Grading Dimensions")
    print("=" * 60)

    code = """
def process_data(data_list):
    result = []
    for item in data_list:
        if item > 0:
            result.append(item * 2)
    return result
    """

    dimensions = [
        GradingDimension.CODE_QUALITY,
        GradingDimension.SPEED,
        GradingDimension.RELIABILITY,
    ]

    for dimension in dimensions:
        grader = get_grader_for_dimension(dimension)
        result = grader.grade(code=code, language="python")
        print(f"\n{dimension.value.upper()}: {result.score}/{result.max_score}")


def example_4_custom_weights():
    """Example 4: Using custom weights"""
    print("\n" + "=" * 60)
    print("Example 4: Custom Grading Weights")
    print("=" * 60)

    code = """
def validate_email(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
    """

    # Create grader with custom configuration
    config = {
        "weights": {
            "structure": 0.1,
            "readability": 0.4,  # Emphasize readability
            "best_practices": 0.3,
            "complexity": 0.2,
        }
    }

    grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY, config)
    result = grader.grade(code=code, language="python")

    print(f"\nScore: {result.score}/{result.max_score}")
    print("(With emphasis on readability)")


def example_5_line_level_feedback():
    """Example 5: Line-level feedback"""
    print("\n" + "=" * 60)
    print("Example 5: Line-Level Feedback")
    print("=" * 60)

    code = """
def process(x,y,z):
    # TODO: implement this
    a=x+y
    b=a*z
    return b
    """

    grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
    result = grader.grade(code=code, language="python")

    print(f"\nScore: {result.score}/{result.max_score}")
    print("\nLine-Level Issues:")

    if hasattr(result, "breakdown") and result.breakdown:
        for component, details in result.breakdown.items():
            if "issues" in details:
                for issue in details["issues"]:
                    print(
                        f"  Line {issue.get('line', 'N/A')}: {issue.get('message', 'Issue')}"
                    )


if __name__ == "__main__":
    print("\n🔥 ToastyAnalytics Examples 🔥\n")

    try:
        example_1_basic_grading()
        example_2_meta_learning()
        example_3_multiple_dimensions()
        example_4_custom_weights()
        example_5_line_level_feedback()

        print("\n" + "=" * 60)
        print("✅ All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
