import json

import requests

code = """
def calculate_average(nums):
    total = 0
    for n in nums:
        total += n
    return total / len(nums)

def process_data(data):
    results = []
    for item in data:
        if item > 0:
            if item < 100:
                if item % 2 == 0:
                    results.append(item * 2)
                else:
                    results.append(item * 3)
    return results
"""

r = requests.post(
    "http://localhost:8000/grade",
    json={
        "code": code,
        "language": "python",
        "user_id": "test_ast",
        "dimensions": ["code_quality"],
    },
)

result = r.json()
print("Response:", json.dumps(result, indent=2))

if "overall_score" in result:
    print("\nScore:", result["overall_score"])
    print("\nFeedback:", result["feedback"]["code_quality"]["feedback"])
    print("\nSuggestions:")
    for s in result["improvement_suggestions"]:
        print(f"  - {s['description']}")

    print("\nLine Feedback:")
    line_feedback = result["feedback"]["code_quality"]["breakdown"].get(
        "line_level_feedback", {}
    )
    for line, msg in line_feedback.items():
        print(f"  Line {line}: {msg}")

    print("\nBreakdown:", result["feedback"]["code_quality"]["breakdown"])
else:
    print("Error:", result.get("detail", "Unknown error"))
