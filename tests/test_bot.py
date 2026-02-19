"""Tests for TelegramBot - access control, message handling, Claude invocation."""

import json
import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

from c3poh.config import (
    C3PohConfig,
    DM_POLICY_ALLOWLIST,
    DM_POLICY_OPEN,
    DM_POLICY_DISABLED,
    DM_POLICY_PAIRING,
)
from c3poh.telegram_bot import TelegramBot


@pytest.fixture
def cfg(tmp_path):
    return C3PohConfig(
        telegram_bot_token="test:TOKEN",
        dm_policy=DM_POLICY_ALLOWLIST,
        allow_from=["111111"],
        state_file=str(tmp_path / "state.json"),
        log_file=str(tmp_path / "c3poh.log"),
        typing_indicator=False,
    )


@pytest.fixture
def bot(cfg):
    return TelegramBot(cfg)


def make_update(text: str, user_id: int = 111111, chat_id: int = 999, chat_type: str = "private"):
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "from": {"id": user_id, "first_name": "Test"},
            "chat": {"id": chat_id, "type": chat_type},
            "text": text,
            "entities": [],
        }
    }


class TestAccessControl:
    def test_allowlisted_user_is_allowed(self, bot):
        assert bot._is_allowed(111111, 999, False) is True

    def test_unlisted_user_is_blocked(self, bot):
        assert bot._is_allowed(999999, 999, False) is False

    def test_open_policy_allows_anyone(self, tmp_path):
        cfg = C3PohConfig(
            telegram_bot_token="tok",
            dm_policy=DM_POLICY_OPEN,
            state_file=str(tmp_path / "state.json"),
            log_file=str(tmp_path / "c3poh.log"),
        )
        bot = TelegramBot(cfg)
        assert bot._is_allowed(999999, 999, False) is True

    def test_disabled_policy_blocks_everyone(self, tmp_path):
        cfg = C3PohConfig(
            telegram_bot_token="tok",
            dm_policy=DM_POLICY_DISABLED,
            state_file=str(tmp_path / "state.json"),
            log_file=str(tmp_path / "c3poh.log"),
        )
        bot = TelegramBot(cfg)
        assert bot._is_allowed(111111, 999, False) is False

    def test_pairing_first_user_becomes_owner(self, tmp_path):
        cfg = C3PohConfig(
            telegram_bot_token="tok",
            dm_policy=DM_POLICY_PAIRING,
            state_file=str(tmp_path / "state.json"),
            log_file=str(tmp_path / "c3poh.log"),
        )
        bot = TelegramBot(cfg)
        assert bot._is_allowed(42, 999, False) is True  # first = owner
        assert bot._is_allowed(99, 999, False) is False  # second = blocked

    def test_pairing_owner_persists_across_instances(self, tmp_path):
        cfg = C3PohConfig(
            telegram_bot_token="tok",
            dm_policy=DM_POLICY_PAIRING,
            state_file=str(tmp_path / "state.json"),
            log_file=str(tmp_path / "c3poh.log"),
        )
        bot1 = TelegramBot(cfg)
        bot1._is_allowed(42, 999, False)  # sets owner

        bot2 = TelegramBot(cfg)  # new instance, same state file
        assert bot2._is_allowed(42, 999, False) is True
        assert bot2._is_allowed(99, 999, False) is False


class TestMentionDetection:
    def test_mentioned_in_group(self, bot):
        message = {
            "text": "@mybot what is 2+2?",
            "entities": [{"type": "mention", "offset": 0, "length": 6}],
        }
        assert bot._is_mentioned(message, "mybot") is True

    def test_not_mentioned_in_group(self, bot):
        message = {
            "text": "hello everyone",
            "entities": [],
        }
        assert bot._is_mentioned(message, "mybot") is False

    def test_mention_case_insensitive(self, bot):
        message = {
            "text": "@MyBot hello",
            "entities": [{"type": "mention", "offset": 0, "length": 6}],
        }
        assert bot._is_mentioned(message, "mybot") is True


class TestClaudeInvocation:
    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_claude_called_with_prompt(self, mock_which, mock_run, bot):
        mock_proc = MagicMock()
        mock_proc.stdout = "Hello from Claude!"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = bot._invoke_claude("say hi")
        assert result == "Hello from Claude!"

    @patch("shutil.which", return_value=None)
    def test_missing_claude_returns_error_message(self, mock_which, bot):
        result = bot._invoke_claude("hello")
        assert "claude CLI not found" in result

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_timeout_returns_friendly_message(self, mock_which, mock_run, bot):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=300)
        result = bot._invoke_claude("do something slow")
        assert "timed out" in result.lower()

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_empty_stdout_with_stderr_returns_error(self, mock_which, mock_run, bot):
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        mock_proc.stderr = "auth error"
        mock_run.return_value = mock_proc
        result = bot._invoke_claude("hello")
        assert "auth error" in result


class TestMessageHandling:
    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_allowed_user_gets_response(self, mock_which, mock_run, bot):
        mock_proc = MagicMock()
        mock_proc.stdout = "Response!"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        sent_messages = []
        def fake_send(chat_id, text, **kwargs):
            sent_messages.append(text)
            return {}
        bot.send_message = fake_send

        update = make_update("hello", user_id=111111)
        bot.handle_message(update, "mybot")
        assert "Response!" in sent_messages

    def test_blocked_user_gets_no_response_in_group(self, bot):
        sent = []
        bot.send_message = lambda cid, text, **kw: sent.append(text)

        update = make_update("hello", user_id=999999, chat_type="group")
        bot.handle_message(update, "mybot")
        assert sent == []

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_group_no_mention_is_ignored(self, mock_which, mock_run, bot):
        sent = []
        bot.send_message = lambda cid, text, **kw: sent.append(text)

        update = make_update("hello everyone", user_id=111111, chat_type="group")
        bot.handle_message(update, "mybot")
        assert sent == []  # not mentioned, should be ignored
        assert not mock_run.called


class TestMessageSplitting:
    def test_short_message_not_split(self, bot):
        chunks = bot._split_message("hello")
        assert chunks == ["hello"]

    def test_long_message_split_correctly(self, bot):
        long_text = "x" * 5000
        chunks = bot._split_message(long_text)
        assert len(chunks) > 1
        assert all(len(c) <= bot.config.max_message_length for c in chunks)
        assert "".join(chunks) == long_text
