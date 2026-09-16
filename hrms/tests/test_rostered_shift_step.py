"""S4: the `rostered_shift` step puts a wrong-shift day back on the rostered shift.

Owner rule (15 Sep 2026): the session belongs to the shift the person is
ROSTERED on that day; shift config is HR's; never today / HR-edited /
HR-removed / leave / paid. The step fixes engine INPUTS — ends the extra
assignment, cancels the invented rows, re-stamps the taps oldest-first — and
the engine rebuilds the day. E16 (forgotten check-out): a pending late OUT is
not attendance evidence until it is approved.

PYTHONPATH=. python3 hrms/tests/test_rostered_shift_step.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import attendance_auto_recovery as auto
from hrms.utils import attendance_recovery as rec

TODAY = datetime(2026, 9, 14, 11, 0)
DAY, NIGHT = "8AM-6PM", "7PM-3.30AM"
TIMES = {DAY: ("08:00:00", "18:00:00"), NIGHT: ("19:30:00", "07:00:00")}
RIA, NITE = "E-RIA", "E-NITE"
#: A person in the Desk created the row. Since Part A that — not a blank
#: `auto_attendance` — is what says "HR's" to `attendance_ownership.classify_row`.
HR_USER = "hr@nasty.local"


def _tap(name, moment, shift, shift_start, attendance=None, employee=RIA, **extra):
	row = frappe._dict(
		name=name,
		employee=employee,
		employee_name=employee,
		time=moment,
		log_type=extra.pop("log_type", "IN"),
		shift=shift,
		shift_start=shift_start,
		attendance=attendance,
		skip_auto_attendance=0,
		remote_approval_status=None,
		synced_from_instance=None,
	)
	row.update(extra)
	return row


def _row(name, day, shift, status="Present", hours=9.0, employee=RIA, **extra):
	row = frappe._dict(
		name=name,
		employee=employee,
		employee_name=employee,
		attendance_date=day,
		shift=shift,
		status=status,
		docstatus=1,
		auto_attendance=1,
		leave_type=None,
		leave_application=None,
		attendance_request=None,
		modify_half_day_status=0,
		synced_from_instance=None,
		working_hours=hours,
		in_time=datetime.combine(day, datetime.min.time()),
		out_time=None if status == "Half Day" else datetime.combine(day, datetime.min.time()),
	)
	row.update(extra)
	return row


def _assignment(name, shift_type, start, end=None, employee=RIA):
	return frappe._dict(name=name, employee=employee, shift_type=shift_type, start_date=start, end_date=end)


def ria_taps():
	"""Ria, 8-10 Sep: 07:50 IN and 18:33 IN each day; the 18:33 opened an invented
	night and the next 07:50 closed it (S2 evidence). Every tap is linked."""
	taps = []
	for d in (8, 9, 10):
		morning = datetime(2026, 9, d, 7, 50)
		evening = datetime(2026, 9, d, 18, 33)
		if d == 8:
			taps.append(_tap("T-8-0750", morning, DAY, datetime(2026, 9, 8, 8, 0), "ATT-D8"))
		else:
			# stolen by the night that opened the evening before (E2)
			taps.append(
				_tap(f"T-{d}-0750", morning, NIGHT, datetime(2026, 9, d - 1, 19, 30), f"ATT-N{d - 1}")
			)
		taps.append(_tap(f"T-{d}-1833", evening, NIGHT, datetime(2026, 9, d, 19, 30), f"ATT-N{d}"))
	taps.append(
		_tap("T-11-0750", datetime(2026, 9, 11, 7, 50), NIGHT, datetime(2026, 9, 10, 19, 30), "ATT-N10")
	)
	return taps


def ria_rows():
	rows = []
	for d in (8, 9, 10):
		rows.append(_row(f"ATT-D{d}", date(2026, 9, d), DAY, "Half Day", 0))
		rows.append(_row(f"ATT-N{d}", date(2026, 9, d), NIGHT, "Present", 13.3))
	return rows


def ria_live_taps():
	"""Ria HR-EMP-00299 as live showed her on 15 Sep 2026 (build 338deae05), every
	stamp and link as found: 4 Sep four taps on the day shift, unlinked, the last a
	Pending late check-out; 7 and 9 Sep an IN linked to a 0 h day row and an OUT
	stamped to the night and linked to a night Half Day; 8 and 10 Sep clean."""
	day_start = lambda d: datetime(2026, 9, d, 8, 0)  # noqa: E731
	taps = [
		_tap("T-4-0800", datetime(2026, 9, 4, 8, 0, 11), DAY, day_start(4)),
		_tap("T-4-1900", datetime(2026, 9, 4, 19, 0, 27), DAY, day_start(4), log_type="OUT"),
		_tap("T-4-1900b", datetime(2026, 9, 4, 19, 0, 33), DAY, day_start(4)),
		_tap(
			"T-4-1901",
			datetime(2026, 9, 4, 19, 1),
			DAY,
			day_start(4),
			log_type="OUT",
			remote_approval_status="Pending",
			is_late_checkout=1,
		),
	]
	for d, out_shift, out_at in (
		(7, NIGHT, (19, 15, 48)),
		(8, DAY, (18, 22, 0)),
		(9, NIGHT, (18, 33, 29)),
		(10, DAY, (18, 22, 0)),
	):
		taps.append(_tap(f"T-{d}-0750", datetime(2026, 9, d, 7, 50, 33), DAY, day_start(d), f"ATT-D{d}"))
		if out_shift == DAY:
			taps.append(
				_tap(
					f"T-{d}-OUT",
					datetime(2026, 9, d, *out_at),
					DAY,
					day_start(d),
					f"ATT-D{d}",
					log_type="OUT",
				)
			)
		else:
			taps.append(
				_tap(
					f"T-{d}-OUT",
					datetime(2026, 9, d, *out_at),
					NIGHT,
					datetime(2026, 9, d, 19, 30),
					f"ATT-N{d}",
					log_type="OUT",
				)
			)
	return taps


def ria_live_rows():
	rows = []
	for d in (7, 9):
		rows.append(_row(f"ATT-D{d}", date(2026, 9, d), DAY, "Present", 0, out_time=None))
		rows.append(_row(f"ATT-N{d}", date(2026, 9, d), NIGHT, "Half Day", 0))
	for d in (8, 10):
		rows.append(_row(f"ATT-D{d}", date(2026, 9, d), DAY, "Present", 10.5))
	return rows


class FakeDoc(SimpleNamespace):
	def __init__(self, log, doctype, **fields):
		super().__init__(**fields)
		self.__dict__["_log"] = log
		self.__dict__["doctype"] = doctype
		self.flags = frappe._dict()

	def save(self, *a, **k):
		self._log.append(("save", self.doctype, self.name, dict(self.__dict__.get("_snapshot", {}))))

	def get(self, key, default=None):
		return self.__dict__.get(key, default)

	def db_set(self, values, *a, **k):
		self._log.append(("db_set", self.doctype, self.name, values))
		for key, value in values.items():
			setattr(self, key, value)

	def cancel(self):
		self._log.append(("cancel", self.doctype, self.name))
		self.docstatus = 2

	def add_comment(self, kind, text):
		self._log.append(("comment", self.doctype, self.name, text))

	def fetch_shift(self):
		self._log.append(("fetch_shift", self.doctype, self.name, self.attendance))
		self.shift = DAY
		self.shift_start = datetime.combine(self.time.date(), datetime.min.time()).replace(hour=8)


class _Step(unittest.TestCase):
	def setUp(self):
		self.log = []
		self.taps = ria_taps()
		self.rows = ria_rows()
		self.assignments = [
			_assignment("SA-DAY", DAY, date(2026, 8, 1)),
			_assignment("SA-NIGHT", NIGHT, date(2026, 8, 20)),
		]
		self.defaults = {}
		self.protection = {}
		self.financial = {}
		self.docs = {}
		self.remarks = []
		self.locks = []
		self.win = rec.recovery_window("2026-09-01", "2026-09-13", TODAY.date())
		self.patches = [
			patch.object(rec, "now_datetime", return_value=TODAY),
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "session", SimpleNamespace(user="hr@x"), create=True),
			patch.object(frappe, "only_for", MagicMock(), create=True),
			patch.object(frappe, "get_roles", lambda *a: ["HR Manager"], create=True),
			patch.object(frappe, "log_error", MagicMock(), create=True),
			patch.object(rec, "require_unfenced", MagicMock()),
			patch.object(rec, "_shift_times", lambda names: {n: TIMES[n] for n in names if n in TIMES}),
			patch.object(rec, "_both_on_purpose", return_value=set()),
			patch.object(rec, "_context", lambda win: self.ctx()),
			patch.object(
				rec, "_day_protection", lambda e, d, for_update, ignore=None: self.protection.get((e, str(d)))
			),
			patch.object(rec, "_financial", lambda e, d, rows, for_update: self.financial.get((e, str(d)))),
			patch.object(
				rec, "_expected_on_rostered", lambda *a: {"status": "Present", "working_hours": 9.7}
			),
			patch.object(rec, "_remark_day", self._remark),
			patch.object(rec, "_lock_employee", lambda e: self.locks.append(e)),
			patch.object(frappe, "get_doc", self._get_doc),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()

	def ctx(self):
		extra = {"defaults": dict(self.defaults)} if self.defaults else {}
		return rec._build_context(self.win, list(self.taps), list(self.rows), list(self.assignments), **extra)

	def _remark(self, employee, day, apply):
		self.remarks.append((employee, str(day), apply))
		self.log.append(("remark", "Attendance", str(day), apply))
		return {"action": "remark", "marked": [f"ATT-NEW-{day}"], "errors": []}

	def _get_doc(self, doctype, name, **kw):
		if (doctype, name) in self.docs:
			return self.docs[(doctype, name)]
		if doctype == "Shift Assignment":
			src = next(a for a in self.assignments if a.name == name)
			doc = FakeDoc(self.log, doctype, **src, status="Active", docstatus=1, synced_from_instance=None)
		elif doctype == "Attendance":
			src = next(r for r in self.rows if r.name == name)
			doc = FakeDoc(self.log, doctype, **src)
		elif doctype == "Employee Checkin":
			src = next(t for t in self.taps if t.name == name)
			doc = FakeDoc(self.log, doctype, **src)
		else:
			raise AssertionError(doctype)
		self.docs[(doctype, name)] = doc
		return doc

	def plan(self):
		return rec._plan_rostered_shift(self.win, for_update=False)

	def apply(self):
		plan = rec._plan_rostered_shift(self.win, for_update=True)
		return plan, rec._apply_rostered_shift(self.win, plan)


class TestStepWiring(unittest.TestCase):
	def test_the_step_comes_right_after_assignments_and_runs_nightly(self):
		self.assertEqual(rec.STEPS.index("rostered_shift"), rec.STEPS.index("assignments") + 1)
		self.assertIn("rostered_shift", rec._PLANNERS)
		self.assertIn("rostered_shift", rec._APPLIERS)
		self.assertIn("rostered_shift", auto.AUTO_STEPS)
		self.assertEqual(rec.ROSTERED_SHIFT_FIX, "rostered_shift")


class TestPlan(_Step):
	def test_e1_e2_every_wrong_shift_day_is_planned_oldest_first_with_before_and_after(self):
		plan = self.plan()
		days = [(p["employee"], p["date"]) for p in plan["planned"]]
		self.assertEqual(days[:3], [(RIA, "2026-09-08"), (RIA, "2026-09-09"), (RIA, "2026-09-10")])
		first = plan["planned"][0]
		self.assertEqual(first["rostered"], DAY)
		self.assertEqual(first["restamp"], ["T-8-1833"])
		self.assertEqual(first["cancel_rows"], ["ATT-N8"])
		self.assertEqual(
			{r["name"]: r["status"] for r in first["before"]}, {"ATT-D8": "Half Day", "ATT-N8": "Present"}
		)
		self.assertEqual(first["expected"]["status"], "Present")
		second = plan["planned"][1]
		# E2: the 07:50 stolen by the night before comes back first, oldest first
		self.assertEqual(second["restamp"], ["T-9-0750", "T-9-1833"])
		self.assertEqual(second["cancel_rows"], ["ATT-N8", "ATT-N9"])

	def test_the_extra_assignment_is_ended_the_day_before_the_first_affected_date(self):
		plan = self.plan()
		self.assertEqual(len(plan["assignments"]), 1)
		ending = plan["assignments"][0]
		self.assertEqual(ending["assignment"], "SA-NIGHT")
		self.assertEqual(ending["first_affected"], "2026-09-08")
		self.assertEqual(ending["end_date"], "2026-09-07")
		# 20 Aug .. 7 Sep stays: the assignment is split, not deleted
		self.assertTrue(ending["split"])
		self.assertEqual(plan["planned"][0]["end_assignments"], ["SA-NIGHT"])

	def test_an_assignment_starting_inside_the_range_goes_inactive(self):
		self.assignments[1] = _assignment("SA-NIGHT", NIGHT, date(2026, 9, 8))
		ending = self.plan()["assignments"][0]
		self.assertFalse(ending["split"])
		self.assertEqual(ending["end_date"], "2026-09-08")

	def test_e3_a_genuine_night_worker_is_untouched(self):
		self.taps = [
			_tap(
				"N1",
				datetime(2026, 9, 8, 19, 40),
				NIGHT,
				datetime(2026, 9, 8, 19, 30),
				"ATT-X",
				employee=NITE,
			),
			_tap(
				"N2",
				datetime(2026, 9, 9, 7, 5),
				NIGHT,
				datetime(2026, 9, 8, 19, 30),
				"ATT-X",
				employee=NITE,
				log_type="OUT",
			),
		]
		self.rows = [_row("ATT-X", date(2026, 9, 8), NIGHT, hours=11.4, employee=NITE)]
		self.assignments = [_assignment("SA-N", NIGHT, date(2026, 8, 1), employee=NITE)]
		plan = self.plan()
		self.assertEqual((plan["planned"], plan["held_back"], plan["assignments"]), ([], [], []))

	def test_e4_two_shifts_on_purpose_are_not_on_the_list_at_all(self):
		# I1 (integration review): held "on purpose" every night still fed the S7
		# recheck and ate RECHECK_CAP; E4/E32 — the ticked person is simply not listed.
		with patch.object(rec, "_both_on_purpose", return_value={"SA-NIGHT"}):
			plan = self.plan()
		self.assertEqual((plan["planned"], plan["assignments"], plan["held_back"]), ([], [], []))

	def test_e13_an_invented_night_row_already_paid_goes_to_hr_untouched(self):
		self.financial[(RIA, "2026-09-09")] = "OT-REQ-9"
		plan = self.plan()
		held = {h["date"]: h for h in plan["held_back"]}
		self.assertIn("2026-09-09", held)
		self.assertTrue(held["2026-09-09"]["hr"])
		self.assertTrue(auto.needs_hr(held["2026-09-09"]))
		self.assertIn("OT-REQ-9", held["2026-09-09"]["reason"])
		# the next day's 07:50 was linked to that paid night row: it cannot be moved either
		self.assertIn("2026-09-10", held)
		self.assertEqual([p["date"] for p in plan["planned"]], ["2026-09-08", "2026-09-11"])

	def test_e14_hr_edited_leave_today_are_held_on_purpose(self):
		self.protection[(RIA, "2026-09-09")] = "ATT-D9 was marked by HR by hand"
		plan = self.plan()
		held = {h["date"]: h for h in plan["held_back"]}
		self.assertEqual(held["2026-09-09"]["reason"], "ATT-D9 was marked by HR by hand")
		self.assertFalse(auto.needs_hr(held["2026-09-09"]))
		self.assertNotIn("2026-09-09", [p["date"] for p in plan["planned"]])

	def test_a_wrong_row_hr_marked_by_hand_holds_its_day_on_purpose(self):
		self.rows[1].auto_attendance = 0  # ATT-N8
		self.rows[1].owner = HR_USER  # ... and a person, not the job, created it
		plan = self.plan()
		held = {h["date"]: h for h in plan["held_back"]}
		self.assertIn("marked by HR by hand", held["2026-09-08"]["reason"])
		self.assertFalse(auto.needs_hr(held["2026-09-08"]))

	def test_e15_a_real_move_to_nights_mid_period_is_respected_per_date(self):
		# day shift ended 9 Sep, nights from 10 Sep: 10 Sep's night taps are right
		self.assignments = [
			_assignment("SA-DAY", DAY, date(2026, 8, 1), date(2026, 9, 9)),
			_assignment("SA-NIGHT", NIGHT, date(2026, 9, 10)),
		]
		self.taps = [
			_tap("A", datetime(2026, 9, 9, 7, 50), DAY, datetime(2026, 9, 9, 8, 0), "ATT-D9"),
			_tap("B", datetime(2026, 9, 9, 18, 3), DAY, datetime(2026, 9, 9, 8, 0), "ATT-D9", log_type="OUT"),
			_tap("C", datetime(2026, 9, 10, 19, 35), NIGHT, datetime(2026, 9, 10, 19, 30), "ATT-N10"),
			_tap(
				"D",
				datetime(2026, 9, 11, 7, 2),
				NIGHT,
				datetime(2026, 9, 10, 19, 30),
				"ATT-N10",
				log_type="OUT",
			),
		]
		self.rows = [_row("ATT-D9", date(2026, 9, 9), DAY), _row("ATT-N10", date(2026, 9, 10), NIGHT)]
		plan = self.plan()
		self.assertEqual((plan["planned"], plan["held_back"], plan["assignments"]), ([], [], []))

	def test_hold_reasons_are_plain_english(self):
		self.financial[(RIA, "2026-09-09")] = "OT-REQ-9"
		with patch.object(rec, "_both_on_purpose", return_value=set()):
			plan = self.plan()
		for held in plan["held_back"]:
			self.assertNotRegex(held["reason"], r"docstatus|_id|None|\{")


class TestApply(_Step):
	def test_e1_the_day_is_fixed_in_order_end_cancel_restamp_rebuild(self):
		_plan, outcome = self.apply()
		self.assertEqual([d["date"] for d in outcome["done"]][:3], ["2026-09-08", "2026-09-09", "2026-09-10"])
		kinds = [entry[:3] for entry in self.log]
		self.assertEqual(kinds[0], ("db_set", "Shift Assignment", "SA-NIGHT"))
		self.assertEqual(self.log[0][3], {"end_date": date(2026, 9, 7)})
		# the assignment is ended once, with a comment saying who and why
		self.assertEqual(sum(1 for k in kinds if k[0] == "db_set"), 1)
		comments = [entry[3] for entry in self.log if entry[0] == "comment" and entry[2] == "SA-NIGHT"]
		self.assertTrue(comments and "Attendance recovery by hr@x" in comments[0])
		first_cancel = kinds.index(("cancel", "Attendance", "ATT-N8"))
		first_fetch = kinds.index(("fetch_shift", "Employee Checkin", "T-8-1833"))
		self.assertLess(first_cancel, first_fetch)
		# the link is cleared before the shift is re-resolved, then saved without validation
		fetch = next(e for e in self.log if e[0] == "fetch_shift" and e[2] == "T-8-1833")
		self.assertIsNone(fetch[3])
		self.assertTrue(self.docs[("Employee Checkin", "T-8-1833")].flags.ignore_validate)
		self.assertIn(("save", "Employee Checkin", "T-8-1833"), [k for k in kinds])
		self.assertEqual(self.remarks[0], (RIA, "2026-09-08", True))
		self.assertLess(kinds.index(("save", "Employee Checkin", "T-8-1833")), len(self.log))

	def test_taps_are_restamped_oldest_first_and_a_cancelled_row_is_not_cancelled_twice(self):
		self.apply()
		fetched = [e[2] for e in self.log if e[0] == "fetch_shift"]
		self.assertEqual(fetched[:5], ["T-8-1833", "T-9-0750", "T-9-1833", "T-10-0750", "T-10-1833"])
		cancelled = [e[2] for e in self.log if e[0] == "cancel"]
		self.assertEqual(cancelled, ["ATT-N8", "ATT-N9", "ATT-N10"])

	def test_the_day_is_rebuilt_by_the_engine_never_by_this_module(self):
		self.apply()
		self.assertEqual(
			self.remarks[:3],
			[(RIA, "2026-09-08", True), (RIA, "2026-09-09", True), (RIA, "2026-09-10", True)],
		)
		self.assertNotIn("Attendance", [e[1] for e in self.log if e[0] == "save"])

	def test_e35_the_employee_lock_is_taken_per_day(self):
		self.apply()
		self.assertEqual(self.locks[:3], [RIA, RIA, RIA])

	def test_a_dry_run_writes_nothing(self):
		fakes = {s: (lambda win, for_update=False: {"planned": [], "held_back": []}) for s in rec.STEPS}
		with patch.dict(rec._PLANNERS, fakes | {"rostered_shift": rec._plan_rostered_shift}):
			result = rec.apply_recovery("rostered_shift", "2026-09-01", "2026-09-13", dry_run=1)
		self.assertEqual(result["planned_count"], 4)
		self.assertEqual(self.log, [])
		self.assertEqual(self.remarks, [])
		self.assertEqual(result["planned"][0]["expected"]["status"], "Present")

	def test_a_row_that_cannot_be_cancelled_holds_its_day_and_the_rest_go_on(self):
		def cancel_boom():
			raise frappe.ValidationError("boom")

		doc = self._get_doc("Attendance", "ATT-N9")
		doc.cancel = cancel_boom
		_plan, outcome = self.apply()
		held = {h["date"] for h in outcome["held_back"]}
		self.assertIn("2026-09-09", held)
		self.assertIn("2026-09-08", {d["date"] for d in outcome["done"]})


class TestStrayTapsAfterACancel(_Step):
	"""fresh.local, 15 Sep 2026: cancelling the night row of 8 Sep unlinked the
	07:50 of 9 Sep, which still carried the night stamp when 8 Sep was
	re-marked — the engine re-invented a night Half Day from it. Every tap a
	cancelled row held is re-stamped BEFORE any day is re-marked, once."""

	def setUp(self):
		super().setUp()
		linked = {
			"ATT-N8": ["T-8-1833", "T-9-0750"],
			"ATT-N9": ["T-9-1833", "T-10-0750"],
			"ATT-N10": ["T-10-1833", "T-11-0750"],
		}

		def get_all(doctype, filters=None, **kw):
			if doctype == "Employee Checkin" and filters and filters.get("attendance"):
				return [frappe._dict(name=n) for n in linked.get(filters["attendance"], [])]
			return []

		patcher = patch.object(frappe, "get_all", get_all)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_the_next_mornings_tap_is_restamped_before_the_day_is_remarked(self):
		self.apply()
		kinds = [e[:3] for e in self.log]
		first_remark = kinds.index(("remark", "Attendance", "2026-09-08"))
		self.assertLess(kinds.index(("fetch_shift", "Employee Checkin", "T-9-0750")), first_remark)
		# re-stamped once, by the day that cancelled the row it hung on
		self.assertEqual(sum(1 for k in kinds if k == ("fetch_shift", "Employee Checkin", "T-9-0750")), 1)

	def test_a_day_is_remarked_by_its_own_step_never_earlier(self):
		self.apply()
		remarks = [e[2] for e in self.log if e[0] == "remark"]
		self.assertEqual(remarks[:4], ["2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11"])


class TestTapInsideTheOtherShiftsHours(_Step):
	"""I2 (integration review): the resolver gives a tap that sits inside the
	night's SCHEDULED hours back to the night while the roster says day. When
	the night assignment stays (it is worked again later, E15) the step cancelled
	the night row, got the night back on re-stamp, only warned, and re-marked the
	same row — cancel/rebuild churn every night. The day is HR's: hold it and
	roll the cancel back."""

	def setUp(self):
		super().setUp()
		doc = self._get_doc("Employee Checkin", "T-9-1833")

		def stays_on_the_night():
			self.log.append(("fetch_shift", "Employee Checkin", doc.name, doc.attendance))
			doc.shift = NIGHT
			doc.shift_start = datetime(2026, 9, 9, 19, 30)

		doc.fetch_shift = stays_on_the_night

	def test_the_day_is_held_for_hr_and_its_cancel_is_rolled_back(self):
		_plan, outcome = self.apply()
		held = next(h for h in outcome["held_back"] if h["date"] == "2026-09-09")
		self.assertTrue(held["hr"])
		self.assertIn("end that shift first", held["reason"])
		self.assertTrue(auto.needs_hr(held), held["reason"])
		# nothing of that day stands: no re-mark, the row's cancel rolled back
		self.assertNotIn(("remark", "Attendance", "2026-09-09", True), [e[:4] for e in self.log])
		frappe.db.rollback.assert_any_call(save_point=rec.ROW_SAVEPOINT)
		self.assertIn(("cancel", "Attendance", "ATT-N9"), [e[:3] for e in self.log])
		# the other days are still fixed
		self.assertEqual(
			{d["date"] for d in outcome["done"]} & {"2026-09-08", "2026-09-10"}, {"2026-09-08", "2026-09-10"}
		)


# --- E16: a pending forgotten check-out is not evidence -----------------------------------

BASE = pathlib.Path(__file__).resolve().parents[1]


class TestLiveRia(_Step):
	"""Ria's live shape (15 Sep 2026): E1/E2 with LINKED taps, a Pending late OUT on 4 Sep."""

	def setUp(self):
		super().setUp()
		self.taps = ria_live_taps()
		self.rows = ria_live_rows()
		self.assignments = [
			_assignment("SA-DAY", DAY, date(2026, 8, 1)),
			_assignment("SA-NIGHT", NIGHT, date(2026, 8, 1)),
		]

	def test_7_and_9_sep_go_back_on_the_day_shift_and_the_clean_days_are_left_alone(self):
		plan, result = self.apply()
		self.assertEqual([p["date"] for p in plan["planned"]], ["2026-09-07", "2026-09-09"])
		self.assertEqual([p["restamp"] for p in plan["planned"]], [["T-7-OUT"], ["T-9-OUT"]])
		self.assertEqual([p["cancel_rows"] for p in plan["planned"]], [["ATT-N7"], ["ATT-N9"]])
		self.assertEqual(plan["assignments"][0]["end_date"], "2026-09-06")
		self.assertEqual([d["date"] for d in result["done"]], ["2026-09-07", "2026-09-09"])
		self.assertEqual(result["held_back"], [])
		self.assertEqual(sorted(self.remarks), [(RIA, "2026-09-07", True), (RIA, "2026-09-09", True)])

	def test_a_day_worker_rostered_only_by_her_default_shift_is_held_for_hr_never_moved_to_the_night(self):
		# fresh.local, 15 Sep 2026: with no day assignment the night assignment read as
		# "rostered" and the step moved her real 8, 9 and 10 Sep day taps onto the night
		# (22.86 h night rows). The Employee default shift says day; the assignment
		# says night: nobody guesses, HR decides.
		self.assignments = [_assignment("SA-NIGHT", NIGHT, date(2026, 8, 1))]
		self.defaults = {RIA: DAY}
		plan, result = self.apply()
		self.assertEqual(plan["planned"], [])
		self.assertEqual(plan["assignments"], [])
		self.assertEqual(result["done"], [])
		self.assertEqual(self.log, [])
		held = {h["date"]: h for h in plan["held_back"]}
		self.assertEqual(sorted(held), ["2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10"])
		for h in held.values():
			self.assertTrue(h["hr"])
			self.assertIn("default shift", h["reason"])
			self.assertIn(DAY, h["reason"])
			self.assertIn("SA-NIGHT", h["reason"])

	def test_skip_stamps_never_refetches_a_tap_off_the_employee_default_shift(self):
		# fresh.local, 15 Sep 2026: once rostered_shift held her, the skip_stamps step's
		# "punches split across shifts" repair re-fetched the 9 Sep 07:54 IN onto the
		# night (the only assignment) and the rebuild invented an 8 Sep night Half Day.
		entry = {
			"employee": RIA,
			"date": "2026-09-09",
			"action": "refetch-shift",
			"punches": ["T-9-0750", "T-9-OUT"],
		}
		moves = [("T-9-0750", DAY, NIGHT)]
		with (
			patch.object(rec, "_audit_plan", return_value=([], [entry], set())),
			patch.object(rec, "_refetch_moves", return_value=moves),
			patch.object(frappe.db, "get_value", return_value=DAY),
		):
			plan = rec._plan_skip_stamps(self.win)
		self.assertEqual(plan["planned"], [])
		held = plan["held_back"][0]
		self.assertTrue(held["hr"])
		self.assertIn("default shift", held["reason"])
		self.assertIn("T-9-0750", held["reason"])
		self.assertIn(NIGHT, held["reason"])
		# no default shift on the employee record: the repair runs as before
		with (
			patch.object(rec, "_audit_plan", return_value=([], [entry], set())),
			patch.object(rec, "_refetch_moves", return_value=moves),
			patch.object(frappe.db, "get_value", return_value=None),
		):
			plan = rec._plan_skip_stamps(self.win)
		self.assertEqual([p["date"] for p in plan["planned"]], ["2026-09-09"])
		self.assertEqual(plan["planned"][0]["moves"], moves)

	def test_f17_the_pending_late_out_alone_is_left_out_and_4_sep_is_still_a_day_to_mark(self):
		# "missing day" family: 4 Sep has IN 08:00, OUT 19:00:27, a double-tap IN and a
		# Pending late OUT, no row for 11 days. The claim is not evidence (E16); the
		# other three taps are, so the day is on the list to mark, not hidden.
		with patch.object(rec, "_holiday_days", return_value=set()):
			plan = rec._plan_no_attendance_row(self.win, ctx=self.ctx())
		self.assertEqual([p["date"] for p in plan["planned"]], ["2026-09-04"])
		self.assertEqual(plan["held_back"], [])
		self.assertEqual(plan["planned"][0]["taps"], 3)
		self.assertIn("3 tap(s)", plan["planned"][0]["reason"])


def _shift_type_namespace():
	tree = ast.parse((BASE / "hr/doctype/shift_type/shift_type.py").read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ShiftType")
	cls.bases = []
	cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "get_employee_checkins"]
	helpers = [
		n
		for n in tree.body
		if (isinstance(n, ast.FunctionDef) and n.name in {"counts_for_attendance", "pending_late_checkouts"})
		or (
			isinstance(n, ast.Assign)
			and any(isinstance(t, ast.Name) and t.id == "CHECKIN_FIELDS" for t in n.targets)
		)
	]
	ns = {"frappe": frappe, "cint": int, "logger": __import__("logging").getLogger("t")}
	exec(compile(ast.Module(body=[*helpers, cls], type_ignores=[]), "shift_type", "exec"), ns)
	return ns


class TestPendingLateCheckoutE16(unittest.TestCase):
	def setUp(self):
		self.ns = _shift_type_namespace()

	def test_a_pending_late_out_does_not_count_a_plain_pending_punch_does(self):
		counts = self.ns["counts_for_attendance"]
		self.assertFalse(counts({"remote_approval_status": "Pending", "is_late_checkout": 1}))
		self.assertTrue(counts({"remote_approval_status": "Pending", "is_late_checkout": 0}))
		self.assertTrue(counts({"remote_approval_status": "Approved", "is_late_checkout": 1}))

	def test_a_rejected_late_out_is_skip_stamped_and_still_dropped(self):
		counts = self.ns["counts_for_attendance"]
		self.assertFalse(
			counts({"remote_approval_status": "Rejected", "skip_auto_attendance": 1, "is_late_checkout": 1})
		)

	def test_the_hourly_read_leaves_a_pending_late_out_for_its_approval(self):
		rows = [
			frappe._dict(name="IN", employee="E1", remote_approval_status=None),
			frappe._dict(name="OUT-LATE", employee="E1", remote_approval_status="Pending"),
			frappe._dict(name="OUT-FAR", employee="E2", remote_approval_status="Pending"),
		]

		def get_all(doctype, **kw):
			if doctype == "Employee Checkin":
				return list(rows)
			if doctype == "Remote Checkin Request":
				self.assertEqual(kw["filters"]["is_late_checkout"], 1)
				self.assertEqual(kw["filters"]["status"], "Pending")
				return [frappe._dict(checkin="OUT-LATE")]
			raise AssertionError(doctype)

		shift = self.ns["ShiftType"]()
		shift.name = "Day"
		shift.process_attendance_after = "2026-09-01"
		shift.last_sync_of_checkin = "2026-09-14 00:00:00"
		with patch.object(frappe, "get_all", get_all):
			read = shift.get_employee_checkins()
		self.assertEqual([r.name for r in read], ["IN", "OUT-FAR"])
		self.assertFalse(read[1].get("is_late_checkout"))


if __name__ == "__main__":
	unittest.main()
