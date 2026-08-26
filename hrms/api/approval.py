"""One authorized approval action, one canonical final state.

Three submittable doctypes share the same contract, and each states it in its
own `on_submit`:

    Leave Application  "Only Leave Applications with status 'Approved' and
                        'Rejected' can be submitted"
    Shift Request      "Only Shift Request with status 'Approved' and
                        'Rejected' can be submitted"
    Expense Claim      "Approval Status must be 'Approved' or 'Rejected'"

So the decision and the submission are not two steps that happen to be adjacent
— they are one transition. The schema says the same thing from the other side:
the decision field is `reqd`, `no_copy` and **not** `allow_on_submit`, so it
cannot be set after submission. There is no legal resting state where a request
is decided but still a draft.

The PWA nevertheless made that state routinely, because the coupling lived in
the client:

    if (status === "Approved" && hasPermission("submit")) docstatus = 1

which only coupled *approvals* — so every rejection parked at `docstatus 0` —
and only when a client-side read of `frappe.client.get_doc_permissions` had
loaded and said yes. When it did not, the approval silently degraded into a
half-transition with no error, no ledger entry, and a second Submit button that
an HR Manager then had to press. That second press is what HR reported.

This module is the transition, server-side and shared, so no caller has to
reassemble it. It changes no permission rule: `doc.submit()` runs the whole
Frappe stack — `check_permission("write")`, `check_permission("submit")`,
permlevel enforcement on the decision field, the `approval_row_scope`
`has_permission` hook, and `before_submit`, which is where
`block_transactions_for_mirrored_employee` refuses to move a mirrored
employee's balances on this hub. Nothing here uses `ignore_permissions`,
`db_set`, or a flag to step around any of it. A failure anywhere raises, and
the request's transaction rolls back whole rather than leaving the document
half-decided.

Not covered here, deliberately: Attendance Request, OT Request and Replacement
Leave Claim, where submitting *is* the approval and there is no separate
decision field to set.
"""

import logging

import frappe
from frappe import _
from frappe.model import get_permitted_fields

logger = logging.getLogger(__name__)

#: doctype -> (decision field, the value meaning "nobody has decided yet")
#:
#: The undecided value differs per doctype and is taken from each field's own
#: `default`, not guessed: Leave Application starts "Open", the other two
#: start "Draft".
DECIDE_THEN_SUBMIT = {
	"Leave Application": ("status", "Open"),
	"Shift Request": ("status", "Draft"),
	"Expense Claim": ("approval_status", "Draft"),
}

#: The only values `decide` will write. Cancellation is a different operation
#: with its own permission (`cancel`) and its own reversal path, and is not
#: reachable from here.
DECISIONS = ("Approved", "Rejected")


def decision_field(doctype: str) -> str:
	"""The decision field for `doctype`, or a hard error.

	An allow-list rather than a caller-supplied fieldname: `decide` is
	whitelisted, so letting the caller name the field would turn it into a
	write-anything endpoint that skips every field-level rule.
	"""
	entry = DECIDE_THEN_SUBMIT.get(doctype)
	if not entry:
		frappe.throw(_("{0} is not an approvable request type.").format(_(doctype)), frappe.ValidationError)
	return entry[0]


def _require_writable_decision_field(doctype: str, fieldname: str) -> None:
	"""Fail early and legibly when the caller cannot write the decision field.

	Without this the failure is real but baffling: the decision field sits at
	`permlevel 1`, and `validate_higher_perm_levels` *silently reverts* a
	permlevel field the user may not write. The submit would then proceed with
	the status still "Open" and die inside `on_submit` complaining about the
	status — a permissions problem wearing a validation problem's error message.
	"""
	if fieldname in get_permitted_fields(doctype, permission_type="write"):
		return

	logger.warning(
		"[approval] %s cannot write %s.%s — decision refused", frappe.session.user, doctype, fieldname
	)
	frappe.throw(
		_("You are not permitted to approve or reject {0}.").format(_(doctype)), frappe.PermissionError
	)


def _state(doc) -> dict:
	"""What the caller should render. The backend's view, not the client's guess.

	`status` is None for a doctype with no decision field — Attendance Request,
	OT Request, Replacement Leave Claim — where submission IS the decision and
	docstatus carries the whole answer.

	This used to index DECIDE_THEN_SUBMIT unconditionally, which was safe while
	`decide` was the only caller: every doctype it serves is in that map.
	`finalize` exists precisely FOR the doctypes that are not, so it raised
	KeyError AFTER a successful doc.submit() — the transition ran, the response
	builder crashed, and the rollback undid the approval. The endpoint written
	to fix a silent non-approval would itself have produced one. Caught on a
	real bench, not by reading.
	"""
	mapping = DECIDE_THEN_SUBMIT.get(doc.doctype)
	return {
		"doctype": doc.doctype,
		"name": doc.name,
		"docstatus": doc.docstatus,
		"status": doc.get(mapping[0]) if mapping else None,
	}


@frappe.whitelist(methods=["POST"])
def decide(doctype: str, name: str, status: str) -> dict:
	"""Record a decision and finalize the request, atomically.

	Returns the resulting state so the caller renders what the server actually
	did rather than what it hoped would happen.
	"""
	fieldname = decision_field(doctype)
	if status not in DECISIONS:
		frappe.throw(
			_("{0} is not a decision. Use {1}.").format(status, " or ".join(DECISIONS)),
			frappe.ValidationError,
		)

	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} {1} not found.").format(_(doctype), name), frappe.DoesNotExistError)

	# Take the row lock BEFORE reading the state the idempotency check below
	# depends on. Without it, two taps (or two approvers) can both read
	# docstatus 0, both proceed, and both write a ledger entry. With it the
	# loser blocks here, then finds the document already decided and returns
	# the winner's outcome instead of duplicating it.
	frappe.db.get_value(doctype, name, "docstatus", for_update=True)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	_require_writable_decision_field(doctype, fieldname)

	current = doc.get(fieldname)

	if doc.docstatus == 1:
		# Already final. Same decision -> the caller retried, or two taps landed;
		# report success without touching anything. Different decision -> the
		# document is settled and reversing it is a cancellation, not a decision.
		if current == status:
			logger.info("[approval] %s %s already %s — no-op", doctype, name, status)
			return _state(doc)
		frappe.throw(
			_("{0} has already been submitted as {1}.").format(_(doctype), _(current)),
			frappe.ValidationError,
		)

	if doc.docstatus == 2:
		frappe.throw(_("{0} has been cancelled.").format(_(doctype)), frappe.ValidationError)

	doc.set(fieldname, status)
	# ONE save cycle: validate -> before_submit (mirrored-employee guard) ->
	# db_update -> on_update -> on_submit (ledger, attendance, notifications).
	# Any failure raises and the whole request rolls back; there is no path that
	# writes the decision and stops.
	doc.submit()

	logger.info(
		"[approval] %s decided %s %s as %s (docstatus=%s)",
		frappe.session.user,
		doctype,
		name,
		status,
		doc.docstatus,
	)
	return _state(doc)


@frappe.whitelist()
def report_half_transitioned(doctype: str | None = None) -> dict:
	"""Requests already stuck decided-but-draft, for an HR ruling.

	Deliberately reports rather than repairs. Submitting one of these writes
	Leave Ledger Entries and consumes the employee's balance, and nothing in the
	row says whether a stale "Approved but draft" record was a real decision that
	never landed or an abandoned click — so finishing them automatically would be
	guessing with someone's leave balance. HR decides; this gives them the list.
	"""
	frappe.only_for(("HR Manager", "HR User", "System Manager"))

	doctypes = [doctype] if doctype else list(DECIDE_THEN_SUBMIT)
	out: dict[str, dict] = {}

	for dt in doctypes:
		fieldname = decision_field(dt)
		rows = frappe.get_all(
			dt,
			filters={"docstatus": 0, fieldname: ("in", DECISIONS)},
			fields=["name", "employee", "company", fieldname, "modified", "modified_by"],
			order_by="modified desc",
			limit=500,
		)
		out[dt] = {"count": len(rows), "rows": rows}
		if rows:
			logger.warning("[approval] %s %s row(s) decided but still draft", len(rows), dt)

	return out


#: docstatus values `finalize` will move a document to. Deliberately not 0:
#: returning a submitted document to draft is not a transition Frappe offers,
#: and pretending otherwise is how the bug below started.
SUBMIT, CANCEL = 1, 2


@frappe.whitelist(methods=["POST"])
def finalize(doctype: str, name: str, docstatus: int) -> dict:
	"""Submit or cancel a request that carries no decision field.

	THE BUG THIS REPLACES, reported from the field and reproduced in one line:
	an OT Request was approved and the app went on asking the employee to submit
	it.

	    set_value REFUSED -> ValidationError Cannot edit standard fields
	    docstatus still: 0

	`RequestActionSheet` sent `{docstatus: 1}` through frappe-ui's
	`document.setValue` — `frappe.client.set_value` — which refuses to write
	docstatus. Correctly: docstatus is a standard field and moving it is a
	TRANSITION, not an edit. Submitting must run validate, before_submit and
	on_submit, and an UPDATE that skipped them would be far worse than the
	refusal — an OT Request would sail past `validate_self_submission` and
	`validate_mandatory_attachment`.

	So the call threw, a red toast showed for a moment on a phone, and the
	document stayed a draft. The approver believed they had approved it.

	`decide` cannot serve these doctypes: it writes a decision FIELD, and
	Attendance Request, OT Request and Replacement Leave Claim have none —
	submission IS the decision. Cancel had the same hole for EVERY doctype in
	the sheet, because a cancel sends no status and fell to the same branch.

	Returns the resulting state, so the caller renders what the server did.
	"""
	docstatus = int(docstatus)
	if docstatus not in (SUBMIT, CANCEL):
		frappe.throw(
			_("{0} is not a transition this endpoint performs.").format(docstatus),
			frappe.ValidationError,
		)

	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} {1} not found.").format(_(doctype), name), frappe.DoesNotExistError)

	# Lock BEFORE reading the state the idempotency check depends on — the same
	# reasoning as `decide`. Two taps on a phone, or two approvers, must not both
	# read docstatus 0 and both proceed.
	frappe.db.get_value(doctype, name, "docstatus", for_update=True)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	# Two taps are one intention. Report the first outcome rather than throwing
	# at somebody who did nothing wrong.
	if doc.docstatus == docstatus:
		logger.info("[approval] %s %s already at docstatus %s — no-op", doctype, name, docstatus)
		return _state(doc)

	if doc.docstatus == 2:
		frappe.throw(_("{0} has been cancelled.").format(_(doctype)), frappe.ValidationError)
	# The real transition: validate -> before_submit -> on_submit (or the cancel
	# chain). Any failure raises and the whole request rolls back; there is no
	# path that half-moves the document.
	#
	# Spelled out rather than dispatched through getattr: this is the one line
	# the whole endpoint exists for, and a dynamic call hides it from every
	# static check — including the test that pins it.
	if docstatus == SUBMIT:
		doc.submit()
	else:
		doc.cancel()

	logger.info(
		"[approval] %s %s %s %s -> docstatus %s",
		frappe.session.user,
		"submitted" if docstatus == SUBMIT else "cancelled",
		doctype,
		name,
		doc.docstatus,
	)
	return _state(doc)
