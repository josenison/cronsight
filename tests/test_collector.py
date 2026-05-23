"""Tests for cronsight.collector module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronsight.collector import (
    CollectionResult,
    ServerConfig,
    collect_from_servers,
    fetch_cron_log,
)

SAMPLE_LOG = (
    "Jun 15 04:00:01 web1 CRON[12345]: (root) CMD (/usr/bin/backup.sh)\n"
    "Jun 15 04:00:01 web1 CRON[12345]: (root) CMD (/usr/bin/cleanup.sh)\n"
)


@pytest.fixture()
def server_config() -> ServerConfig:
    return ServerConfig(host="192.168.1.1", user="admin", port=22)


def test_server_config_ssh_args_basic(server_config: ServerConfig) -> None:
    args = server_config.ssh_args()
    assert "ssh" in args
    assert "admin@192.168.1.1" in args
    assert "-p" in args


def test_server_config_ssh_args_with_identity() -> None:
    cfg = ServerConfig(host="10.0.0.1", user="ci", identity_file="/home/user/.ssh/id_rsa")
    args = cfg.ssh_args()
    assert "-i" in args
    assert "/home/user/.ssh/id_rsa" in args


def test_fetch_cron_log_success(server_config: ServerConfig) -> None:
    mock_result = MagicMock(returncode=0, stdout=SAMPLE_LOG, stderr="")
    with patch("cronsight.collector.subprocess.run", return_value=mock_result):
        result = fetch_cron_log(server_config)
    assert result.success
    assert result.server == "192.168.1.1"
    assert len(result.entries) == 2


def test_fetch_cron_log_ssh_error(server_config: ServerConfig) -> None:
    mock_result = MagicMock(returncode=1, stdout="", stderr="Permission denied")
    with patch("cronsight.collector.subprocess.run", return_value=mock_result):
        result = fetch_cron_log(server_config)
    assert not result.success
    assert "Permission denied" in result.error


def test_fetch_cron_log_timeout(server_config: ServerConfig) -> None:
    import subprocess
    with patch("cronsight.collector.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=15)):
        result = fetch_cron_log(server_config)
    assert not result.success
    assert "timed out" in result.error


def test_collect_from_servers_aggregates_results() -> None:
    configs = [
        ServerConfig(host="host1", user="u"),
        ServerConfig(host="host2", user="u"),
    ]
    mock_result = MagicMock(returncode=0, stdout=SAMPLE_LOG, stderr="")
    with patch("cronsight.collector.subprocess.run", return_value=mock_result):
        results = collect_from_servers(configs)
    assert len(results) == 2
    assert all(r.success for r in results)
