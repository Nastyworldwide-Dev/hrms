"""Unit tests for attendance-timezone resolution.

Pure unit tests: `frappe.db` is mocked, so these run without a bench or site
(`python -m unittest hrms.utils.test_timezone` from the repo root with a
frappe-importable interpreter), as well as under `bench run-tests`.
"""

import datetime
import unittest
from unittest.mock import patch

import frappe

from hrms.utils.timezone import employee_now, get_attendance_timezone

KL = "Asia/Kuala_Lumpur"
DUBAI = "Asia/Dubai"
SHANGHAI = "Asia/Shanghai"


class _FakeDB:
	"""Stands in for frappe.db — answers get_value from canned tables."""

	def __init__(self, shift_locations=None, employees=None, companies=None, assignments=None):
		self.shift_locations = shift_locations or {}
		self.employees = employees or {}
		self.companies = companies or {}
		self.assignments = assignments or {}
		self.calls = []

	def get_value(self, doctype, filters, fieldname, **kwargs):
		self.calls.append((doctype, filters, fieldname))
		if doctype == "Shift Location":
			return self.shift_locations.get(filters)
		if doctype == "Employee":
			return self.employees.get(filters)
		if doctype == "Company":
			return self.companies.get(filters)
		return None

	def get_all(self, doctype, **kwargs):
		if doctype == "Shift Assignment":
			employee = dict(kwargs.get("filters") or {}).get("employee")
			loc = self.assignments.get(employee)
			return [{"shift_location": loc}] if loc else []
		return []


class TestAttendanceTimezone(unittest.TestCase):
	def _run(self, db, *args, **kwargs):
		# nowdate() reads System Settings, which needs a site; the date itself
		# is irrelevant to resolution order, so pin it.
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", db.get_all),
			patch("hrms.utils.timezone.nowdate", return_value="2026-08-03"),
			patch.object(frappe, "local", type("L", (), {})()),
		):
			return get_attendance_timezone(*args, **kwargs)

	def test_shift_location_wins_over_company(self):
		"""Where the employee physically punches beats where they are registered.

		The real case: a UAE-registered company with staff working in Malaysia.
		"""
		db = _FakeDB(
			shift_locations={"Damansara": KL},
			employees={"HR-EMP-001": "NSTY INTERNATIONAL LTD"},
			companies={"NSTY INTERNATIONAL LTD": DUBAI},
		)
		self.assertEqual(self._run(db, "HR-EMP-001", "Damansara"), KL)

	def test_falls_back_to_company_when_location_has_no_timezone(self):
		db = _FakeDB(
			shift_locations={"Damansara": None},
			employees={"HR-EMP-001": "Nasty Worldwide Sdn Bhd"},
			companies={"Nasty Worldwide Sdn Bhd": KL},
		)
		self.assertEqual(self._run(db, "HR-EMP-001", "Damansara"), KL)

	def test_resolves_active_assignment_location_when_not_passed(self):
		"""Callers like punch() don't know the location yet — resolve it."""
		db = _FakeDB(
			shift_locations={"China Office": SHANGHAI},
			employees={"HR-EMP-002": "Nasty Worldwide Sdn Bhd"},
			companies={"Nasty Worldwide Sdn Bhd": KL},
			assignments={"HR-EMP-002": "China Office"},
		)
		self.assertEqual(self._run(db, "HR-EMP-002"), SHANGHAI)

	def test_falls_back_to_company_when_no_assignment(self):
		db = _FakeDB(
			employees={"HR-EMP-003": "Nasty Worldwide Sdn Bhd"},
			companies={"Nasty Worldwide Sdn Bhd": KL},
		)
		self.assertEqual(self._run(db, "HR-EMP-003"), KL)

	def test_falls_back_to_system_timezone_when_nothing_configured(self):
		"""Unconfigured sites keep today's behaviour exactly."""
		db = _FakeDB(employees={"HR-EMP-004": "Some Co"}, companies={"Some Co": None})
		with patch("hrms.utils.timezone.get_system_timezone", return_value=DUBAI):
			self.assertEqual(self._run(db, "HR-EMP-004"), DUBAI)

	def test_no_employee_falls_back_to_system_timezone(self):
		db = _FakeDB()
		with patch("hrms.utils.timezone.get_system_timezone", return_value=DUBAI):
			self.assertEqual(self._run(db, None), DUBAI)


class TestEmployeeNow(unittest.TestCase):
	def test_returns_naive_wall_clock_of_the_attendance_timezone(self):
		"""Naive on purpose — stored check-in times are naive wall clock, so
		comparisons must share that basis."""
		with patch("hrms.utils.timezone.get_attendance_timezone", return_value=KL):
			now = employee_now("HR-EMP-001")

		self.assertIsNone(now.tzinfo, "must be naive to compare with stored times")
		expected = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(hours=8)
		self.assertLess(abs((now - expected).total_seconds()), 5)

	def test_dubai_site_and_malaysian_employee_differ_by_four_hours(self):
		"""The exact production skew: site clock Dubai, employee in Malaysia."""
		with patch("hrms.utils.timezone.get_attendance_timezone", return_value=KL):
			my_now = employee_now("HR-EMP-001")
		with patch("hrms.utils.timezone.get_attendance_timezone", return_value=DUBAI):
			ae_now = employee_now("HR-EMP-999")

		self.assertAlmostEqual((my_now - ae_now).total_seconds(), 4 * 3600, delta=5)


if __name__ == "__main__":
	unittest.main()
