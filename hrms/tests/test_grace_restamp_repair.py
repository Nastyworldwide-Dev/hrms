"""The one-time repair for punches a neighbouring shift's grace swallowed.

86f324f4b fixed the RULE: a punch inside another assigned shift's own
scheduled hours is no longer claimed by a neighbouring session whose grace
window merely reaches it. It fixes nothing already written — Norazmi's 11
August IN still carries the night's stamp, his day still has two Attendance
rows, and the Fix screen still refuses to rebuild it.

Nabil, 22 September 2026: "if we can make 1 time job to run auto and fix these
is good, less manual work. manual if needed but auto must be done correctly."
So the deploy repairs it and walks away.

What is pinned here:

* the job only touches employees who held MORE THAN ONE shift assignment in
  the window — one assignment cannot be swallowed by another's grace, and
  every other employee is work nobody needs;
* it re-resolves through `hrms.utils.restamp.restamp`, which is the same
  resolution a fresh tap gets, so the repair cannot drift from the rule;
* mirrored punches are never touched (restamp's own filter, asserted here so
  a future rewrite of this job cannot lose it);
* it is idempotent — a second run re-resolves to the same stamps and writes
  nothing;
* it NEVER raises: a deploy must not fail because a background job could not
  be queued.

    PYTHONPATH=. python3 hrms/tests/test_grace_restamp_repair.py
"""

import datetime as dt
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.utils import grace_restamp_repair as repair


class TestOnlyTheEmployeesWhoCouldBeAffected(unittest.TestCase):
	"""One assignment cannot be swallowed by another assignment's grace."""

	def test_an_employee_with_two_assignments_is_in_the_run(self):
		rows = [
			{"employee": "EMP-1", "shift_type": "7PM - 3.30AM"},
			{"employee": "EMP-1", "shift_type": "8AM - 6PM"},
			{"employee": "EMP-2", "shift_type": "8AM - 6PM"},
		]
		with patch.object(frappe, "get_all", return_value=rows):
			self.assertEqual(repair.employees_at_risk("2026-08-01", "2026-09-22"), ["EMP-1"])

	def test_the_same_shift_assigned_twice_is_not_two_shifts(self):
		# A re-issued assignment for ONE shift type cannot overlap itself in a
		# way the grace rule could misread: it is the same window.
		rows = [
			{"employee": "EMP-1", "shift_type": "8AM - 6PM"},
			{"employee": "EMP-1", "shift_type": "8AM - 6PM"},
		]
		with patch.object(frappe, "get_all", return_value=rows):
			self.assertEqual(repair.employees_at_risk("2026-08-01", "2026-09-22"), [])

	def test_nobody_assigned_means_nothing_to_do(self):
		with patch.object(frappe, "get_all", return_value=[]):
			self.assertEqual(repair.employees_at_risk("2026-08-01", "2026-09-22"), [])


class TestTheRepairGoesThroughTheOneResolution(unittest.TestCase):
	def test_each_employee_is_restamped_over_the_window(self):
		calls = []

		def _restamp(employee, from_date, to_date, *, reason, dry_run):
			calls.append((employee, from_date, to_date, reason, dry_run))
			return {"planned": [{"name": "CK-1"}], "released": [], "days": ["2026-08-11"]}

		with (
			patch.object(repair, "employees_at_risk", return_value=["EMP-1", "EMP-2"]),
			patch.object(repair, "restamp", _restamp),
			patch.object(frappe.db, "commit"),
		):
			out = repair.run_repair("2026-08-01", "2026-09-22")
		self.assertEqual([c[0] for c in calls], ["EMP-1", "EMP-2"])
		self.assertTrue(all(c[4] is False for c in calls), "the repair WRITES; a dry run repairs nothing")
		self.assertEqual(out["employees"], 2)
		self.assertEqual(out["punches"], 2)

	def test_an_employee_who_throws_does_not_end_the_run(self):
		def _restamp(employee, from_date, to_date, *, reason, dry_run):
			if employee == "EMP-1":
				raise ValueError("boom")
			return {"planned": [], "released": [], "days": []}

		with (
			patch.object(repair, "employees_at_risk", return_value=["EMP-1", "EMP-2"]),
			patch.object(repair, "restamp", _restamp),
			patch.object(frappe.db, "commit"),
			patch.object(frappe.db, "rollback"),
			patch.object(frappe, "log_error"),
		):
			out = repair.run_repair("2026-08-01", "2026-09-22")
		self.assertEqual(out["employees"], 2, "both were attempted")
		self.assertEqual(out["failed"], ["EMP-1"])

	def test_a_second_run_writes_nothing(self):
		# Idempotence is a property of the resolution, not of a marker: restamp
		# only writes a stamp that DIFFERS, so a repaired punch resolves to what
		# it already carries and is skipped.
		with (
			patch.object(repair, "employees_at_risk", return_value=["EMP-1"]),
			patch.object(repair, "restamp", lambda *a, **kw: {"planned": [], "released": [], "days": []}),
			patch.object(frappe.db, "commit"),
		):
			out = repair.run_repair("2026-08-01", "2026-09-22")
		self.assertEqual(out["punches"], 0)


class TestTheDeployJustAsksForIt(unittest.TestCase):
	def test_the_patch_only_enqueues(self):
		from hrms.patches.v16_0 import run_grace_restamp_repair_once as patch_mod

		with patch.object(frappe, "enqueue") as enqueue:
			patch_mod.execute()
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])

	def test_a_failed_enqueue_never_fails_the_deploy(self):
		from hrms.patches.v16_0 import run_grace_restamp_repair_once as patch_mod

		with (
			patch.object(frappe, "enqueue", side_effect=RuntimeError("no redis")),
			patch.object(frappe, "log_error") as log_error,
		):
			patch_mod.execute()  # must not raise
		log_error.assert_called_once()

	def test_the_patch_is_registered(self):
		line = "hrms.patches.v16_0.run_grace_restamp_repair_once"
		text = (pathlib.Path(__file__).resolve().parents[1] / "patches.txt").read_text()
		self.assertIn(line, text, "a patch nobody lists never runs")


class TestMirroredPunchesAreNeverTouched(unittest.TestCase):
	def test_restamp_still_excludes_synced_punches(self):
		# The repair inherits this from restamp. Asserted here so a future
		# rewrite of the job cannot quietly drop it: a mirrored punch belongs to
		# the instance that owns it (post-cutover guardrail).
		from hrms.utils import restamp as restamp_mod

		source = pathlib.Path(restamp_mod.__file__).read_text()
		self.assertIn('"synced_from_instance": ("is", "not set")', source)


if __name__ == "__main__":
	unittest.main()
