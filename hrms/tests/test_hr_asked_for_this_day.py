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


def row(**extra):
	base = {
		"name": "HR-ATT-2026-15657",
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

	def test_a_live_request_over_the_day_still_holds(self):
		with classifier("hr"):
			self.assertIsNotNone(
				rec.protected_reason(DAY, TODAY, [row()], request="Leave Application LAP-3", hr_asked=True)
			)


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
