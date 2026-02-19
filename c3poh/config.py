"""
C3Poh configuration.
Controls Telegram bot credentials, DM policy, and allowlist.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ── DM policy constants ───────────────────────────────────────────────────────

DM_POLICY_ALLOWLIST = "allowlist"   # only users in allow_from can DM (default/recommended)
DM_POLICY_PAIRING   = "pairing"     # first user to /start becomes the owner
DM_POLICY_OPEN      = "open"        # anyone can DM (⚠️ dangerous)
DM_POLICY_DISABLED  = "disabled"    # no DMs accepted

DM_POLICIES = (DM_POLICY_ALLOWLIST, DM_POLICY_PAIRING, DM_POLICY_OPEN, DM_POLICY_DISABLED)


@dataclass
class C3PohConfig:
    # Telegram credentials
    telegram_bot_token: str = ""          # required - set via env or config file

    # Access control (don't skip this)
    dm_policy: str = DM_POLICY_ALLOWLIST  # sane default: only allowlisted users
    allow_from: list = field(default_factory=list)  # list of numeric Telegram user IDs

    # Group chat behavior
    require_mention: bool = True          # only respond when @mentioned in groups

    # HTTP server (receives notifications from TinMan and other tools)
    notify_port: int = 7734              # localhost:7734/notify
    notify_host: str = "127.0.0.1"      # localhost only - never expose publicly

    # Claude Code invocation
    claude_bin: str = "claude"           # path to claude CLI
    claude_timeout_seconds: int = 300    # 5 min max per response

    # Message handling
    max_message_length: int = 4000       # Telegram max is ~4096
    typing_indicator: bool = True        # show "typing..." while Claude processes

    # Session / state
    state_file: str = "~/.c3poh/state.json"
    log_file: str = "~/.c3poh/c3poh.log"
    log_messages: bool = True            # log incoming/outgoing messages

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "C3PohConfig":
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "C3PohConfig":
        """
        Load config with priority:
          1. CLI-provided path
          2. ./c3poh.json
          3. ~/.c3poh/config.json
          4. built-in sane defaults
        Then overlay env vars.
        """
        search_paths = []
        if config_path:
            search_paths.append(Path(config_path).expanduser())
        search_paths.extend([
            Path("c3poh.json"),
            Path.home() / ".c3poh" / "config.json",
        ])

        data: dict = {}

        for p in search_paths:
            if p.exists():
                with open(p) as f:
                    data = json.load(f)
                break

        # Required: Telegram bot token from env (preferred) or config
        env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if env_token:
            data["telegram_bot_token"] = env_token

        # allow_from from env (comma-separated numeric IDs)
        env_allow = os.environ.get("C3POH_ALLOW_FROM", "")
        if env_allow:
            data["allow_from"] = [x.strip() for x in env_allow.split(",") if x.strip()]

        # Other env overrides
        env_map = {
            "C3POH_DM_POLICY": ("dm_policy", str),
            "C3POH_NOTIFY_PORT": ("notify_port", int),
            "C3POH_CLAUDE_TIMEOUT": ("claude_timeout_seconds", int),
        }
        for env_key, (field_name, cast) in env_map.items():
            val = os.environ.get(env_key)
            if val is not None:
                data[field_name] = cast(val)

        return cls.from_dict(data)

    def save(self, path: Optional[str] = None) -> Path:
        target = Path(path).expanduser() if path else Path.home() / ".c3poh" / "config.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        # Never write the bot token to disk in plain text - use env var
        data = self.to_dict()
        data["telegram_bot_token"] = ""  # scrub before saving
        with open(target, "w") as f:
            json.dump(data, f, indent=2)
        return target

    def validate(self) -> list[str]:
        """Return list of validation errors. Empty = valid."""
        errors = []
        if not self.telegram_bot_token:
            errors.append(
                "TELEGRAM_BOT_TOKEN is not set. "
                "Set it via env var or c3poh.json."
            )
        if self.dm_policy not in DM_POLICIES:
            errors.append(
                f"dm_policy must be one of: {', '.join(DM_POLICIES)}"
            )
        if self.dm_policy == DM_POLICY_ALLOWLIST and not self.allow_from:
            errors.append(
                "dm_policy is 'allowlist' but allow_from is empty. "
                "Add your Telegram numeric user ID to allow_from, or change dm_policy."
            )
        if self.dm_policy == DM_POLICY_OPEN:
            errors.append(
                "WARNING: dm_policy is 'open' — anyone with your bot link can send commands. "
                "This is fine for demos, dangerous for anything real."
            )
        return errors
