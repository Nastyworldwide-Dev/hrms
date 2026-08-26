"""Give existing requests the decision they were already given.

OT Request, Attendance Request and Replacement Leave Claim gained a `status`
field so an approver could DECLINE one — before this they were submittable with
no decision field at all, so the PWA could render Submit and never Reject.

Every row written before that field existed has `status` NULL. Left alone:

* a submitted request reads as undecided, and `on_submit` now refuses anything
  that is not Approved or Rejected — so amending or resubmitting one would
  throw at a document that was approved months ago;
* `get_replacement_leave_bank` filters `status != "Rejected"`, and NULL is not
  `!= 'Rejected'` in SQL — it is NULL, which is not true. **Every historical
  OT Request would silently drop out of the bank**, wiping replacement-leave
  entitlement that employees have already earned.

That second one is why this patch is not optional and why it runs on the same
migrate as the field.

The mapping is what already happened, not a guess:

    docstatus 1 (submitted)  -> Approved   somebody submitted it, and for these
                                           doctypes submitting IS approving
    docstatus 0 (draft)      -> Open       nobody has decided yet
    docstatus 2 (cancelled)  -> Open       a cancellation is not a rejection;
                                           the row is out of play either way and
                                           inventing "Rejected" would put a
                                           decision in somebody's mouth

Only ever fills NULL. A row that already carries a status was decided under the
new field and is not this patch's business.

Written with db.set_value(update_modified=False) rather than doc.save(): these
are submitted documents, saving them would re-run validation and on_submit
guards against data that predates both, and `modified` drives the sync
watermark — bumping thousands of rows would make the next pull re-read a window
it has already covered.
"""

import frappe

DOCTYPES = ("OT Request", "Attendance Request", "Replacement Leave Claim")

#: docstatus -> the decision that docstatus already represents
DECISION = {0: "Open", 1: "Approved", 2: "Open"}


def execute():
	filled = {}
	for doctype in DOCTYPES:
		if not frappe.db.table_exists(doctype):
			continue
		if not frappe.db.has_column(doctype, "status"):
			# The field lands with the doctype JSON on this same migrate; if it
			# is somehow absent there is nothing to fill and nothing to fix here.
			frappe.log_error(
				title="backfill_request_decision_status: no status column",
				message=f"{doctype} has no `status` column, so nothing was backfilled.",
			)
			continue

		rows = frappe.get_all(
			doctype,
			filters={"status": ("is", "not set")},
			fields=["name", "docstatus"],
		)
		for row in rows:
			frappe.db.set_value(
				doctype,
				row.name,
				"status",
				DECISION.get(row.docstatus, "Open"),
				update_modified=False,
			)
		if rows:
			filled[doctype] = len(rows)

	if not filled:
		print("[backfill_request_decision_status] every request already carries a status")
		return

	frappe.db.commit()
	print(f"[backfill_request_decision_status] filled {sum(filled.values())}: {filled}")
