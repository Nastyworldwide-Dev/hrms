"""A new open-ended Shift Assignment ends the ones it supersedes.

10 September 2026: approving a shift change created the new assignment and
left the old open-ended one Active. Two Active assignments sent one day's IN
and OUT to two shifts (hrms/utils/shift_resolution.py), and the old shift's
hourly job kept marking the person Absent on its own days. Nabil: "once HR
assigned or the shift is changed as requested, it should follow that".

On submit of an assignment, every earlier assignment of the same employee
under a different shift that still runs on the new start date is ended the
day before — through `end_date`, which is editable after submit, with a
comment naming the assignment that superseded it. Mirrored rows are left to
their source (write-block). The rule layer (hrms/hr/shift_rules.py) closes
its own rows the same way.
"""

import logging

import frappe
from frappe import _
from frappe.utils import getdate

from hrms.utils.shift_resolution import superseded_assignments

logger = logging.getLogger(__name__)


def close_superseded_assignments(doc, method=None):
	if doc.end_date or doc.status != "Active":
		return
	existing = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": doc.employee,
			"docstatus": 1,
			"status": "Active",
			"name": ("!=", doc.name),
			"synced_from_instance": ("is", "not set"),
		},
		fields=["name", "shift_type", "start_date", "end_date"],
	)
	for row in existing:
		row["start_date"] = getdate(row["start_date"])
		row["end_date"] = getdate(row["end_date"]) if row.get("end_date") else None
	for name, end_date in superseded_assignments(existing, getdate(doc.start_date), doc.shift_type, doc.name):
		frappe.db.set_value("Shift Assignment", name, "end_date", end_date)
		frappe.get_doc("Shift Assignment", name).add_comment(
			"Comment",
			_("Ended on {0}: superseded by {1} ({2}) from {3}.").format(
				end_date, doc.name, doc.shift_type, doc.start_date
			),
		)
		logger.info("[shift_assignment] %s ended on %s, superseded by %s", name, end_date, doc.name)
