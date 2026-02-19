"""
C3Poh message logger.
"""

import json
from datetime import datetime
from pathlib import Path

from .config import C3PohConfig


class C3PohLogger:
    def __init__(self, config: C3PohConfig):
        self.config = config
        self._path = Path(config.log_file).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, entry: dict):
        if not self.config.log_messages:
            return
        with open(self._path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_message(self, user_id: int, chat_id: int, text: str, direction: str):
        self._write({
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": "message",
            "direction": direction,
            "user_id": user_id,
            "chat_id": chat_id,
            "text_length": len(text),
        })

    def log_blocked(self, user_id: int, chat_id: int):
        self._write({
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": "blocked",
            "user_id": user_id,
            "chat_id": chat_id,
        })
        print(f"[C3Poh] Blocked unauthorized user {user_id}")
