"""
Test that grading actually differentiates between code quality levels
"""

import json

import requests

API_BASE = "http://localhost:8000"

test_cases = [
    ("Minimal (bad)", "def add(a, b): return a + b"),
    (
        "With docstring",
        """
def multiply(a, b):
    '''Multiply two numbers'''
    return a * b
""",
    ),
    (
        "With type hints + docstring",
        """
def divide(a: float, b: float) -> float:
    '''Divide two numbers with error handling'''
    if b == 0:
        raise ValueError('Cannot divide by zero')
    return a / b
""",
    ),
    (
        "Production quality",
        """
def process_data(items: list) -> dict:
    '''
    Process a list of items and return statistics.
    
    Args:
        items: List of numeric values to process
        
    Returns:
        Dictionary containing count, total, and average
        
    Raises:
        ValueError: If items list is invalid
    '''
    if not items:
        raise ValueError('Items list cannot be empty')
    
    if not all(isinstance(x, (int, float)) for x in items):
        raise TypeError('All items must be numeric')
    
    total_sum = sum(items)
    item_count = len(items)
    
    return {
        'count': item_count,
        'total': total_sum,
        'average': total_sum / item_count
    }
""",
    ),
]

print("=" * 70)
print("GRADING DIFFERENTIATION TEST")
print("=" * 70)
print("\nTesting if grader actually differentiates code quality...\n")

for name, code in test_cases:
    response = requests.post(
        f"{API_BASE}/grade",
        json={
            "code": code,
            "language": "python",
            "user_id": "differentiation-test",
            "dimensions": ["code_quality", "readability"],
        },
    )

    if response.status_code == 200:
        data = response.json()
        print(
            f"{name:25} | Overall: {data['overall_score']:5.1f} | CQ: {data['scores']['code_quality']:5.1f} | Read: {data['scores']['readability']:5.1f}"
        )
    else:
        print(f"{name:25} | ERROR: {response.status_code}")

print("\n" + "=" * 70)
print("If scores are all the same, the grader is BROKEN")
print("If scores vary by quality, it's WORKING")
print("=" * 70)
