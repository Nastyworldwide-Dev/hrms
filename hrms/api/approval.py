"""Atomic request decisions shared by PWA and Desk.

Capability checks and decisions share source-read, company, workflow, self and
field authority. A routed reviewer may use the existing elevated submission
path only after those checks; controller validators and transaction effects
still run. Decisions lock the persisted request and optionally compare the
revision reviewed by the caller. Identical retries never submit twice.

Legacy pure transitions remain in finalize; configured workflows use Frappe's
workflow transition endpoint instead of direct decision controls.
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
#: Doctype -> the field naming its approver. The named person IS the routing,
#: whatever roles they hold — mirrors pwa_notifications.APPROVER_FIELD.
APPROVER_FIELD = {
	"Leave Application": "leave_approver",
	"Expense Claim": "expense_approver",
	"Shift Request": "approver",
}


def _is_routed_approver(doc, user: str | None = None) -> bool:
	"""Is the supplied user (by default the session) this request's approver?

	FOUND BY RUNNING AS A REAL USER: a team lead holding only the Employee role
	— exactly who reports_to routes OT, Attendance Request and Replacement
	Leave Claim to — got PermissionError from decide(). is_approver() computed
	them an approver, the notification was addressed to them, the Team tab
	rendered their queue, and doc.submit() refused the role. Every surface
	delivered the work; the last line denied it.

	The precedent is remote_checkin._ensure_approver: authorisation is ROUTING
	(are you the person this is addressed to, or HR?), and the transition then
	runs elevated. Three routing shapes, matching is_approver():

	  * HR — sees and decides everything;
	  * the doc's own approver field names the caller;
	  * the doc's employee reports_to the caller's employee.

	Deliberately NOT "anyone who can read": a worker can read their own request
	and must not be able to decide it (validate_self_submission double-guards
	that, but routing refuses it first, with a message about routing).
	"""
	user = frappe.session.user if user is None else user
	if {"System Manager", "HR Manager", "HR User"} & set(frappe.get_roles(user)):
		# HR operators may decide — but a company-fenced one only inside their
		# fence. company_visible is True for an unfenced operator (no Company
		# User Permission) and for the request's own companies, so this changes
		# nothing for admin/unfenced HR and stops a fenced HR deciding another
		# company's request. A fenced-out operator falls through: they may still
		# be the named approver or the reports_to manager below.
		from hrms.overrides.company_scope import company_visible

		subject = doc.get("employee")
		company = frappe.db.get_value("Employee", subject, "company") if subject else doc.get("company")
		if company_visible(company, user):
			return True
	field = APPROVER_FIELD.get(doc.doctype)
	if field and doc.get(field) == user:
		return True
	employee = doc.get("employee")
	if not employee:
		return False
	# Canonical identity, not a raw user_id read: a reports_to manager whose
	# mirror user_id drifted in case would otherwise be refused approval of their
	# own report's request; ambiguous logins fail closed here too.
	from hrms.utils.identity import own_employees

	mine = own_employees(user)
	if not mine:
		return False
	routed = frappe.db.get_value("Employee", employee, "reports_to") == mine[0]
	logger.debug("[approval] routing %s %s -> %s via reports_to: %s", doc.doctype, doc.name, user, routed)
	return routed


DECIDE_THEN_SUBMIT = {
	"Leave Application": ("status", "Open"),
	"Shift Request": ("status", "Draft"),
	"Expense Claim": ("approval_status", "Draft"),
	# Added 26 Aug 2026. These three were submittable with no decision field at
	# all, so RequestActionSheet could render Submit but never Reject — an
	# approver could approve and had no way to decline. Each one PAYS OUT on
	# submit (banked overtime hours, Attendance records, Leave Allocation days),
	# so their controllers guard the consequence on status == "Approved": a
	# rejection reaches docstatus 1 like any other decision.
	"OT Request": ("status", "Open"),
	"Attendance Request": ("status", "Open"),
	"Replacement Leave Claim": ("status", "Open"),
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


def _request_read_allowed(doc) -> bool:
	"""Native document visibility plus the explicit company boundary."""
	from hrms.overrides.company_scope import company_visible

	logger.debug("[approval] checking request visibility for %s", doc.doctype)
	if not frappe.has_permission(doc.doctype, "read", doc=doc):
		return False
	employee = doc.get("employee")
	company = frappe.db.get_value("Employee", employee, "company") if employee else doc.get("company")
	return company_visible(company) and company_visible(doc.get("company") or company)


def _decision_access(doc, status: str = "Approved") -> str | None:
	"""Return the authorized execution mode without changing session or rights."""
	from frappe.model.workflow import get_workflow_name

	from hrms.utils.identity import normalize_login

	logger.debug("[approval] checking decision access for %s", doc.doctype)
	entry = DECIDE_THEN_SUBMIT.get(doc.doctype)
	employee = doc.get("employee")
	if not entry or not employee or get_workflow_name(doc.doctype):
		return None
	if not _request_read_allowed(doc):
		return None
	employee_user = frappe.db.get_value("Employee", employee, "user_id")
	if normalize_login(employee_user) == normalize_login(frappe.session.user):
		setting = {
			"Leave Application": "prevent_self_leave_approval",
			"Expense Claim": "prevent_self_expense_approval",
		}.get(doc.doctype)
		if not setting:
			return None
		if frappe.db.get_single_value("HR Settings", setting) and (
			doc.doctype != "Leave Application" or status == "Approved"
		):
			return None
	if frappe.has_permission(doc.doctype, "submit", doc=doc):
		if frappe.has_permission(doc.doctype, "write", doc=doc) and entry[0] in get_permitted_fields(
			doc.doctype, permission_type="write"
		):
			return "native"
	return "routed" if _is_routed_approver(doc) else None


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
def decide(doctype: str, name: str, status: str, expected_modified: str | None = None) -> dict:
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
	access = _decision_access(doc, status)
	if not access:
		frappe.throw(_("You are not permitted to decide this request."), frappe.PermissionError)
	if access == "routed":
		# Routing replaces the role gate only after source read, company and
		# self-policy checks. Existing controller validators still run below.
		doc.flags.ignore_permissions = True

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

	if current != DECIDE_THEN_SUBMIT[doctype][1]:
		frappe.throw(_("This request is no longer awaiting a decision."), frappe.ValidationError)
	if expected_modified is not None:
		from frappe.utils import get_datetime

		if get_datetime(doc.modified) != get_datetime(expected_modified):
			frappe.throw(
				_("This request changed since you reviewed it. Reload and review it again."),
				frappe.TimestampMismatchError,
			)

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
def can_decide(doctype: str, name: str) -> bool:
	"""Whether the current user can open and approve this pending request.

	Uses the same access gate as decide; active workflows retain their own
	transition endpoint. Business validators still run at submission time.
	"""
	logger.debug("[approval] can_decide %s %s for %s", doctype, name, frappe.session.user)
	if doctype not in DECIDE_THEN_SUBMIT or not frappe.db.exists(doctype, name):
		return False
	doc = frappe.get_doc(doctype, name)
	fieldname, pending = DECIDE_THEN_SUBMIT[doctype]
	return bool(doc.docstatus == 0 and doc.get(fieldname) == pending and _decision_access(doc))


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
	if not _request_read_allowed(doc):
		frappe.throw(_("You are not permitted to access this request."), frappe.PermissionError)
	if docstatus == SUBMIT and doctype in DECIDE_THEN_SUBMIT:
		# Legacy decided drafts must not bypass the decision endpoint's gate.
		access = _decision_access(doc, doc.get(DECIDE_THEN_SUBMIT[doctype][0]))
		if not access:
			frappe.throw(_("You are not permitted to decide this request."), frappe.PermissionError)
		if access == "routed":
			doc.flags.ignore_permissions = True
	else:
		# Cancellation keeps its distinct right and existing routed authority;
		# the self-approval restriction does not forbid withdrawing a decision.
		action = "submit" if docstatus == SUBMIT else "cancel"
		if frappe.has_permission(doctype, action, doc=doc):
			doc.check_permission("read")
		elif _is_routed_approver(doc):
			doc.flags.ignore_permissions = True
		else:
			frappe.throw(_("This request is not routed to you for approval."), frappe.PermissionError)

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
