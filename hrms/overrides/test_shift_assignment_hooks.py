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
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.overrides import shift_assignment_hooks as hooks
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
			patch.object(hooks, "refuse_overlapping_assignments") as refuse,
		):
			close_superseded_assignments(doc)
		# The overlap rule runs AFTER the superseded rows are ended (S3 G1).
		if doc.status == "Active":
			refuse.assert_called_once_with(doc)
		else:
			refuse.assert_not_called()
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
			patch.object(hooks, "refuse_overlapping_assignments"),
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


class TestAHandMadeShiftClearsTheDayMarks(unittest.TestCase):
	"""Owner, 7 Oct 2026: a shift HR submits in the Desk form over a day marked Off is the newer
	word, so the mark goes. Shifts made in code (roster splits, schedules, the bulk tool) go
	through create_shift_assignment, which tags them to keep the marks."""

	def _run(self, doc):
		with patch.object(hooks, "_delete_day_markers") as clear:
			hooks.clear_day_markers_on_submit(doc)
		return clear

	def test_the_marks_go_whoever_submitted_the_shift(self):
		# review of de84475ac: an approver with no HR role approving a Shift Request submits the
		# shift; the submit already passed their checks, so the mark is removed without a second
		# Roster Day permission check that would refuse the whole approval
		doc = _doc(start_date=date(2026, 10, 8), end_date=date(2026, 10, 8), flags=SimpleNamespace())
		with (
			patch.object(frappe.db, "table_exists", return_value=True, create=True),
			patch.object(frappe, "get_all", return_value=["EMP-2026-10-08"]),
			patch.object(frappe, "delete_doc") as delete,
			patch("hrms.utils.ot_calculation.forget_rostered_day_types"),
		):
			hooks.clear_day_markers_on_submit(doc)
		delete.assert_called_once_with("Roster Day", "EMP-2026-10-08", ignore_permissions=True)

	def test_the_roster_api_is_imported_only_when_the_hook_runs(self):
		source = pathlib.Path(hooks.__file__).read_text()
		self.assertNotIn("\nfrom hrms.api.roster import", source)

	def test_a_desk_submit_clears_the_marks_in_its_dates(self):
		doc = _doc(start_date=date(2026, 10, 8), end_date=date(2026, 10, 10), flags=SimpleNamespace())
		self._run(doc).assert_called_once_with("HR-EMP-00014", date(2026, 10, 8), date(2026, 10, 10))

	def test_an_open_ended_desk_submit_clears_from_its_start(self):
		doc = _doc(start_date=date(2026, 10, 8), end_date=None, flags=SimpleNamespace())
		self._run(doc).assert_called_once_with("HR-EMP-00014", date(2026, 10, 8), None)

	def test_a_shift_made_in_code_keeps_the_marks(self):
		doc = _doc(flags=SimpleNamespace(keep_day_markers=True))
		self._run(doc).assert_not_called()

	def test_an_inactive_shift_keeps_the_marks(self):
		doc = _doc(status="Inactive", flags=SimpleNamespace())
		self._run(doc).assert_not_called()

	def test_the_hook_is_wired_on_submit(self):
		hooks_py = (pathlib.Path(hooks.__file__).resolve().parents[1] / "hooks.py").read_text()
		block = hooks_py[hooks_py.index('"Shift Assignment": {') :]
		block = block[: block.index("},")]
		self.assertIn("hrms.overrides.shift_assignment_hooks.clear_day_markers_on_submit", block)

	def test_a_mirrored_shift_keeps_the_marks(self):
		# a row copied from the other site is that site's word, not HR's here
		doc = _doc(flags=SimpleNamespace(), synced_from_instance="verifica")
		self._run(doc).assert_not_called()

	def test_every_shift_made_in_code_is_tagged_to_keep_the_marks(self):
		# review of de84475ac: the shift rules create OPEN-ENDED shifts, so an untagged one
		# would wipe every future mark of that person; the Fix-a-day tool re-creates a shift
		# as a repair. An approved Shift Request is a person's decision and is left untagged.
		root = pathlib.Path(hooks.__file__).resolve().parents[1]
		for path, creator in (
			("hr/shift_rules.py", "def _create_assignment("),
			("api/attendance_master_edit.py", "def _submit_assignment("),
		):
			body = (root / path).read_text()
			body = body[body.index(creator) :]
			self.assertIn("flags.keep_day_markers = True", body[: body.index(".submit()")], path)

	def test_no_new_shift_creator_can_forget_the_tag(self):
		# the tag is opt-out: a creator that forgets it wipes day marks. Every place that builds a
		# Shift Assignment must be tagged here or named below as a person's decision.
		import re

		root = pathlib.Path(hooks.__file__).resolve().parents[1]
		tagged = {
			"hr/doctype/shift_assignment_tool/shift_assignment_tool.py",
			"hr/shift_rules.py",
			"api/attendance_master_edit.py",
		}
		a_persons_decision = {
			"hr/doctype/shift_request/shift_request.py",
			"hr/doctype/shift_swap_request/shift_swap_request.py",
		}
		creators = set()
		for path in root.rglob("*.py"):
			rel = path.relative_to(root).as_posix()
			if "/test_" in rel or rel.startswith(("tests/", "patches/")) or "/probes/" in rel:
				continue
			text = path.read_text()
			if re.search(
				r'new_doc\("Shift Assignment"\)|get_doc\(\s*\{\s*"doctype": "Shift Assignment"', text
			) or ("copy_doc(assignment)" in text and "Shift Assignment" in text):
				creators.add(rel)
		creators.discard("api/roster.py")  # its "doctype" dict is a filter, not a document
		self.assertEqual(creators, tagged | a_persons_decision)
		for rel in tagged:
			self.assertIn("keep_day_markers = True", (root / rel).read_text(), rel)

	def test_create_shift_assignment_tags_its_shifts_to_keep_the_marks(self):
		from hrms.hr.doctype.shift_assignment_tool import shift_assignment_tool as tool

		source = pathlib.Path(tool.__file__).read_text()
		body = source[source.index("def create_shift_assignment(") :]
		self.assertIn("assignment.flags.keep_day_markers = True", body[: body.index("assignment.submit()")])


if __name__ == "__main__":
	unittest.main()
