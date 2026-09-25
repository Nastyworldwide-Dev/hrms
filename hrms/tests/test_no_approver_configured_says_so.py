"""An employee with no approver configured is told that, not "you picked wrong".

Owner ruling, 21 Sep 2026: "make it clear and not confusing", on the project's
standing rule that the system self-identifies — we never ask staff or HR to run
a URL or a console step to find out what is wrong.

Both approver fences threw the same message whether the pick was wrong or the
employee had nobody above them at all:

  * `ShiftRequest.validate_approver` — "Only Approvers can Approve this Request."
  * `hr.utils.validate_staff_approver` — "{0} is not one of your designated
    approvers. Please select your reporting manager."

The second is actively misleading when the list is empty: there IS no reporting
manager to select, and the employee cannot fix it. An empty list is an HR
configuration gap (no `reports_to`, no approver on the Employee record, or the
chain above is inactive), so it must say so and name HR as the fix.

A non-empty list keeps its existing message: the pick really was wrong, and the
employee can correct it from the dropdown.

Bench-free:
    PYTHONPATH=. python3 hrms/tests/test_no_approver_configured_says_so.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr import utils as hr_utils

STAFF = "staff@example.com"
EMPLOYEE = "HR-EMP-STAFF"


def _message(excinfo) -> str:
	return str(excinfo.exception)


class _Fence:
	"""The frappe surface both fences touch, with a configurable approver list."""

	def __init__(self, approvers):
		self.approvers = approvers

	def __enter__(self):
		from hrms.hr.doctype.shift_request import shift_request

		db = MagicMock()
		db.get_value.side_effect = lambda *a, **k: None
		self.patches = [
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user=STAFF)),
			patch.object(hr_utils, "get_designated_approvers", return_value=self.approvers),
			# `shift_request` imports the resolver by name at module load, so it
			# holds its own reference — patching only `hr_utils` leaves the real
			# function in place there and every shift case reads an empty chain.
			patch.object(shift_request, "get_designated_approvers", return_value=self.approvers),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()


class _Doc:
	def __init__(self, approver):
		self.doctype = "Leave Application"
		self.name = "LEAVE-0001"
		self.employee = EMPLOYEE
		self.leave_approver = approver

	def is_new(self):
		return False

	def get(self, fieldname):
		return getattr(self, fieldname, None)


def file_leave(approver, approvers):
	"""validate_staff_approver on a request the employee files for themselves."""
	with _Fence(approvers):
		with patch.object(
			frappe.db,
			"get_value",
			side_effect=lambda dt, name, fields=None, **k: (
				frappe._dict(user_id=STAFF, leave_approver=None, reports_to=None)
				if isinstance(fields, list)
				else None
			),
		):
			hr_utils.validate_staff_approver(
				_Doc(approver), "leave_approver", "leave_approver", "leave_approvers"
			)


def file_shift(approver, approvers):
	from hrms.hr.doctype.shift_request.shift_request import ShiftRequest

	doc = frappe._dict(
		doctype="Shift Request", name=None, employee=EMPLOYEE, approver=approver, status="Draft"
	)
	doc.is_new = lambda: True
	doc.has_value_changed = lambda _f: True
	with _Fence(approvers):
		ShiftRequest.validate_approver(doc)


class TestAnEmptyChainNamesTheRealProblem(unittest.TestCase):
	"""Nobody is above this employee — the employee cannot fix that."""

	def test_leave_says_no_approver_is_configured(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			file_leave("someone@example.com", [])
		message = _message(caught)
		self.assertIn("No approver", message)
		self.assertIn("HR", message)

	def test_leave_does_not_tell_them_to_pick_a_manager_that_is_not_there(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			file_leave("someone@example.com", [])
		self.assertNotIn("select your reporting manager", _message(caught))

	def test_shift_says_no_approver_is_configured(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			file_shift("someone@example.com", [])
		message = _message(caught)
		self.assertIn("No approver", message)
		self.assertIn("HR", message)


class TestAWrongPickStillSaysWrongPick(unittest.TestCase):
	"""Somebody IS above them; the employee can fix this from the dropdown."""

	def test_leave_routes_to_their_own_approver_instead_of_refusing(self):
		# SUPERSEDED 25 Sep 2026 (owner: "nobody is supposed to choose their
		# approver"): on the employee's own leave there is no pick to refuse;
		# the approver is set to their own, whatever was sent.
		doc = _Doc("stranger@example.com")
		with _Fence(["boss@example.com"]):
			with patch.object(
				frappe.db,
				"get_value",
				side_effect=lambda dt, name, fields=None, **k: (
					frappe._dict(user_id=STAFF, leave_approver=None, reports_to=None)
					if isinstance(fields, list)
					else STAFF
				),
			):
				hr_utils.validate_staff_approver(doc, "leave_approver", "leave_approver", "leave_approvers")
		self.assertEqual(doc.leave_approver, "boss@example.com")

	def test_shift_keeps_its_message(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			file_shift("stranger@example.com", ["boss@example.com"])
		message = _message(caught)
		self.assertIn("Only Approvers", message)
		self.assertNotIn("No approver", message)

	def test_the_right_pick_still_passes(self):
		file_leave("boss@example.com", ["boss@example.com"])  # must not raise
		file_shift("boss@example.com", ["boss@example.com"])  # must not raise


if __name__ == "__main__":
	unittest.main(verbosity=2)
