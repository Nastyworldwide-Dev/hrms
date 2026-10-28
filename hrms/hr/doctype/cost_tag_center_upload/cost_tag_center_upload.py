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
			apply_uploads([self.name])


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


def apply_uploads(names):
	"""Put the named Pending upload rows on their employees, one save each.

	Each employee is its own savepoint: one that fails is rolled back alone,
	its rows marked Failed with the reason, and the rest carry on. The save
	runs as a Desk save would (in_import off), not with the importer's
	shortcuts, so defaults, select checks and notifications all apply."""
	records = frappe.get_all(
		DOCTYPE,
		filters={"status": "Pending", "name": ("in", list(names))},
		fields=["name", "employee", "allocation_month", "cost_center", "territory", "percentage"],
		order_by="creation asc",
	)
	by_employee = {}
	for record in records:
		by_employee.setdefault(record.employee, []).append(record)

	in_import = frappe.flags.in_import
	frappe.flags.in_import = False
	try:
		for i, (employee_id, rows) in enumerate(by_employee.items()):
			save_point = f"cost_tag_upload_{i}"
			frappe.db.savepoint(save_point)
			try:
				_apply_employee(employee_id, rows)
			except Exception as e:
				frappe.db.rollback(save_point=save_point)
				_mark(rows, "Failed", _clean(e))
				logger.warning("[cost_tag_upload] employee=%s rows=%d failed: %s", employee_id, len(rows), e)
				continue
			_mark(rows, "Done", None)
			logger.info("[cost_tag_upload] employee=%s rows=%d applied", employee_id, len(rows))
	finally:
		frappe.flags.in_import = in_import


def _apply_employee(employee_id, rows):
	employee = frappe.get_doc("Employee", employee_id)
	table = employee.get(TABLE) or []
	for record in rows:
		row, added = place_row(
			table, record.allocation_month, record.cost_center, record.territory, record.percentage
		)
		if added:
			employee.append(TABLE, row)
			# re-read: append stores a new child row, and a later row of the
			# same file with the same month and tag must find it
			table = employee.get(TABLE)
	employee.save()


def after_data_import(doc, method=None):
	"""Data Import on_change: once an import of upload rows has ENDED, apply
	the rows it created.

	The status alone can't tell: the importer sets "Partial Success" after its
	first row, mid-import. It has ended when its log covers every row of the
	file (payload_count). An import that stopped (Error, Timed Out) marks its
	rows Failed instead of leaving them waiting. Never raises — an error here
	would roll back the whole import — it is logged and the rows stay Pending."""
	if doc.get("reference_doctype") != DOCTYPE:
		return
	if doc.get("status") not in ("Success", "Partial Success", "Error", "Timed Out"):
		return
	try:
		logs = frappe.get_all(
			"Data Import Log",
			filters={"data_import": doc.name},
			fields=["docname", "row_indexes", "success"],
		)
		names = [log.docname for log in logs if log.success and log.docname]
		if doc.get("status") in ("Error", "Timed Out"):
			# the import stopped: its rows would wait for ever, so say so
			if names:
				frappe.db.set_value(
					DOCTYPE,
					{"name": ("in", names), "status": "Pending"},
					{"status": "Failed", "error": _("The import did not finish. Upload the file again.")},
					update_modified=False,
				)
			return
		if len(logs) < (doc.get("payload_count") or 0):
			return
		if names:
			apply_uploads(names)
	except Exception:
		logger.exception("[cost_tag_upload] data_import=%s could not apply its rows", doc.name)


def _mark(rows, status, error):
	for record in rows:
		frappe.db.set_value(DOCTYPE, record.name, {"status": status, "error": error}, update_modified=False)


def _clean(e):
	"""The message HR reads in the Why it failed column, without HTML tags."""
	return re.sub(r"<[^>]+>", "", str(e)).strip()
