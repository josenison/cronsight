"""Tests for cronsight.parser module."""

from datetime import datetime

import pytest

from cronsight.parser import CronEntry, parse_cron_line, parse_cron_log

SAMPLE_CMD_LINE = (
    "Oct 15 14:32:01 web-01 CROND[4521]: (deploy) CMD (/usr/local/bin/backup.sh)"
)
SAMPLE_SESSION_LINE = (
    "Oct 15 14:32:01 web-01 CRON[4521]: (deploy) SESSION (opening)"
)
NON_CRON_LINE = "Oct 15 14:32:01 web-01 sshd[999]: Accepted publickey for root"


class TestParseCronLine:
    def test_parses_valid_cmd_line(self):
        entry = parse_cron_line(SAMPLE_CMD_LINE, year=2024)
        assert isinstance(entry, CronEntry)
        assert entry.host == "web-01"
        assert entry.pid == 4521
        assert entry.user == "deploy"
        assert entry.action == "CMD"
        assert entry.command == "/usr/local/bin/backup.sh"
        assert entry.timestamp == datetime(2024, 10, 15, 14, 32, 1)

    def test_parses_session_line(self):
        entry = parse_cron_line(SAMPLE_SESSION_LINE, year=2024)
        assert entry is not None
        assert entry.action == "SESSION"
        assert entry.command == "opening"

    def test_returns_none_for_non_cron_line(self):
        assert parse_cron_line(NON_CRON_LINE) is None

    def test_returns_none_for_empty_string(self):
        assert parse_cron_line("") is None

    def test_defaults_to_current_year(self):
        entry = parse_cron_line(SAMPLE_CMD_LINE)
        assert entry is not None
        assert entry.timestamp.year == datetime.now().year

    def test_is_cmd_property_true_for_cmd(self):
        entry = parse_cron_line(SAMPLE_CMD_LINE, year=2024)
        assert entry.is_cmd is True

    def test_is_cmd_property_false_for_session(self):
        entry = parse_cron_line(SAMPLE_SESSION_LINE, year=2024)
        assert entry.is_cmd is False

    def test_raw_field_preserved(self):
        entry = parse_cron_line(SAMPLE_CMD_LINE, year=2024)
        assert entry.raw == SAMPLE_CMD_LINE


class TestParseCronLog:
    def test_parses_multiple_lines(self):
        lines = [SAMPLE_CMD_LINE, SAMPLE_SESSION_LINE, NON_CRON_LINE]
        entries = parse_cron_log(lines, year=2024)
        assert len(entries) == 2

    def test_empty_input_returns_empty_list(self):
        assert parse_cron_log([]) == []

    def test_all_non_matching_returns_empty_list(self):
        entries = parse_cron_log([NON_CRON_LINE, "garbage", ""], year=2024)
        assert entries == []
