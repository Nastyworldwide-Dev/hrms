"""Shift Attendance as an Excel file, from Nadi (owner, 15 Oct 2026).

For an Attendance Report Viewer only (the Shenzhen staff who count the month).
The rows are the Shift Attendance report's own: the same execute(), so the
company fence (report_scope.attendance_viewer_companies) and the columns are
the report's, never restated here. One month at a time, the way they count.
"""

import calendar
import logging

import frappe
from frappe import _

from hrms.utils.report_scope import ATTENDANCE_VIEWER_ROLE, attendance_viewer_companies

logger = logging.getLogger(__name__)


def month_range(month: str) -> tuple[str, str]:
	"""("2026-10-01", "2026-10-31") for "2026-10"; a ValueError for anything else. Pure."""
	year, mon = (int(part) for part in month.split("-"))
	if not 1 <= mon <= 12 or not 2000 <= year <= 2100:
		raise ValueError(month)
	last = calendar.monthrange(year, mon)[1]
	return f"{year:04d}-{mon:02d}-01", f"{year:04d}-{mon:02d}-{last:02d}"


def sheet_rows(columns: list, data: list) -> list[list]:
	"""The report as a sheet: one header row, then a row per day; hidden columns left out. Pure."""
	shown = [col for col in columns if not col.get("hidden")]
	rows = [[col.get("label") for col in shown]]
	for entry in data:
		rows.append([_cell(entry.get(col["fieldname"])) for col in shown])
	return rows


def _cell(value):
	"""A sheet cell: numbers and text as they are, anything else (dates, times) as text."""
	if value is None or isinstance(value, (int, float, str)):
		return value
	return str(value)


@frappe.whitelist(methods=["GET"])
def my_company() -> dict:
	"""What the download screen shows: the companies the caller's file holds."""
	_require_viewer()
	return {"companies": attendance_viewer_companies() or []}


@frappe.whitelist(methods=["GET"])
def download(month: str):
	"""Send `month` ("YYYY-MM") of Shift Attendance as .xlsx to an Attendance Report Viewer."""
	_require_viewer()
	try:
		from_date, to_date = month_range(month)
	except (ValueError, AttributeError):
		frappe.throw(_("Choose a month."), frappe.ValidationError)

	from frappe.utils.xlsxutils import build_xlsx_response

	from hrms.hr.report.shift_attendance.shift_attendance import execute

	columns, data, *_rest = execute(
		{"from_date": from_date, "to_date": to_date, "include_attendance_without_checkins": 1}
	)
	logger.info("[attendance_download] %s %s: %d row(s)", frappe.session.user, month, len(data))
	build_xlsx_response(sheet_rows(columns, data), f"shift-attendance-{month}")


def _require_viewer():
	if ATTENDANCE_VIEWER_ROLE not in frappe.get_roles():
		logger.warning("[attendance_download] refused %s: no viewer role", frappe.session.user)
		frappe.throw(_("Only an Attendance Report Viewer can download this."), frappe.PermissionError)
