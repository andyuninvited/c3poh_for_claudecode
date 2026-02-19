"""
C3Poh state management.
Persists pairing owner and other runtime state to disk.
"""

import json
from pathlib import Path
from typing import Optional

from .config import C3PohConfig


class C3PohState:
    def __init__(self, config: C3PohConfig):
        self._path = Path(config.state_file).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get_owner(self) -> Optional[int]:
        """Return the paired owner user ID, or None."""
        v = self._data.get("owner_user_id")
        return int(v) if v is not None else None

    def set_owner(self, user_id: int):
        self._data["owner_user_id"] = user_id
        self._save()

    def clear_owner(self):
        self._data.pop("owner_user_id", None)
        self._save()
