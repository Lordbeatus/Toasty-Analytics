"""
Simple script to test the meta-learning feedback loop!

This shows you exactly how to:
1. Grade some code
2. Send feedback on the grading
3. See the meta-learning system adapt
"""

import json
import time
from datetime import datetime

import requests

API_BASE = "http://localhost:8000"
USER_ID = "test-user-123"


def print_header(text):
    """Print a nice header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def grade_code(code, language="python", user_id=USER_ID):
    """Grade a piece of code"""
    print(f"\n📝 Grading {language} code...")
    print(f"Code:\n{code[:100]}..." if len(code) > 100 else f"Code:\n{code}")

    response = requests.post(
        f"{API_BASE}/grade",
        json={
            "code": code,
            "language": language,
            "user_id": user_id,
            "dimensions": [
                "code_quality"
            ],  # Valid dimensions: code_quality, speed, reliability, efficiency
        },
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Grading ID: {result['grading_id']}")
        print(f"📊 Overall Score: {result.get('overall_score', 0):.1f}/100")
        feedback_text = result.get("feedback", "No feedback provided")
        if isinstance(feedback_text, str):
            print(f"💬 Feedback: {feedback_text[:150]}...")
        else:
            print(f"💬 Feedback: {str(feedback_text)[:150]}...")
        return result
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None


def send_feedback(
    grading_id, rating, comments="", helpful_suggestions=None, user_id=USER_ID
):
    """Send feedback on a grading to trigger meta-learning"""
    print(f"\n💭 Sending feedback...")
    print(f"   Rating: {rating}/5 ⭐")
    if comments:
        print(f"   Comments: {comments}")

    response = requests.post(
        f"{API_BASE}/feedback",
        json={
            "grading_id": grading_id,
            "user_id": user_id,
            "rating": rating,  # 1-5 scale
            "comments": comments,
            "helpful_suggestions": helpful_suggestions or [],
        },
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Feedback recorded!")
        print(f"   Message: {result.get('message', 'Success')}")
        if "meta_learning" in result:
            print(f"   🧠 Meta-learning triggered: {result['meta_learning']}")
        return result
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None


def main():
    print_header("🧪 Testing Meta-Learning Feedback Loop")

    # Test 1: Grade a simple function
    print_header("Test 1: Grade Simple Function")
    code1 = """
def calculate_average(numbers):
    return sum(numbers) / len(numbers)
"""
    result1 = grade_code(code1)

    if result1:
        time.sleep(1)
        # Send positive feedback
        send_feedback(
            result1["grading_id"],
            rating=5,
            comments="Great analysis! Very helpful suggestions.",
        )

    # Test 2: Grade a more complex function
    print_header("Test 2: Grade Complex Function")
    code2 = """
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
    result2 = grade_code(code2)

    if result2:
        time.sleep(1)
        # Send moderate feedback
        send_feedback(
            result2["grading_id"],
            rating=4,
            comments="Good, but could provide more performance insights.",
            helpful_suggestions=["Mention memoization for optimization"],
        )

    # Test 3: Grade code with issues
    print_header("Test 3: Grade Code With Issues")
    code3 = """
def process_data(x):
    # TODO: implement this
    pass
"""
    result3 = grade_code(code3)

    if result3:
        time.sleep(1)
        # Send critical feedback
        send_feedback(
            result3["grading_id"],
            rating=2,
            comments="Should detect that this is incomplete code.",
        )

    # Test 4: Re-grade similar code to see if meta-learning adapted
    print_header("Test 4: Re-grade Similar Code (Testing Adaptation)")
    code4 = """
def calculate_sum(numbers):
    return sum(numbers)
"""
    result4 = grade_code(code4)

    print_header("✨ Summary")
    print(
        """
The meta-learning system is now learning from your feedback!

What happened:
1. ✅ Graded 4 different code samples
2. ✅ Sent feedback with ratings (5, 4, 2 stars)
3. ✅ Meta-learning system adjusted its strategies based on your input

Next steps:
- Check the database to see learning records
- Grade more code - it should adapt to your preferences over time
- Monitor in Grafana: http://localhost:3000

The more feedback you provide, the smarter it gets! 🧠
"""
    )


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API at http://localhost:8000")
        print("   Make sure all containers are running:")
        print("   docker-compose ps")
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
