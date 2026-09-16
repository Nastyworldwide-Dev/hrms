"""The Attendance Ownership Check report shows HR who owns each day, and writes nothing.

HR cannot act on the ownership classifier until they can see it: which rows the
machine made, which a person made, which nothing settles, and what the engine
would mark if the day were rebuilt. This is that page — HR roles only, fenced to
the caller's companies the way Shift Attendance is, and read-only throughout:
the "would be" column comes from the recovery's own dry-run preview.

	PYTHONPATH=. python3 hrms/tests/test_attendance_ownership_report.py
"""

import json
import pathlib
import sys
import unittest
from datetime import date
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.report.attendance_ownership_check import attendance_ownership_check as report
from hrms.utils import attendance_ownership as own

HRMS = pathlib.Path(__file__).resolve().parent.parent
REPORT_DIR = HRMS / "hr" / "report" / "attendance_ownership_check"
JSON = json.loads((REPORT_DIR / "attendance_ownership_check.json").read_text())
JS = (REPORT_DIR / "attendance_ownership_check.js").read_text()

DAY = date(2026, 8, 12)


def _classified(**extra):
	row = {
		"employee": "E1",
		"employee_name": "Ria",
		"date": str(DAY),
		"attendance": "ATT-1",
		"status": "Present",
		"working_hours": 9.0,
		"shift": "8AM-6PM",
		"docstatus": 1,
		"auto_attendance": 0,
		"owner": own.OWNER_SYSTEM,
		"reason": "the hourly job marked it from 2 punch(es)",
		"would_relabel": True,
		"punches": 2,
	}
	row.update(extra)
	return row


class TestTheReportIsHROnly(unittest.TestCase):
	def test_it_is_a_script_report_over_attendance(self):
		self.assertEqual(JSON["report_type"], "Script Report")
		self.assertEqual(JSON["ref_doctype"], "Attendance")
		self.assertEqual(JSON["module"], "HR")

	def test_only_hr_manager_and_system_manager_can_open_it(self):
		"""A Script Report gets no row scope from the framework, so a staff role
		here would be an org-wide read of Attendance."""
		self.assertEqual({r["role"] for r in JSON["roles"]}, {"HR Manager", "System Manager"})

	def test_it_fences_itself_to_the_callers_companies(self):
		source = (REPORT_DIR / "attendance_ownership_check.py").read_text()
		self.assertIn("scoped_companies", source)


class TestColumns(unittest.TestCase):
	def test_every_column_hr_reads_the_page_by_is_there(self):
		names = [c["fieldname"] for c in report._columns()]
		for wanted in (
			"employee_name",
			"employee",
			"date",
			"status",
			"working_hours",
			"owner_label",
			"reason",
			"would_relabel",
			"preview",
		):
			self.assertIn(wanted, names, wanted)

	def test_the_attendance_row_is_a_link_so_hr_can_open_it(self):
		column = next(c for c in report._columns() if c["fieldname"] == "attendance")
		self.assertEqual(column["fieldtype"], "Link")
		self.assertEqual(column["options"], "Attendance")


class TestFilters(unittest.TestCase):
	def test_the_window_defaults_to_the_first_of_august_until_yesterday(self):
		filters = frappe._dict()
		with patch.object(report, "_today", return_value=date(2026, 9, 16)):
			report._apply_defaults(filters)
		self.assertEqual(filters["from_date"], "2026-08-01")
		self.assertEqual(filters["to_date"], "2026-09-15")

	def test_a_window_hr_typed_is_left_alone(self):
		filters = frappe._dict(from_date="2026-09-01", to_date="2026-09-10")
		with patch.object(report, "_today", return_value=date(2026, 9, 16)):
			report._apply_defaults(filters)
		self.assertEqual(filters["from_date"], "2026-09-01")
		self.assertEqual(filters["to_date"], "2026-09-10")

	def test_hr_asking_for_today_is_given_yesterday_instead(self):
		"""Today's shifts are still running: a verdict on them would be read off
		half a day. The rule is a ceiling, not just a default."""
		filters = frappe._dict(from_date="2026-09-01", to_date="2026-09-16")
		with patch.object(report, "_today", return_value=date(2026, 9, 16)):
			report._apply_defaults(filters)
		self.assertEqual(filters["to_date"], "2026-09-15")

	def test_a_window_that_starts_after_it_ends_is_pulled_back_to_the_ceiling(self):
		"""Clamping the end can leave the start behind it. An inverted range reads
		as zero rows, so HR would get a blank page with nothing saying why."""
		filters = frappe._dict(from_date="2026-09-16")
		with patch.object(report, "_today", return_value=date(2026, 9, 16)):
			report._apply_defaults(filters)
		self.assertEqual(filters["to_date"], "2026-09-15")
		self.assertEqual(filters["from_date"], "2026-09-15")

	def test_a_future_date_is_clamped_too(self):
		filters = frappe._dict(from_date="2026-09-01", to_date="2027-01-01")
		with patch.object(report, "_today", return_value=date(2026, 9, 16)):
			report._apply_defaults(filters)
		self.assertEqual(filters["to_date"], "2026-09-15")

	def test_the_owner_filter_offers_exactly_the_labels_the_classifier_produces(self):
		for owner in own.OWNERS:
			self.assertIn(f'"{owner}"', JS, owner)

	def test_the_page_says_it_writes_nothing(self):
		self.assertIn("read-only", JS.lower())


class TestTheCompanyFence(unittest.TestCase):
	"""Pure: the fence and the filters over already-classified rows."""

	EMPLOYEES = {  # noqa: RUF012
		"E1": {"employee_name": "Ria", "company": "Nasty"},
		"E2": {"employee_name": "Siti", "company": "Other Co"},
	}

	def test_a_row_outside_the_fence_is_dropped(self):
		rows = [_classified(), _classified(employee="E2", attendance="ATT-2")]
		out = report.fence_rows(rows, frappe._dict(), self.EMPLOYEES, ["Nasty"])
		self.assertEqual([r["attendance"] for r in out], ["ATT-1"])

	def test_an_unfenced_caller_sees_every_company(self):
		rows = [_classified(), _classified(employee="E2", attendance="ATT-2")]
		out = report.fence_rows(rows, frappe._dict(), self.EMPLOYEES, [])
		self.assertEqual(len(out), 2)

	def test_the_employee_filter_narrows_the_page(self):
		rows = [_classified(), _classified(employee="E2", attendance="ATT-2")]
		out = report.fence_rows(rows, frappe._dict(employee="E2"), self.EMPLOYEES, [])
		self.assertEqual([r["attendance"] for r in out], ["ATT-2"])

	def test_the_owner_filter_narrows_the_page(self):
		rows = [_classified(), _classified(attendance="ATT-2", owner=own.OWNER_HR, would_relabel=False)]
		out = report.fence_rows(rows, frappe._dict(owner=own.OWNER_HR), self.EMPLOYEES, [])
		self.assertEqual([r["attendance"] for r in out], ["ATT-2"])

	def test_each_row_carries_a_label_hr_can_read_and_a_yes_no(self):
		out = report.fence_rows([_classified()], frappe._dict(), self.EMPLOYEES, [])
		self.assertEqual(out[0]["owner_label"], report.OWNER_LABELS[own.OWNER_SYSTEM])
		self.assertEqual(out[0]["would_relabel"], "yes")


class TestSummary(unittest.TestCase):
	def test_the_summary_counts_every_label(self):
		rows = [
			{"owner": own.OWNER_SYSTEM, "would_relabel": "yes"},
			{"owner": own.OWNER_SYSTEM, "would_relabel": "no"},
			{"owner": own.OWNER_HR, "would_relabel": "no"},
			{"owner": own.OWNER_UNSURE, "would_relabel": "no"},
		]
		message = report._summary(rows)
		for piece in ("2", "1", report.OWNER_LABELS[own.OWNER_HR]):
			self.assertIn(str(piece), message)


class TestThePreviewNeverWrites(unittest.TestCase):
	def test_the_preview_goes_through_the_recoverys_dry_run_and_swallows_its_failures(self):
		with patch.object(report, "_expected_day", side_effect=RuntimeError("no shift")):
			self.assertIn("could not", report.preview_for(_classified()).lower())

	def test_a_failed_preview_keeps_the_exception_in_the_log_not_in_the_cell(self):
		with patch.object(report, "_expected_day", side_effect=RuntimeError("secret-internal-id")):
			self.assertNotIn("secret-internal-id", report.preview_for(_classified()))

	def test_a_preview_reads_as_the_status_and_the_hours_the_engine_would_mark(self):
		with patch.object(
			report,
			"_expected_day",
			return_value={"status": "Present", "working_hours": 9.5, "shift": "8AM-6PM"},
		):
			self.assertEqual(report.preview_for(_classified()), "Present · 9.5h · 8AM-6PM")

	def test_the_report_module_never_calls_a_writing_step(self):
		source = (REPORT_DIR / "attendance_ownership_check.py").read_text()
		for writer in ("relabel_system_rows", "db.set_value", "dry_run=0", ".insert(", ".save("):
			self.assertNotIn(writer, source, writer)


if __name__ == "__main__":
	unittest.main()
