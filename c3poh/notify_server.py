"""
C3Poh local HTTP notification server.
Listens on localhost:7734/notify for POST requests from TinMan and other tools.
Pure stdlib - no Flask, no FastAPI.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable


class NotifyHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for POST /notify"""

    notify_callback: Callable[[str], None] = lambda msg: None  # set by NotifyServer

    def do_POST(self):
        if self.path != "/notify":
            self._respond(404, {"error": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 65536:  # 64 KB max
            self._respond(413, {"error": "Payload too large"})
            return

        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode())
        except json.JSONDecodeError:
            self._respond(400, {"error": "Invalid JSON"})
            return

        # Extract message text from various payload shapes
        # Supports TinMan format, plain text, and generic {"message": "..."}
        message = self._extract_message(payload)
        if not message:
            self._respond(400, {"error": "No message content found"})
            return

        try:
            self.notify_callback(message)
            self._respond(200, {"ok": True})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "service": "c3poh"})
        else:
            self._respond(404, {"error": "Not found"})

    def _extract_message(self, payload: dict) -> str:
        # TinMan heartbeat format
        if "result" in payload and "source" in payload:
            result = payload["result"]
            status = result.get("status", "unknown")
            ts = result.get("timestamp", "")
            output = result.get("output", "")
            error = result.get("error", "")

            icon = {"ok": "✓", "alert": "⚠️", "error": "❌"}.get(status, "?")
            lines = [f"[TinMan] {icon} Heartbeat — {ts}"]
            if output:
                lines.append(output)
            if error:
                lines.append(f"Error: {error}")
            return "\n".join(lines)

        # Plain string
        if isinstance(payload, str):
            return payload

        # Generic {"message": "..."} or {"text": "..."}
        return payload.get("message") or payload.get("text") or ""

    def _respond(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Suppress default BaseHTTPRequestHandler logs (noisy)
        pass


class NotifyServer:
    """
    Runs the notification HTTP server in a daemon thread.
    Binds to localhost only (127.0.0.1) by design.
    """

    def __init__(self, host: str, port: int, callback: Callable[[str], None]):
        self.host = host
        self.port = port
        self.callback = callback
        self._server: HTTPServer = None
        self._thread: threading.Thread = None

    def start(self):
        NotifyHandler.notify_callback = self.callback

        self._server = HTTPServer((self.host, self.port), NotifyHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"[C3Poh] Notify server: http://{self.host}:{self.port}/notify")

    def stop(self):
        if self._server:
            self._server.shutdown()
