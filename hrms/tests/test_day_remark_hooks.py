"""Every other event that changes a past day's evidence re-marks that day too.

The punch decision is wired in remote_checkin_request_hooks (test_day_remark).
The rest go through hrms.overrides.day_remark_hooks, one handler per event
shape, all calling the one shared hrms.utils.day_remark.remark_day_after_commit:

  * a punch added to a past day (late sync, ERP import, HR adding a tap) and a
    punch deleted: the day the punch belongs to;
  * a punch edited so its evidence changed (skip ticked or cleared, time, type or
    shift changed): the day before AND after the edit — a moved punch changes two;
  * a Leave Application or Attendance Request cancelled: every past day it held.

Plus the invariant over the punch events: event x prior day state x day type ->
the day row equals what the engine marks from scratch.

    PYTHONPATH=. python3 hrms/tests/test_day_remark_hooks.py
"""

import copy
import sys
import unittest
from datetime import date, datetime, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from test_day_remark import (
	DAY,
	DAY_TYPES,
	EMP,
	IN,
	NOW,
	OUT,
	PRIOR,
	Store,
	actual,
	engine_patches,
	oracle,
	stand_in_shift,
)

import frappe


def punch_doc(row, before=None, method=None):
	doc = SimpleNamespace(**dict(row))
	doc.doctype = "Employee Checkin"
	doc.get = lambda key, default=None: getattr(doc, key, default)
	doc.get_doc_before_save = lambda: before
	return doc


def queued_by(handler, doc, method=None):
	from hrms.overrides import day_remark_hooks as dh

	with patch.object(dh, "remark_day_after_commit") as remark:
		handler(doc, method)
	return [(c.args[0], c.args[1]) for c in remark.call_args_list]


class TestPunchEvents(unittest.TestCase):
	def _row(self, **extra):
		store = Store()
		return frappe._dict(store.punches[OUT], **extra)

	def test_a_punch_added_to_a_past_day_queues_its_shift_day(self):
		from hrms.overrides import day_remark_hooks as dh

		self.assertEqual(queued_by(dh.remark_punch_day, punch_doc(self._row()), "after_insert"), [(EMP, DAY)])

	def test_a_deleted_punch_queues_its_day(self):
		from hrms.overrides import day_remark_hooks as dh

		self.assertEqual(queued_by(dh.remark_punch_day, punch_doc(self._row()), "on_trash"), [(EMP, DAY)])

	def test_a_mirrored_punch_is_the_source_instance_business(self):
		from hrms.overrides import day_remark_hooks as dh

		doc = punch_doc(self._row(synced_from_instance="erp"))
		self.assertEqual(queued_by(dh.remark_punch_day, doc, "after_insert"), [])

	def test_a_save_that_changes_no_evidence_queues_nothing(self):
		from hrms.overrides import day_remark_hooks as dh

		row = self._row()
		self.assertEqual(queued_by(dh.remark_changed_punch_day, punch_doc(row, before=frappe._dict(row))), [])

	def test_the_insert_save_is_left_to_after_insert(self):
		from hrms.overrides import day_remark_hooks as dh

		self.assertEqual(queued_by(dh.remark_changed_punch_day, punch_doc(self._row(), before=None)), [])

	def test_ticking_skip_queues_the_day(self):
		from hrms.overrides import day_remark_hooks as dh

		row = self._row(skip_auto_attendance=1)
		before = frappe._dict(row, skip_auto_attendance=0)
		self.assertEqual(queued_by(dh.remark_changed_punch_day, punch_doc(row, before=before)), [(EMP, DAY)])

	def test_a_punch_moved_to_another_day_queues_both_days(self):
		from hrms.overrides import day_remark_hooks as dh

		row = self._row()
		moved = frappe._dict(
			row, time=datetime(2026, 9, 11, 16, 58, 32), shift_start=datetime(2026, 9, 11, 9, 0)
		)
		queued = queued_by(dh.remark_changed_punch_day, punch_doc(moved, before=frappe._dict(row)))
		self.assertEqual(sorted(queued), [(EMP, date(2026, 9, 11)), (EMP, DAY)])

	def test_a_failing_queue_never_undoes_the_save(self):
		from hrms.overrides import day_remark_hooks as dh

		with patch.object(dh, "remark_day_after_commit", side_effect=RuntimeError("no db")):
			dh.remark_punch_day(punch_doc(self._row()), "after_insert")


class TestRequestCancelled(unittest.TestCase):
	def _request(self, doctype, from_date, to_date):
		doc = SimpleNamespace(
			doctype=doctype, name="REQ-1", employee=EMP, from_date=from_date, to_date=to_date, docstatus=2
		)
		doc.get = lambda key, default=None: getattr(doc, key, default)
		return doc

	def test_every_day_a_cancelled_leave_held_is_queued(self):
		from hrms.overrides import day_remark_hooks as dh

		doc = self._request("Leave Application", "2026-09-10", "2026-09-12")
		self.assertEqual(
			queued_by(dh.remark_request_days, doc, "on_cancel"),
			[(EMP, date(2026, 9, 10)), (EMP, date(2026, 9, 11)), (EMP, date(2026, 9, 12))],
		)

	def test_a_cancelled_attendance_request_too(self):
		from hrms.overrides import day_remark_hooks as dh

		doc = self._request("Attendance Request", "2026-09-12", "2026-09-12")
		self.assertEqual(queued_by(dh.remark_request_days, doc, "on_cancel"), [(EMP, DAY)])

	def test_a_long_request_is_bounded(self):
		from hrms.overrides import day_remark_hooks as dh

		doc = self._request("Leave Application", "2026-01-01", "2026-12-31")
		self.assertEqual(len(queued_by(dh.remark_request_days, doc, "on_cancel")), dh.MAX_REQUEST_DAYS)


def _approved(store):
	for p in store.punches.values():
		p.update(remote_approval_status="Approved", requires_remote_approval=0)


def add_out(store):
	"""OUT arrives after the day was marked from the IN (late sync / ERP import / HR add)."""
	from hrms.overrides import day_remark_hooks as dh

	row = store.punches[OUT]
	return dh.remark_punch_day, punch_doc(row), "after_insert"


def skip_out(store):
	from hrms.overrides import day_remark_hooks as dh

	before = frappe._dict(store.punches[OUT])
	store.punches[OUT].skip_auto_attendance = 1
	return dh.remark_changed_punch_day, punch_doc(store.punches[OUT], before=before), "on_update"


def unskip_out(store):
	from hrms.overrides import day_remark_hooks as dh

	before = frappe._dict(store.punches[OUT], skip_auto_attendance=1)
	store.punches[OUT].skip_auto_attendance = 0
	return dh.remark_changed_punch_day, punch_doc(store.punches[OUT], before=before), "on_update"


def delete_in(store):
	from hrms.overrides import day_remark_hooks as dh

	row = store.punches.pop(IN)
	return dh.remark_punch_day, punch_doc(row), "on_trash"


EVENTS = {
	"OUT added": add_out,
	"OUT skipped": skip_out,
	"OUT un-skipped": unskip_out,
	"IN deleted": delete_in,
}


def event_and_commit(store, day_type, event):
	from hrms.utils import attendance_recovery as rec
	from hrms.utils import day_remark as dr

	shift = stand_in_shift()
	callbacks = []
	db = MagicMock()
	db.exists.return_value = None
	db.after_commit.add.side_effect = callbacks.append

	def enqueue(method, **kwargs):
		return dr.remark_day(kwargs["employee"], kwargs["day"], kwargs.get("reason"))

	patches = [
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_all", side_effect=store.get_all),
		patch.object(frappe, "get_doc", side_effect=lambda doctype, *a, **k: shift),
		patch.object(frappe, "enqueue", side_effect=enqueue, create=True),
		patch.object(dr, "employee_now", return_value=NOW),
		patch.object(dr, "lock_employee_row"),
		patch.object(rec, "_day_protection", return_value=None),
		*engine_patches(store, day_type, shift),
	]
	for p in patches:
		p.start()
	try:
		handler, doc, method = event(store)
		handler(doc, method)
		for callback in callbacks:
			callback()
	finally:
		for p in reversed(patches):
			p.stop()
	return callbacks


class TestTheDayAfterAPunchEventIsWhatTheEngineMarksFromScratch(unittest.TestCase):
	def test_matrix(self):
		for day_label, day_type in DAY_TYPES.items():
			for prior_label, seed in PRIOR.items():
				for event_label, event in EVENTS.items():
					with self.subTest(day=day_label, prior=prior_label, event=event_label):
						store = Store()
						_approved(store)
						if event is unskip_out:
							store.punches[OUT].skip_auto_attendance = 1
						seed(store)
						callbacks = event_and_commit(store, day_type, event)
						self.assertTrue(callbacks, "the event asked for no re-mark after commit")
						self.assertEqual(actual(store), oracle(store, day_type))


if __name__ == "__main__":
	unittest.main()
