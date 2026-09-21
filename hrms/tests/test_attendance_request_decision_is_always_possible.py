"""A decision on an Attendance Request is always possible.

Reported 21 Sep 2026 (verifica-live, HR-ARQ-26-…): a manager tapped Approve
and read

    No attendance to create: 07-08-2026 (Attendance status unchanged).

That refusal belongs to FILING: it stops an employee asking for a day that is
already what they ask for. It ran again at DECISION time, because `validate`
runs on every save and `decide()` sets the status and submits in one save.
By then the day had been marked Present by the punches (or by the mirror),
so the request could be neither approved — nor REJECTED, since a rejection is
the same save. It sat in the manager's queue forever with an error on every
tap.

Rule: `validate_no_attendance_to_create` judges an undecided request only.
Once `status` carries a decision the request goes through; approving a day
already marked is the harmless no-op `create_or_update_attendance` already
handles, and rejecting creates nothing to begin with.

Bench-free: the method is lifted from the controller by AST, as
test_attendance_request_refusal_is_plain_text.py does.

    python3 hrms/tests/test_attendance_request_decision_is_always_possible.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

PATH = pathlib.Path(__file__).resolve().parents[1] / "hr/doctype/attendance_request/attendance_request.py"

UNCHANGED = [{"date": "2026-08-07", "reason": "Attendance status unchanged", "action": "Skip"}]


class _Refused(Exception):
	pass


def _lift():
	tree = ast.parse(PATH.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AttendanceRequest")
	fn = next(
		n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "validate_no_attendance_to_create"
	)
	frappe = MagicMock()
	frappe.throw.side_effect = lambda msg, *a, **k: (_ for _ in ()).throw(_Refused(msg))
	frappe.bold = lambda v: v
	ns = {
		"frappe": frappe,
		"_": lambda s: s,
		"date_diff": lambda a, b: 0,
		"format_date": lambda d: d,
		"logger": MagicMock(),
	}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(PATH), "exec"), ns)
	return ns["validate_no_attendance_to_create"]


def _request(status):
	return SimpleNamespace(
		name="HR-ARQ-26-09-00040",
		status=status,
		from_date="2026-08-07",
		to_date="2026-08-07",
		get_attendance_warnings=lambda: UNCHANGED,
	)


class TestDecisionIsAlwaysPossible(unittest.TestCase):
	def test_filing_a_day_already_marked_is_still_refused(self):
		with self.assertRaises(_Refused):
			_lift()(_request("Open"))

	def test_approving_a_day_marked_since_filing_goes_through(self):
		_lift()(_request("Approved"))

	def test_rejecting_a_day_marked_since_filing_goes_through(self):
		_lift()(_request("Rejected"))


if __name__ == "__main__":
	unittest.main()
