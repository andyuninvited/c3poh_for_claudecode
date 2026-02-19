"""
C3Poh Telegram bot - long-polling implementation.
Uses only Python stdlib + urllib (zero external dependencies).
Receives messages, checks allowlist, invokes Claude, sends response.
"""

import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import C3PohConfig, DM_POLICY_ALLOWLIST, DM_POLICY_PAIRING, DM_POLICY_OPEN, DM_POLICY_DISABLED
from .logger import C3PohLogger
from .state import C3PohState


class TelegramError(Exception):
    pass


class TelegramBot:
    """
    Long-polling Telegram bot.
    Pure stdlib - no python-telegram-bot, no httpx, no requests.
    """

    def __init__(self, config: C3PohConfig):
        self.config = config
        self.logger = C3PohLogger(config)
        self.state = C3PohState(config)
        self._base_url = f"https://api.telegram.org/bot{config.telegram_bot_token}"
        self._offset = 0

    # ── Telegram API primitives ────────────────────────────────────────────────

    def _call(self, method: str, payload: Optional[dict] = None, timeout: int = 30) -> dict:
        url = f"{self._base_url}/{method}"
        data = json.dumps(payload or {}).encode() if payload else None
        headers = {"Content-Type": "application/json"} if data else {}

        req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode()
            raise TelegramError(f"HTTP {e.code}: {body_text}") from e
        except urllib.error.URLError as e:
            raise TelegramError(f"URL error: {e.reason}") from e

        if not body.get("ok"):
            raise TelegramError(f"Telegram API error: {body.get('description', 'unknown')}")
        return body.get("result", {})

    def get_me(self) -> dict:
        return self._call("getMe")

    def send_message(self, chat_id: int, text: str, parse_mode: str = "") -> dict:
        """Send a message, splitting if over max length."""
        chunks = self._split_message(text)
        result = {}
        for chunk in chunks:
            payload: dict = {"chat_id": chat_id, "text": chunk}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            result = self._call("sendMessage", payload)
        return result

    def send_chat_action(self, chat_id: int, action: str = "typing"):
        try:
            self._call("sendChatAction", {"chat_id": chat_id, "action": action})
        except TelegramError:
            pass  # typing indicator failure is non-fatal

    def get_updates(self, offset: int = 0, timeout: int = 20) -> list:
        result = self._call(
            "getUpdates",
            {"offset": offset, "timeout": timeout, "allowed_updates": ["message"]},
            timeout=timeout + 5,
        )
        return result if isinstance(result, list) else []

    def _split_message(self, text: str) -> list[str]:
        """Split long messages into chunks under max_message_length."""
        limit = self.config.max_message_length
        if len(text) <= limit:
            return [text]
        chunks = []
        while text:
            chunks.append(text[:limit])
            text = text[limit:]
        return chunks

    # ── Access control ────────────────────────────────────────────────────────

    def _is_allowed(self, user_id: int, chat_id: int, is_group: bool) -> bool:
        policy = self.config.dm_policy

        if policy == DM_POLICY_DISABLED:
            return False

        if policy == DM_POLICY_OPEN:
            return True

        # Normalize allow_from to strings for comparison
        allow_from = [str(uid).strip() for uid in self.config.allow_from]

        if policy == DM_POLICY_ALLOWLIST:
            return str(user_id) in allow_from

        if policy == DM_POLICY_PAIRING:
            # First user to interact becomes the owner
            owner = self.state.get_owner()
            if owner is None:
                self.state.set_owner(user_id)
                return True
            return str(user_id) == str(owner)

        return False

    def _is_mentioned(self, message: dict, bot_username: str) -> bool:
        """Check if bot is @mentioned in a group message."""
        text = message.get("text", "")
        entities = message.get("entities", [])
        for entity in entities:
            if entity.get("type") == "mention":
                offset = entity["offset"]
                length = entity["length"]
                mention = text[offset:offset + length]
                if mention.lstrip("@").lower() == bot_username.lower():
                    return True
        return False

    # ── Claude invocation ──────────────────────────────────────────────────────

    def _invoke_claude(self, prompt: str) -> str:
        """Call claude CLI and return response text."""
        claude_bin = shutil.which(self.config.claude_bin) or self.config.claude_bin
        if not shutil.which(claude_bin):
            return (
                "❌ claude CLI not found.\n"
                "Install Claude Code: https://claude.ai/code"
            )

        try:
            proc = subprocess.run(
                [claude_bin, "--print", prompt],
                capture_output=True,
                text=True,
                timeout=self.config.claude_timeout_seconds,
            )
            output = proc.stdout.strip()
            if not output and proc.stderr.strip():
                return f"❌ Claude error: {proc.stderr.strip()}"
            return output or "_(no output)_"
        except subprocess.TimeoutExpired:
            return f"⏱️ Claude timed out after {self.config.claude_timeout_seconds}s."
        except Exception as e:
            return f"❌ Error invoking Claude: {e}"

    # ── Message handler ────────────────────────────────────────────────────────

    def handle_message(self, update: dict, bot_username: str):
        message = update.get("message", {})
        if not message:
            return

        chat = message.get("chat", {})
        from_user = message.get("from", {})
        text = message.get("text", "").strip()
        chat_id = chat.get("id")
        user_id = from_user.get("id")
        is_group = chat.get("type") in ("group", "supergroup")

        if not text or not chat_id or not user_id:
            return

        # Group: only respond when mentioned
        if is_group and self.config.require_mention:
            if not self._is_mentioned(message, bot_username):
                return

        # Access control
        if not self._is_allowed(user_id, chat_id, is_group):
            self.logger.log_blocked(user_id, chat_id)
            if not is_group:
                # DM the rejection (only in DMs, not groups)
                try:
                    self.send_message(
                        chat_id,
                        "🚫 You're not authorized to use this bot.\n"
                        "Contact the owner to be added to the allowlist.",
                    )
                except TelegramError:
                    pass
            return

        # Strip bot mention from text for group messages
        if is_group:
            text = text.replace(f"@{bot_username}", "").strip()

        if not text:
            return

        self.logger.log_message(user_id, chat_id, text, direction="in")

        # Show typing indicator
        if self.config.typing_indicator:
            self.send_chat_action(chat_id)

        # Invoke Claude
        response = self._invoke_claude(text)

        self.logger.log_message(user_id, chat_id, response, direction="out")

        try:
            self.send_message(chat_id, response)
        except TelegramError as e:
            print(f"[C3Poh] Failed to send message: {e}", file=sys.stderr)

    # ── Notification receiver (from TinMan/other tools) ───────────────────────

    def notify_all_allowed(self, text: str):
        """
        Send a notification to all allowlisted users.
        Used by the HTTP notify endpoint to forward TinMan heartbeat alerts.
        """
        recipients = [str(uid) for uid in self.config.allow_from]
        owner = self.state.get_owner()
        if owner and str(owner) not in recipients:
            recipients.append(str(owner))

        for uid in recipients:
            try:
                self.send_message(int(uid), text)
            except (TelegramError, ValueError) as e:
                print(f"[C3Poh] Notify to {uid} failed: {e}", file=sys.stderr)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        """Start long-polling loop."""
        errors = self.config.validate()
        # Filter out warnings (non-fatal)
        fatal = [e for e in errors if not e.startswith("WARNING")]
        if fatal:
            for e in fatal:
                print(f"[C3Poh] ❌ {e}", file=sys.stderr)
            sys.exit(1)
        for warning in [e for e in errors if e.startswith("WARNING")]:
            print(f"[C3Poh] ⚠️  {warning}")

        # Verify token
        try:
            me = self.get_me()
        except TelegramError as e:
            print(f"[C3Poh] ❌ Telegram auth failed: {e}", file=sys.stderr)
            print("[C3Poh] Check your TELEGRAM_BOT_TOKEN.", file=sys.stderr)
            sys.exit(1)

        bot_username = me.get("username", "")
        bot_name = me.get("first_name", "C3Poh")

        print(f"\n[C3Poh] ✓ Connected as @{bot_username} ({bot_name})")
        print(f"[C3Poh] DM policy: {self.config.dm_policy}")
        if self.config.allow_from:
            print(f"[C3Poh] Allowlist: {self.config.allow_from}")
        print(f"[C3Poh] Notify server: http://{self.config.notify_host}:{self.config.notify_port}/notify")
        print("[C3Poh] Listening... (Ctrl+C to stop)\n")

        while True:
            try:
                updates = self.get_updates(offset=self._offset, timeout=20)
                for update in updates:
                    self._offset = update["update_id"] + 1
                    try:
                        self.handle_message(update, bot_username)
                    except Exception as e:
                        print(f"[C3Poh] Handler error: {e}", file=sys.stderr)
            except TelegramError as e:
                print(f"[C3Poh] Poll error: {e}", file=sys.stderr)
                time.sleep(5)
            except KeyboardInterrupt:
                print("\n[C3Poh] Stopped.")
                break
            except Exception as e:
                print(f"[C3Poh] Unexpected error: {e}", file=sys.stderr)
                time.sleep(5)
