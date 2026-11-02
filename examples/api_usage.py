"""
HTTP API examples.

Start the server first (with a .env copied from .env.example):

    cp .env.example .env
    uvicorn toastyanalytics.api:app --port 8000

Then run this file:

    python examples/api_usage.py

Set TOASTY_API_KEY if your server uses a key other than the development default.
"""

import os

import requests

API_URL = os.getenv("TOASTY_API_URL", "http://localhost:8000")
API_KEY = os.getenv("TOASTY_API_KEY", "dev-local-key")
USER_ID = "example-user"

session = requests.Session()


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def authenticate():
    """Exchange the API key for a user-scoped JWT and attach it to the session."""
    section("Authenticate")

    response = session.post(
        f"{API_URL}/auth/token",
        json={"user_id": USER_ID},
        headers={"X-API-Key": API_KEY},
        timeout=30,
    )
    if response.status_code in (401, 403):
        raise SystemExit(
            f"Authentication failed ({response.status_code}). Set TOASTY_API_KEY "
            "to a key configured in TOASTY_API_KEYS; .env.example defines "
            "'dev-local-key'."
        )
    response.raise_for_status()

    token = response.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print(f"Authenticated as {USER_ID}")


def example_1_grade():
    """Grade a snippet and print the scores."""
    section("Example 1: Grade code")

    response = session.post(
        f"{API_URL}/grade",
        json={
            "user_id": USER_ID,
            "code": "def add(a, b):\n    return a + b\n",
            "language": "python",
            "dimensions": ["code_quality"],
        },
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    print(f"Grading ID: {result['grading_id']}")
    print(f"Overall score: {result['overall_score']}")
    for dimension, score in result["scores"].items():
        print(f"  {dimension}: {score}")
    return result["grading_id"]


def example_2_feedback(grading_id):
    """Send feedback so the meta-learner can adapt."""
    section("Example 2: Submit feedback")

    response = session.post(
        f"{API_URL}/feedback",
        json={
            "grading_id": grading_id,
            "user_id": USER_ID,
            "rating": 4,
            "comments": "Useful suggestions, slightly strict on naming.",
        },
        timeout=30,
    )
    response.raise_for_status()
    print(response.json())


def example_3_analytics():
    """Read the aggregated analytics for a user."""
    section("Example 3: User analytics")

    response = session.get(f"{API_URL}/analytics/user/{USER_ID}", timeout=30)
    response.raise_for_status()
    print(response.json())


def example_4_dimensions():
    """List the grading dimensions the service supports."""
    section("Example 4: Available dimensions")

    response = session.get(f"{API_URL}/dimensions", timeout=30)
    response.raise_for_status()
    for dimension in response.json()["dimensions"]:
        print(f"  {dimension['name']}: {dimension['description']}")


def example_5_health():
    """Check that the service and its database are up."""
    section("Example 5: Health check")

    # Health is public and needs no credentials.
    response = requests.get(f"{API_URL}/health", timeout=30)
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    try:
        authenticate()
        grading_id = example_1_grade()
        example_2_feedback(grading_id)
        example_3_analytics()
        example_4_dimensions()
        example_5_health()
        print("\nAll examples completed.")
    except requests.ConnectionError:
        print(
            f"Could not reach {API_URL}. "
            "Start the server with: uvicorn toastyanalytics.api:app --port 8000"
        )
    except requests.HTTPError as exc:
        print(f"Request failed: {exc.response.status_code} {exc.response.text}")
