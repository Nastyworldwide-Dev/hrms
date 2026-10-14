"""A time slip excuses a late arrival (owner, 14 Oct 2026).

It is a Fix a day request with reason "Time Slip": one past or current day,
a reason, a slip file, the usual approver. Approved: that day is not late,
and no re-mark may bring the mark back. Rules lifted by AST (the modules
import erpnext):

    python3 hrms/tests/test_time_slip.py
"""

import ast
import datetime
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

HR = pathlib.Path(__file__).resolve().parent.parent / "hr" / "doctype"
REQUEST = HR / "attendance_request" / "attendance_request.py"
CHECKIN = HR / "employee_checkin" / "employee_checkin.py"


class _Refused(Exception):
	pass


def _class_body(source, cls):
	tree = ast.parse(source.read_text())
	return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls).body


def _lift(source, cls, name, namespace):
	fn = next(n for n in _class_body(source, cls) if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), "exec"), namespace)
	return namespace[name]


def _getdate(v=None):
	if v is None:
		return datetime.date(2026, 10, 14)
	return v if isinstance(v, datetime.date) else datetime.date.fromisoformat(v)


class TestFiling(unittest.TestCase):
	def setUp(self):
		self.frappe = MagicMock()
		self.frappe.throw.side_effect = _Refused
		self.frappe.db.exists.return_value = None
		ns = {"frappe": self.frappe, "_": lambda s: s, "getdate": _getdate, "TIME_SLIP": "Time Slip"}
		self.check = _lift(REQUEST, "AttendanceRequest", "validate_time_slip", ns)

	def slip(self, day="2026-10-14", to=None, reason="Clinic Visit"):
		return SimpleNamespace(
			name="ARQ-1",
			employee="E1",
			from_date=day,
			to_date=to or day,
			time_slip_reason=reason,
			half_day=1,
			in_time="09:00",
			out_time="18:00",
		)

	def test_a_slip_for_today_is_filed_with_no_hours_of_its_own(self):
		doc = self.slip()
		self.check(doc)
		self.assertEqual((doc.half_day, doc.in_time, doc.out_time), (0, None, None))

	def test_a_slip_covers_one_day(self):
		with self.assertRaises(_Refused):
			self.check(self.slip(to="2026-10-15"))

	def test_a_slip_cannot_be_for_a_day_not_yet_come(self):
		with self.assertRaises(_Refused):
			self.check(self.slip(day="2026-10-16"))

	def test_a_reason_is_required(self):
		with self.assertRaises(_Refused):
			self.check(self.slip(reason=None))

	def test_one_slip_per_day(self):
		self.frappe.db.exists.return_value = "ARQ-0"
		with self.assertRaises(_Refused):
			self.check(self.slip())


class TestWiring(unittest.TestCase):
	def _calls(self, source, cls, name):
		fn = next(n for n in _class_body(source, cls) if isinstance(n, ast.FunctionDef) and n.name == name)
		return [
			n.func.attr for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		]

	def test_validate_sends_a_slip_down_its_own_rules_only(self):
		"""A slip returns before the Fix a day rules (overlap, hours, nothing to create)."""
		fn = next(
			n
			for n in _class_body(REQUEST, "AttendanceRequest")
			if isinstance(n, ast.FunctionDef) and n.name == "validate"
		)
		branch = next(s for s in fn.body if isinstance(s, ast.If) and "is_time_slip" in ast.unparse(s.test))
		self.assertIn("validate_time_slip", ast.unparse(branch.body))
		self.assertIsInstance(branch.body[-1], ast.Return)
		after = fn.body[fn.body.index(branch) + 1 :]
		self.assertIn("validate_request_overlap", " ".join(ast.unparse(s) for s in after))

	def test_an_approved_slip_excuses_instead_of_marking(self):
		calls = self._calls(REQUEST, "AttendanceRequest", "on_submit")
		self.assertIn("excuse_late_arrival", calls)

	def test_a_slip_does_not_block_a_fix_a_day(self):
		src = REQUEST.read_text()
		body = src[src.index("def validate_request_overlap") : src.index("def throw_overlap_error")]
		self.assertIn("Request.reason != TIME_SLIP", body)

	def test_a_slip_always_needs_its_file(self):
		src = REQUEST.read_text()
		body = src[
			src.index("def validate_mandatory_attachment") : src.index("def validate_for_self_approval")
		]
		self.assertIn("not self.is_time_slip()", body)


class TestGuard(unittest.TestCase):
	"""Every marking routes through create_or_update_attendance; an approved
	slip must hold the late mark off there, or the nightly re-mark undoes it."""

	def test_marking_drops_late_for_an_excused_day(self):
		tree = ast.parse(CHECKIN.read_text())
		fn = next(
			n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "create_or_update_attendance"
		)
		first = fn.body[1] if isinstance(fn.body[0], ast.Expr) else fn.body[0]
		self.assertIn("excused_late", ast.unparse(first))
		self.assertIn("late_entry = False", ast.unparse(first))

	def test_excused_late_reads_only_approved_slips(self):
		tree = ast.parse(CHECKIN.read_text())
		fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "excused_late")
		src = ast.unparse(fn)
		for needle in ("'Time Slip'", "'Approved'", "'docstatus': 1"):
			self.assertIn(needle, src)


if __name__ == "__main__":
	unittest.main()
