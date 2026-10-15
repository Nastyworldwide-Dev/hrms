"""Shift Attendance as an Excel file, from Nadi (owner, 15 Oct 2026).

For an Attendance Report Viewer only (the Shenzhen staff who count the month).
The rows are the Shift Attendance report's own: the same execute(), so the
company fence (report_scope.attendance_viewer_companies) and the columns are
the report's, never restated here. One month at a time, the way they count.
"""

import calendar
import logging
import re

import frappe
from frappe import _

from hrms.utils.report_scope import ATTENDANCE_VIEWER_ROLE, attendance_viewer_companies

logger = logging.getLogger(__name__)

#: "2026-10" and nothing else: int() also takes " 10", "+10", "1_0" and other digits
MONTH = re.compile(r"\d{4}-\d{2}", re.ASCII)


def month_range(month: str) -> tuple[str, str]:
	"""("2026-10-01", "2026-10-31") for "2026-10"; a ValueError for anything else. Pure."""
	year, mon = (int(part) for part in month.split("-"))
	if not 1 <= mon <= 12 or not 2000 <= year <= 2100:
		raise ValueError(month)
	last = calendar.monthrange(year, mon)[1]
	return f"{year:04d}-{mon:02d}-01", f"{year:04d}-{mon:02d}-{last:02d}"


#: Hidden in the Desk report (the Employee link already shows the name there), but
#: a sheet has no link, so without it the file reads as bare IDs (owner, 15 Oct 2026)
SHEET_SHOWS = ("employee_name",)


def sheet_rows(columns: list, data: list) -> list[list]:
	"""The report as a sheet: one header row, then a row per day; hidden columns left
	out, except SHEET_SHOWS. Pure."""
	shown = [col for col in columns if not col.get("hidden") or col.get("fieldname") in SHEET_SHOWS]
	rows = [[col.get("label") for col in shown]]
	for entry in data:
		rows.append([_cell(entry.get(col["fieldname"])) for col in shown])
	return rows


#: A cell starting with one of these is read as a formula by Excel. Frappe 16's
#: make_xlsx (xlsxwriter) no longer escapes them, unlike 15 (security review of
#: 5bff5d377): a name typed as =HYPERLINK(...) would run on the viewer's machine.
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _cell(value):
	"""A sheet cell: numbers as they are, text as text (never a formula), anything
	else (dates, times) as text. Pure."""
	if value is None or isinstance(value, (int, float)):
		return value
	text = str(value)
	return "'" + text if text.startswith(FORMULA_START) else text


@frappe.whitelist(methods=["GET"])
def my_company() -> dict:
	"""What the download screen shows: the companies the caller's file holds."""
	_require_viewer()
	return {"companies": attendance_viewer_companies() or []}


@frappe.whitelist(methods=["GET"])
def download(month: str):
	"""Send `month` ("YYYY-MM") of Shift Attendance as .xlsx to an Attendance Report Viewer."""
	_require_viewer()
	if not isinstance(month, str) or not MONTH.fullmatch(month):
		frappe.throw(_("Choose a month."), frappe.ValidationError)
	try:
		from_date, to_date = month_range(month)
	except ValueError:
		frappe.throw(_("Choose a month."), frappe.ValidationError)

	from frappe.utils.xlsxutils import build_xlsx_response

	from hrms.hr.report.shift_attendance.shift_attendance import execute

	columns, data, *_rest = execute(
		{"from_date": from_date, "to_date": to_date, "include_attendance_without_checkins": 1}
	)
	logger.info("[attendance_download] %s %s: %d row(s)", frappe.session.user, month, len(data))
	# the name from the checked dates, never the raw argument
	build_xlsx_response(sheet_rows(columns, data), f"shift-attendance-{from_date[:7]}")


def _require_viewer():
	if ATTENDANCE_VIEWER_ROLE not in frappe.get_roles():
		logger.warning("[attendance_download] refused %s: no viewer role", frappe.session.user)
		frappe.throw(_("Only an Attendance Report Viewer can download this."), frappe.PermissionError)
