# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Cost Tag/Center Upload — one row of HR's Cost Tag/Center Excel.

HR uploads it through Data Import ("Insert New Records"). The rows are put on
each employee's Cost Tag/Center Allocation table (Employee → Overview), owner's
rule, 28 Oct 2026: the same Year/Month and tag already there is replaced,
anything else is a new row. The Employee ID decides whose profile it goes on;
the Staff Name is only there so the file is readable.

Data Import saves one Excel row at a time, but a month only adds up to 100%
once all its rows are in, so a 60/40 split would be refused at the 60. So an
imported row waits as Pending, and when the import ends each employee's rows go
on together with one Employee.save — the Employee's own checks (each month
totals 100%) run on the finished month. A row added by hand in Desk is applied
at once. Each row ends Done or Failed with the reason; a failing employee is
left as it was and does not stop the others.
"""

import logging
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

logger = logging.getLogger(__name__)

DOCTYPE = "Cost Tag/Center Upload"
TABLE = "interco_cost_allocation"


class CostTagCenterUpload(Document):
	def after_insert(self):
		if not frappe.flags.in_import:
			apply_pending_uploads()


def place_row(rows, month, cost_center, territory, percentage):
	"""Replace the percentage of the row with the same month and tag, or make a
	new row. Returns (row, added): `added` rows are not yet on the employee."""
	if not (cost_center or territory):
		frappe.throw(_("Cost Tag/Center is required."))
	month = getdate(month).replace(day=1)
	for row in rows:
		if row.get("allocation_month") and getdate(row.get("allocation_month")).replace(day=1) != month:
			continue
		if cost_center:
			same = row.get("cost_center") == cost_center
		else:
			same = not row.get("cost_center") and row.get("territory") == territory
		if same:
			row.percentage = flt(percentage)
			return row, False
	return frappe._dict(
		allocation_month=month,
		cost_center=cost_center,
		territory=None if cost_center else territory,
		percentage=flt(percentage),
	), True


def apply_pending_uploads():
	"""Put every Pending upload row on its employee, one save per employee."""
	records = frappe.get_all(
		DOCTYPE,
		filters={"status": "Pending"},
		fields=["name", "employee", "allocation_month", "cost_center", "territory", "percentage"],
		order_by="creation asc",
	)
	by_employee = {}
	for record in records:
		by_employee.setdefault(record.employee, []).append(record)

	for employee_id, rows in by_employee.items():
		try:
			employee = frappe.get_doc("Employee", employee_id)
			table = employee.get(TABLE) or []
			for record in rows:
				row, added = place_row(
					table, record.allocation_month, record.cost_center, record.territory, record.percentage
				)
				if added:
					# the appended child, not the dict, so a later row of the
					# same file with the same month and tag replaces it
					table = employee.get(TABLE) or []
					if not any(r is row for r in table):
						employee.append(TABLE, row)
						table = employee.get(TABLE)
			employee.save()
		except Exception as e:
			_mark(rows, "Failed", _clean(e))
			logger.warning("[cost_tag_upload] employee=%s rows=%d failed: %s", employee_id, len(rows), e)
			continue
		_mark(rows, "Done", None)
		logger.info("[cost_tag_upload] employee=%s rows=%d applied", employee_id, len(rows))


def after_data_import(doc, method=None):
	"""Data Import on_change: once an import of upload rows ends, apply them.
	db_set fires on_change only, so this hook — not on_update — sees the end."""
	if doc.get("reference_doctype") != DOCTYPE:
		return
	if doc.get("status") not in ("Success", "Partial Success"):
		return
	apply_pending_uploads()


def _mark(rows, status, error):
	for record in rows:
		frappe.db.set_value(DOCTYPE, record.name, {"status": status, "error": error}, update_modified=False)


def _clean(e):
	"""The message HR reads in the Why it failed column, without HTML tags."""
	return re.sub(r"<[^>]+>", "", str(e)).strip()
