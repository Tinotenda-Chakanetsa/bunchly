"""Report exporters — render a ``ReportResult`` as CSV or XLSX.

Spec §9.17 also lists PDF export; PDF needs a rendering dependency not
in requirements, so it is intentionally left out — CSV and XLSX cover
the spreadsheet workflows. Large-dataset exports should move to a
background job before production (see handoff notes).
"""
from __future__ import annotations

import csv
import io

from django.http import HttpResponse

from .registry import ReportResult


def _stringify(value) -> str:
    if value is None:
        return ""
    return str(value)


def export_csv(result: ReportResult, filename: str) -> HttpResponse:
    """Render a report as a downloadable CSV file."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    keys = [c["key"] for c in result.columns]
    writer.writerow([c["label"] for c in result.columns])
    for row in result.rows:
        writer.writerow([_stringify(row.get(k)) for k in keys])

    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    return response


def export_xlsx(result: ReportResult, filename: str) -> HttpResponse:
    """Render a report as a downloadable XLSX workbook."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"

    keys = [c["key"] for c in result.columns]
    sheet.append([c["label"] for c in result.columns])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in result.rows:
        sheet.append([_stringify(row.get(k)) for k in keys])

    buffer = io.BytesIO()
    workbook.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    return response


def export_report(result: ReportResult, fmt: str, filename: str) -> HttpResponse:
    """Dispatch to the CSV or XLSX exporter by format string."""
    if fmt == "xlsx":
        return export_xlsx(result, filename)
    return export_csv(result, filename)
