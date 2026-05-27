"""Tests for RubSettings configuration loading."""

from __future__ import annotations

from pathlib import Path

from rub.config import RubSettings


class TestRubSettingsDefaults:
    """Test default configuration values."""

    def test_default_config_dir(self, monkeypatch):
        monkeypatch.delenv("RUB_CONFIG_DIR", raising=False)
        monkeypatch.delenv("RUB_CACHE_DIR", raising=False)
        monkeypatch.delenv("RUB_CACHE_ENABLED", raising=False)
        monkeypatch.delenv("RUB_CACHE_TTL", raising=False)
        monkeypatch.delenv("RUB_LOG_LEVEL", raising=False)
        settings = RubSettings()
        assert settings.config_dir == Path.home() / ".config" / "rub"

    def test_default_cache_enabled(self, monkeypatch):
        monkeypatch.delenv("RUB_CACHE_ENABLED", raising=False)
        settings = RubSettings()
        assert settings.cache_enabled is True

    def test_default_cache_ttl(self, monkeypatch):
        monkeypatch.delenv("RUB_CACHE_TTL", raising=False)
        settings = RubSettings()
        assert settings.cache_ttl == 3600

    def test_default_log_level(self, monkeypatch):
        monkeypatch.delenv("RUB_LOG_LEVEL", raising=False)
        settings = RubSettings()
        assert settings.log_level == "WARNING"


class TestRubSettingsEnvOverrides:
    """Test that RUB_ env vars override defaults."""

    def test_cache_enabled_false(self, monkeypatch):
        monkeypatch.setenv("RUB_CACHE_ENABLED", "false")
        settings = RubSettings()
        assert settings.cache_enabled is False

    def test_cache_ttl_override(self, monkeypatch):
        monkeypatch.setenv("RUB_CACHE_TTL", "7200")
        settings = RubSettings()
        assert settings.cache_ttl == 7200

    def test_log_level_override(self, monkeypatch):
        monkeypatch.setenv("RUB_LOG_LEVEL", "DEBUG")
        settings = RubSettings()
        assert settings.log_level == "DEBUG"


class TestCacheDbPath:
    """Test cache_db_path property."""

    def test_default_cache_db_path(self, monkeypatch):
        monkeypatch.delenv("RUB_CACHE_DIR", raising=False)
        monkeypatch.delenv("RUB_CONFIG_DIR", raising=False)
        settings = RubSettings()
        expected = Path.home() / ".config" / "rub" / "cache.db"
        assert settings.cache_db_path == expected

    def test_custom_cache_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("RUB_CACHE_DIR", str(tmp_path))
        settings = RubSettings()
        assert settings.cache_db_path == tmp_path / "cache.db"
