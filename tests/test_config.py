"""Tests for C3Poh config loading, validation, and env overrides."""

import json
from pathlib import Path

import pytest

from c3poh.config import (
    C3PohConfig,
    DM_POLICY_ALLOWLIST,
    DM_POLICY_PAIRING,
    DM_POLICY_OPEN,
    DM_POLICY_DISABLED,
)


class TestDefaults:
    def test_default_dm_policy_is_allowlist(self):
        cfg = C3PohConfig()
        assert cfg.dm_policy == DM_POLICY_ALLOWLIST

    def test_default_notify_host_is_localhost(self):
        cfg = C3PohConfig()
        assert cfg.notify_host == "127.0.0.1"

    def test_default_require_mention_is_true(self):
        cfg = C3PohConfig()
        assert cfg.require_mention is True

    def test_token_not_set_by_default(self):
        cfg = C3PohConfig()
        assert cfg.telegram_bot_token == ""


class TestValidation:
    def test_missing_token_is_error(self):
        cfg = C3PohConfig(dm_policy=DM_POLICY_ALLOWLIST, allow_from=["123"])
        errors = cfg.validate()
        assert any("TELEGRAM_BOT_TOKEN" in e for e in errors)

    def test_allowlist_policy_with_empty_allow_from_is_error(self):
        cfg = C3PohConfig(telegram_bot_token="tok", dm_policy=DM_POLICY_ALLOWLIST, allow_from=[])
        errors = cfg.validate()
        assert any("allow_from is empty" in e for e in errors)

    def test_valid_allowlist_config_no_errors(self):
        cfg = C3PohConfig(
            telegram_bot_token="123:ABC",
            dm_policy=DM_POLICY_ALLOWLIST,
            allow_from=["987654321"],
        )
        errors = [e for e in cfg.validate() if not e.startswith("WARNING")]
        assert errors == []

    def test_open_policy_is_warning_not_error(self):
        cfg = C3PohConfig(
            telegram_bot_token="tok",
            dm_policy=DM_POLICY_OPEN,
        )
        errors = cfg.validate()
        # Should have a WARNING but no fatal errors beyond token
        warnings = [e for e in errors if e.startswith("WARNING")]
        assert any("open" in w for w in warnings)

    def test_invalid_dm_policy_is_error(self):
        cfg = C3PohConfig(telegram_bot_token="tok", dm_policy="banana")
        errors = cfg.validate()
        assert any("dm_policy" in e for e in errors)

    def test_pairing_policy_no_allow_from_required(self):
        cfg = C3PohConfig(
            telegram_bot_token="tok",
            dm_policy=DM_POLICY_PAIRING,
            allow_from=[],
        )
        errors = [e for e in cfg.validate() if not e.startswith("WARNING")]
        # pairing doesn't require allow_from
        assert not any("allow_from" in e for e in errors)


class TestEnvVarOverrides:
    def test_token_from_env(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-123")
        cfg = C3PohConfig.load()
        assert cfg.telegram_bot_token == "test-token-123"

    def test_allow_from_from_env(self, monkeypatch):
        monkeypatch.setenv("C3POH_ALLOW_FROM", "111,222,333")
        cfg = C3PohConfig.load()
        assert "111" in cfg.allow_from
        assert "222" in cfg.allow_from

    def test_dm_policy_from_env(self, monkeypatch):
        monkeypatch.setenv("C3POH_DM_POLICY", "pairing")
        cfg = C3PohConfig.load()
        assert cfg.dm_policy == "pairing"


class TestSave:
    def test_save_does_not_write_token(self, tmp_path):
        cfg = C3PohConfig(telegram_bot_token="super-secret-token")
        saved = cfg.save(str(tmp_path / "config.json"))
        with open(saved) as f:
            data = json.load(f)
        assert data["telegram_bot_token"] == ""

    def test_save_and_reload_policy(self, tmp_path):
        cfg = C3PohConfig(
            telegram_bot_token="tok",
            dm_policy=DM_POLICY_PAIRING,
            allow_from=["42"],
        )
        saved = cfg.save(str(tmp_path / "config.json"))
        reloaded = C3PohConfig.load(str(saved))
        assert reloaded.dm_policy == DM_POLICY_PAIRING
        assert "42" in reloaded.allow_from
