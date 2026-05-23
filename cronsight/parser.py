"""Parser for cron job log entries from remote servers."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Common syslog cron format: Oct 15 14:32:01 hostname CROND[1234]: (user) CMD (command)
CRON_LOG_PATTERN = re.compile(
    r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+CRON(?:D)?\[(?P<pid>\d+)\]:\s+"
    r"\((?P<user>[^)]+)\)\s+(?P<action>\w+)\s+\((?P<command>.+)\)$"
)


@dataclass
class CronEntry:
    timestamp: datetime
    host: str
    pid: int
    user: str
    action: str
    command: str
    raw: str = field(repr=False)

    @property
    def is_cmd(self) -> bool:
        return self.action.upper() == "CMD"


def parse_cron_line(line: str, year: Optional[int] = None) -> Optional[CronEntry]:
    """Parse a single syslog cron log line into a CronEntry.

    Args:
        line: Raw log line string.
        year: Year to use for timestamp (defaults to current year).

    Returns:
        CronEntry if line matches cron format, else None.
    """
    match = CRON_LOG_PATTERN.match(line.strip())
    if not match:
        return None

    if year is None:
        year = datetime.now().year

    raw_ts = f"{match.group('month')} {match.group('day')} {match.group('time')} {year}"
    try:
        timestamp = datetime.strptime(raw_ts, "%b %d %H:%M:%S %Y")
    except ValueError:
        return None

    return CronEntry(
        timestamp=timestamp,
        host=match.group("host"),
        pid=int(match.group("pid")),
        user=match.group("user"),
        action=match.group("action"),
        command=match.group("command"),
        raw=line.strip(),
    )


def parse_cron_log(lines: list[str], year: Optional[int] = None) -> list[CronEntry]:
    """Parse multiple log lines, skipping non-matching entries."""
    entries = []
    for line in lines:
        entry = parse_cron_line(line, year=year)
        if entry is not None:
            entries.append(entry)
    return entries
