"""The break grid's Duration column must stay derived, and the lying one gone.

`break_hours` is a Flexible-only input; Fixed breaks deduct their Start-End
window. The grid surfaced break_hours for BOTH types, so every Fixed row
showed a dead 0.00 while the deduction worked fine — reported as "break
duration tak reflect". The fix is a VIRTUAL `duration` field computed on read
from the same fields the deduction engine uses.

Three ways the fix can silently rot, each pinned:

  * `duration` becomes a stored column (is_virtual dropped) — it then goes
    stale under every write path that skips validate: the shadow sync inserts
    Shift Types with ignore_validate, and data import / db.set_value never
    ran it either;
  * `break_hours` regains in_list_view — the misleading 0.00 returns;
  * the property drifts from the engine's inputs — display and deduction
    fork, which is the drift class this repo keeps re-earning.

Structural pins are JSON/AST; the arithmetic runs against a frappe stub.
"""

import ast
import json
import os
import pathlib
import sys
import types
import unittest
from datetime import time
from unittest.mock import MagicMock

sys.path.insert(0, os.getcwd())

DOCTYPE_DIR = pathlib.Path(__file__).resolve().parent.parent / "hr" / "doctype" / "shift_break"


def _fields():
	return {f["fieldname"]: f for f in json.loads((DOCTYPE_DIR / "shift_break.json").read_text())["fields"]}


class TestShiftBreakSchema(unittest.TestCase):
	def test_duration_is_virtual_and_in_the_grid(self):
		field = _fields()["duration"]
		self.assertEqual(field.get("is_virtual"), 1, "duration became a stored column — it will go stale")
		self.assertEqual(field.get("in_list_view"), 1)
		self.assertEqual(field.get("read_only"), 1)

	def test_break_hours_stays_out_of_the_grid(self):
		self.assertFalse(
			_fields()["break_hours"].get("in_list_view"),
			"break_hours is back in the grid — every Fixed row will show a dead 0.00 again",
		)

	def test_property_reads_the_engine_inputs(self):
		tree = ast.parse((DOCTYPE_DIR / "shift_break.py").read_text())
		func = next(
			n
			for n in ast.walk(tree)
			if isinstance(n, ast.FunctionDef)
			and n.name == "duration"
			and any(getattr(d, "id", None) == "property" for d in n.decorator_list)
		)
		attrs = {n.attr for n in ast.walk(func) if isinstance(n, ast.Attribute)}
		self.assertLessEqual(
			{"start_time", "end_time", "break_hours", "break_type"},
			attrs,
			"the duration property no longer derives from the deduction engine's own inputs",
		)


class TestDurationArithmetic(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		for name in ("frappe", "frappe.utils", "frappe.model", "frappe.model.document"):
			if name not in sys.modules:
				mod = types.ModuleType(name)
				mod.__getattr__ = lambda attr: MagicMock()
				sys.modules[name] = mod
		sys.modules["frappe.model.document"].Document = object
		sys.modules["frappe.utils"].get_time = lambda v: (
			v if isinstance(v, time) else time.fromisoformat(str(v))
		)

		from hrms.hr.doctype.shift_break.shift_break import ShiftBreak

		# staticmethod: a bare function stored on the class would rebind as a
		# method and swallow the row argument as `self`
		cls.duration = staticmethod(ShiftBreak.duration.fget)

	def _row(self, **kw):
		defaults = {"break_type": "Fixed", "break_hours": None, "start_time": None, "end_time": None}
		return types.SimpleNamespace(**{**defaults, **kw})

	def test_fixed_window_yields_its_length(self):
		self.assertEqual(self.duration(self._row(start_time="12:00:00", end_time="13:00:00")), 1.0)
		self.assertEqual(self.duration(self._row(start_time="12:00:00", end_time="12:30:00")), 0.5)

	def test_flexible_yields_the_entered_hours(self):
		self.assertEqual(self.duration(self._row(break_type="Flexible", break_hours=1.5)), 1.5)

	def test_half_filled_rows_render_blank_not_broken(self):
		self.assertIsNone(self.duration(self._row(start_time="12:00:00")))
		self.assertIsNone(self.duration(self._row(start_time="13:00:00", end_time="12:00:00")))
		self.assertIsNone(self.duration(self._row(break_type="Flexible", break_hours=0)))


if __name__ == "__main__":
	unittest.main()
