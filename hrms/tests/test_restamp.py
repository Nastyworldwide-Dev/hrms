"""The roster is the source of the shift stamp; the stamp is a cache.

A Shift Assignment change used to re-stamp nothing: a day worker's 24 Aug
02:00 OUT stamped on the stray 19:30-03:30 night assignment kept
`shift_start = 23 Aug 19:30` for ever, so Fix Day opened 23 Aug for a 24 Aug
row (audit E §5, H3). `hrms.utils.restamp` re-runs the tap-time resolution
over the unlinked punches of a range and re-marks every day touched; the
Shift Assignment hooks queue it whenever the roster changes.

Stub-only, like test_employee_checkin_override_restamp.py.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_restamp.py
"""

import ast
import datetime as dt
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.overrides import shift_assignment_hooks as hooks
from hrms.utils import restamp as mod

HRMS = pathlib.Path(__file__).resolve().parents[1]
EMP = "HR-EMP-00014"
OUT_TIME = dt.datetime(2026, 8, 24, 2, 0)
NIGHT_START = dt.datetime(2026, 8, 23, 19, 30)
NIGHT_END = dt.datetime(2026, 8, 24, 3, 30)
DAY_START = dt.datetime(2026, 8, 24, 9, 0)
DAY_END = dt.datetime(2026, 8, 24, 18, 0)


def _row(**extra):
	row = frappe._dict(
		name="CK-OUT",
		time=OUT_TIME,
		log_type="OUT",
		attendance=None,
		synced_from_instance=None,
		shift="7PM-3:30AM",
		shift_start=NIGHT_START,
		shift_end=NIGHT_END,
		offshift=0,
	)
	row.update(extra)
	return row


class _Punch(SimpleNamespace):
	"""Stand-in for the loaded Employee Checkin: fetch_shift re-stamps onto the day shift."""

	def fetch_shift(self):
		self.shift = "9AM-6PM"
		self.shift_start = DAY_START
		self.shift_end = DAY_END
		self.shift_actual_start = DAY_START - dt.timedelta(hours=1)
		self.shift_actual_end = DAY_END + dt.timedelta(hours=1)
		self.overtime_type = None
		self.offshift = 0


class _OffShiftPunch(_Punch):
	"""The verifier's probe: the night assignment is cancelled and nothing else
	covers 02:00, so fetch_shift on a LOADED doc clears shift/offshift only and
	leaves shift_start/shift_end/shift_actual_* as they were."""

	def fetch_shift(self):
		self.shift = None
		self.offshift = 1
		self.overtime_type = None


def _punch(row, cls=_Punch):
	return cls(
		**row, shift_actual_start=None, shift_actual_end=None, overtime_type=None, flags=SimpleNamespace()
	)


class TestRestamp(unittest.TestCase):
	def _run(self, rows, cls=_Punch, **kw):
		db = MagicMock()
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", return_value=rows),
			patch.object(
				frappe,
				"get_doc",
				side_effect=lambda _dt, name: _punch(next(r for r in rows if r.name == name), cls),
			),
			patch.object(mod, "remark_day_after_commit", return_value=True) as remark,
		):
			result = mod.restamp(EMP, dt.date(2026, 8, 24), dt.date(2026, 8, 24), reason="test", **kw)
		return result, db, remark

	def test_a_night_stamped_24_aug_out_moves_to_the_day_shift_and_both_days_are_re_marked(self):
		result, db, remark = self._run([_row()], dry_run=False)
		self.assertTrue(result["applied"])
		self.assertEqual(len(result["planned"]), 1)
		plan = result["planned"][0]
		self.assertEqual(plan["name"], "CK-OUT")
		self.assertEqual(plan["old"]["shift"], "7PM-3:30AM")
		self.assertEqual(plan["new"]["shift"], "9AM-6PM")
		self.assertEqual(str(plan["old"]["shift_start"]), str(NIGHT_START))
		self.assertEqual(str(plan["new"]["shift_start"]), str(DAY_START))
		# the writer is hook-free and refuses a punch linked or mirrored meanwhile
		db.set_value.assert_called_once()
		args = db.set_value.call_args.args
		self.assertEqual(args[0], "Employee Checkin")
		self.assertEqual(args[1]["name"], "CK-OUT")
		self.assertEqual(args[1]["attendance"], ("is", "not set"))
		self.assertEqual(args[1]["synced_from_instance"], ("is", "not set"))
		self.assertEqual(args[2]["shift"], "9AM-6PM")
		self.assertEqual(args[2]["shift_start"], DAY_START)
		self.assertEqual(args[2]["offshift"], 0)
		# the day it left (23 Aug) and the day it joined (24 Aug), oldest first
		self.assertEqual(result["days"], ["2026-08-23", "2026-08-24"])
		self.assertEqual(
			[(c.args[0], str(c.args[1])) for c in remark.call_args_list],
			[(EMP, "2026-08-23"), (EMP, "2026-08-24")],
		)

	def test_a_punch_no_shift_covers_any_more_is_cleared_whole_and_dated_by_its_clock(self):
		result, db, remark = self._run([_row()], cls=_OffShiftPunch, dry_run=False)
		plan = result["planned"][0]
		self.assertIsNone(plan["new"]["shift"])
		self.assertIsNone(plan["new"]["shift_start"])
		self.assertEqual(plan["new"]["offshift"], 1)
		written = db.set_value.call_args.args[2]
		for field in (
			"shift",
			"shift_start",
			"shift_end",
			"shift_actual_start",
			"shift_actual_end",
			"overtime_type",
		):
			self.assertIsNone(written[field], field)
		self.assertEqual(written["offshift"], 1)
		self.assertEqual(result["days"], ["2026-08-23", "2026-08-24"])
		self.assertEqual([str(c.args[1]) for c in remark.call_args_list], ["2026-08-23", "2026-08-24"])

	def test_a_linked_punch_the_roster_now_places_elsewhere_is_re_stamped_and_released(self):
		result, db, remark = self._run([_row(attendance="HR-ATT-1")], dry_run=False)
		self.assertEqual([p["name"] for p in result["planned"]], ["CK-OUT"])
		self.assertEqual(result["released"], ["CK-OUT"])
		db.set_value.assert_called_once()
		args = db.set_value.call_args.args
		self.assertEqual(args[1]["name"], "CK-OUT")
		self.assertEqual(args[1]["synced_from_instance"], ("is", "not set"))
		self.assertEqual(args[1]["attendance"], "HR-ATT-1", "releases exactly the link it saw")
		self.assertEqual(args[2]["shift"], "9AM-6PM")
		self.assertIsNone(args[2]["attendance"])
		self.assertEqual([str(c.args[1]) for c in remark.call_args_list], ["2026-08-23", "2026-08-24"])

	def test_a_dry_run_plans_and_writes_nothing(self):
		result, db, remark = self._run([_row()])
		self.assertFalse(result["applied"])
		self.assertEqual(len(result["planned"]), 1)
		self.assertEqual(result["days"], ["2026-08-23", "2026-08-24"])
		db.set_value.assert_not_called()
		remark.assert_not_called()

	def test_a_linked_punch_the_roster_still_places_the_same_way_keeps_its_link(self):
		row = _row(attendance="HR-ATT-1", shift="9AM-6PM", shift_start=DAY_START, shift_end=DAY_END)
		result, db, remark = self._run([row], dry_run=False)
		self.assertEqual(result["planned"], [])
		self.assertEqual(result["released"], [])
		db.set_value.assert_not_called()
		remark.assert_not_called()

	def test_a_punch_the_roster_still_places_the_same_way_is_untouched(self):
		row = _row(shift="9AM-6PM", shift_start=DAY_START, shift_end=DAY_END)
		result, db, remark = self._run([row], dry_run=False)
		self.assertEqual(result["planned"], [])
		self.assertEqual(result["days"], [])
		db.set_value.assert_not_called()
		remark.assert_not_called()


class TestShiftAssignmentQueuesOneJob(unittest.TestCase):
	def _submit(self, doc, method="on_submit"):
		db = MagicMock()
		with patch.object(frappe, "db", db), patch.object(frappe, "enqueue") as enqueue:
			hooks.queue_restamp(doc, method)
			db.after_commit.add.assert_called_once()
			db.after_commit.add.call_args.args[0]()
		return enqueue

	def test_on_submit_enqueues_exactly_one_deduplicated_job_over_the_assignments_range(self):
		doc = SimpleNamespace(
			name="SA-NEW",
			employee=EMP,
			shift_type="9AM-6PM",
			start_date=dt.date(2026, 8, 20),
			end_date=dt.date(2026, 8, 31),
			synced_from_instance=None,
			modified=dt.datetime(2026, 9, 21, 10, 0),
		)
		enqueue = self._submit(doc)
		enqueue.assert_called_once()
		kw = enqueue.call_args.kwargs
		self.assertEqual(enqueue.call_args.args[0], "hrms.utils.restamp.restamp")
		self.assertEqual(kw["job_id"], f"restamp::{EMP}::2026-08-20::2026-08-31::2026-09-21 10:00:00")
		self.assertTrue(kw["deduplicate"])
		self.assertEqual((kw["employee"], kw["from_date"], kw["to_date"]), (EMP, "2026-08-20", "2026-08-31"))
		self.assertFalse(kw["dry_run"])
		self.assertIn("SA-NEW", kw["reason"])
		self.assertIn("on_submit", kw["reason"])

	def test_an_open_ended_assignment_runs_to_today(self):
		doc = SimpleNamespace(
			name="SA-OPEN",
			employee=EMP,
			start_date=dt.date(2026, 9, 1),
			end_date=None,
			synced_from_instance=None,
		)
		with patch.object(hooks, "employee_now", return_value=dt.datetime(2026, 9, 21, 10, 0)):
			enqueue = self._submit(doc, "on_cancel")
		self.assertEqual(enqueue.call_args.kwargs["to_date"], "2026-09-21")

	def test_an_end_date_edit_reaches_the_punches_stamped_after_the_new_end(self):
		# the stray night assignment ran open; HR ends it on 15 Aug — the 16 Aug..today
		# punches are the ones stamped from it while it was still open
		doc = SimpleNamespace(
			name="SA-NIGHT",
			employee=EMP,
			start_date=dt.date(2026, 8, 1),
			end_date=dt.date(2026, 8, 15),
			synced_from_instance=None,
		)
		with patch.object(hooks, "employee_now", return_value=dt.datetime(2026, 9, 21, 10, 0)):
			enqueue = self._submit(doc, "on_update_after_submit")
		kw = enqueue.call_args.kwargs
		self.assertEqual((kw["from_date"], kw["to_date"]), ("2026-08-01", "2026-09-21"))

	def test_two_roster_changes_the_same_day_each_run_their_own_job(self):
		# deduplicate drops a job whose twin has STARTED; the change moment keeps them apart
		ids = []
		for minute in (10, 40):
			doc = SimpleNamespace(
				name="SA-NIGHT",
				employee=EMP,
				start_date=dt.date(2026, 8, 1),
				end_date=dt.date(2026, 8, 15),
				synced_from_instance=None,
				modified=dt.datetime(2026, 9, 21, 9, minute),
			)
			with patch.object(hooks, "employee_now", return_value=dt.datetime(2026, 9, 21, 10, 0)):
				ids.append(self._submit(doc, "on_update_after_submit").call_args.kwargs["job_id"])
		self.assertNotEqual(ids[0], ids[1])

	def test_a_mirrored_assignment_queues_nothing(self):
		doc = SimpleNamespace(
			name="SA-MIRROR",
			employee=EMP,
			start_date=dt.date(2026, 9, 1),
			end_date=None,
			synced_from_instance="erp",
		)
		db = MagicMock()
		with patch.object(frappe, "db", db):
			hooks.queue_restamp(doc, "on_submit")
		db.after_commit.add.assert_not_called()

	def test_hooks_py_wires_submit_cancel_and_end_date_edits(self):
		tree = ast.parse((HRMS / "hooks.py").read_text(encoding="utf-8"))
		doc_events = next(
			node.value
			for node in ast.walk(tree)
			if isinstance(node, ast.Assign)
			and any(getattr(t, "id", None) == "doc_events" for t in node.targets)
		)
		entry = next(
			ast.literal_eval(value)
			for key, value in zip(doc_events.keys, doc_events.values, strict=True)
			if isinstance(key, ast.Constant) and key.value == "Shift Assignment"
		)
		handler = "hrms.overrides.shift_assignment_hooks.queue_restamp"
		for event in ("on_submit", "on_cancel", "on_update_after_submit"):
			handlers = entry.get(event, [])
			handlers = [handlers] if isinstance(handlers, str) else list(handlers)
			self.assertIn(handler, handlers, event)


class TestPreviewIsHrOnly(unittest.TestCase):
	def test_preview_refuses_a_non_hr_user(self):
		def only_for(roles):
			raise frappe.PermissionError("not you")

		with patch.object(frappe, "only_for", only_for), patch.object(mod, "restamp") as run:
			with self.assertRaises(frappe.PermissionError):
				mod.preview(EMP, "2026-08-24", "2026-08-24")
		run.assert_not_called()

	def test_preview_is_a_dry_run(self):
		with (
			patch.object(frappe, "only_for", lambda roles: None),
			patch.object(mod, "_ensure_company_visible", lambda employee: None),
			patch.object(mod, "restamp") as run,
		):
			mod.preview(EMP, "2026-08-24", "2026-08-24")
		self.assertTrue(run.call_args.kwargs["dry_run"])

	def test_a_fenced_hr_user_cannot_preview_another_companys_employee(self):
		"""Role membership is not the company fence (roster.py is the pattern)."""
		import hrms.overrides.company_scope as scope

		db = SimpleNamespace(get_value=lambda *a, **k: "Company B")
		with (
			patch.object(frappe, "only_for", lambda roles: None),
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", SimpleNamespace(user="hr-a@x.com")),
			patch.object(scope, "company_visible", lambda company, **k: company != "Company B"),
			patch.object(mod, "restamp") as run,
		):
			with self.assertRaises(frappe.PermissionError):
				mod.preview(EMP, "2026-08-24", "2026-08-24")
		run.assert_not_called()


if __name__ == "__main__":
	unittest.main()
