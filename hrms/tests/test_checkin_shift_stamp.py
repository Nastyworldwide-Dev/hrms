"""Every shift a punch is given carries the shift's overtime type with it.

fetch_shift has four ways of deciding which shift a punch belongs to: the
upstream window, a check-out closing its own session, an early arrival
attaching to the shift it precedes, and the multi-assignment resolver. Three of
them were written by hand and only upstream copied `overtime_type`.

That field is not decoration. The hourly job takes the whole day's overtime
type from the FIRST eligible punch (shift_type.get_attendance), so one punch
stamped with overtime_type=None makes the entire day ineligible for overtime —
no error, no log, the hours simply never reach the Overtime Slip. An early
arriver was the worst case: arriving early is what made his punch first.

So the invariant is structural, not per-case: no path may stamp a shift by
hand. They all go through _stamp_shift, and _stamp_shift writes overtime_type.

AST only — no bench required.
"""

import ast
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent
SOURCE = HRMS / "overrides" / "employee_checkin_override.py"
HOOKS = HRMS / "overrides" / "remote_checkin_request_hooks.py"

# The stamp is a set: a punch that carries shift_start without the shift's
# overtime type is a punch the hourly job will price wrongly.
STAMPED = {
	"shift",
	"shift_start",
	"shift_end",
	"shift_actual_start",
	"shift_actual_end",
	"overtime_type",
	"offshift",
}


def _class(tree, name):
	for node in ast.walk(tree):
		if isinstance(node, ast.ClassDef) and node.name == name:
			return node
	raise AssertionError(f"class {name} not found")


def _method(tree, class_name, name):
	for node in ast.walk(_class(tree, class_name)):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{class_name}.{name} not found")


def _self_attrs_assigned(node) -> set[str]:
	found = set()
	for sub in ast.walk(node):
		if not isinstance(sub, ast.Assign):
			continue
		for target in sub.targets:
			if (
				isinstance(target, ast.Attribute)
				and isinstance(target.value, ast.Name)
				and target.value.id == "self"
			):
				found.add(target.attr)
	return found


class TestOneStampForEveryPath(unittest.TestCase):
	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())

	def test_the_stamp_writes_the_overtime_type(self):
		stamp = _method(self.tree, "CustomEmployeeCheckin", "_stamp_shift")
		self.assertEqual(
			STAMPED,
			_self_attrs_assigned(stamp),
			"_stamp_shift must write exactly the shift stamp, overtime_type included — "
			"the hourly job reads the day's overtime type off the first punch",
		)

	def test_the_stamp_refuses_a_punch_already_linked_to_attendance(self):
		stamp = _method(self.tree, "CustomEmployeeCheckin", "_stamp_shift")
		guarded = any(
			isinstance(node, ast.If)
			and isinstance(node.test, ast.Attribute)
			and node.test.attr == "attendance"
			for node in ast.walk(stamp)
		)
		self.assertTrue(
			guarded,
			"_stamp_shift must return early when self.attendance is set — a linked "
			"punch is never re-derived (bulk_fetch_shift calls fetch_shift on them)",
		)

	def test_no_resolution_path_stamps_a_shift_by_hand(self):
		for name in ("fetch_shift", "_attach_early_arrival", "_close_open_session"):
			method = _method(self.tree, "CustomEmployeeCheckin", name)
			written = _self_attrs_assigned(method)
			# clearing to off-shift is not a stamp
			leaked = written & (STAMPED - {"shift", "offshift"})
			self.assertEqual(
				set(),
				leaked,
				f"{name} assigns {sorted(leaked)} directly — route it through "
				"_stamp_shift or the next field added to the stamp will be missed here",
			)


class TestTheLateCheckoutRepairRebindsTheWholeStamp(unittest.TestCase):
	"""reprocess_late_checkout_attendance copies the IN's shift onto the OUT by
	raw db.set_value. It is the fourth writer of a shift stamp, and it is the
	one _stamp_shift cannot reach."""

	def test_the_rebound_fields_include_the_overtime_type(self):
		tree = ast.parse(HOOKS.read_text())
		for node in ast.walk(tree):
			if not isinstance(node, ast.DictComp):
				continue
			fields = {
				elt.value
				for gen in node.generators
				if isinstance(gen.iter, ast.Tuple)
				for elt in gen.iter.elts
				if isinstance(elt, ast.Constant)
			}
			if "shift_actual_start" in fields:
				self.assertIn(
					"overtime_type",
					fields,
					"the OUT is rebound to its IN's shift without the overtime type — "
					"the day's overtime disappears when the OUT is read first",
				)
				return
		raise AssertionError("the shift-rebinding comprehension is gone — re-point this test")
