"""A zero is an answer; it is not an explanation.

Fifteen distinct situations end in no overtime for a date, and every one of them
was reported with the same sentence — "No punch-verified overtime for this date"
on the form, "your check-outs prove at most 0.0 hours" on save. Both state a
CONCLUSION and hide the CAUSE, and only one of the fifteen causes is the
employee's own to answer. The rest need HR, and nothing told anyone that.

Bench-free: the shared frappe stub, the way every other suite here does it.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "hrms", "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import ot_calculation as ot

DAY = "2026-09-03"


def _row(**kw):
	base = {
		"log_type": "IN",
		"shift": "Day Shift",
		"offshift": 0,
		"skip_auto_attendance": 0,
		"requires_remote_approval": 0,
		"remote_approval_status": "",
	}
	base.update(kw)
	# frappe.get_all hands back attribute-accessible rows; a plain dict here
	# would pass a test the real call would fail.
	return frappe._dict(base)


class TestTheZeroNamesItsCause(unittest.TestCase):
	def _explain(self, rows, ot_enabled=True):
		with (
			patch.object(ot.frappe, "get_all", return_value=rows),
			patch.object(ot, "_get_shift_ot_config", return_value={"x": 1} if ot_enabled else None),
		):
			return ot._explain_no_overtime("EMP-1", DAY)

	def test_no_punches_at_all_says_so(self):
		self.assertIn("No check-ins", self._explain([]))

	def test_punches_with_no_shift_point_at_the_assignment(self):
		"""The single biggest silent-zero source: a punch with no shift makes OT
		evaluate to nothing, and it is HR's to fix, not the employee's."""
		said = self._explain([_row(shift=None), _row(shift=None, log_type="OUT")])
		self.assertIn("not attached to any shift", said)
		self.assertIn("HR", said)

	def test_overtime_switched_off_on_the_shift_says_which_shift(self):
		said = self._explain([_row(), _row(log_type="OUT")], ot_enabled=False)
		self.assertIn("not enabled", said)
		self.assertIn("Day Shift", said)

	def test_an_off_shift_punch_is_named_rather_than_silently_dropped(self):
		said = self._explain([_row(offshift=1), _row(log_type="OUT")])
		self.assertIn("off-shift", said)

	def test_a_punch_waiting_for_approval_is_named(self):
		said = self._explain(
			[_row(requires_remote_approval=1, remote_approval_status="Pending"), _row(log_type="OUT")]
		)
		self.assertIn("approval", said)

	def test_a_missing_check_out_is_named(self):
		self.assertIn("no check-out", self._explain([_row(), _row()]))

	def test_a_genuinely_empty_day_invents_no_cause(self):
		"""When the punches look fine and the hours really are zero there is no
		honest cause to name, and inventing one would be worse than silence."""
		self.assertEqual(self._explain([_row(), _row(log_type="OUT")]), "")


if __name__ == "__main__":
	unittest.main()
