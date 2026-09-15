"""C.O.R.E. configuration: centralized, secret-free, standalone by default."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _restore_global_settings():
    """Re-read config after each test so monkeypatched env never leaks."""
    yield
    defaults = sys.modules["asis.configuration.defaults"]
    environment = sys.modules["asis.configuration.environment"]
    settings_mod = sys.modules["asis.configuration.settings"]
    importlib.reload(defaults)
    importlib.reload(environment)
    importlib.reload(settings_mod)


def _reload_config(monkeypatch, **env):
    import sys

    for key in list(env):
        if env[key] is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, env[key])
    # NOTE: asis.configuration.__init__ re-exports a global named
    # `settings`, shadowing the submodule attribute — so resolve the real
    # modules via sys.modules instead of `import ... as`.
    import asis.configuration.defaults  # noqa: F401
    import asis.configuration.environment  # noqa: F401
    import asis.configuration.settings  # noqa: F401

    defaults = sys.modules["asis.configuration.defaults"]
    environment = sys.modules["asis.configuration.environment"]
    settings_mod = sys.modules["asis.configuration.settings"]
    importlib.reload(defaults)
    importlib.reload(environment)
    importlib.reload(settings_mod)
    return settings_mod


def test_core_defaults_standalone(monkeypatch):
    for key in (
        "ASIS_CORE_ENABLED",
        "ASIS_CORE_HOST",
        "ASIS_CORE_PORT",
        "ASIS_CORE_DEVICE_FILE",
        "ASIS_CORE_CA_FILE",
        "ASIS_CORE_INSECURE",
        "ASIS_CORE_CONNECT_TIMEOUT",
        "ASIS_CORE_REQUEST_TIMEOUT",
        "ASIS_CORE_RECONNECT_ENABLED",
        "ASIS_CORE_RECONNECT_DELAY",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = _reload_config(monkeypatch)
    core = settings.load_settings().core
    assert core.enabled is False
    assert core.host == "127.0.0.1"
    assert core.port == 5000
    assert core.insecure is False
    assert core.connect_timeout == 10
    assert core.request_timeout == 30
    assert core.reconnect_enabled is True
    assert core.reconnect_delay == 5


def test_core_env_overrides(monkeypatch):
    settings = _reload_config(
        monkeypatch,
        ASIS_CORE_ENABLED="true",
        ASIS_CORE_HOST="192.168.1.10",
        ASIS_CORE_PORT="5001",
        ASIS_CORE_INSECURE="yes",
        ASIS_CORE_CONNECT_TIMEOUT="7",
        ASIS_CORE_REQUEST_TIMEOUT="45",
        ASIS_CORE_RECONNECT_ENABLED="0",
        ASIS_CORE_RECONNECT_DELAY="2",
    )
    core = settings.load_settings().core
    assert core.enabled is True
    assert core.host == "192.168.1.10"
    assert core.port == 5001
    assert core.insecure is True
    assert core.connect_timeout == 7
    assert core.request_timeout == 45
    assert core.reconnect_enabled is False
    assert core.reconnect_delay == 2


def test_invalid_port_falls_back_to_default(monkeypatch):
    for bad in ("abc", "0", "-1", "99999", ""):
        settings = _reload_config(monkeypatch, ASIS_CORE_PORT=bad)
        assert settings.load_settings().core.port == 5000, bad


def test_invalid_timeouts_fall_back_to_defaults(monkeypatch):
    settings = _reload_config(
        monkeypatch,
        ASIS_CORE_CONNECT_TIMEOUT="0",
        ASIS_CORE_REQUEST_TIMEOUT="never",
        ASIS_CORE_RECONNECT_DELAY="9999",
    )
    core = settings.load_settings().core
    assert core.connect_timeout == 10
    assert core.request_timeout == 30
    assert core.reconnect_delay == 5


def test_invalid_host_falls_back_to_default(monkeypatch):
    settings = _reload_config(monkeypatch, ASIS_CORE_HOST="   ")
    assert settings.load_settings().core.host == "127.0.0.1"


def test_env_example_documents_core_keys():
    example = Path(__file__).resolve().parents[1] / ".env.example"
    assert example.exists()
    text = example.read_text()
    for key in (
        "ASIS_CORE_ENABLED",
        "ASIS_CORE_HOST",
        "ASIS_CORE_PORT",
        "ASIS_CORE_REQUEST_TIMEOUT",
    ):
        assert key in text
    assert "credential" not in text.lower() or "runtime-only" in text.lower()
