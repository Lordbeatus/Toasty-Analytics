"""
Quick WebSocket test for server_v2.py
"""

import asyncio
import json

import pytest
import websockets

pytestmark = pytest.mark.skip(reason="Requires live server and async support")


async def test_websocket():
    uri = "ws://localhost:8000/ws/test-user-123"
    print(f"🔌 Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")

            # Wait for welcome message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 Received: {data}")

            # Keep listening for events
            print("\n👂 Listening for events (press Ctrl+C to stop)...")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"\n🔔 Event received:")
                print(json.dumps(data, indent=2))

    except websockets.exceptions.ConnectionClosed:
        print("❌ Connection closed")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
