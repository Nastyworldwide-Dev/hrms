"""Replacement Leave discovery offers exactly the days the form will accept.

`get_claimable_ot_summary` sized Overtime-Pay days with `get_ot_claim_capacity`
but Replacement-Leave days from raw `Attendance.ot_hours`. The form
(`get_ot_claim_summary`) and the save (`OTRequest.set_punch_verified_cap`) both
use `get_ot_claim_capacity(employee, date, "Replacement Leave")`. So the PWA card
offered a day, the employee tapped it, and the form said "nothing to claim".

Pinned: with the capacity engine answering 0 h for one worked day and 1.5 h for
another, the RL summary lists only the second, with the engine's hours.

    PYTHONPATH=. python3 hrms/tests/test_rl_discovery_uses_capacity.py
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
CAPPED_OUT = date(2026, 9, 24)  # Attendance says 2 h; the capacity engine says 0
CLAIMABLE = date(2026, 9, 25)  # Attendance says 2 h; the capacity engine says 1.5
CAPACITY = {CAPPED_OUT: 0.0, CLAIMABLE: 1.5}


def _discover():
	def get_all(doctype, filters=None, fields=None, **kwargs):
		if doctype == "Attendance":
			return [frappe._dict(attendance_date=day, ot_hours=2.0) for day in CAPACITY]
		if doctype == "OT Request":
			return []
		raise AssertionError(doctype)

	def capacity(employee, day, compensation, **kwargs):
		assert compensation == "Replacement Leave", compensation
		return {"hours": CAPACITY[day], "monthly_remaining": None}

	with (
		patch.object(frappe, "get_all", side_effect=get_all),
		patch.object(frappe.db, "get_value", return_value=0),  # NOT eligible for overtime pay
		patch.object(ot, "get_ot_claim_capacity", side_effect=capacity),
	):
		return harness.API["get_claimable_ot_summary"](employee=EMPLOYEE)


class TestReplacementLeaveDiscoveryMatchesTheForm(unittest.TestCase):
	def test_only_days_with_capacity_are_offered_with_the_engine_hours(self):
		result = _discover()
		self.assertEqual(result["compensation"], "Replacement Leave")
		self.assertEqual(result["days"], [{"date": str(CLAIMABLE), "hours": 1.5}])
		self.assertEqual(result["claimable_days"], 1)
		self.assertEqual(result["claimable_hours"], 1.5)


if __name__ == "__main__":
	unittest.main()
