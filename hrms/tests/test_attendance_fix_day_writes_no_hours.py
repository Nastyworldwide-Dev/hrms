"""The Fix Day screen never writes a result — only evidence.

Owner rule (Nabil, 16 Sep 2026): "HR corrects the EVIDENCE, never the result."
The reason is written in the defect history: every earlier attendance defect in
this app came from a SECOND place doing the same arithmetic as the engine —
typed corrections that kept inflated `working_hours` (test_typed_hours_drift),
an OT figure repaired in one path and not another.

So `hrms.api.attendance_fix_day` may read hours and overtime to show HR the day
before and after, and it may never write them. Checked in the syntax tree
rather than by grepping, so a write cannot hide behind a variable name or a
formatted string: every call that writes is found, and the forbidden field
names are looked for inside it.

    PYTHONPATH=. python3 hrms/tests/test_attendance_fix_day_writes_no_hours.py
"""

import ast
import pathlib
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "api/attendance_fix_day.py"

#: Anything that puts a value into the database.
WRITE_CALLS = {"set_value", "db_set", "insert", "save", "submit", "update", "sql", "set", "bulk_update"}
#: The result fields. The engine owns every one of them.
RESULT_FIELDS = {
	"working_hours",
	"ot_hours",
	"ot_rate_weighted_hours",
	"ot_rate_bands",
	"actual_overtime_duration",
	"standard_working_hours",
}


def _called_name(node):
	func = node.func
	if isinstance(func, ast.Attribute):
		return func.attr
	if isinstance(func, ast.Name):
		return func.id
	return None


def _strings(node):
	return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


class TestFixDayWritesNoResult(unittest.TestCase):
	def setUp(self):
		self.tree = ast.parse(MODULE.read_text(encoding="utf-8"))

	def test_no_write_call_carries_a_result_field(self):
		offences = []
		for node in ast.walk(self.tree):
			if not isinstance(node, ast.Call):
				continue
			name = _called_name(node)
			if name not in WRITE_CALLS:
				continue
			named = _strings(node) & RESULT_FIELDS
			if named:
				offences.append(f"line {node.lineno}: {name}() names {sorted(named)}")
		self.assertEqual(offences, [], "the Fix Day screen must never write hours or overtime")

	def test_no_result_field_is_assigned_as_an_attribute(self):
		"""`doc.working_hours = x` is a write too, even without a call."""
		offences = []
		for node in ast.walk(self.tree):
			targets = []
			if isinstance(node, ast.Assign):
				targets = node.targets
			elif isinstance(node, ast.AugAssign | ast.AnnAssign):
				targets = [node.target]
			for target in targets:
				if isinstance(target, ast.Attribute) and target.attr in RESULT_FIELDS:
					offences.append(f"line {node.lineno}: {target.attr} assigned")
		self.assertEqual(offences, [])

	def test_the_day_is_rebuilt_through_the_one_engine(self):
		"""Not writing the result is only half of it: the result must still be
		recomputed, by the shared re-mark and by nothing local."""
		source = MODULE.read_text(encoding="utf-8")
		self.assertIn("from hrms.utils.day_remark import remark_day", source)
		# Amended 17 Sep 2026: the call gained `hr_asked=True`. HR pressing a
		# button on one day is not the nightly job, and the "a person keyed this
		# row" hold would otherwise leave the day exactly as HR found it. Still
		# ONE engine and still no local maths, which is what this test is for.
		self.assertIn("remark_day(employee, day, reason, hr_asked=True, requests_ok=requests_ok)", source)

	def test_reading_the_result_for_the_screen_is_still_allowed(self):
		"""The guard above must not be satisfied by showing HR nothing: the
		before/after HR reads is exactly these fields, read."""
		source = MODULE.read_text(encoding="utf-8")
		self.assertIn('row.get("working_hours")', source)
		self.assertIn('row.get("ot_hours")', source)


if __name__ == "__main__":
	unittest.main()
