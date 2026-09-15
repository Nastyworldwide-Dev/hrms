"""Existing Compensatory Leave Requests get the decision they were already given.

Nabil, 15 Sep 2026: "yes add that reject button". Comp leave gained a `status`
field. Every row written before it has none, and the new controller reads it:

* on_cancel reverses the Leave Allocation days only when status is Approved —
  an old approved request left undecided would cancel WITHOUT taking its days
  back, a silent stale balance;
* on_submit refuses anything that is not Approved or Rejected.

The trap: frappe's schema sync adds the column with `DEFAULT 'Open'`
(frappe/database/schema.py, DbColumn.get_definition), and MariaDB fills existing
rows with that default. So an old SUBMITTED request reads "Open", not NULL, and
a NULL-only backfill would miss every one of them. A submitted "Open" row cannot
exist under the new controller, so mapping it to Approved is safe.

Mapping (what already happened, not a guess):

    submitted (1), status NULL / "" / Open  -> Approved  submit WAS approving
    draft (0),     status NULL / ""         -> Open      nobody decided yet
    cancelled (2)                           -> untouched out of play

Bench-free:  PYTHONPATH=. python3 hrms/tests/test_backfill_comp_leave_decision_status.py
"""

import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.patches.v16_0 import backfill_comp_leave_decision_status as patch_module

D = "Compensatory Leave Request"


class TestTheDecisionForEachRow(unittest.TestCase):
	def test_a_submitted_request_was_approved(self):
		for status in (None, "", "Open"):
			with self.subTest(status=status):
				self.assertEqual(patch_module.decision_for(1, status), "Approved")

	def test_a_draft_without_a_status_is_open(self):
		for status in (None, ""):
			with self.subTest(status=status):
				self.assertEqual(patch_module.decision_for(0, status), "Open")

	def test_a_decided_row_is_left_alone(self):
		for docstatus, status in ((1, "Approved"), (1, "Rejected"), (0, "Open"), (0, "Approved")):
			with self.subTest(docstatus=docstatus, status=status):
				self.assertIsNone(patch_module.decision_for(docstatus, status))

	def test_a_cancelled_request_is_never_touched(self):
		for status in (None, "", "Open", "Approved", "Rejected"):
			with self.subTest(status=status):
				self.assertIsNone(patch_module.decision_for(2, status))


class _Site:
	"""The rows and the saved list columns a run reads and writes."""

	def __init__(self, rows, saved_columns=None, has_column=True):
		self.rows = {r["name"]: dict(r) for r in rows}
		self.saved = saved_columns
		self.db = MagicMock()
		self.db.table_exists.return_value = True
		self.db.has_column.return_value = has_column
		self.db.exists.side_effect = lambda dt, name=None: dt == "List View Settings" and saved_columns
		self.db.get_value.side_effect = lambda dt, name, field: self.saved
		self.db.set_value.side_effect = self._set_value

	def _set_value(self, doctype, name, field, value, update_modified=True):
		if doctype == D:
			self.rows[name][field] = value
		else:
			self.saved = value

	def get_all(self, doctype, filters=None, fields=None, **kwargs):
		return [frappe._dict(r) for r in self.rows.values()]

	def run(self):
		with (
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "get_all", side_effect=self.get_all),
			patch.object(frappe, "log_error", create=True),
		):
			patch_module.execute()
		return self.db.set_value.call_args_list


class TestTheRun(unittest.TestCase):
	ROWS = (
		{"name": "CMP-SUBMITTED-DEFAULTED", "docstatus": 1, "status": "Open"},
		{"name": "CMP-SUBMITTED-NULL", "docstatus": 1, "status": None},
		{"name": "CMP-DRAFT-NULL", "docstatus": 0, "status": None},
		{"name": "CMP-CANCELLED", "docstatus": 2, "status": "Open"},
		{"name": "CMP-REJECTED", "docstatus": 1, "status": "Rejected"},
	)

	def test_rows_get_the_decision_they_already_had(self):
		site = _Site(self.ROWS)
		site.run()
		self.assertEqual(
			{name: row["status"] for name, row in site.rows.items()},
			{
				"CMP-SUBMITTED-DEFAULTED": "Approved",
				"CMP-SUBMITTED-NULL": "Approved",
				"CMP-DRAFT-NULL": "Open",
				"CMP-CANCELLED": "Open",
				"CMP-REJECTED": "Rejected",
			},
		)

	def test_the_sync_watermark_is_not_bumped(self):
		calls = _Site(self.ROWS).run()
		row_writes = [c for c in calls if c.args[0] == D]
		self.assertTrue(row_writes)
		for call in row_writes:
			self.assertIs(call.kwargs.get("update_modified"), False)

	def test_a_second_run_writes_nothing(self):
		site = _Site(self.ROWS)
		site.run()
		site.db.set_value.reset_mock()
		self.assertEqual(site.run(), [])

	def test_without_the_column_nothing_is_written(self):
		self.assertEqual(_Site(self.ROWS, has_column=False).run(), [])

	def test_hrs_saved_columns_gain_the_status_column(self):
		saved = json.dumps([{"fieldname": "employee_name", "label": "Employee Name"}])
		site = _Site([], saved_columns=saved)
		site.run()
		self.assertEqual([c["fieldname"] for c in json.loads(site.saved)], ["employee_name", "status"])


if __name__ == "__main__":
	unittest.main()
