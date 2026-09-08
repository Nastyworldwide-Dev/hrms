""" "Days you can claim" covers every day that can still be filed.

The discovery list behind the OT form's quick-picks and the dashboard's
"you have X h to claim" card looked back a fixed 45 days, while the filing
rule (hrms/utils/filing_window.py) accepts an OT date back to the start of
the cycle two cycles ago — on 30 Sep, 16 Jul. A day worked on 20 Jul was
therefore still claimable through the date picker but never offered, and an
employee who trusted the list believed it was gone. Discovery now spans the
same window the validation enforces; a caller may still ask for a shorter
recent view, never a wider one.

Bench-free: the real endpoint body runs through the shared API harness; the
Attendance and OT Request reads honour the date filters the endpoint sends.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_ot_discovery_window.py
"""

import importlib
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

harness = importlib.import_module("test_ot_claim_monthly_capacity")
ot = importlib.import_module("hrms.utils.ot_calculation")

EMPLOYEE = "EMP-SYNTHETIC"
TODAY = date(2026, 9, 30)  # the harness clock; cycle began 16 Sep, so 16 Jul is the earliest filable date
INSIDE_WINDOW_BUT_OLD = date(2026, 7, 20)  # 72 days back: filable, hidden by a 45-day lookback
BEFORE_WINDOW = date(2026, 7, 10)
RECENT = date(2026, 9, 25)


def _discover(**params):
	worked = (BEFORE_WINDOW, INSIDE_WINDOW_BUT_OLD, RECENT)

	def get_all(doctype, filters=None, fields=None, **kwargs):
		if doctype == "Attendance":
			start, end = filters["attendance_date"][1]
			return [
				frappe._dict(attendance_date=day, ot_hours=1.0)
				for day in worked
				if date.fromisoformat(str(start)) <= day <= date.fromisoformat(str(end))
			]
		if doctype == "OT Request":
			return []
		raise AssertionError(doctype)

	with (
		patch.object(frappe, "get_all", side_effect=get_all),
		patch.object(frappe.db, "get_value", return_value=1),  # eligible for overtime pay
		patch.object(
			ot,
			"get_ot_claim_capacity",
			return_value={"hours": 1.0, "monthly_remaining": None, "uncapped_hours": 0.0},
		),
	):
		return harness.API["get_claimable_ot_summary"](employee=EMPLOYEE, **params)


class TestDiscoveryWindow(unittest.TestCase):
	def test_every_filable_day_is_offered(self):
		result = _discover()
		self.assertEqual([day["date"] for day in result["days"]], ["2026-09-25", "2026-07-20"])
		self.assertEqual(result["from_date"], "2026-07-16")
		self.assertEqual(result["to_date"], str(TODAY))

	def test_a_day_before_the_filing_window_is_not_offered(self):
		self.assertNotIn("2026-07-10", [day["date"] for day in _discover()["days"]])

	def test_a_caller_may_narrow_the_window_but_never_widen_it(self):
		self.assertEqual([day["date"] for day in _discover(days=10)["days"]], ["2026-09-25"])
		self.assertEqual(_discover(days=400)["from_date"], "2026-07-16")


if __name__ == "__main__":
	unittest.main()
