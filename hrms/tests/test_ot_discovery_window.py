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
import importlib.util
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

harness = importlib.import_module("test_ot_claim_monthly_capacity")
ot = importlib.import_module("hrms.utils.ot_calculation")

EMPLOYEE = "EMP-SYNTHETIC"
# The harness clock. The fence itself is DERIVED, not written down: this file's
# question — "discovery offers exactly what filing accepts, never wider" — is
# policy-independent, so it must not need editing when the policy moves. It did
# need editing once, which is how this comment came to be here.
TODAY = date(2026, 9, 30)

_fw_spec = importlib.util.spec_from_file_location(
	"_filing_window", Path(__file__).resolve().parents[1] / "utils" / "filing_window.py"
)
_filing_window = importlib.util.module_from_spec(_fw_spec)
_fw_spec.loader.exec_module(_filing_window)
FENCE = _filing_window.earliest_filable_date(TODAY)
INSIDE_WINDOW_BUT_OLD = date(2026, 7, 20)  # 72 days back: filable, hidden by a 45-day lookback
BEFORE_WINDOW = FENCE - timedelta(days=1)  # the day before the fence, wherever it sits
RECENT = date(2026, 9, 25)


def _discover(requests=(), reads=None, **params):
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
			if reads is not None:
				reads.append(dict(filters=filters, fields=fields, **kwargs))
			start, end = filters["ot_date"][1]
			op, limit = filters["docstatus"]
			assert op == "<", op
			return [
				frappe._dict(row)
				for row in requests
				if start <= row["ot_date"] <= end and row["docstatus"] < limit
			]
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
		self.assertEqual(result["from_date"], str(FENCE))
		self.assertEqual(result["to_date"], str(TODAY))

	def test_a_day_before_the_filing_window_is_not_offered(self):
		self.assertNotIn(str(BEFORE_WINDOW), [day["date"] for day in _discover()["days"]])

	def test_a_caller_may_narrow_the_window_but_never_widen_it(self):
		self.assertEqual([day["date"] for day in _discover(days=10)["days"]], ["2026-09-25"])
		self.assertEqual(_discover(days=400)["from_date"], str(FENCE))


class TestClaimedDaysAreReturned(unittest.TestCase):
	"""Days that already have a request are not silently dropped: the form shows them
	greyed with their decision. Same single read, same window, cancelled excluded."""

	REQUESTS = (
		dict(ot_date=RECENT, claimed_hours=2.5, status="Approved", docstatus=1),
		dict(ot_date=INSIDE_WINDOW_BUT_OLD, claimed_hours=1.0, status="Open", docstatus=0),
		dict(ot_date=date(2026, 9, 20), claimed_hours=3.0, status="Rejected", docstatus=1),
		dict(ot_date=date(2026, 9, 21), claimed_hours=4.0, status="Approved", docstatus=2),
		dict(ot_date=BEFORE_WINDOW, claimed_hours=1.0, status="Approved", docstatus=1),
	)

	def test_claimed_days_carry_hours_and_decision_newest_first(self):
		result = _discover(requests=self.REQUESTS)
		self.assertEqual(
			result["claimed"],
			[
				{"date": "2026-09-25", "hours": 2.5, "status": "Approved", "docstatus": 1},
				{"date": "2026-09-20", "hours": 3.0, "status": "Rejected", "docstatus": 1},
				{"date": "2026-07-20", "hours": 1.0, "status": "Open", "docstatus": 0},
			],
		)
		# claimed days are still not offered as claimable
		self.assertEqual(result["days"], [])
		self.assertEqual(result["days_already_claimed"], 3)

	def test_one_ot_request_read_in_the_filing_window(self):
		reads = []
		_discover(requests=self.REQUESTS, reads=reads)
		self.assertEqual(len(reads), 1)
		self.assertEqual(reads[0]["filters"]["ot_date"], ["between", [FENCE, TODAY]])
		self.assertEqual(reads[0]["filters"]["docstatus"], ["<", 2])
		self.assertNotIn("pluck", reads[0])

	def test_no_requests_means_an_empty_claimed_list(self):
		self.assertEqual(_discover()["claimed"], [])


if __name__ == "__main__":
	unittest.main()
