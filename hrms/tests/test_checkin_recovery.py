"""A punch a sync pull wrote over is found from owner + creation and re-created.

PYTHONPATH=. python3 hrms/tests/test_checkin_recovery.py
"""

import pathlib
import sys
import unittest
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.sync.checkin_recovery import (
	LOCAL,
	MIRRORED,
	OVERWRITTEN,
	classify_punch,
	infer_log_types,
	plan_recovery,
	true_punch_time,
)

EMPLOYEE_OF_USER = {
	"nabil@nasty.test": "HR-EMP-00012",
	"mirza@nasty.test": "HR-EMP-00301",
	"hr@nasty.test": "HR-EMP-00002",
}
OPERATORS = {"Administrator", "hr@nasty.test"}
RUNS = [(datetime(2026, 9, 8, 14, 0, 0), datetime(2026, 9, 8, 14, 20, 0))]


def _row(**overrides):
	row = {
		"name": "EMP-CKIN-09-2026-000007",
		"employee": "HR-EMP-00301",
		"owner": "nabil@nasty.test",
		"creation": datetime(2026, 9, 4, 9, 2, 11),
		"synced_from_instance": "Nasty-Live",
	}
	row.update(overrides)
	return row


class TestClassifyPunch(unittest.TestCase):
	def test_an_unstamped_row_is_local(self):
		verdict = classify_punch(_row(synced_from_instance=None), RUNS, EMPLOYEE_OF_USER, OPERATORS)
		self.assertEqual(verdict["kind"], LOCAL)
		self.assertEqual(verdict["true_employee"], "HR-EMP-00301")

	def test_a_row_owned_by_the_sync_operator_is_mirrored(self):
		verdict = classify_punch(
			_row(owner="hr@nasty.test", creation=datetime(2026, 9, 8, 14, 5)),
			RUNS,
			EMPLOYEE_OF_USER,
			OPERATORS,
		)
		self.assertEqual(verdict["kind"], MIRRORED)

	def test_the_operators_own_employee_link_never_makes_a_mirrored_insert_overwritten(self):
		"""HR pressed Sync and HR has an Employee record: every row her run inserted
		is owned by her user and shows someone else. That is a mirrored insert,
		decided by the run window, never a lost punch of hers."""
		verdict = classify_punch(
			_row(owner="hr@nasty.test", employee="HR-EMP-00301", creation=datetime(2026, 9, 8, 14, 5)),
			RUNS,
			EMPLOYEE_OF_USER,
			OPERATORS,
		)
		self.assertEqual(verdict["kind"], MIRRORED)

	def test_the_operators_own_punch_outside_every_run_is_still_recovered(self):
		verdict = classify_punch(
			_row(owner="hr@nasty.test", employee="HR-EMP-00301", creation=datetime(2026, 9, 4, 9, 0)),
			RUNS,
			EMPLOYEE_OF_USER,
			OPERATORS,
		)
		self.assertEqual(verdict["kind"], OVERWRITTEN)
		self.assertEqual(verdict["true_employee"], "HR-EMP-00002")

	def test_a_row_created_by_another_employees_user_was_overwritten(self):
		"""Nabil's user created it; it now shows Mirza's punch. Nabil's punch is gone."""
		verdict = classify_punch(_row(), RUNS, EMPLOYEE_OF_USER, OPERATORS)
		self.assertEqual(verdict["kind"], OVERWRITTEN)
		self.assertEqual(verdict["true_employee"], "HR-EMP-00012")
		self.assertIn("another employee", verdict["reason"])

	def test_a_row_created_outside_every_sync_run_was_overwritten(self):
		"""Same employee on both sides, but the row was born hours before any run."""
		verdict = classify_punch(_row(employee="HR-EMP-00012"), RUNS, EMPLOYEE_OF_USER, OPERATORS)
		self.assertEqual(verdict["kind"], OVERWRITTEN)
		self.assertEqual(verdict["reason"], "created outside every sync run")

	def test_a_row_created_inside_a_run_by_a_staff_user_is_mirrored(self):
		"""HR who punch AND press Sync own both kinds; the run window decides."""
		verdict = classify_punch(
			_row(employee="HR-EMP-00012", creation=datetime(2026, 9, 8, 14, 3)),
			RUNS,
			EMPLOYEE_OF_USER,
			OPERATORS,
		)
		self.assertEqual(verdict["kind"], MIRRORED)


class TestTruePunchTime(unittest.TestCase):
	def test_system_clock_becomes_the_attendance_clock(self):
		moment = true_punch_time(datetime(2026, 9, 4, 9, 2, 11), "UTC", "Asia/Kuala_Lumpur")
		self.assertEqual(moment, datetime(2026, 9, 4, 17, 2, 11))

	def test_same_zone_is_untouched(self):
		moment = true_punch_time("2026-09-04 09:02:11", "Asia/Kuala_Lumpur", "Asia/Kuala_Lumpur")
		self.assertEqual(moment, datetime(2026, 9, 4, 9, 2, 11))


class TestInferLogTypes(unittest.TestCase):
	def test_two_unknowns_become_in_then_out(self):
		out = infer_log_types(
			[
				{"time": datetime(2026, 9, 4, 18, 30), "log_type": None, "source": "recovered"},
				{"time": datetime(2026, 9, 4, 9, 0), "log_type": None, "source": "recovered"},
			]
		)
		self.assertEqual([p["log_type"] for p in out], ["IN", "OUT"])
		self.assertEqual({p["confidence"] for p in out}, {"inferred"})

	def test_a_known_local_in_makes_the_later_unknown_an_out(self):
		out = infer_log_types(
			[
				{"time": datetime(2026, 9, 4, 9, 0), "log_type": "IN", "source": "local"},
				{"time": datetime(2026, 9, 4, 18, 0), "log_type": None, "source": "recovered"},
			]
		)
		self.assertEqual(out[1]["log_type"], "OUT")
		self.assertEqual(out[0]["confidence"], "known")

	def test_a_punch_next_to_hrs_manual_one_takes_its_type(self):
		"""HR keyed an OUT at 18:00 sharp to patch the day; the real OUT at 18:07
		comes back. Alternation alone would have called it an IN."""
		out = infer_log_types(
			[
				{"time": datetime(2026, 9, 4, 8, 41), "log_type": None, "source": "recovered"},
				{"time": datetime(2026, 9, 4, 18, 0), "log_type": "OUT", "source": "local"},
				{"time": datetime(2026, 9, 4, 18, 7), "log_type": None, "source": "recovered"},
			]
		)
		self.assertEqual([p["log_type"] for p in out], ["IN", "OUT", "OUT"])
		self.assertEqual(out[2]["confidence"], "neighbour")

	def test_a_request_type_wins_and_is_labelled(self):
		out = infer_log_types([{"time": datetime(2026, 9, 4, 9, 0), "log_type": "OUT", "source": "request"}])
		self.assertEqual(out[0]["log_type"], "OUT")
		self.assertEqual(out[0]["confidence"], "request")


class TestPlanRecovery(unittest.TestCase):
	def _plan(self, rows, requests=None, local=None, recovered=()):
		return plan_recovery(
			rows,
			requests or {},
			local or {},
			set(recovered),
			lambda employee: "Asia/Kuala_Lumpur",
			"Asia/Kuala_Lumpur",
		)

	def _overwritten(self, name="EMP-CKIN-09-2026-000007", creation=datetime(2026, 9, 4, 9, 2, 11)):
		return {
			"name": name,
			"synced_from_instance": "Nasty-Live",
			"creation": creation,
			"true_employee": "HR-EMP-00012",
		}

	def test_an_overwritten_row_is_planned_as_a_new_punch(self):
		[entry] = self._plan([self._overwritten()])
		self.assertEqual(entry["action"], "insert")
		self.assertEqual(entry["employee"], "HR-EMP-00012")
		self.assertEqual(entry["time"], datetime(2026, 9, 4, 9, 2, 11))
		self.assertEqual(entry["log_type"], "IN")
		self.assertEqual(entry["confidence"], "inferred")
		self.assertEqual(entry["stamped_from"], "Nasty-Live")

	def test_a_row_already_recovered_is_skipped(self):
		[entry] = self._plan([self._overwritten()], recovered=["EMP-CKIN-09-2026-000007"])
		self.assertEqual(entry["action"], "skip-already-recovered")

	def test_a_local_punch_within_a_minute_means_the_employee_re_punched(self):
		local = {"HR-EMP-00012": [{"name": "X", "time": datetime(2026, 9, 4, 9, 2, 41), "log_type": "IN"}]}
		[entry] = self._plan([self._overwritten()], local=local)
		self.assertEqual(entry["action"], "skip-local-exists")

	def test_the_linked_request_supplies_the_log_type(self):
		requests = {"EMP-CKIN-09-2026-000007": {"log_type": "OUT", "checkin_time": "2026-09-04 09:03:00"}}
		[entry] = self._plan([self._overwritten()], requests=requests)
		self.assertEqual((entry["log_type"], entry["confidence"]), ("OUT", "request"))

	def test_a_request_too_far_from_the_true_time_is_not_trusted(self):
		requests = {"EMP-CKIN-09-2026-000007": {"log_type": "OUT", "checkin_time": "2026-09-04 12:00:00"}}
		[entry] = self._plan([self._overwritten()], requests=requests)
		self.assertEqual((entry["log_type"], entry["confidence"]), ("IN", "inferred"))

	def test_the_days_local_punches_anchor_the_inference(self):
		"""The IN survived locally; only the evening OUT was overwritten."""
		local = {"HR-EMP-00012": [{"name": "X", "time": datetime(2026, 9, 4, 9, 0, 0), "log_type": "IN"}]}
		[entry] = self._plan([self._overwritten(creation=datetime(2026, 9, 4, 18, 31, 0))], local=local)
		self.assertEqual(entry["log_type"], "OUT")

	def test_entries_come_back_ordered_by_employee_and_time(self):
		rows = [
			self._overwritten("B", datetime(2026, 9, 4, 18, 0)),
			self._overwritten("A", datetime(2026, 9, 4, 9, 0)),
		]
		plan = self._plan(rows)
		self.assertEqual([e["source_name"] for e in plan], ["A", "B"])
		self.assertEqual([e["log_type"] for e in plan], ["IN", "OUT"])


class TestCollectEmployeeFilter(unittest.TestCase):
	"""The Employee filter must find rows by the TRUE employee: an overwritten
	punch shows somebody else in its employee column."""

	def _get_all(self, doctype, **kwargs):
		if doctype == "Employee Checkin":
			if kwargs.get("pluck") == "device_id":
				return []
			for condition in kwargs.get("filters") or []:
				# a SQL filter on the SHOWN employee hides the overwritten row
				if list(condition)[-3:-1] == ["employee", "="] and condition[-1] != "HR-EMP-00301":
					return []
			return [
				frappe._dict(
					name="EMP-CKIN-09-2026-000007",
					employee="HR-EMP-00301",
					employee_name="Mirza",
					log_type="IN",
					time=datetime(2026, 9, 4, 8, 41, 5),
					owner="nabil@nasty.test",
					creation=datetime(2026, 9, 4, 9, 2, 11),
					synced_from_instance="Nasty-Live",
					device_id=None,
					attendance=None,
					shift=None,
				)
			]
		if doctype == "Employee":
			return [frappe._dict(name="HR-EMP-00012", user_id="nabil@nasty.test")]
		return []

	def test_filtering_by_the_true_employee_finds_the_overwritten_row(self):
		from unittest.mock import patch

		from hrms.sync import checkin_recovery
		from hrms.utils import timezone

		with (
			patch.object(frappe, "get_all", side_effect=self._get_all),
			patch.object(timezone, "get_attendance_timezone", return_value="Asia/Kuala_Lumpur"),
			patch.object(
				sys.modules["frappe.utils"],
				"get_system_timezone",
				create=True,
				return_value="Asia/Kuala_Lumpur",
			),
			patch.object(
				sys.modules["frappe.utils"],
				"add_days",
				lambda d, n: d + __import__("datetime").timedelta(days=n),
			),
		):
			mine = checkin_recovery.collect("2026-09-01", "2026-09-09", "HR-EMP-00012")
			theirs = checkin_recovery.collect("2026-09-01", "2026-09-09", "HR-EMP-00301")
		self.assertEqual([e["source_name"] for e in mine["plan"]], ["EMP-CKIN-09-2026-000007"])
		self.assertEqual(mine["plan"][0]["employee"], "HR-EMP-00012")
		self.assertEqual(theirs["plan"], [])


if __name__ == "__main__":
	unittest.main()
