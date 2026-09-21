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

21 September 2026: the roster is the source of the shift stamp; the stamp is
a cache. Submit, cancel and an end_date edit each queue ONE deduplicated
`hrms.utils.restamp.restamp` job over the assignment's own range, so punches
stamped from a wrong assignment stop keeping that stamp for ever (audit E H3).
"""

import logging
from functools import partial

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from hrms.hr.doctype.shift_assignment.shift_assignment import refuse_overlapping_assignments
from hrms.utils.shift_resolution import superseded_assignments
from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)


def close_superseded_assignments(doc, method=None):
	"""End what the new assignment supersedes; then refuse what still overlaps.

	The refusal runs here as well as in validate so a creator that skips
	validate (`flags.ignore_validate`, bulk tools) meets the same rule on
	submit — after the superseded rows are ended, so a plain shift change
	still goes through.
	"""
	if doc.status != "Active":
		return
	if doc.end_date:
		refuse_overlapping_assignments(doc)
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
	refuse_overlapping_assignments(doc)


def queue_restamp(doc, method=None):
	"""After commit, one job re-stamps the punches of the assignment's range.

	The range is the assignment's own start..end (end = the employee's today
	when open, and on an end_date edit too: the punches that need the roster
	re-read are the ones AFTER the new end, stamped while it was still open).
	One job per roster CHANGE: the job id carries the assignment's modified
	stamp, because `deduplicate` drops a job whose twin has already STARTED
	(frappe background_jobs.py) and a second end_date edit the same day would
	otherwise be lost. The job is idempotent, so two of them cost only time.
	Mirrored rows are the ERP's; their punches are never re-stamped here.
	"""
	if getattr(doc, "synced_from_instance", None):
		return
	start = getdate(doc.start_date)
	dated = getattr(doc, "end_date", None) and method != "on_update_after_submit"
	end = getdate(doc.end_date) if dated else employee_now(doc.employee).date()
	reason = f"shift assignment {doc.name} {method}"
	changed = str(getattr(doc, "modified", None) or now_datetime())
	frappe.db.after_commit.add(partial(_enqueue_restamp, doc.employee, str(start), str(end), reason, changed))
	logger.info(
		"[shift_assignment] %s: re-stamp of %s %s..%s queued after commit", doc.name, doc.employee, start, end
	)


def _enqueue_restamp(employee, from_date, to_date, reason, changed):
	frappe.enqueue(
		"hrms.utils.restamp.restamp",
		queue="short",
		job_id=f"restamp::{employee}::{from_date}::{to_date}::{changed}",
		deduplicate=True,
		employee=employee,
		from_date=from_date,
		to_date=to_date,
		reason=reason,
		dry_run=False,
	)
