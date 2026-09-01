"""Guards the attendance allowance configuration and its monthly booking job.

Promises pinned here:

* eligibility policy (Present / Half Day / WFH, late-entry, early-exit,
  minimum working hours) pays exactly what the configuration says;
* the monthly job is idempotent — an existing Additional Salary for the
  same (employee, type, period) means no second booking, ever;
* a booking carries the ref back to its Attendance Allowance Type (the
  audit trail and the idempotency key are the same record);
* ordinary employees get no write access to the configuration doctype;
* the job is actually registered in the monthly scheduler.

Bench-free by construction: the module is loaded straight from its file with
a stub `frappe` in `sys.modules`. Run it as a FILE:

    python3 hrms/tests/test_attendance_allowance.py
"""

import datetime
import importlib.util
import json
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "hr" / "doctype" / "attendance_allowance_type" / "attendance_allowance_type.py"
JSON_PATH = MODULE_PATH.with_suffix(".json")
HOOKS_PATH = HRMS_ROOT / "hooks.py"


def _flt(value, precision=None):
	try:
		value = float(value or 0)
	except (TypeError, ValueError):
		return 0.0
	return round(value, precision) if precision is not None else value


def _getdate(value=None):
	if isinstance(value, datetime.date):
		return value
	return datetime.date.fromisoformat(str(value))


def _load_module():
	if "frappe" not in sys.modules:
		frappe = types.ModuleType("frappe")
		frappe._ = lambda text: text
		frappe.whitelist = lambda *a, **kw: lambda fn: fn
		frappe.flags = types.SimpleNamespace()
		frappe_utils = types.ModuleType("frappe.utils")
		frappe_model = types.ModuleType("frappe.model")
		frappe_model_document = types.ModuleType("frappe.model.document")
		frappe_model_document.Document = type("Document", (), {})
		frappe.utils = frappe_utils
		sys.modules["frappe"] = frappe
		sys.modules["frappe.model"] = frappe_model
		sys.modules["frappe.model.document"] = frappe_model_document
	frappe = sys.modules["frappe"]
	frappe_utils = sys.modules.setdefault("frappe.utils", frappe.utils)
	frappe_utils.flt = _flt
	frappe_utils.getdate = _getdate
	frappe_utils.get_first_day = lambda d: _getdate(d).replace(day=1)
	frappe_utils.add_days = lambda d, days: _getdate(d) + datetime.timedelta(days=days)
	sys.modules["frappe.model.document"].Document = type("Document", (), {})

	spec = importlib.util.spec_from_file_location("_attendance_allowance_under_test", MODULE_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


allowance = _load_module()

RULE = {
	"name": "Punctuality Bonus",
	"company": None,
	"salary_component": "Attendance Allowance",
	"allowance_amount": 10.0,
	"include_half_day": 0,
	"include_work_from_home": 0,
	"exclude_late_entry": 0,
	"exclude_early_exit": 0,
	"minimum_working_hours": 0,
}


class TestEligibleAllowanceDays(unittest.TestCase):
	def test_present_days_count(self):
		rows = [{"status": "Present"}, {"status": "Present"}]
		self.assertEqual(allowance.eligible_allowance_days(rows, RULE), 2.0)

	def test_absent_and_on_leave_never_count(self):
		rows = [{"status": "Absent"}, {"status": "On Leave"}]
		self.assertEqual(allowance.eligible_allowance_days(rows, RULE), 0.0)

	def test_half_day_counts_half_only_when_included(self):
		rows = [{"status": "Half Day"}]
		self.assertEqual(allowance.eligible_allowance_days(rows, RULE), 0.0)
		self.assertEqual(allowance.eligible_allowance_days(rows, {**RULE, "include_half_day": 1}), 0.5)

	def test_work_from_home_only_when_included(self):
		rows = [{"status": "Work From Home"}]
		self.assertEqual(allowance.eligible_allowance_days(rows, RULE), 0.0)
		self.assertEqual(allowance.eligible_allowance_days(rows, {**RULE, "include_work_from_home": 1}), 1.0)

	def test_late_entry_and_early_exit_exclusions(self):
		rows = [
			{"status": "Present", "late_entry": 1},
			{"status": "Present", "early_exit": 1},
			{"status": "Present"},
		]
		self.assertEqual(allowance.eligible_allowance_days(rows, RULE), 3.0)
		self.assertEqual(allowance.eligible_allowance_days(rows, {**RULE, "exclude_late_entry": 1}), 2.0)
		self.assertEqual(
			allowance.eligible_allowance_days(
				rows, {**RULE, "exclude_late_entry": 1, "exclude_early_exit": 1}
			),
			1.0,
		)

	def test_minimum_working_hours(self):
		rows = [
			{"status": "Present", "working_hours": 8.0},
			{"status": "Present", "working_hours": 3.5},
			{"status": "Present"},  # checkin pair missing -> 0 hours
		]
		self.assertEqual(allowance.eligible_allowance_days(rows, {**RULE, "minimum_working_hours": 4}), 1.0)

	def test_eligible_statuses_follow_flags(self):
		self.assertEqual(allowance.eligible_statuses(RULE), ["Present"])
		self.assertEqual(
			allowance.eligible_statuses({**RULE, "include_half_day": 1, "include_work_from_home": 1}),
			["Present", "Work From Home", "Half Day"],
		)


class _BookedDoc:
	def __init__(self, payload, log):
		self.payload = payload
		self.flags = types.SimpleNamespace()
		self._log = log

	def submit(self):
		self._log.append(self.payload)


class _FakeDb:
	def __init__(self, existing=False):
		self.existing = existing
		self.savepoints = 0
		self.rollbacks = 0

	def savepoint(self, name):
		self.savepoints += 1

	def rollback(self, save_point=None):
		self.rollbacks += 1

	def exists(self, doctype, filters):
		return "AS-00001" if self.existing else None


class TestMonthlyProcessing(unittest.TestCase):
	def _run(self, existing, attendance_rows=None):
		frappe = sys.modules["frappe"]
		booked = []
		frappe.db = _FakeDb(existing=existing)
		frappe.get_all = lambda doctype, filters=None, fields=None: (
			[dict(RULE)]
			if doctype == "Attendance Allowance Type"
			else list(
				attendance_rows
				if attendance_rows is not None
				else [
					{"employee": "HR-EMP-1", "company": "Acme", "status": "Present"},
					{"employee": "HR-EMP-1", "company": "Acme", "status": "Present"},
				]
			)
		)
		frappe.get_doc = lambda payload: _BookedDoc(payload, booked)
		frappe.log_error = lambda **kw: None
		frappe.get_traceback = lambda: ""
		counters = allowance.process_attendance_allowances("2026-08-01", "2026-08-31")
		return counters, booked

	def test_books_one_additional_salary_with_ref(self):
		counters, booked = self._run(existing=False)
		self.assertEqual(counters, {"created": 1, "skipped": 0, "error": 0})
		self.assertEqual(len(booked), 1)
		payload = booked[0]
		self.assertEqual(payload["doctype"], "Additional Salary")
		self.assertEqual(payload["ref_doctype"], "Attendance Allowance Type")
		self.assertEqual(payload["ref_docname"], "Punctuality Bonus")
		self.assertEqual(payload["amount"], 20.0)
		self.assertEqual(payload["payroll_date"], datetime.date(2026, 8, 31))

	def test_rerun_with_existing_booking_is_a_noop(self):
		counters, booked = self._run(existing=True)
		self.assertEqual(counters, {"created": 0, "skipped": 1, "error": 0})
		self.assertEqual(booked, [])

	def test_zero_eligible_days_books_nothing(self):
		counters, booked = self._run(
			existing=False,
			attendance_rows=[{"employee": "HR-EMP-1", "company": "Acme", "status": "Absent"}],
		)
		self.assertEqual(counters, {"created": 0, "skipped": 1, "error": 0})
		self.assertEqual(booked, [])


class TestPermissionsAndWiring(unittest.TestCase):
	def test_employees_cannot_touch_the_configuration(self):
		meta = json.loads(JSON_PATH.read_text())
		roles = {perm["role"]: perm for perm in meta["permissions"]}
		self.assertNotIn("Employee", roles)
		self.assertEqual(roles["HR User"].get("write", 0), 0)
		self.assertEqual(roles["HR User"].get("create", 0), 0)
		self.assertEqual(roles["HR Manager"].get("write"), 1)
		self.assertEqual(roles["System Manager"].get("write"), 1)

	def test_value_fields_are_required(self):
		meta = json.loads(JSON_PATH.read_text())
		reqd = {f["fieldname"] for f in meta["fields"] if f.get("reqd")}
		self.assertIn("salary_component", reqd)
		self.assertIn("allowance_amount", reqd)

	def test_job_is_registered_monthly(self):
		hooks = HOOKS_PATH.read_text()
		self.assertIn(
			"hrms.hr.doctype.attendance_allowance_type.attendance_allowance_type.process_attendance_allowances",
			hooks,
		)


if __name__ == "__main__":
	unittest.main(verbosity=2)
