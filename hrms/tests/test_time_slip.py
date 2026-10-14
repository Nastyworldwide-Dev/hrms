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


class TestEveryLateWriter(unittest.TestCase):
	"""Review of 37f2d86f4: two writers computed late outside the shared
	marking function, so HR's Fix Day and a half-day leave approval brought
	the late mark back on an excused day."""

	def test_fix_day_asks_excused_late(self):
		src = (
			pathlib.Path(__file__).resolve().parent.parent / "api" / "attendance_master_edit.py"
		).read_text()
		body = src[
			src.index("def _edit(") : src.index("saved = _insert_attendance(", src.index("def _edit("))
		]
		self.assertIn("excused_late(emp.name, day)", body)

	def test_half_day_leave_asks_excused_late(self):
		src = (HR / "leave_application" / "leave_application.py").read_text()
		at = src.index("late_early_for_row(doc, self.half_day_session)")
		self.assertIn("excused_late(self.employee, date)", src[at : at + 400])


class TestCancelRestoresLate(unittest.TestCase):
	"""Review of 37f2d86f4 and 980c1586d: a cancelled slip must bring the late
	mark back, by working that day's flag out again, not by re-marking the day
	(a late-only change would cancel a row that may be paid)."""

	def test_cancel_of_a_slip_withdraws_the_excuse_only(self):
		fn = next(
			n
			for n in _class_body(REQUEST, "AttendanceRequest")
			if isinstance(n, ast.FunctionDef) and n.name == "on_cancel"
		)
		first = fn.body[0]
		self.assertIn("is_time_slip", ast.unparse(first.test))
		self.assertIn("withdraw_late_excuse", ast.unparse(first.body))
		self.assertIsInstance(first.body[-1], ast.Return)

	def test_the_excuse_is_withdrawn_from_the_rows_own_times(self):
		src = REQUEST.read_text()
		body = src[src.index("def withdraw_late_excuse") : src.index("def create_attendance_records")]
		self.assertIn("late_early_for_row(row, approved_session(", body)
		self.assertNotIn("cancel()", body)

	def test_a_re_mark_still_ignores_a_late_only_difference(self):
		src = CHECKIN.read_text()
		fn = src[src.index("def _same_day_result") : src.index("def _replace_automation_attendance")]
		self.assertNotIn("late_entry", fn)


class TestPatch(unittest.TestCase):
	def setUp(self):
		path = (
			pathlib.Path(__file__).resolve().parent.parent / "patches" / "v16_0" / "add_time_slip_reason.py"
		)
		tree = ast.parse(path.read_text())
		ns = {"TIME_SLIP": "Time Slip"}
		fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "with_time_slip")
		exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), ns)
		self.add = ns["with_time_slip"]

	def test_hrs_own_reasons_are_kept(self):
		self.assertEqual(
			self.add("Work From Home\nOn Duty\nTraining"), "Work From Home\nOn Duty\nTraining\nTime Slip"
		)

	def test_it_is_added_once(self):
		self.assertEqual(self.add("On Duty\nTime Slip"), "On Duty\nTime Slip")


if __name__ == "__main__":
	unittest.main()
