"""HR's own press is not protected from HR.

Owner, 17 Sep 2026, on what the Fix Day rebuild has to deliver:

> "i just want to ensure we already settle the pairing (in out) correctly, the
> system must automate things that it needs, like their total working hours, if
> they have ot? make sure it can be claim in their nadi pwa, and calendar wont
> show absent, half day whatsoever."

It would not have. `attendance_recovery.protected_reason` holds any row the
ownership classifier calls HR's — the guard that stops the NIGHTLY JOB from
overwriting a day a person keyed by hand. Norazlin's 4 September row reads
"Absent (HR)", so after HR cancelled the ghost, paired the session and ignored
the glitch taps, the re-mark would have declined and the day would have stayed
Absent with no hours and no OT: the exact complaint, survived intact.

The hold protects HR's work FROM THE MACHINE. When HR is the one asking — one
press, on one day, with a reason, recorded in the fix log and undoable — there
is nobody to protect them from. Every other protection is untouched and still
wins: a draft, a leave, a half-day leave, an attendance request, a day HR
removed in Shift Attendance, an approved payout, a running shift, today.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_hr_asked_for_this_day.py
"""

from __future__ import annotations

import ast
import pathlib
import sys
import types
import unittest
from datetime import date
from unittest.mock import patch

sys.path[:0] = [str(pathlib.Path(__file__).resolve().parents[2])]

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.utils import attendance_recovery as rec

MODULE = "hrms.utils.attendance_ownership"
TODAY = date(2026, 9, 17)
DAY = date(2026, 9, 4)


def row(name="HR-ATT-2026-15657", **extra):
	base = {
		"name": name,
		"docstatus": 1,
		"status": "Absent",
		"auto_attendance": 0,
		"leave_type": None,
		"leave_application": None,
		"attendance_request": None,
		"modify_half_day_status": 0,
	}
	base.update(extra)
	return base


def classifier(owner, reason="a person saved this row"):
	module = types.ModuleType(MODULE)
	module.OWNER_HR = "hr"
	module.OWNER_REQUEST = "request"
	module.OWNER_SYSTEM = "system"
	module.OWNER_UNSURE = "unsure"
	module.classify_row = lambda r, versions=None, source=None: (owner, reason)
	return patch.dict(sys.modules, {MODULE: module})


class TheHoldStillStopsTheMachineCase(unittest.TestCase):
	"""Nothing about the nightly job changes."""

	def test_an_hr_owned_row_is_held_from_the_job(self):
		with classifier("hr"):
			self.assertIsNotNone(rec.protected_reason(DAY, TODAY, [row()]))

	def test_unsure_is_still_held_from_the_job(self):
		with classifier("unsure"):
			self.assertIsNotNone(rec.protected_reason(DAY, TODAY, [row()]))


class WhenHrAsksCase(unittest.TestCase):
	def test_hr_owned_is_no_longer_a_hold(self):
		with classifier("hr"):
			self.assertIsNone(rec.protected_reason(DAY, TODAY, [row()], hr_asked=True))

	def test_unsure_is_no_longer_a_hold_either(self):
		with classifier("unsure"):
			self.assertIsNone(rec.protected_reason(DAY, TODAY, [row()], hr_asked=True))

	def test_a_row_from_a_request_still_holds(self):
		"""Owner-by-REQUEST is not HR's handiwork: a leave or an attendance
		request speaks for the day and has to be cancelled first, whoever asks."""
		with classifier("request"):
			self.assertIsNotNone(rec.protected_reason(DAY, TODAY, [row()], hr_asked=True))


class EveryOtherProtectionStillWinsCase(unittest.TestCase):
	def held(self, **extra):
		with classifier("hr"):
			return rec.protected_reason(DAY, TODAY, [row(**extra)], hr_asked=True, **self.extra_kwargs())

	def extra_kwargs(self):
		return {}

	def test_a_draft_still_holds(self):
		self.assertIsNotNone(self.held(docstatus=0))

	def test_a_leave_still_holds(self):
		self.assertIsNotNone(self.held(leave_type="Annual Leave"))

	def test_a_half_day_leave_still_holds(self):
		self.assertIsNotNone(self.held(modify_half_day_status=1))

	def test_an_attendance_request_still_holds(self):
		self.assertIsNotNone(self.held(attendance_request="ATR-0001"))

	def test_today_still_holds(self):
		with classifier("hr"):
			self.assertIsNotNone(rec.protected_reason(TODAY, TODAY, [row()], hr_asked=True))

	def test_a_day_hr_removed_still_holds(self):
		with classifier("hr"):
			self.assertIsNotNone(rec.protected_reason(DAY, TODAY, [row()], removed_by_hr=True, hr_asked=True))

	def test_an_approved_payout_still_holds(self):
		with classifier("hr"):
			self.assertIsNotNone(
				rec.protected_reason(DAY, TODAY, [row()], financial="OTR-0007", hr_asked=True)
			)

	def test_a_mirrored_row_still_holds(self):
		"""A row the other instance owns is not HR's to rewrite here, whoever
		presses. Every other mirrored guard in this codebase says the same
		(_restamp_tap, _end_extra_assignment, Fix Day's own tap writer); before
		this, a mirrored row was held only by reading as UNSURE — which
		`hr_asked` waives."""
		with classifier("unsure"):
			self.assertIsNotNone(
				rec.protected_reason(DAY, TODAY, [row(synced_from_instance="nasty-live")], hr_asked=True)
			)

	def test_the_mirrored_row_is_held_by_its_own_hold_not_a_new_one(self):
		with classifier("unsure"):
			held = rec.protected_reason(DAY, TODAY, [row(synced_from_instance="nasty-live")], hr_asked=True)
		self.assertIsNotNone(held)
		self.assertIn("HR-ATT-2026-15657", held)

	def test_a_live_request_over_the_day_still_holds(self):
		with classifier("hr"):
			self.assertIsNotNone(
				rec.protected_reason(DAY, TODAY, [row()], request="Leave Application LAP-3", hr_asked=True)
			)


class TheNeverWorseGuardCovversHrsPressCase(unittest.TestCase):
	"""Review of b9794c65b, second Critical.

	There are two rebuild paths in this codebase and only one of them has the
	never-worse guard: `attendance_recovery.guarded_rebuild` takes a savepoint,
	compares the day before and after, and ROLLS BACK a rebuild that lowered a
	submitted day's status or hours. `day_remark.remark_day` — the path Fix Day
	uses — calls `_remark_released_day` bare.

	That was harmless while `owner_hold` refused to rebuild an HR-owned row at
	all. `hr_asked` opens exactly that door: a day HR raised to Present by hand
	could be recomputed from punches alone and come back Absent, with nothing
	catching it. The waiver has to bring the guard with it.
	"""

	def run_remark(self, hr_asked, remark_result=None, guard_result=None):
		from hrms.utils import day_remark as dr

		calls = {"guarded": 0, "bare": 0}

		def guarded(employee, day, remark, source="recovery"):
			calls["guarded"] += 1
			calls["source"] = source
			return guard_result if guard_result is not None else {"marked": ["ATT-1"]}

		def bare(employee, day, apply):
			calls["bare"] += 1
			return remark_result if remark_result is not None else {"marked": ["ATT-1"]}

		with (
			patch.object(dr, "_shift_still_running", lambda employee, day: False),
			patch.object(dr, "lock_employee_row", lambda employee: None),
			patch.object(dr, "_retire_unmarkable_rows", lambda *a, **k: []),
			patch.object(rec, "_day_protection", lambda *a, **k: None),
			patch.object(rec, "_rebuild_under_guard", guarded),
			patch.object(rec, "_remark_released_day", bare),
		):
			answer = dr._remark_once("HR-EMP-00021", DAY, "fix day: rebuild_day", hr_asked=hr_asked)
		return answer, calls

	def test_hrs_press_goes_through_the_guard(self):
		_, calls = self.run_remark(hr_asked=True)
		self.assertEqual(calls["guarded"], 1, "a rebuild HR asked for must be rollback-protected")
		self.assertEqual(calls["bare"], 0)

	def test_a_rollback_comes_back_as_held_not_as_success(self):
		answer, _ = self.run_remark(
			hr_asked=True, guard_result={"held": "it would have gone Present -> Absent", "hr": True}
		)
		self.assertEqual(answer["action"], "held")
		self.assertIn("Absent", answer["detail"])

	def test_a_rebuild_that_did_not_make_the_day_worse_is_applied(self):
		answer, _ = self.run_remark(hr_asked=True)
		self.assertEqual(answer["action"], "remarked")
		self.assertEqual(answer["marked"], ["ATT-1"])

	def test_the_nightly_path_is_left_exactly_as_it_was(self):
		# Its missing guard is older than this change and is ticketed, not
		# widened here: a behaviour change to the automatic pass is its own job.
		_, calls = self.run_remark(hr_asked=False)
		self.assertEqual(calls["bare"], 1)
		self.assertEqual(calls["guarded"], 0)

	def test_the_guard_records_who_asked(self):
		_, calls = self.run_remark(hr_asked=True)
		self.assertIn("fix", calls["source"], "the day-fix log says which pass rebuilt the day")


class TheDayIsHandedBackToTheEngineCase(unittest.TestCase):
	"""The fourth door, found on live after everything else was fixed.

	Owner, 17 Sep 2026: he cancelled the ghost row, paired 09:03 IN with 18:09
	OUT and ignored the three glitch taps. The Fix Day screen showed exactly
	that. `HR-ATT-2026-15657` still read "Absent (HR) · in — · out — · 0 h".

	`shift_type.get_automation_attendance` filters `auto_attendance: 1` and says
	so in its own docstring: "Never returned, so never rebuilt from punches: a
	row HR marked by hand". So the engine found no row to update, tried to
	CREATE one, hit DuplicateAttendanceError, and swallowed it — the day was
	never touched. Waiving the hold in `protected_reason` got the rebuild
	started; this is the gate three layers further down with its own copy of
	"who owns this row".

	Asking the engine to rebuild a day from its punches IS handing the row back
	to the engine, so that is what happens — and the ownership flag then tells
	the truth about who computed the values in it.
	"""

	def rows(self, *extra):
		return [row(name=f"ATT-{i}", **kw) for i, kw in enumerate(extra, start=1)]

	def released(self, *extra):
		store = {r["name"]: dict(r) for r in self.rows(*extra)}

		def get_all(doctype, filters=None, fields=None, **kw):
			return [dict(r) for r in store.values()]

		def set_value(doctype, name, field, value, **kw):
			store[name][field] = value

		with (
			patch.object(rec, "_attendance_rows", lambda employee, day: list(store.values())),
			patch.object(rec.frappe.db, "set_value", set_value, create=True),
		):
			names = rec.release_to_automation("HR-EMP-00021", DAY)
		return names, store

	def test_an_hr_owned_row_is_handed_back(self):
		names, store = self.released({})
		self.assertEqual(names, ["ATT-1"])
		self.assertEqual(store["ATT-1"]["auto_attendance"], 1)

	def test_a_row_the_engine_already_owns_is_left_alone(self):
		names, _ = self.released({"auto_attendance": 1})
		self.assertEqual(names, [], "nothing to hand back")

	def test_a_leave_row_is_never_handed_back(self):
		self.assertEqual(self.released({"leave_type": "Annual Leave"})[0], [])

	def test_an_on_leave_row_is_never_handed_back(self):
		self.assertEqual(self.released({"status": "On Leave"})[0], [])

	def test_a_half_day_leave_is_never_handed_back(self):
		self.assertEqual(self.released({"modify_half_day_status": 1})[0], [])

	def test_a_row_from_an_attendance_request_is_never_handed_back(self):
		self.assertEqual(self.released({"attendance_request": "ATR-0001"})[0], [])

	def test_a_mirrored_row_is_never_handed_back(self):
		self.assertEqual(self.released({"synced_from_instance": "nasty-live"})[0], [])

	def test_a_draft_is_never_handed_back(self):
		self.assertEqual(self.released({"docstatus": 0})[0], [])

	def test_a_cancelled_row_is_never_handed_back(self):
		self.assertEqual(self.released({"docstatus": 2})[0], [])


class OnlyOnHrsPressCase(unittest.TestCase):
	def run_remark(self, hr_asked):
		from hrms.utils import day_remark as dr

		order = []

		def guarded(employee, day, remark, source="recovery"):
			return remark(employee, day, True)

		with (
			patch.object(dr, "_shift_still_running", lambda employee, day: False),
			patch.object(dr, "lock_employee_row", lambda employee: None),
			patch.object(dr, "_retire_unmarkable_rows", lambda *a, **k: []),
			patch.object(rec, "_day_protection", lambda *a, **k: None),
			patch.object(rec, "_rebuild_under_guard", guarded),
			patch.object(rec, "release_to_automation", lambda e, d: order.append("released") or ["ATT-1"]),
			patch.object(
				rec,
				"_remark_released_day",
				lambda e, d, apply: order.append("remarked") or {"marked": ["ATT-1"]},
			),
		):
			dr._remark_once("HR-EMP-00021", DAY, "fix day", hr_asked=hr_asked)
		return order

	def test_the_day_is_handed_back_before_it_is_remarked(self):
		self.assertEqual(self.run_remark(hr_asked=True), ["released", "remarked"])

	def test_the_nightly_job_hands_nothing_back(self):
		self.assertEqual(self.run_remark(hr_asked=False), ["remarked"])


class ItIsWiredAllTheWayThroughCase(unittest.TestCase):
	"""A parameter nothing passes is a parameter that fixes nothing."""

	def body(self, module_path, name):
		source = pathlib.Path(module_path).read_text()
		return next(
			ast.unparse(node)
			for node in ast.walk(ast.parse(source))
			if isinstance(node, ast.FunctionDef) and node.name == name
		)

	def test_the_day_protection_passes_it_on(self):
		self.assertIn("hr_asked", self.body(rec.__file__, "_day_protection"))

	def test_the_remark_passes_it_on(self):
		from hrms.utils import day_remark

		self.assertIn("hr_asked", self.body(day_remark.__file__, "_remark_once"))
		self.assertIn("hr_asked", self.body(day_remark.__file__, "remark_day"))

	def test_fix_day_asks_as_hr(self):
		from hrms.api import attendance_fix_day

		self.assertIn("hr_asked=True", self.body(attendance_fix_day.__file__, "_rebuild"))

	def test_the_nightly_job_does_not(self):
		from hrms.utils import day_remark

		self.assertNotIn("hr_asked=True", self.body(day_remark.__file__, "remark_day_after_commit"))


if __name__ == "__main__":
	unittest.main()
