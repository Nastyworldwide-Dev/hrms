"""The ERP's pre-cutover punches are copied here, then those days are rebuilt (B2/B3).

Insert-only, source-keyed, and every guard the lone-IN closer learned holds
here too — because this copy is the same act over a far wider window:

* the write switch (HR Settings `attendance_erp_backfill`) reads as OFF while
  its field does not exist, and a run refuses when it is off;
* a pilot list (HR Settings `attendance_rebuild_pilot_employees`) is a FENCE:
  non-empty means only those employees, whoever the caller asked for;
* a tap within 3 minutes of ANY hub tap — counted, skipped, rejected, mirrored
  — is the same tap and is refused, so a copy never doubles a punch;
* an employee-day that is today, HR-removed, HR-owned, covered by a leave or a
  request, or one a payout depends on, is left alone;
* the instance lock is taken again after every commit, and a sync in flight
  stops the run;
* nothing is ever written to the ERP, and nothing raises into a background job.

After the punches land, each touched day is rebuilt through the engine, oldest
first, under the never-worse guard.

    PYTHONPATH=. python3 hrms/tests/test_erp_backfill_copy.py
"""

import pathlib
import sys
import unittest
from datetime import date, datetime, timedelta
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

from hrms.sync import erp_backfill as bf

EMP = "HR-EMP-00313"
OTHER = "HR-EMP-00999"
DAY = date(2026, 8, 17)
D = datetime


def _erp(moment, log_type="OUT", name="ERP-1", employee=EMP):
	return {"name": name, "employee": employee, "time": moment, "log_type": log_type, "device_id": "ERP"}


def _hub(moment, log_type="IN", name="EC-1", **extra):
	row = {
		"name": name,
		"employee": EMP,
		"time": moment,
		"log_type": log_type,
		"shift_start": D(2026, 8, 17, 0, 0),
		"skip_auto_attendance": 0,
		"remote_approval_status": None,
	}
	row.update(extra)
	return row


class TestPlanBackfill(unittest.TestCase):
	"""What one employee's copy would insert, before any day protection."""

	def test_a_punch_the_hub_does_not_hold_is_planned(self):
		planned, refused = bf.plan_backfill(
			EMP, [_erp(D(2026, 8, 17, 18, 0))], [_hub(D(2026, 8, 17, 9, 0))], DAY, DAY
		)
		self.assertEqual(len(planned), 1)
		self.assertEqual(planned[0]["time"], "2026-08-17 18:00:00")
		self.assertEqual((planned[0]["employee"], planned[0]["date"]), (EMP, str(DAY)))
		self.assertEqual(planned[0]["remote_name"], "ERP-1")
		self.assertEqual(refused, [])

	def test_a_punch_within_three_minutes_of_a_hub_tap_is_refused(self):
		planned, refused = bf.plan_backfill(
			EMP, [_erp(D(2026, 8, 17, 9, 2))], [_hub(D(2026, 8, 17, 9, 0))], DAY, DAY
		)
		self.assertEqual(planned, [])
		self.assertIn("duplicate", refused[0]["reason"])

	def test_a_skipped_or_rejected_hub_tap_still_refuses_the_copy(self):
		"""HR skip-stamped it or an approver rejected it: the tap IS here, and a
		person decided about it. Copying it back would undo that decision."""
		for tap in (
			_hub(D(2026, 8, 17, 18, 0), "OUT", skip_auto_attendance=1),
			_hub(D(2026, 8, 17, 18, 0), "OUT", remote_approval_status="Rejected"),
		):
			planned, refused = bf.plan_backfill(EMP, [_erp(D(2026, 8, 17, 18, 1))], [tap], DAY, DAY)
			self.assertEqual(planned, [])
			self.assertIn("duplicate", refused[0]["reason"])

	def test_a_day_outside_the_window_is_not_planned(self):
		planned, _refused = bf.plan_backfill(EMP, [_erp(D(2026, 8, 20, 18, 0))], [], DAY, DAY)
		self.assertEqual(planned, [])

	def test_the_log_type_the_erp_recorded_is_carried(self):
		planned, _refused = bf.plan_backfill(EMP, [_erp(D(2026, 8, 17, 18, 0), "IN")], [], DAY, DAY)
		self.assertEqual(planned[0]["log_type"], "IN")


class _CopyCase(unittest.TestCase):
	"""A run with every read mocked: no bench, no ERP, no database."""

	def setUp(self):
		self.db = MagicMock()
		self.client = MagicMock()
		self.client.get_list.side_effect = lambda *a, **k: list(self.erp)
		self.erp = [_erp(D(2026, 8, 17, 18, 0))]
		self.hub = {EMP: [_hub(D(2026, 8, 17, 9, 0))]}
		self.inserted = []
		self.rebuilt = []
		patches = [
			patch.object(frappe, "db", self.db),
			patch.object(bf, "_enabled", return_value=True),
			patch.object(bf, "_pilot_text", return_value=""),
			patch.object(bf, "_source_instance", return_value="erp-live"),
			patch.object(bf, "_sync_running", return_value=False),
			patch.object(bf, "_client", return_value=self.client),
			patch.object(bf, "_employees_in_scope", side_effect=self._scope),
			patch.object(bf, "_hub_punches", side_effect=lambda *a, **k: dict(self.hub)),
			patch.object(bf, "_protection", return_value=None),
			patch.object(bf, "_lock", return_value=True),
			patch.object(bf, "_insert", side_effect=self._insert),
			patch.object(bf, "rebuild_days", side_effect=self._rebuild),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def _scope(self, instance, employees=None):
		return list(employees) if employees else [EMP]

	def _insert(self, entry, instance):
		self.inserted.append(entry)
		return f"EC-NEW-{len(self.inserted)}"

	def _rebuild(self, days):
		self.rebuilt = list(days)
		return {"rebuilt": [{"employee": e, "date": str(d)} for e, d in days], "held_back": []}

	def run_copy(self, **kwargs):
		return bf.backfill_punches(DAY, DAY, dry_run=0, **kwargs)


class TestCopyGuards(_CopyCase):
	def test_a_missing_punch_is_inserted_and_its_day_rebuilt(self):
		out = self.run_copy()
		self.assertEqual(len(out["inserted"]), 1)
		self.assertEqual(self.inserted[0]["time"], "2026-08-17 18:00:00")
		self.assertEqual(self.rebuilt, [(EMP, DAY)])

	def test_the_switch_off_copies_nothing(self):
		with patch.object(bf, "_enabled", return_value=False):
			out = self.run_copy()
		self.assertEqual(self.inserted, [])
		self.assertIn(bf.SWITCH, out["note"])

	def test_a_dry_run_plans_but_writes_nothing(self):
		out = bf.backfill_punches(DAY, DAY, dry_run=1)
		self.assertTrue(out["dry_run"])
		self.assertEqual(len(out["planned"]), 1)
		self.assertEqual(self.inserted, [])
		self.db.commit.assert_not_called()

	def test_the_pilot_list_is_a_fence(self):
		with patch.object(bf, "_pilot_text", return_value=f"{EMP}, {OTHER}"):
			self.run_copy(employees=[OTHER])
		self.assertEqual(self.inserted, [], "an employee outside the asked-for set is not copied")
		with patch.object(bf, "_pilot_text", return_value=OTHER):
			self.run_copy()
		self.assertEqual(self.inserted, [], "an employee outside the pilot list is not copied")

	def test_a_protected_day_is_held_and_never_inserted(self):
		with patch.object(bf, "_protection", return_value="HR-ATT-1 was marked by HR by hand"):
			out = self.run_copy()
		self.assertEqual(self.inserted, [])
		self.assertIn("by hand", out["held_back"][0]["reason"])
		self.assertTrue(out["held_back"][0]["hr"])

	def test_it_never_writes_to_the_erp(self):
		self.run_copy()
		self.assertEqual(
			sorted({call[0] for call in self.client.method_calls}),
			["get_list"],
			"the copy may only GET from the ERP",
		)

	def test_a_sync_in_flight_stops_the_run(self):
		with patch.object(bf, "_sync_running", return_value=True):
			out = self.run_copy()
		self.assertEqual(self.inserted, [])
		self.assertIn("sync running", out["note"])

	def test_a_failed_insert_holds_that_punch_and_never_raises(self):
		with patch.object(bf, "_insert", side_effect=ValueError("boom")):
			out = self.run_copy()
		self.assertIn("boom", out["held_back"][0]["reason"])
		self.db.rollback.assert_called_with(save_point=bf.ROW_SAVEPOINT)

	def test_a_source_key_duplicate_is_already_imported_not_an_error(self):
		with (
			patch.object(bf, "_insert", side_effect=ValueError("dup")),
			patch.object(bf, "is_source_key_duplicate", return_value=True),
		):
			out = self.run_copy()
		self.assertEqual(out["held_back"], [])
		self.assertEqual(out["already_imported"], 1)

	def test_the_lock_is_taken_again_after_each_commit(self):
		self.erp = [
			_erp(D(2026, 8, 17, 12, 0) + timedelta(seconds=i * 300), name=f"ERP-{i}") for i in range(51)
		]
		with patch.object(bf, "_lock", side_effect=[True, False]) as lock:
			out = self.run_copy()
		self.assertEqual(lock.call_count, 2)
		self.assertEqual(len(out["inserted"]), bf.COMMIT_EVERY)
		self.assertIn("sync running", out["held_back"][0]["reason"])

	def test_a_window_after_the_cutover_is_refused(self):
		out = bf.backfill_punches(date(2026, 9, 4), date(2026, 9, 5), dry_run=0)
		self.assertIn("cutover", out["note"])
		self.assertEqual(self.inserted, [])

	def test_a_crash_anywhere_is_a_note_not_an_exception(self):
		with patch.object(bf, "_hub_punches", side_effect=RuntimeError("database gone")):
			out = self.run_copy()
		self.assertIn("database gone", out["note"])


class TestRebuildDays(unittest.TestCase):
	"""The copied days go back through the engine, oldest first, under the guard."""

	def setUp(self):
		self.db = MagicMock()
		self.locked = []
		self.guarded = []
		patches = [
			patch.object(frappe, "db", self.db),
			patch.object(bf, "_lock_employee", side_effect=self.locked.append),
			patch.object(bf, "_protection", return_value=None),
			patch.object(bf, "_guarded_rebuild", side_effect=self._rebuild),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)
		self.held = {}

	def _rebuild(self, employee, day):
		self.guarded.append((employee, day))
		if day in self.held:
			return {"held": self.held[day], "hr": True}
		return {"marked": [f"HR-ATT-{day.day}"]}

	def test_days_are_rebuilt_oldest_first_under_the_employee_lock(self):
		out = bf.rebuild_days([(EMP, date(2026, 8, 19)), (EMP, DAY)])
		self.assertEqual(self.guarded, [(EMP, DAY), (EMP, date(2026, 8, 19))])
		self.assertEqual(self.locked, [EMP, EMP])
		self.assertEqual(len(out["rebuilt"]), 2)

	def test_a_day_the_never_worse_guard_refused_is_listed_for_hr(self):
		self.held[DAY] = "would turn Present into Absent"
		out = bf.rebuild_days([(EMP, DAY)])
		self.assertEqual(out["rebuilt"], [])
		self.assertIn("Present into Absent", out["held_back"][0]["reason"])
		self.assertTrue(out["held_back"][0]["hr"])

	def test_a_protected_day_is_not_rebuilt(self):
		with patch.object(bf, "_protection", return_value="HR-ATT-1 is a leave record"):
			out = bf.rebuild_days([(EMP, DAY)])
		self.assertEqual(self.guarded, [])
		self.assertIn("leave", out["held_back"][0]["reason"])

	def test_it_commits_in_batches_and_never_raises(self):
		with patch.object(bf, "_guarded_rebuild", side_effect=RuntimeError("engine blew up")):
			out = bf.rebuild_days([(EMP, DAY)])
		self.assertIn("engine blew up", out["held_back"][0]["reason"])


if __name__ == "__main__":
	unittest.main()
