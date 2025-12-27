"""
Quick test script to verify ToastyAnalytics V2 is working
Tests the real grading logic and event system
"""

import json
import threading
import time

import pytest
import requests

try:
    import websocket

    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    websocket = None

BASE_URL = "http://localhost:8000"

pytestmark = pytest.mark.skip(reason="Requires live server on localhost:8000")


def test_health():
    """Test health endpoint"""
    print("\n🏥 Testing Health Endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_dimensions():
    """Test dimensions endpoint"""
    print("\n📊 Testing Dimensions Endpoint...")
    response = requests.get(f"{BASE_URL}/dimensions")
    print(f"Status: {response.status_code}")
    print(f"Available dimensions: {response.json()}")
    return response.status_code == 200


def test_grading():
    """Test grading with real code"""
    print("\n🎯 Testing Grading Endpoint...")

    test_code = """
def calculate_fibonacci(n):
    '''Calculate nth Fibonacci number'''
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

# Test the function
result = calculate_fibonacci(10)
print(f"Fibonacci(10) = {result}")
"""

    payload = {
        "code": test_code,
        "language": "python",
        "dimensions": ["code_quality", "speed", "reliability"],
    }

    print(f"Sending code for grading...")
    response = requests.post(
        f"{BASE_URL}/grade", json=payload, headers={"Content-Type": "application/json"}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"\n📈 Grading Results:")
        print(f"Overall Score: {result.get('overall_score', 'N/A')}")
        print(f"\nDimension Scores:")
        for dim, score in result.get("dimension_scores", {}).items():
            print(f"  - {dim}: {score:.2f}")
        print(f"\nRecommendations:")
        for rec in result.get("recommendations", []):
            print(f"  • {rec}")
    else:
        print(f"Error: {response.text}")

    return response.status_code == 200


@pytest.mark.skipif(not WEBSOCKET_AVAILABLE, reason="websocket-client not installed")
def test_websocket():
    """Test WebSocket connection"""
    print("\n🔌 Testing WebSocket Connection...")

    messages_received = []

    def on_message(ws, message):
        print(f"📨 Received: {message}")
        messages_received.append(message)

    def on_error(ws, error):
        print(f"❌ Error: {error}")

    def on_close(ws, close_status_code, close_msg):
        print(f"🔒 Connection closed")

    def on_open(ws):
        print(f"✅ WebSocket connected!")
        # Send a test message
        ws.send(json.dumps({"type": "ping"}))

    try:
        ws_url = "ws://localhost:8000/ws/test_user"
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        # Run WebSocket in separate thread
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

        # Wait a bit for connection
        time.sleep(2)

        # Close connection
        ws.close()

        return True
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 ToastyAnalytics V2 - Comprehensive Test Suite")
    print("=" * 60)

    results = {
        "Health Check": test_health(),
        "Dimensions": test_dimensions(),
        "Grading": test_grading(),
        "WebSocket": test_websocket(),
    }

    print("\n" + "=" * 60)
    print("📋 Test Results Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All tests passed! System is fully operational.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")

    return all_passed


if __name__ == "__main__":
    # Install websocket-client if needed
    try:
        import websocket
    except ImportError:
        print("Installing websocket-client...")
        import subprocess

        subprocess.check_call(["pip", "install", "websocket-client"])
        import websocket

    success = run_all_tests()
    exit(0 if success else 1)
