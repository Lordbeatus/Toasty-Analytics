"""
Test multi-dimension grading with server_v2.py
"""

import pytest
import requests

pytestmark = pytest.mark.skip(reason="Requires live server on localhost:8000")


def test_single_dimension():
    """Test grading with single dimension (code_quality)"""
    print("🧪 Test 1: Single Dimension (Code Quality)")

    response = requests.post(
        "http://localhost:8000/grade",
        json={
            "code": "def hello():\n    print('Hello World')",
            "language": "python",
            "user_id": "test-user-123",
            "dimensions": ["code_quality"],
        },
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Score: {data['overall_score']}/100")
        print(f"   Dimensions tested: {list(data['scores'].keys())}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    print()


def test_multi_dimension():
    """Test grading with multiple dimensions"""
    print("🧪 Test 2: Multi-Dimension (Code Quality + Reliability)")

    code = """def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)"""

    response = requests.post(
        "http://localhost:8000/grade",
        json={
            "code": code,
            "language": "python",
            "user_id": "test-user-456",
            "dimensions": ["code_quality", "reliability"],
        },
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Overall Score: {data['overall_score']}/100")
        print(f"   Dimension Scores:")
        for dim, score in data["scores"].items():
            print(f"     - {dim}: {score}/100")
        print(f"   Suggestions: {len(data['improvement_suggestions'])} found")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    print()


def test_with_speed():
    """Test with speed dimension (requires generation_time in context)"""
    print("🧪 Test 3: Speed Dimension (with context)")

    response = requests.post(
        "http://localhost:8000/grade",
        json={
            "code": "print('Fast code')",
            "language": "python",
            "user_id": "test-user-789",
            "dimensions": ["speed"],
            "context": {"generation_time": 2.5},  # 2.5 seconds
        },
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Speed Score: {data['scores']['speed']}/100")
        feedback = data["feedback"]["speed"]
        print(f"   Feedback: {feedback['feedback']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    print()


def test_all_dimensions():
    """Test all three dimensions together"""
    print("🧪 Test 4: All Dimensions (Quality + Speed + Reliability)")

    code = """def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1"""

    response = requests.post(
        "http://localhost:8000/grade",
        json={
            "code": code,
            "language": "python",
            "user_id": "test-user-all",
            "dimensions": ["code_quality", "speed", "reliability"],
            "context": {"generation_time": 3.2},
        },
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Overall Score: {data['overall_score']:.1f}/100")
        print(f"   Dimension Breakdown:")
        for dim, score in data["scores"].items():
            print(f"     - {dim}: {score}/100")
        print(f"   Learning Applied: {data['learning_applied']}")
        print(f"   Cached: {data['cached']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("ToastyAnalytics v2 - Multi-Dimension Grading Tests")
    print("=" * 60)
    print()

    try:
        test_single_dimension()
        test_multi_dimension()
        test_with_speed()
        test_all_dimensions()

        print("=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running?")
        print("   Try: docker-compose up -d")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
