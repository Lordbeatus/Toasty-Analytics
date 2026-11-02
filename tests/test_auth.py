"""Authentication and authorization tests."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from toastyanalytics.api import app
from toastyanalytics.auth.jwt_auth import AuthManager, auth_manager, parse_api_keys

API_KEY_HEADERS = {"X-API-Key": "test-api-key"}


@pytest.fixture
def client():
    return TestClient(app)


def _issue_token(client, user_id="alice", **payload):
    body = {"user_id": user_id, **payload}
    response = client.post("/auth/token", json=body, headers=API_KEY_HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


class TestAPIKeyAuth:
    def test_missing_credentials_are_rejected(self, client):
        response = client.get("/dimensions")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    def test_invalid_api_key_is_rejected(self, client):
        response = client.get("/dimensions", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    def test_api_key_grants_scoped_access(self, client):
        response = client.get("/dimensions", headers=API_KEY_HEADERS)
        assert response.status_code == 200
        names = {dim["name"] for dim in response.json()["dimensions"]}
        assert "accuracy" in names
        assert "prompt_quality" in names

    def test_public_endpoints_need_no_credentials(self, client):
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 200


class TestTokenIssuance:
    def test_token_requires_api_key(self, client):
        response = client.post("/auth/token", json={"user_id": "alice"})
        assert response.status_code == 401

    def test_issue_and_use_token(self, client):
        tokens = _issue_token(client)

        me = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert me.status_code == 200
        assert me.json()["user_id"] == "alice"
        assert me.json()["auth_type"] == "jwt"
        assert me.json()["roles"] == []

    def test_token_grants_api_access(self, client):
        tokens = _issue_token(client)
        response = client.get(
            "/dimensions",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200

    def test_refresh_mints_new_access_token(self, client):
        tokens = _issue_token(client)
        refreshed = client.post(
            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["access_token"] != tokens["access_token"]

    def test_refresh_token_is_not_an_access_token(self, client):
        tokens = _issue_token(client)
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        )
        assert response.status_code == 401

    def test_garbage_token_is_rejected(self, client):
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer not-a-token"}
        )
        assert response.status_code == 401

    def test_expired_token_is_rejected(self, client):
        expired_manager = AuthManager(access_ttl_minutes=-1)
        token = expired_manager.create_access_token("alice", ["*"], [])
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_rejects_unknown_scopes(self, client):
        response = client.post(
            "/auth/token",
            json={"user_id": "alice", "scopes": ["not:a:scope"]},
            headers=API_KEY_HEADERS,
        )
        assert response.status_code == 400


class TestAuthorization:
    def test_scope_is_enforced(self, client):
        token = auth_manager.create_access_token("limited", ["grade:read"], [])
        headers = {"Authorization": f"Bearer {token}"}

        assert client.get("/dimensions", headers=headers).status_code == 200

        response = client.post(
            "/grade",
            json={
                "user_id": "limited",
                "code": "def f(): pass",
                "language": "python",
                "dimensions": ["code_quality"],
            },
            headers=headers,
        )
        assert response.status_code == 403

    def test_cannot_grade_for_another_user(self, client):
        tokens = _issue_token(client, user_id="alice")
        response = client.post(
            "/grade",
            json={
                "user_id": "bob",
                "code": "def f(): pass",
                "language": "python",
                "dimensions": ["code_quality"],
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 403

    def test_cannot_read_another_users_analytics(self, client):
        tokens = _issue_token(client, user_id="alice")
        response = client.get(
            "/analytics/user/bob",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 403

    def test_admin_token_can_access_other_users(self, client):
        tokens = _issue_token(client, user_id="operator", roles=["admin"])
        assert tokens
        response = client.get(
            "/analytics/user/bob",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        # Admin passes the ownership check; bob may still not exist.
        assert response.status_code in (200, 404)


class TestWebSocketAuth:
    def test_connection_requires_credentials(self, client):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/alice"):
                pass

    def test_token_query_parameter_is_accepted(self, client):
        tokens = _issue_token(client, user_id="alice")
        with client.websocket_connect(
            f"/ws/alice?token={tokens['access_token']}"
        ) as ws:
            ws.send_text("ping")
            assert ws.receive_json()["type"] == "ack"

    def test_cannot_connect_as_another_user(self, client):
        tokens = _issue_token(client, user_id="alice")
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws/bob?token={tokens['access_token']}"):
                pass


class TestAPIKeyParsing:
    def test_parses_roles_and_scopes(self):
        records = parse_api_keys("k1:alice:admin:*,k2:ci::grade:read|analytics:read")
        assert records["k1"].user_id == "alice"
        assert records["k1"].scopes == ("*",)
        assert records["k1"].roles == ("admin",)
        assert records["k2"].scopes == ("grade:read", "analytics:read")
        assert records["k2"].roles == ()

    def test_rejects_malformed_entries(self):
        with pytest.raises(ValueError):
            parse_api_keys("missing-parts")

    def test_rejects_unknown_scopes(self):
        with pytest.raises(ValueError):
            parse_api_keys("k1:alice::make:coffee")
