"""Guards on the HR levers that created wrong attendance (S3 of the end-it plan).

15 September 2026, attendance-lost-ot-plan.md §S3 and the v3 evidence §8:
- a second Active Shift Assignment whose ROSTERED hours overlap the first was
  accepted (night 19:30-07:00 beside an early 06:00 shift passed the raw
  start/end check), and the bulk tool/hook could bypass the form;
- HR could flip log_type / shift / skip on a punch already inside an
  Attendance row (only `time` was locked), and skip a punch with no reason;
- a status-only edit on a submitted row kept auto_attendance=1, so the hourly
  job re-marked HR's fix an hour later;
- shift buffers longer than the shift itself, and the mode mix that pays a
  mid-day gap, were accepted silently, and end_time/buffers could change under
  unmarked punches;
- the hourly job took no per-employee lock while HR's master edit did.

Shift definitions are HR's: every guard here refuses or warns, never rewrites.

PYTHONPATH=. python3 hrms/tests/test_hr_lever_guards.py
"""

import ast
import json
import pathlib
import sys
import unittest
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.shift_assignment import shift_assignment as sa
from hrms.overrides import shift_assignment_hooks as hooks

HRMS = pathlib.Path(__file__).resolve().parent.parent
TOOL = HRMS / "hr/doctype/shift_assignment_tool/shift_assignment_tool.py"
DAY = date(2026, 9, 7)


def _t(h, m=0):
	return timedelta(hours=h, minutes=m)


# --- G1: two rostered shifts at the same hours ---------------------------------


class TestScheduledHoursOverlap(unittest.TestCase):
	"""Pure rule: two shifts as intervals on a 48-hour line, either shifted by a day."""

	def test_sequential_day_shifts_do_not_overlap(self):
		self.assertFalse(sa.scheduled_hours_overlap(_t(8), _t(13), _t(14), _t(18)))

	def test_touching_shifts_do_not_overlap(self):
		self.assertFalse(sa.scheduled_hours_overlap(_t(8), _t(13), _t(13), _t(18)))

	def test_a_night_shift_beside_a_day_shift_does_not_overlap(self):
		self.assertFalse(sa.scheduled_hours_overlap(_t(19, 30), _t(7), _t(8), _t(18)))

	def test_a_night_shift_running_into_the_next_morning_shift_overlaps(self):
		# 19:30 -> 07:00 still runs when a 06:00 shift starts the next day
		self.assertTrue(sa.scheduled_hours_overlap(_t(19, 30), _t(7), _t(6), _t(14)))
		self.assertTrue(sa.scheduled_hours_overlap(_t(6), _t(14), _t(19, 30), _t(7)))

	def test_two_day_shifts_at_the_same_hours_overlap(self):
		self.assertTrue(sa.scheduled_hours_overlap(_t(8), _t(18), _t(9), _t(17)))

	def test_time_objects_and_strings_are_accepted(self):
		self.assertTrue(sa.scheduled_hours_overlap(time(8), "18:00:00", time(9, 30), "17:00:00"))

	def test_the_stored_helper_uses_the_rule(self):
		rows = {
			"NIGHT": frappe._dict(start_time=_t(19, 30), end_time=_t(7)),
			"EARLY": frappe._dict(start_time=_t(6), end_time=_t(14)),
		}
		with patch.object(frappe.db, "get_value", side_effect=lambda dt, name, *a, **k: rows[name]):
			self.assertTrue(sa.has_overlapping_timings("NIGHT", "EARLY"))


class _Assignment(SimpleNamespace):
	def __init__(self, **kw):
		defaults = dict(
			name="SA-NEW",
			employee="HR-EMP-00014",
			shift_type="EARLY",
			start_date=date(2026, 9, 10),
			end_date=None,
			status="Active",
			docstatus=0,
			both_shifts_on_purpose=0,
			flags=frappe._dict(),
		)
		defaults.update(kw)
		super().__init__(**defaults)

	def get(self, key, default=None):
		return getattr(self, key, default)


EXISTING_NIGHT = [frappe._dict(name="SA-OLD", shift_type="NIGHT", docstatus=1, status="Active")]


class TestRefuseOverlappingAssignments(unittest.TestCase):
	def _run(self, doc, existing, overlap):
		with (
			patch.object(sa, "active_assignments_on", return_value=list(existing)),
			patch.object(sa, "has_overlapping_timings", return_value=overlap),
			patch.object(frappe.db, "get_single_value", return_value=1),
		):
			sa.refuse_overlapping_assignments(doc)

	def test_overlapping_hours_are_refused_even_when_multiple_shifts_are_allowed(self):
		with self.assertRaises(sa.OverlappingShiftError):
			self._run(_Assignment(), EXISTING_NIGHT, overlap=True)

	def test_sequential_hours_pass(self):
		self._run(_Assignment(), EXISTING_NIGHT, overlap=False)

	def test_hr_can_tick_both_shifts_on_purpose(self):
		self._run(_Assignment(both_shifts_on_purpose=1), EXISTING_NIGHT, overlap=True)

	def test_an_inactive_assignment_is_not_checked(self):
		self._run(_Assignment(status="Inactive"), EXISTING_NIGHT, overlap=True)

	def test_the_form_and_the_submit_hook_share_the_guard(self):
		for path in (sa.__file__, hooks.__file__):
			tree = ast.parse(pathlib.Path(path).read_text())
			fn_name = "validate_overlapping_shifts" if path == sa.__file__ else "close_superseded_assignments"
			fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name)
			names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
			self.assertIn("refuse_overlapping_assignments", names, path)

	def test_the_bulk_tool_offers_only_employees_the_rule_would_refuse(self):
		src = TOOL.read_text()
		self.assertIn("overlapping_shift_types", src)
		self.assertNotIn("Interval(hours=24)", src, "the tool must not keep its own raw-hours SQL")

	def test_overlapping_shift_types_lists_the_ones_the_rule_refuses(self):
		rows = [
			frappe._dict(name="EARLY", start_time=_t(6), end_time=_t(14)),
			frappe._dict(name="NIGHT", start_time=_t(19, 30), end_time=_t(7)),
			frappe._dict(name="PM", start_time=_t(14), end_time=_t(18)),
		]
		with patch.object(frappe, "get_all", return_value=rows):
			self.assertEqual(sa.overlapping_shift_types("NIGHT"), ["EARLY", "NIGHT"])


if __name__ == "__main__":
	unittest.main()
