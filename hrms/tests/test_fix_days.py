"""Fix Days: one press over a date range — re-stamp, pair, cancel, rebuild, log.

Owner, 21 Sep 2026, on Norazmi's 1-4 September (screenshots): every punch had
been corrected by hand — one IN and one OUT a day, all Counted, all on
8AM-6PM — and the Attendance list still read "Absent (HR)" 0.00 h on each of
them, beside the cancelled night rows and one Half Day 0.01 h from a double
tap under the night stamp. On 3 September the IN still carried 7PM-3.30AM
while its OUT was on 8AM-6PM. The punches were fixed; nothing recomputed the
days; the glitch stamps were mixed.

`fix_days(employee, from_date, to_date, shift=None, reason="", dry_run=True)`
does for every day of the range what Fix Day does for one: the punches get
the day's stamp, double taps drop out as noise, the rows HR hand-marked are
cancelled (HR is asking), the engine rebuilds the day, one log row per day.
A leave day is left alone and said so; a paid day is refused for that day
only; a day with no complete session is reported open and NOT rebuilt.

Bench-free, the Store/FakeDB harness of test_attendance_fix_day.py:

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_days.py
"""

import copy
import json
import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe
from frappe.utils import getdate

from hrms.api import attendance_fix_day as fd

EMP = "HR-EMP-0042"
TODAY = date(2026, 9, 21)
DAY_SHIFT = "8AM - 6PM"
NIGHT = "7PM - 3.30AM"
USER = "hr@nastyworldwide.com"
SEP1, SEP2, SEP3, SEP4 = date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 4)


def at(day, clock):
	return datetime.combine(day, time.fromisoformat(clock))


def day_stamp(day):
	return {
		"shift": DAY_SHIFT,
		"shift_start": at(day, "08:00"),
		"shift_end": at(day, "18:00"),
		"shift_actual_start": at(day, "07:00"),
		"shift_actual_end": at(day, "19:00"),
		"offshift": 0,
	}


def night_stamp(day):
	return {
		"shift": NIGHT,
		"shift_start": at(day, "19:00"),
		"shift_end": at(day + (date(2026, 1, 2) - date(2026, 1, 1)), "03:30"),
		"shift_actual_start": at(day, "18:00"),
		"shift_actual_end": at(day + (date(2026, 1, 2) - date(2026, 1, 1)), "04:30"),
		"offshift": 0,
	}


class Store:
	"""One person's taps, attendance rows and fix log, in memory."""

	def __init__(self):
		self.taps = {}
		self.rows = {}
		self.logs = {}
		self.comments = []
		self.rebuilt = []
		self.cancelled = []
		self.counter = 0

	def tap(self, name, when, log_type, stamp, attendance=None, **extra):
		self.taps[name] = {
			"name": name,
			"employee": EMP,
			"time": when,
			"log_type": log_type,
			"attendance": attendance,
			"skip_auto_attendance": 0,
			"skipped_as_noise": 0,
			"device_id": "door-1",
			"overtime_type": None,
			"synced_from_instance": None,
			"remote_approval_status": None,
			**stamp,
			**extra,
		}
		return self.taps[name]

	def row(self, name, day, **extra):
		self.rows[name] = {
			"name": name,
			"employee": EMP,
			"attendance_date": day,
			"status": "Absent",
			"docstatus": 1,
			"shift": DAY_SHIFT,
			"in_time": None,
			"out_time": None,
			"working_hours": 0.0,
			"ot_hours": 0.0,
			"auto_attendance": 0,
			"leave_type": None,
			"leave_application": None,
			"attendance_request": None,
			"modify_half_day_status": 0,
			"synced_from_instance": None,
			**extra,
		}
		return self.rows[name]


class FakeDB:
	def __init__(self, store):
		self.store = store

	def _table(self, doctype):
		return {"Employee Checkin": self.store.taps, fd.LOG_DOCTYPE: self.store.logs}[doctype]

	def get_value(self, doctype, name, fields=None, as_dict=False, for_update=False, **kwargs):
		if doctype == "Employee":
			row = {"name": name, "employee_name": "Norazmi", "company": "NZ", "default_shift": DAY_SHIFT}
		else:
			row = self._table(doctype).get(name)
		if row is None:
			return None
		return frappe._dict({field: row.get(field) for field in (fields or row)})

	def set_value(self, doctype, name, fields, value=None):
		if isinstance(fields, str):
			fields = {fields: value}
		self._table(doctype)[name].update(fields)


class FixDaysCase(unittest.TestCase):
	def setUp(self):
		self.store = Store()
		self.financial = {}
		self.paid = {}
		self.request = None
		self.leave = None
		self.requests = {}
		self.docs_fetched = []
		self.roster = {}
		stack = ExitStack()
		self.addCleanup(stack.close)
		stack.enter_context(patch.object(frappe, "db", FakeDB(self.store)))
		stack.enter_context(patch.object(frappe, "session", SimpleNamespace(user=USER)))
		stack.enter_context(patch.object(frappe, "only_for", lambda *a, **k: None))
		stack.enter_context(patch.object(fd.company_scope, "company_visible", lambda *a, **k: True))
		stack.enter_context(patch.object(fd.hr_removed_day, "removed_by_hr", lambda *a: False))

		def seam(name, value):
			stack.enter_context(patch.object(fd, name, value))

		seam("_today", lambda employee: TODAY)
		seam("_lock_employee", lambda employee: None)
		seam("_shift_running", lambda employee, day: False)
		seam("_financial", lambda employee, day, rows, for_update: self.financial.get(getdate(day)))
		seam("_request_cover", lambda employee, day: self.request)
		seam("_paid_day", lambda employee, day, rows, for_update: self.paid.get(getdate(day)))
		seam("_leave_cover", lambda employee, day: self.leave)
		seam("_requests_on", lambda employee, day: [dict(r) for r in self.requests.get(getdate(day), [])])
		# any controller load of a request document is recorded: Fix days must never make one
		stack.enter_context(
			patch.object(
				frappe,
				"get_doc",
				lambda doctype, name=None, *a, **k: self.docs_fetched.append((doctype, name)),
			)
		)
		seam("_day_attendance", self.day_attendance)
		seam("_day_taps", self.day_taps)
		seam("_range_taps", self.range_taps)
		seam(
			"_shift_stamp",
			lambda shift, day: day_stamp(getdate(day)) if shift == DAY_SHIFT else night_stamp(getdate(day)),
		)
		seam("_roster_stamp", lambda tap: self.roster.get(tap["name"]))
		seam("_day_pairing", lambda taps: None)
		seam("_comment", lambda doctype, name, text: self.store.comments.append((doctype, name, text)))
		seam("_cancel_attendance", self.cancel_attendance)
		seam("_rebuild", self.rebuild)
		seam("_write_log", self.write_log)
		self.queued = []
		seam("_remark_later", lambda employee, day, reason: self.queued.append(str(day)))

	# --- the store behind the seams -------------------------------------------

	def day_attendance(self, employee, day):
		return [
			copy.deepcopy(row)
			for row in self.store.rows.values()
			if getdate(row["attendance_date"]) == getdate(day) and row["docstatus"] < 2
		]

	def day_taps(self, employee, day):
		return [
			copy.deepcopy(tap)
			for tap in sorted(self.store.taps.values(), key=lambda t: t["time"])
			if getdate(tap["shift_start"] or tap["time"]) == getdate(day)
		]

	def range_taps(self, employee, from_date, to_date):
		return [
			copy.deepcopy(tap)
			for tap in sorted(self.store.taps.values(), key=lambda t: t["time"])
			if getdate(from_date)
			<= getdate(tap["time"])
			<= getdate(to_date) + (date(2026, 1, 2) - date(2026, 1, 1))
		]

	def keep_request(self, day, doctype, name, status="Approved", hours=None):
		req = {"doctype": doctype, "name": name, "status": status, "hours": hours}
		self.requests.setdefault(getdate(day), []).append(req)
		return req

	def cancel_attendance(self, name):
		self.store.rows[name]["docstatus"] = 2
		self.store.cancelled.append(name)

	def rebuild(self, employee, day, reason, **kwargs):
		self.store.rebuilt.append((employee, str(getdate(day)), reason))
		self.store.counter += 1
		self.store.row(
			f"HR-ATT-NEW-{self.store.counter}",
			getdate(day),
			status="Present",
			working_hours=9.9,
			auto_attendance=1,
		)
		return {"action": "remarked", "marked": 1}

	def write_log(self, fields):
		self.store.counter += 1
		name = f"HRFIX-{self.store.counter:05d}"
		self.store.logs[name] = {"name": name, "undone": 0, **fields}
		return name

	# --- Norazmi's 1-4 September, as the screenshots show it ---------------------

	def norazmi(self):
		s = self.store
		s.tap("CK-1-IN", at(SEP1, "07:58"), "IN", day_stamp(SEP1), "HR-ATT-2026-15173")
		s.tap("CK-1-OUT", at(SEP1, "18:02"), "OUT", day_stamp(SEP1), "HR-ATT-2026-15173")
		s.tap("CK-2-IN", at(SEP2, "07:56"), "IN", day_stamp(SEP2), "HR-ATT-2026-15174")
		s.tap("CK-2-OUT", at(SEP2, "18:01"), "OUT", day_stamp(SEP2), "HR-ATT-2026-15174")
		# the mixed day: the IN still carries the night stamp
		s.tap("CK-3-IN", at(SEP3, "07:59"), "IN", night_stamp(SEP3), "HR-ATT-2026-15175")
		s.tap("CK-3-OUT", at(SEP3, "18:01"), "OUT", day_stamp(SEP3), "HR-ATT-2026-15175")
		# the double tap under the night stamp that made a 0.01 h Half Day
		s.tap("CK-4-IN", at(SEP4, "07:57"), "IN", day_stamp(SEP4), "HR-ATT-2026-15176")
		s.tap("CK-4-OUT", at(SEP4, "18:02:50"), "OUT", day_stamp(SEP4), "HR-ATT-2026-15176")
		s.tap("CK-4-GLITCH-IN", at(SEP4, "18:03:01"), "IN", night_stamp(SEP4), "HR-ATT-2026-HALF")
		s.tap("CK-4-GLITCH-OUT", at(SEP4, "18:03:22"), "OUT", night_stamp(SEP4), "HR-ATT-2026-HALF")
		for day, name in ((SEP1, "15173"), (SEP2, "15174"), (SEP3, "15175"), (SEP4, "15176")):
			s.row(f"HR-ATT-2026-{name}", day)  # Absent (HR), 0.00 h
			s.row(f"HR-ATT-2026-N{name}", day, shift=NIGHT, status="Present", docstatus=2, auto_attendance=1)
		s.row("HR-ATT-2026-HALF", SEP4, shift=NIGHT, status="Half Day", working_hours=0.01, auto_attendance=1)

	def fix(self, **kwargs):
		kwargs.setdefault("shift", DAY_SHIFT)
		kwargs.setdefault("reason", "punches were fixed, the days never recomputed")
		return fd.fix_days(EMP, str(SEP1), str(SEP4), **kwargs)

	def by_date(self, answer):
		return {entry["date"]: entry for entry in answer["days"]}

	def refusal(self, call, *args, **kwargs):
		with self.assertRaises(frappe.ValidationError) as caught:
			call(*args, **kwargs)
		return str(caught.exception)


class TestTheNorazmiCaseDryRun(FixDaysCase):
	def setUp(self):
		super().setUp()
		self.norazmi()
		self.answer = self.fix(dry_run=True)
		self.days = self.by_date(self.answer)

	def test_it_reports_every_day_of_the_range_and_writes_nothing(self):
		self.assertEqual(sorted(self.days), ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"])
		self.assertTrue(self.answer["dry_run"])
		self.assertEqual(self.store.cancelled, [])
		self.assertEqual(self.store.rebuilt, [])
		self.assertEqual(self.store.logs, {})
		self.assertEqual(self.store.taps["CK-3-IN"]["shift"], NIGHT)

	def test_the_3_sep_in_is_restamped_from_the_night_to_the_day(self):
		taps = {tap["name"]: tap for tap in self.days["2026-09-03"]["taps"]}
		self.assertEqual(taps["CK-3-IN"]["before"]["shift"], NIGHT)
		self.assertEqual(taps["CK-3-IN"]["after"]["shift"], DAY_SHIFT)
		self.assertEqual(taps["CK-3-IN"]["after"]["shift_start"], "2026-09-03 08:00:00")
		self.assertTrue(taps["CK-3-IN"]["changed"])
		self.assertFalse(taps["CK-3-OUT"]["changed"], "a punch already on the stamp is left alone")

	def test_the_double_tap_is_noise(self):
		self.assertEqual(
			sorted(n["name"] for n in self.days["2026-09-04"]["noise"]), ["CK-4-GLITCH-IN", "CK-4-GLITCH-OUT"]
		)
		self.assertEqual(self.days["2026-09-01"]["noise"], [])

	def test_the_hr_absent_rows_and_the_half_day_are_listed_to_cancel(self):
		self.assertEqual(
			[(r["name"], r["status"], r["hours"]) for r in self.days["2026-09-01"]["rows_to_cancel"]],
			[("HR-ATT-2026-15173", "Absent", 0.0)],
		)
		self.assertEqual(
			sorted(r["name"] for r in self.days["2026-09-04"]["rows_to_cancel"]),
			["HR-ATT-2026-15176", "HR-ATT-2026-HALF"],
		)

	def test_the_cancelled_night_rows_are_not_part_of_the_day(self):
		for entry in self.days.values():
			self.assertNotIn("N151", "".join(r["name"] for r in entry["rows_to_cancel"]))

	def test_every_day_would_be_rebuilt_from_its_first_in_to_its_last_out(self):
		for entry in self.days.values():
			self.assertIsNone(entry["blocked"])
			self.assertIn("rebuild", entry["result"])
		self.assertEqual(self.days["2026-09-04"]["session"]["in"]["name"], "CK-4-IN")
		self.assertEqual(self.days["2026-09-04"]["session"]["out"]["name"], "CK-4-OUT")

	def test_the_totals_add_up(self):
		totals = self.answer["totals"]
		self.assertEqual((totals["days"], totals["rebuilt"], totals["open"], totals["blocked"]), (4, 4, 0, 0))
		self.assertEqual((totals["restamped"], totals["noise"], totals["cancelled"]), (3, 2, 5))


class TestTheNorazmiCaseApplied(FixDaysCase):
	def setUp(self):
		super().setUp()
		self.norazmi()
		self.answer = self.fix(dry_run=False)
		self.days = self.by_date(self.answer)

	def test_the_hr_absent_rows_and_the_half_day_are_cancelled(self):
		self.assertEqual(
			sorted(self.store.cancelled),
			[
				"HR-ATT-2026-15173",
				"HR-ATT-2026-15174",
				"HR-ATT-2026-15175",
				"HR-ATT-2026-15176",
				"HR-ATT-2026-HALF",
			],
		)

	def test_each_day_is_rebuilt_by_the_one_engine(self):
		self.assertEqual(
			[day for _, day, _ in self.store.rebuilt],
			["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"],
		)

	def test_one_log_row_per_day_with_the_shift_and_the_noise_on_it(self):
		self.assertEqual(len(self.store.logs), 4)
		entries = sorted(self.store.logs.values(), key=lambda e: e["fix_date"])
		self.assertEqual([e["action"] for e in entries], ["fix_days"] * 4)
		self.assertEqual(
			[e["fix_date"] for e in entries], ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]
		)
		plan = json.loads(entries[3]["after_state"])["plan"]
		self.assertEqual(plan["shift"], DAY_SHIFT)
		self.assertEqual(sorted(d["name"] for d in plan["drop"]), ["CK-4-GLITCH-IN", "CK-4-GLITCH-OUT"])
		self.assertIn("HR-ATT-2026-HALF", [c["name"] for c in plan["cancel"]])
		self.assertIn("CK-3-IN", entries[2]["refs"])

	def test_the_3_sep_in_now_carries_the_day_stamp_and_is_released(self):
		tap = self.store.taps["CK-3-IN"]
		self.assertEqual(tap["shift"], DAY_SHIFT)
		self.assertEqual(tap["shift_start"], at(SEP3, "08:00"))
		self.assertEqual(tap["offshift"], 0)
		self.assertIsNone(tap["attendance"])
		self.assertEqual(tap["time"], at(SEP3, "07:59"), "the device's time is never touched")

	def test_the_double_tap_is_skipped_as_noise(self):
		for name in ("CK-4-GLITCH-IN", "CK-4-GLITCH-OUT"):
			self.assertEqual(self.store.taps[name]["skip_auto_attendance"], 1)
			self.assertEqual(self.store.taps[name]["skipped_as_noise"], 1)
		self.assertEqual(self.store.taps["CK-4-OUT"]["skip_auto_attendance"], 0)

	def test_the_answer_reads_the_rebuilt_day(self):
		self.assertFalse(self.answer["dry_run"])
		for entry in self.days.values():
			self.assertEqual(entry["result"], "Present 9.9 h")
			self.assertIsNotNone(entry["log"])
		self.assertEqual(self.answer["totals"]["rebuilt"], 4)

	def test_apply_needs_a_reason(self):
		self.assertIn("Say why", self.refusal(self.fix, dry_run=False, reason=""))

	def test_a_form_posts_dry_run_as_a_string(self):
		"""frappe hands whitelisted methods form values as strings: "0" must
		apply, "1" must not — bool("0") would have read a cleared tick as set."""
		before = len(self.store.rebuilt)
		self.assertTrue(self.fix(dry_run="1")["dry_run"])
		self.assertEqual(len(self.store.rebuilt), before, 'a string "1" is a dry run')
		answer = self.fix(dry_run="0")
		self.assertFalse(answer["dry_run"])
		self.assertEqual(len(self.store.rebuilt), before + 4, 'a string "0" applies')


class TestTheDaysItLeavesAlone(FixDaysCase):
	def setUp(self):
		super().setUp()
		self.norazmi()

	def test_a_leave_day_in_the_range_is_untouched_and_reported(self):
		self.store.row(
			"HR-ATT-2026-15174", SEP2, status="On Leave", leave_type="Annual Leave", auto_attendance=1
		)
		days = self.by_date(self.fix(dry_run=False))
		self.assertIn("leave", days["2026-09-02"]["blocked"])
		self.assertEqual(days["2026-09-02"]["rows_to_cancel"], [])
		self.assertNotIn("HR-ATT-2026-15174", self.store.cancelled)
		self.assertNotIn("2026-09-02", [day for _, day, _ in self.store.rebuilt])
		# the other three days still went through
		self.assertEqual(len(self.store.rebuilt), 3)

	def test_a_paid_day_is_refused_for_that_day_only(self):
		# `_paid_day`: the slip / paid overtime reader Fix days asks (an approved
		# OT Request alone is not money any more — see TestTheRequestsOnADayAreKept)
		self.paid[SEP3] = "Sal Slip/HR-EMP-0042/00009"
		days = self.by_date(self.fix(dry_run=False))
		self.assertIn("already paid", days["2026-09-03"]["blocked"])
		self.assertEqual(
			self.store.taps["CK-3-IN"]["shift"], NIGHT, "a refused day's punches are not re-stamped"
		)
		self.assertNotIn("HR-ATT-2026-15175", self.store.cancelled)
		self.assertEqual(len(self.store.rebuilt), 3)
		self.assertEqual(len(self.store.logs), 3)

	def test_a_day_with_only_an_in_is_left_open_not_rebuilt_and_not_cancelled(self):
		del self.store.taps["CK-2-OUT"]
		days = self.by_date(self.fix(dry_run=False))
		self.assertIsNone(days["2026-09-02"]["blocked"])
		self.assertIn("left open", days["2026-09-02"]["result"])
		self.assertIn("closes", days["2026-09-02"]["result"])
		self.assertNotIn("HR-ATT-2026-15174", self.store.cancelled)
		self.assertNotIn("2026-09-02", [day for _, day, _ in self.store.rebuilt])
		self.assertEqual(len(self.store.rebuilt), 3)

	def test_a_future_day_is_blocked(self):
		answer = fd.fix_days(EMP, str(SEP4), str(TODAY), shift=DAY_SHIFT, reason="x", dry_run=True)
		self.assertIn("not over yet", self.by_date(answer)[str(TODAY)]["blocked"])


class TestTheRequestsOnADayAreKept(FixDaysCase):
	"""Owner ruling, 21 Sep 2026: an approved request stays intact and the
	attendance row is rebuilt from the punches anyway. HR cancels nothing by
	hand first; the request is never touched. Leave and money still hold."""

	def setUp(self):
		super().setUp()
		self.norazmi()
		self.ot = self.keep_request(SEP2, "OT Request", "OTR-0007", hours=2)
		# what `_financial` answers today for a day with approved overtime on it —
		# Fix days must not be asking it any more
		self.financial[SEP2] = "OTR-0007"

	def test_an_approved_ot_request_day_is_rebuilt_and_the_request_untouched(self):
		days = self.by_date(self.fix(dry_run=False))
		self.assertIsNone(days["2026-09-02"]["blocked"])
		self.assertIn("2026-09-02", [day for _, day, _ in self.store.rebuilt])
		self.assertEqual(len(self.store.rebuilt), 4)
		self.assertIn("HR-ATT-2026-15174", self.store.cancelled)
		self.assertEqual(self.docs_fetched, [], "no controller load of the request: no cancel, no save")
		self.assertEqual(self.ot["status"], "Approved")
		self.assertEqual(
			days["2026-09-02"]["requests_kept"],
			[
				{
					"doctype": "OT Request",
					"name": "OTR-0007",
					"label": "OT Request OTR-0007 2 h (Approved) — OT hours on the row are recomputed "
					"from the punches; the request keeps its approval",
				}
			],
		)
		log = next(e for e in self.store.logs.values() if e["fix_date"] == "2026-09-02")
		plan = json.loads(log["after_state"])["plan"]
		self.assertEqual([r["name"] for r in plan["requests_kept"]], ["OTR-0007"])

	def test_an_attendance_request_day_is_rebuilt_from_its_punches_and_the_request_kept(self):
		self.store.row(
			"HR-ATT-2026-15175",
			SEP3,
			status="Work From Home",
			attendance_request="HR-AREQ-0001",
			auto_attendance=0,
		)
		self.keep_request(SEP3, "Attendance Request", "HR-AREQ-0001")
		self.request = "Attendance Request HR-AREQ-0001 (Approved) covers it"  # what `_request_cover` says
		days = self.by_date(self.fix(dry_run=False))
		self.assertIsNone(days["2026-09-03"]["blocked"])
		self.assertEqual([r["name"] for r in days["2026-09-03"]["rows_to_cancel"]], ["HR-ATT-2026-15175"])
		self.assertIn("HR-ATT-2026-15175", self.store.cancelled)
		self.assertIn("2026-09-03", [day for _, day, _ in self.store.rebuilt])
		self.assertEqual(self.docs_fetched, [])
		self.assertEqual([r["name"] for r in days["2026-09-03"]["requests_kept"]], ["HR-AREQ-0001"])
		self.assertEqual(self.store.taps["CK-3-IN"]["shift"], DAY_SHIFT)

	def test_a_leave_day_is_still_skipped_and_named(self):
		self.leave = "Leave Application HR-LAP-0003 (Approved) covers it"
		days = self.by_date(self.fix(dry_run=False))
		for day in ("2026-09-01", "2026-09-03", "2026-09-04"):
			self.assertIn("HR-LAP-0003", days[day]["blocked"])
			self.assertNotEqual(days[day]["taps"], [], "the punches are still listed")
		self.assertEqual(self.store.rebuilt, [], "a leave day is never rebuilt")

	def test_a_paid_ot_day_stays_refused_and_the_other_days_proceed(self):
		self.paid[SEP2] = "Sal Slip/HR-EMP-0042/00009"
		days = self.by_date(self.fix(dry_run=False))
		self.assertIn("already paid", days["2026-09-02"]["blocked"])
		self.assertIn("Sal Slip/HR-EMP-0042/00009", days["2026-09-02"]["blocked"])
		self.assertNotIn("HR-ATT-2026-15174", self.store.cancelled)
		self.assertEqual(len(self.store.rebuilt), 3)
		self.assertEqual([r["name"] for r in days["2026-09-02"]["requests_kept"]], ["OTR-0007"])

	def test_a_dry_run_lists_the_kept_requests_and_writes_nothing(self):
		answer = self.fix(dry_run=True)
		days = self.by_date(answer)
		self.assertEqual([r["name"] for r in days["2026-09-02"]["requests_kept"]], ["OTR-0007"])
		self.assertEqual(days["2026-09-01"]["requests_kept"], [])
		self.assertIsNone(days["2026-09-02"]["blocked"])
		self.assertEqual(self.store.rebuilt, [])
		self.assertEqual(self.store.cancelled, [])
		self.assertEqual(self.docs_fetched, [])
		self.assertEqual(answer["totals"]["kept"], 1)

	def test_the_engine_is_asked_with_requests_ok(self):
		seen = []
		with patch.object(fd, "_rebuild", lambda *a, **k: seen.append(k) or self.rebuild(*a)):
			self.fix(dry_run=False)
		self.assertEqual(len(seen), 4)
		self.assertTrue(all(k.get("requests_ok") for k in seen), "the engine's own hold is lifted too")


class TestANightSessionBelongsToItsInsDay(FixDaysCase):
	"""The engine's IN-anchored rule (employee_checkin_override, session_days):
	an IN opens a session on its clock day and every punch within the session
	window belongs to that day, whatever the clock says. A night OUT the next
	morning is NOT the next day's punch."""

	def setUp(self):
		super().setUp()
		# both punches sit under the wrong (day) stamp; HR says the range is the night shift
		self.store.tap("CK-N-IN", at(SEP2, "20:00"), "IN", day_stamp(SEP2), "HR-ATT-2026-N1")
		self.store.tap("CK-N-OUT", at(SEP3, "08:04"), "OUT", day_stamp(SEP3), "HR-ATT-2026-N2")
		self.store.row("HR-ATT-2026-N1", SEP2)
		self.store.row("HR-ATT-2026-N2", SEP3)
		self.answer = fd.fix_days(EMP, str(SEP2), str(SEP3), shift=NIGHT, reason="night", dry_run=True)
		self.days = self.by_date(self.answer)

	def test_the_morning_out_joins_the_night_in_on_its_day(self):
		taps = {t["name"]: t["after"] for t in self.days["2026-09-02"]["taps"]}
		self.assertEqual(taps["CK-N-IN"], {"shift": NIGHT, "shift_start": "2026-09-02 19:00:00"})
		self.assertEqual(taps["CK-N-OUT"], {"shift": NIGHT, "shift_start": "2026-09-02 19:00:00"})
		self.assertEqual(self.days["2026-09-02"]["result"], "will rebuild from 20:00:00 to 08:04:00")
		self.assertEqual(self.days["2026-09-02"]["noise"], [])

	def test_the_next_day_is_not_left_open_by_a_punch_that_is_not_its_own(self):
		self.assertEqual(self.days["2026-09-03"]["taps"], [])
		self.assertNotIn("left open", self.days["2026-09-03"]["result"])
		self.assertEqual(self.answer["totals"]["open"], 0)


class TestTheRosterDecidesWhenNoShiftIsGiven(FixDaysCase):
	def setUp(self):
		super().setUp()
		self.norazmi()
		# the roster, re-read now, puts every punch on the day shift
		for name, tap in self.store.taps.items():
			self.roster[name] = day_stamp(getdate(tap["time"]))

	def test_the_roster_resolution_restamps_the_night_in(self):
		days = self.by_date(self.fix(shift=None, dry_run=False))
		taps = {tap["name"]: tap for tap in days["2026-09-03"]["taps"]}
		self.assertTrue(taps["CK-3-IN"]["changed"])
		self.assertFalse(taps["CK-3-OUT"]["changed"])
		self.assertEqual(self.store.taps["CK-3-IN"]["shift"], DAY_SHIFT)
		self.assertIsNone(json.loads(next(iter(self.store.logs.values()))["after_state"])["plan"]["shift"])
		self.assertEqual(self.queued, [], "every day a tap left is inside the range: nothing to queue")

	def test_a_day_outside_the_range_that_a_tap_left_is_queued_for_the_engine(self):
		# the 1 Sep IN sat under 31 Aug's night stamp; the roster moves it onto 1 Sep
		self.store.taps["CK-1-IN"].update(night_stamp(date(2026, 8, 31)))
		self.fix(shift=None, dry_run=False)
		self.assertEqual(self.queued, ["2026-08-31"])
		self.assertEqual(self.store.taps["CK-1-IN"]["shift"], DAY_SHIFT)


class TestTheUndo(FixDaysCase):
	def setUp(self):
		super().setUp()
		self.norazmi()
		self.answer = self.fix(dry_run=False)
		self.days = self.by_date(self.answer)

	def test_undoing_a_days_fix_puts_the_stamps_back(self):
		fd.undo_fix(self.days["2026-09-03"]["log"], reason="wrong shift")
		tap = self.store.taps["CK-3-IN"]
		self.assertEqual(tap["shift"], NIGHT)
		self.assertEqual(str(tap["shift_start"]), "2026-09-03 19:00:00")
		self.assertEqual(self.store.logs[self.days["2026-09-03"]["log"]]["undone"], 1)

	def test_undoing_the_glitch_day_puts_the_noise_back_and_says_the_row_stays_cancelled(self):
		answer = fd.undo_fix(self.days["2026-09-04"]["log"], reason="look again")
		self.assertEqual(self.store.taps["CK-4-GLITCH-IN"]["skip_auto_attendance"], 0)
		self.assertEqual(self.store.taps["CK-4-GLITCH-IN"]["shift"], NIGHT)
		self.assertIn("stays cancelled", answer["note"])
		self.assertEqual(self.store.rows["HR-ATT-2026-HALF"]["docstatus"], 2)

	def test_the_undo_does_not_link_a_tap_back_to_the_row_it_cancelled(self):
		fd.undo_fix(self.days["2026-09-03"]["log"], reason="x")
		self.assertIsNone(self.store.taps["CK-3-IN"]["attendance"])


class TestTheEndpointContract(unittest.TestCase):
	def test_fix_days_is_an_action_the_undo_knows(self):
		self.assertIn("fix_days", fd.ACTIONS)
		self.assertIn("fix_days", fd.CANCELLING_ACTIONS)
		self.assertIn("fix_days", fd.UNDOABLE_APART_FROM_THE_CANCEL)

	def test_it_types_no_hours(self):
		import ast
		import pathlib

		from hrms.api import attendance_fix_days as module

		source = pathlib.Path(module.__file__).read_text()
		for word in ("working_hours", "ot_hours"):
			self.assertNotIn(f'"{word}"', source, f"{word} is the engine's to compute, never typed here")


if __name__ == "__main__":
	unittest.main()


class TestAFixThatMarksNothingIsNotDone(FixDaysCase):
	"""Family B (25 Sep 2026): the bulk path shared Save & rebuild's hole. A day
	whose shift has auto attendance off came back "remarked" with no row and
	was logged as fixed. It is refused with the engine's reason instead."""

	def test_a_day_the_engine_marked_nothing_for_is_refused(self):
		self.norazmi()
		with patch.object(
			fd,
			"_rebuild",
			lambda *a, **k: {"action": "remarked", "marked": [], "errors": ["Day: auto attendance is off"]},
		):
			message = self.refusal(self.fix, dry_run=False)
		self.assertIn("auto attendance is off", message)
		self.assertEqual(self.store.logs, {})
