"""
Interactive Tutorial: Testing ToastyAnalytics Meta-Learning
This script helps you complete the immediate next steps!
"""

import json
import time

import requests

API_URL = "http://localhost:8000"

print("=" * 70)
print("📚 ToastyAnalytics - Next Steps Tutorial")
print("=" * 70)
print()

# Step 1: Test with different code samples
print("✅ Step 1: Testing with Different Code Samples")
print("-" * 70)

test_samples = [
    {
        "name": "Simple Function",
        "code": "def add(a, b):\n    return a + b",
        "language": "python",
    },
    {
        "name": "Complex Algorithm",
        "code": """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
""",
        "language": "python",
    },
    {
        "name": "JavaScript Async",
        "code": """
async function fetchData(url) {
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}
""",
        "language": "javascript",
    },
]

results = []
for sample in test_samples:
    print(f"\n🔍 Testing: {sample['name']}")
    response = requests.post(
        f"{API_URL}/grade",
        json={
            "code": sample["code"],
            "language": sample["language"],
            "user_id": "tutorial-user",
            "dimensions": ["code_quality"],
        },
    )

    if response.status_code == 200:
        result = response.json()
        score = result["overall_score"]
        results.append({"name": sample["name"], "score": score})
        print(f"   Score: {score}/100 ✅")
    else:
        print(f"   Error: {response.status_code} ❌")

print("\n✅ Completed: Tested multiple code samples\n")

# Step 2: Send feedback to trigger meta-learning
print("✅ Step 2: Sending Feedback to Trigger Meta-Learning")
print("-" * 70)

# First, get a grading to provide feedback on
print("\n📝 Grading code for feedback test...")
grade_response = requests.post(
    f"{API_URL}/grade",
    json={
        "code": "def process_data(data):\n    # TODO: implement\n    pass",
        "language": "python",
        "user_id": "feedback-user",
        "dimensions": ["code_quality"],
    },
)

if grade_response.status_code == 200:
    grading_result = grade_response.json()
    grading_id = grading_result["grading_id"]
    print(f"   Grading ID: {grading_id}")
    print(f"   Score: {grading_result['overall_score']}/100")

    # Send feedback
    print("\n💬 Sending user feedback...")
    feedback_response = requests.post(
        f"{API_URL}/feedback",
        json={
            "grading_id": grading_id,
            "user_id": "feedback-user",
            "rating": 4,
            "comments": "Good analysis, but would like more specific suggestions",
            "helpful_suggestions": [],
        },
    )

    if feedback_response.status_code == 200:
        feedback_result = feedback_response.json()
        print(f"   ✅ Feedback recorded!")
        print(
            f"   Learning triggered: {feedback_result.get('learning_triggered', False)}"
        )
        if feedback_result.get("updated_strategies"):
            print(
                f"   Updated strategies: {len(feedback_result['updated_strategies'])}"
            )
    else:
        print(f"   ❌ Feedback error: {feedback_response.status_code}")
else:
    print(f"   ❌ Grading error: {grade_response.status_code}")

print("\n✅ Completed: Triggered meta-learning with feedback\n")

# Step 3: Check cache performance
print("✅ Step 3: Monitoring Cache Performance")
print("-" * 70)

print("\n🔄 Testing cache with duplicate requests...")

# Same code, same user - should hit cache on second request
test_code = "def hello(): return 'world'"
user_id = "cache-test-user"

# First request (cache miss)
print("   Request 1 (cache miss expected)...")
start = time.time()
response1 = requests.post(
    f"{API_URL}/grade",
    json={
        "code": test_code,
        "language": "python",
        "user_id": user_id,
        "dimensions": ["code_quality"],
    },
)
time1 = time.time() - start

if response1.status_code == 200:
    result1 = response1.json()
    print(f"   ✅ Time: {time1*1000:.2f}ms | Cached: {result1.get('cached', False)}")

# Second request (cache hit)
print("   Request 2 (cache hit expected)...")
start = time.time()
response2 = requests.post(
    f"{API_URL}/grade",
    json={
        "code": test_code,
        "language": "python",
        "user_id": user_id,
        "dimensions": ["code_quality"],
    },
)
time2 = time.time() - start

if response2.status_code == 200:
    result2 = response2.json()
    print(f"   ✅ Time: {time2*1000:.2f}ms | Cached: {result2.get('cached', False)}")

    if time2 < time1:
        speedup = ((time1 - time2) / time1) * 100
        print(f"   🚀 Cache speedup: {speedup:.1f}%")

print("\n✅ Completed: Cache performance monitored\n")

# Step 4: View Grafana dashboards
print("✅ Step 4: Grafana Dashboards")
print("-" * 70)
print("\n📊 Dashboard should now be auto-loaded!")
print("   URL: http://localhost:3000")
print("   Login: admin / admin")
print("   Look for: 'ToastyAnalytics - AI Code Grading' dashboard")
print()

# Summary
print("=" * 70)
print("🎉 Tutorial Complete!")
print("=" * 70)
print("\n📈 Summary:")
print(f"   • Tested {len(results)} different code samples")
print(f"   • Sent feedback to trigger meta-learning")
print(f"   • Monitored cache performance")
print(f"   • Grafana dashboard is ready at http://localhost:3000")
print()
print("🎯 Immediate Next Steps Completed:")
print("   ✅ Monitor cache performance over time")
print("   ✅ Send feedback to trigger meta-learning")
print("   ✅ Test with different code samples")
print("   ✅ Review Grafana dashboards")
print()
print("📚 Short-term Goals Available:")
print("   → Add more test cases")
print("   → Implement neural network graders")
print("   → Add GraphQL API layer")
print("   → Create VS Code extension integration")
print()
print("Open http://localhost:3000 to see your metrics! 📊")
print("=" * 70)
