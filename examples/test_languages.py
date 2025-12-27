"""
Test ToastyAnalytics with multiple programming languages
"""

import requests

API_URL = "http://localhost:8000"

# Test cases for different languages
test_cases = [
    {
        "name": "Python",
        "code": """
def fibonacci(n):
    '''Calculate Fibonacci number'''
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
        "language": "python",
    },
    {
        "name": "JavaScript",
        "code": """
function fibonacci(n) {
    // Calculate Fibonacci number
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}
""",
        "language": "javascript",
    },
    {
        "name": "Java",
        "code": """
public class Fibonacci {
    /**
     * Calculate Fibonacci number
     */
    public static int fibonacci(int n) {
        if (n <= 1) {
            return n;
        }
        return fibonacci(n - 1) + fibonacci(n - 2);
    }
}
""",
        "language": "java",
    },
    {
        "name": "C++",
        "code": """
// Calculate Fibonacci number
int fibonacci(int n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}
""",
        "language": "cpp",
    },
    {
        "name": "TypeScript",
        "code": """
/**
 * Calculate Fibonacci number
 */
function fibonacci(n: number): number {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}
""",
        "language": "typescript",
    },
]

print("=" * 70)
print("Testing ToastyAnalytics with Multiple Languages")
print("=" * 70)
print()

for test in test_cases:
    print(f"🔍 Testing {test['name']}...")

    try:
        response = requests.post(
            f"{API_URL}/grade",
            json={
                "code": test["code"],
                "language": test["language"],
                "user_id": f"test-{test['language']}",
                "dimensions": ["code_quality"],
            },
        )

        if response.status_code == 200:
            result = response.json()
            score = result["overall_score"]
            print(f"   ✅ Score: {score}/100")
            print(
                f"   Feedback: {result['feedback']['code_quality']['feedback'][:60]}..."
            )
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

    print()

print("=" * 70)
print("✅ Multi-language test complete!")
print("=" * 70)
