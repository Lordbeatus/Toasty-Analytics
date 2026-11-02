import pytest

from toastyanalytics.api import ConnectionManager


class _BrokenWebSocket:
    async def send_json(self, message):
        raise RuntimeError("socket closed")


@pytest.mark.asyncio
async def test_send_personal_message_removes_broken_connection():
    manager = ConnectionManager()
    ws = _BrokenWebSocket()
    user_id = "user-1"
    manager.active_connections[user_id] = {ws}

    await manager.send_personal_message({"type": "test"}, user_id)

    assert user_id not in manager.active_connections


@pytest.mark.asyncio
async def test_broadcast_removes_broken_connections():
    manager = ConnectionManager()
    ws = _BrokenWebSocket()
    user_id = "user-2"
    manager.active_connections[user_id] = {ws}

    await manager.broadcast({"type": "test"})

    assert user_id not in manager.active_connections
