"""Tests for the C3Poh notification HTTP server."""

import json
import threading
import time
import urllib.request
import urllib.error

import pytest

from c3poh.notify_server import NotifyServer


@pytest.fixture
def server_port():
    return 17734  # Use different port than default to avoid conflicts in tests


@pytest.fixture
def notify_server(server_port):
    received = []
    srv = NotifyServer(
        host="127.0.0.1",
        port=server_port,
        callback=received.append,
    )
    srv.start()
    time.sleep(0.1)  # let the thread start
    yield srv, received
    srv.stop()


def post(port: int, payload: dict, path: str = "/notify") -> tuple[int, dict]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get(port: int, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class TestNotifyServer:
    def test_health_endpoint(self, notify_server, server_port):
        srv, received = notify_server
        code, body = get(server_port, "/health")
        assert code == 200
        assert body["status"] == "ok"

    def test_plain_message_payload(self, notify_server, server_port):
        srv, received = notify_server
        code, body = post(server_port, {"message": "hello from TinMan"})
        assert code == 200
        assert body["ok"] is True
        assert "hello from TinMan" in received[0]

    def test_tinman_heartbeat_format(self, notify_server, server_port):
        srv, received = notify_server
        payload = {
            "source": "tinman",
            "result": {
                "status": "alert",
                "timestamp": "2025-01-01T00:00:00Z",
                "output": "- Disk space low",
                "error": "",
                "duration_seconds": 2.1,
            }
        }
        code, body = post(server_port, payload)
        assert code == 200
        assert "TinMan" in received[0]
        assert "Disk space low" in received[0]

    def test_tinman_ok_heartbeat_format(self, notify_server, server_port):
        srv, received = notify_server
        payload = {
            "source": "tinman",
            "result": {
                "status": "ok",
                "timestamp": "2025-01-01T00:00:00Z",
                "output": "HEARTBEAT_OK",
                "error": "",
                "duration_seconds": 1.5,
            }
        }
        code, _ = post(server_port, payload)
        assert code == 200
        assert "HEARTBEAT_OK" in received[0]

    def test_unknown_path_returns_404(self, notify_server, server_port):
        srv, _ = notify_server
        code, body = post(server_port, {"message": "test"}, path="/unknown")
        assert code == 404

    def test_invalid_json_returns_400(self, notify_server, server_port):
        srv, _ = notify_server
        req = urllib.request.Request(
            f"http://127.0.0.1:{server_port}/notify",
            data=b"not json at all",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 400

    def test_text_field_payload(self, notify_server, server_port):
        srv, received = notify_server
        code, _ = post(server_port, {"text": "hello via text field"})
        assert code == 200
        assert "hello via text field" in received[0]
