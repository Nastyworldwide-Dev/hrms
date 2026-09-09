"""A new open-ended Shift Assignment ends the ones it supersedes.

PYTHONPATH=. python3 hrms/overrides/test_shift_assignment_hooks.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.overrides.shift_assignment_hooks import close_superseded_assignments

MODULE = pathlib.Path(__file__).resolve().parent / "shift_assignment_hooks.py"


def _doc(**kw):
	defaults = dict(
		name="SA-NEW",
		employee="HR-EMP-00014",
		shift_type="10AM-7PM",
		start_date=date(2026, 9, 1),
		end_date=None,
		status="Active",
	)
	defaults.update(kw)
	return SimpleNamespace(**defaults)


OLD_NIGHT = frappe._dict(name="SA-OLD", shift_type="7PM-3:30AM", start_date=date(2026, 6, 1), end_date=None)


class TestClose(unittest.TestCase):
	def _run(self, doc, existing):
		with (
			patch.object(frappe, "get_all", return_value=list(existing)),
			patch.object(frappe.db, "set_value") as set_value,
			patch.object(frappe, "get_doc", return_value=MagicMock()) as get_doc,
		):
			close_superseded_assignments(doc)
		return set_value, get_doc

	def test_the_superseded_night_shift_is_ended_the_day_before(self):
		set_value, get_doc = self._run(_doc(), [OLD_NIGHT])
		set_value.assert_called_once_with("Shift Assignment", "SA-OLD", "end_date", date(2026, 8, 31))
		get_doc.return_value.add_comment.assert_called_once()

	def test_a_dated_assignment_ends_nothing(self):
		set_value, _ = self._run(_doc(end_date=date(2026, 9, 30)), [OLD_NIGHT])
		set_value.assert_not_called()

	def test_an_inactive_assignment_ends_nothing(self):
		set_value, _ = self._run(_doc(status="Inactive"), [OLD_NIGHT])
		set_value.assert_not_called()

	def test_mirrored_rows_are_left_to_their_source(self):
		with (
			patch.object(frappe, "get_all", return_value=[]) as get_all,
			patch.object(frappe.db, "set_value"),
		):
			close_superseded_assignments(_doc())
		self.assertEqual(get_all.call_args.kwargs["filters"]["synced_from_instance"], ("is", "not set"))

	def test_it_is_the_shared_rule_that_decides(self):
		tree = ast.parse(MODULE.read_text())
		fn = next(
			n
			for n in ast.walk(tree)
			if isinstance(n, ast.FunctionDef) and n.name == "close_superseded_assignments"
		)
		self.assertIn("superseded_assignments", {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)})


if __name__ == "__main__":
	unittest.main()
