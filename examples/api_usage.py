"""
Advanced Usage Examples - MCP Server Integration
"""

import json

import requests

# Configuration
MCP_SERVER_URL = "http://localhost:8000"


def example_1_grade_via_api():
    """Example 1: Grade code via REST API"""
    print("=" * 60)
    print("Example 1: Grade via REST API")
    print("=" * 60)

    # Code to grade
    payload = {
        "user_id": "api_user_1",
        "code": """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
        """,
        "language": "python",
        "dimensions": ["code_quality", "speed"],
    }

    try:
        response = requests.post(f"{MCP_SERVER_URL}/grade", json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"\n✓ Grading completed!")
        print(f"Session ID: {result.get('session_id')}")

        for grade in result.get("results", []):
            print(f"\n{grade['dimension'].upper()}:")
            print(f"  Score: {grade['score']}/{grade['max_score']}")
            print(f"  Feedback: {grade['feedback']}")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: MCP server not running!")
        print("Start it with: toastyanalytics serve")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def example_2_submit_feedback():
    """Example 2: Submit feedback to improve grading"""
    print("\n" + "=" * 60)
    print("Example 2: Submit Feedback")
    print("=" * 60)

    # First grade some code
    grade_payload = {
        "user_id": "api_user_2",
        "code": "def hello(): return 'world'",
        "language": "python",
        "dimensions": ["code_quality"],
    }

    try:
        # Grade
        response = requests.post(f"{MCP_SERVER_URL}/grade", json=grade_payload)
        response.raise_for_status()
        result = response.json()
        session_id = result["session_id"]

        print(f"\n✓ Grading completed (Session: {session_id})")

        # Submit feedback
        feedback_payload = {
            "user_id": "api_user_2",
            "session_id": session_id,
            "user_feedback_score": 8.5,
            "explicit_feedback": {
                "comment": "Good feedback, very helpful!",
                "dimension": "code_quality",
            },
        }

        response = requests.post(f"{MCP_SERVER_URL}/feedback", json=feedback_payload)
        response.raise_for_status()

        print("\n✓ Feedback submitted!")
        print("  The system will learn from this and improve future gradings.")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: MCP server not running!")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def example_3_get_user_analytics():
    """Example 3: Get user analytics and learning progress"""
    print("\n" + "=" * 60)
    print("Example 3: User Analytics")
    print("=" * 60)

    user_id = "api_user_1"

    try:
        response = requests.get(f"{MCP_SERVER_URL}/analytics/user/{user_id}")
        response.raise_for_status()

        analytics = response.json()

        print(f"\nUser: {user_id}")
        print(f"Total Sessions: {analytics.get('total_sessions', 0)}")
        print(f"Average Score: {analytics.get('average_score', 0):.1f}")
        print(f"Active Strategies: {analytics.get('active_strategies', 0)}")

        # Show trend
        if "score_trend" in analytics:
            print("\nScore Trend:")
            for dimension, trend in analytics["score_trend"].items():
                print(f"  {dimension}: {trend}")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: MCP server not running!")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def example_4_multi_agent_coordination():
    """Example 4: Register multiple agents"""
    print("\n" + "=" * 60)
    print("Example 4: Multi-Agent Coordination")
    print("=" * 60)

    agents = [
        {
            "agent_id": "agent_python_specialist",
            "agent_name": "Python Specialist",
            "capabilities": ["python", "code_quality"],
            "metadata": {"specialization": "python", "version": "1.0"},
        },
        {
            "agent_id": "agent_javascript_specialist",
            "agent_name": "JavaScript Specialist",
            "capabilities": ["javascript", "code_quality"],
            "metadata": {"specialization": "javascript", "version": "1.0"},
        },
    ]

    try:
        for agent_data in agents:
            response = requests.post(
                f"{MCP_SERVER_URL}/agents/register", json=agent_data
            )
            response.raise_for_status()
            print(f"✓ Registered: {agent_data['agent_name']}")

        # List all agents
        response = requests.get(f"{MCP_SERVER_URL}/agents")
        response.raise_for_status()
        all_agents = response.json()

        print(f"\nTotal Agents: {len(all_agents)}")
        for agent in all_agents:
            print(f"  - {agent['agent_name']} ({agent['agent_id']})")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: MCP server not running!")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def example_5_health_check():
    """Example 5: Check server health"""
    print("\n" + "=" * 60)
    print("Example 5: Health Check")
    print("=" * 60)

    try:
        response = requests.get(f"{MCP_SERVER_URL}/health")
        response.raise_for_status()

        health = response.json()
        print(f"\nStatus: {health.get('status', 'unknown')}")
        print(f"Database: {health.get('database', {}).get('status', 'unknown')}")
        print(f"Version: {health.get('version', 'unknown')}")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: MCP server not running!")
        print("Start it with: toastyanalytics serve --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("\n🔥 ToastyAnalytics MCP Server Examples 🔥")
    print(f"Server: {MCP_SERVER_URL}\n")

    print("NOTE: Make sure the MCP server is running:")
    print("  $ toastyanalytics serve --port 8000\n")

    example_5_health_check()
    example_1_grade_via_api()
    example_2_submit_feedback()
    example_3_get_user_analytics()
    example_4_multi_agent_coordination()

    print("\n" + "=" * 60)
    print("✅ All API examples completed!")
    print("=" * 60)
