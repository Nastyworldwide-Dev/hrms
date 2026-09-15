"""An Attendance Request that would create nothing is refused in words, not a table.

`validate_no_attendance_to_create` raised through `frappe.msgprint(...,
as_table=True, raise_exception=True)` with a list-of-lists message. Desk
renders that as an HTML table; the PWA shows the server message as text, so
the employee read this on their phone (fresh.local, 15 Sep 2026):

    [['Date', 'Reason', 'Action'], ['2026-09-09', 'Attendance status unchanged', 'Skip']]

The same refusal now arrives as one sentence per day, through frappe.throw
like every other validation on the doctype:

    No attendance to create: 2026-09-09 (Attendance status unchanged).

Bench-free: the method is lifted from the controller by AST and driven with
canned warnings.

    python3 hrms/tests/test_attendance_request_refusal_is_plain_text.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

PATH = pathlib.Path(__file__).resolve().parents[1] / "hr/doctype/attendance_request/attendance_request.py"


class _Refused(Exception):
	pass


def _lift(namespace):
	tree = ast.parse(PATH.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AttendanceRequest")
	fn = next(
		n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "validate_no_attendance_to_create"
	)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(PATH), "exec"), namespace)
	return namespace["validate_no_attendance_to_create"]


def _run(warnings, from_date="2026-09-09", to_date="2026-09-09"):
	frappe = MagicMock()
	frappe.throw.side_effect = lambda msg, *a, **k: (_ for _ in ()).throw(_Refused(msg))
	frappe.bold = lambda v: v
	ns = {
		"frappe": frappe,
		"_": lambda s: s,
		"date_diff": lambda a, b: int(a[-2:]) - int(b[-2:]),
		"format_date": lambda d: d,
		"logger": MagicMock(),
	}
	validate = _lift(ns)
	validate(
		SimpleNamespace(
			name="AR-1", from_date=from_date, to_date=to_date, get_attendance_warnings=lambda: warnings
		)
	)
	return frappe


class TestRefusalIsPlainText(unittest.TestCase):
	def test_a_day_that_creates_nothing_is_refused_in_one_sentence(self):
		with self.assertRaises(_Refused) as ctx:
			_run([{"date": "2026-09-09", "reason": "Attendance status unchanged", "action": "Skip"}])
		message = str(ctx.exception)
		self.assertIsInstance(message, str)
		self.assertIn("2026-09-09", message)
		self.assertIn("Attendance status unchanged", message)
		self.assertNotIn("[[", message, "a list rendered as text is not a message")

	def test_every_skipped_day_is_named(self):
		with self.assertRaises(_Refused) as ctx:
			_run(
				[
					{"date": "2026-09-09", "reason": "On Leave", "action": "Skip"},
					{"date": "2026-09-10", "reason": "Holiday", "action": "Skip"},
				],
				to_date="2026-09-10",
			)
		self.assertIn("2026-09-09 (On Leave)", str(ctx.exception))
		self.assertIn("2026-09-10 (Holiday)", str(ctx.exception))

	def test_a_request_that_still_creates_or_overwrites_something_passes(self):
		frappe = _run(
			[
				{"date": "2026-09-09", "reason": "On Leave", "action": "Skip"},
				{"date": "2026-09-10", "reason": "Attendance already marked", "action": "Overwrite"},
			],
			to_date="2026-09-10",
		)
		frappe.throw.assert_not_called()
		frappe.msgprint.assert_not_called()


if __name__ == "__main__":
	unittest.main()
