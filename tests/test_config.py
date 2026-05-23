"""Tests for cronsight.config module."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from cronsight.config import ConfigError, load_config


VALID_TOML = textwrap.dedent("""\
    [servers.web1]
    host = "192.168.1.10"
    user = "deploy"
    port = 2222
    log_path = "/var/log/syslog"

    [servers.db1]
    host = "10.0.0.5"
    user = "root"
""")

MISSING_HOST_TOML = textwrap.dedent("""\
    [servers.broken]
    user = "admin"
""")

EMPTY_TOML = ""


def test_load_config_returns_server_configs(tmp_path: Path) -> None:
    cfg_file = tmp_path / "servers.toml"
    cfg_file.write_text(VALID_TOML)
    servers = load_config(cfg_file)
    assert len(servers) == 2
    hosts = {s.host for s in servers}
    assert "192.168.1.10" in hosts
    assert "10.0.0.5" in hosts


def test_load_config_respects_custom_port(tmp_path: Path) -> None:
    cfg_file = tmp_path / "servers.toml"
    cfg_file.write_text(VALID_TOML)
    servers = load_config(cfg_file)
    web1 = next(s for s in servers if s.host == "192.168.1.10")
    assert web1.port == 2222


def test_load_config_default_port(tmp_path: Path) -> None:
    cfg_file = tmp_path / "servers.toml"
    cfg_file.write_text(VALID_TOML)
    servers = load_config(cfg_file)
    db1 = next(s for s in servers if s.host == "10.0.0.5")
    assert db1.port == 22


def test_load_config_missing_host_raises(tmp_path: Path) -> None:
    cfg_file = tmp_path / "servers.toml"
    cfg_file.write_text(MISSING_HOST_TOML)
    with pytest.raises(ConfigError, match="host"):
        load_config(cfg_file)


def test_load_config_empty_file_raises(tmp_path: Path) -> None:
    cfg_file = tmp_path / "servers.toml"
    cfg_file.write_text(EMPTY_TOML)
    with pytest.raises(ConfigError, match="No servers"):
        load_config(cfg_file)


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nonexistent.toml")
