"""
Quick test script for ToastyAnalytics API
Run this to verify everything is working!
"""

import json

import requests

# API endpoint
API_URL = "http://localhost:8000"


def grade_code(code, user_id="test-user", dimensions=None):
    """Grade a code snippet"""
    if dimensions is None:
        dimensions = ["code_quality"]

    response = requests.post(
        f"{API_URL}/grade",
        json={
            "code": code,
            "language": "python",
            "user_id": user_id,
            "dimensions": dimensions,
        },
    )

    return response.json()


# Example 1: Simple code
print("=" * 60)
print("Test 1: Simple Hello World")
print("=" * 60)
result = grade_code("def hello():\n    print('Hello World')")
print(f"Score: {result['overall_score']}/100")
print(f"Feedback: {result['feedback']['code_quality']['feedback']}")
print()

# Example 2: Multi-dimension grading
print("=" * 60)
print("Test 2: Binary Search (All Dimensions)")
print("=" * 60)
code = """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""

result = grade_code(
    code, user_id="advanced-user", dimensions=["code_quality", "reliability"]
)

print(f"Overall Score: {result['overall_score']}/100")
print("\nDimension Scores:")
for dim, score in result["scores"].items():
    print(f"  - {dim}: {score}/100")

print(f"\nSuggestions: {len(result['improvement_suggestions'])}")
print()

# Example 3: Check API health
print("=" * 60)
print("System Health Check")
print("=" * 60)
health = requests.get(f"{API_URL}/health").json()
print(f"Status: {health['status']}")
print(f"Services:")
for service, status in health["services"].items():
    print(f"  - {service}: {status}")
