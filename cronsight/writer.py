"""Write exported report content to files or stdout."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from cronsight.aggregator import AggregatedReport
from cronsight.exporter import export_csv, export_json

ExportFormat = Literal["json", "csv"]


class WriterError(Exception):
    """Raised when output cannot be written."""


def _render(report: AggregatedReport, fmt: ExportFormat) -> str:
    """Render the report to a string in the requested format."""
    if fmt == "json":
        return export_json(report)
    if fmt == "csv":
        return export_csv(report)
    raise WriterError(f"Unknown export format: {fmt!r}")


def write_report(
    report: AggregatedReport,
    fmt: ExportFormat,
    output_path: str | None = None,
) -> None:
    """Write the report to *output_path* or stdout if *output_path* is None."""
    content = _render(report, fmt)

    if output_path is None:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
        return

    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise WriterError(f"Could not write to {output_path!r}: {exc}") from exc
