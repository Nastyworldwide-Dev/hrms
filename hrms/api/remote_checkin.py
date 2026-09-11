"""Remote check-in PWA endpoints.

hrms.api.remote_checkin.submit_remarks(request, employee_remarks)
hrms.api.remote_checkin.list_pending_for_approver()
hrms.api.remote_checkin.approve(request, approver_remarks)
hrms.api.remote_checkin.reject(request, approver_remarks)
hrms.api.remote_checkin.get_pending_count()  # for Profile badge
"""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Count
from frappe.utils import add_days, cint, get_datetime, now_datetime

from hrms.utils.company_scope import permitted_company_filter
from hrms.utils.geofence import usable_accuracy

#: The PWA names the provider it got the fix from; the row stores a word HR can read.
LOCATION_SOURCES = {"high": "GPS", "gps": "GPS", "coarse": "Network", "network": "Network"}
from hrms.utils.identity import get_employee
from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)

# What makes a later IN the start of a NEW session is not how long after this
# one it lands — it is whether an OUT closed this session first. This used to be
# a 60-second SAME_PUNCH_WINDOW, which caught a double tap and missed the real
# thing: production carried a duplicate IN 10m53s later with no OUT between, and
# that employee could never file a late check-out at all. No constant is right
# here, so there is no longer a constant.

HR_MANAGER_ROLE = "HR Manager"


def _ensure_owner(request_name: str) -> dict:
	row = frappe.db.get_value(
		"Remote Checkin Request",
		request_name,
		["name", "employee", "status"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Request not found."))

	employee_user = frappe.db.get_value("Employee", row.employee, "user_id")
	if employee_user != frappe.session.user:
		frappe.throw(_("You can only edit your own request."), frappe.PermissionError)
	return row


def _ensure_approver(request_name: str) -> dict:
	row = frappe.db.get_value(
		"Remote Checkin Request",
		request_name,
		["name", "approver", "status", "checkin", "employee"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Request not found."))

	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	is_admin = bool(roles & {"System Manager", HR_MANAGER_ROLE})
	if not (is_admin or user == row.approver):
		logger.warning(
			"[remote_checkin] DENY action by %s on %s (approver=%s)",
			user,
			request_name,
			row.approver,
		)
		frappe.throw(_("You are not the assigned approver for this request."), frappe.PermissionError)
	return row


@frappe.whitelist()
def submit_remarks(request: str, employee_remarks: str = "") -> dict:
	"""Backfill the employee's reason after the check-in was saved.

	An OUT request that inherits an earlier Approved IN is already in
	status=Approved by the time the dialog reaches the user; storing a
	reason against it is harmless (and useful for audit), so we don't
	throw there. Rejected requests block the write because the row is
	closed and the user is being asked to amend a decision that's gone
	the wrong way for them.
	"""
	row = _ensure_owner(request)
	if row.status == "Rejected":
		frappe.throw(_("This request has been rejected and can no longer be edited."))
	frappe.db.set_value("Remote Checkin Request", request, "employee_remarks", employee_remarks or "")
	logger.info(
		"[remote_checkin] submit_remarks request=%s status=%s by=%s",
		request,
		row.status,
		frappe.session.user,
	)
	return {"ok": True, "name": request, "status": row.status}


PENDING_REQUEST_FIELDS = (
	"name",
	"employee",
	"employee_name",
	"checkin",
	"checkin_time",
	"log_type",
	"latitude",
	"longitude",
	"distance_m",
	"employee_remarks",
	"nearest_shift_location",
)


def _pending_for_approver_query(user: str, statuses: tuple[str, ...] = ("Pending",)):
	"""Requests in `statuses` routed to `user`, fenced to their permitted companies.

	Remote Checkin Request carries no company field, so the fence rides on the
	requesting Employee. Being named as approver is not by itself authority to
	see the row: a group HR user fenced to one company must not be handed
	another company's out-of-radius punches. ONE query for the pending queue,
	the badge count and the decided history — three surfaces, one scope.
	"""
	RemoteCheckinRequest = frappe.qb.DocType("Remote Checkin Request")
	query = (
		frappe.qb.from_(RemoteCheckinRequest)
		.where(RemoteCheckinRequest.status.isin(list(statuses)))
		.where(RemoteCheckinRequest.approver == user)
	)

	companies = permitted_company_filter(endpoint="remote_checkin.list_pending_for_approver")
	if companies is not None:
		Employee = frappe.qb.DocType("Employee")
		query = (
			query.left_join(Employee)
			.on(RemoteCheckinRequest.employee == Employee.name)
			.where(Employee.company.isin(companies))
		)
		logger.info(
			"[api] remote_checkin pending fenced to %d company(ies) for %s",
			len(companies),
			user,
		)

	return query, RemoteCheckinRequest


def _with_checkin_selfie(query, RemoteCheckinRequest):
	"""Join the punch so the list carries its `selfie_image`.

	The photo is the one piece of evidence the employee supplies with an
	out-of-radius punch, and it lives on Employee Checkin — not on the request
	the approver is shown. Without this join the queue reached the approver as a
	name, a time and a distance, and the photo was reachable only from Desk.
	List surfaces only: the badge count has no use for it.
	"""
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
	query = query.left_join(EmployeeCheckin).on(RemoteCheckinRequest.checkin == EmployeeCheckin.name)
	return query, EmployeeCheckin.selfie_image.as_("selfie_image")


@frappe.whitelist()
def list_pending_for_approver() -> list[dict]:
	"""List pending requests where the current user is the approver."""
	user = frappe.session.user
	query, RemoteCheckinRequest = _pending_for_approver_query(user)
	query, selfie = _with_checkin_selfie(query, RemoteCheckinRequest)
	rows = (
		query.select(*[RemoteCheckinRequest[field] for field in PENDING_REQUEST_FIELDS], selfie)
		.orderby(RemoteCheckinRequest.checkin_time, order=Order.desc)
		.limit(200)
		.run(as_dict=True)
	)
	logger.info("[remote_checkin] list_pending_for_approver user=%s rows=%d", user, len(rows))
	return rows


DECIDED_REQUEST_FIELDS = (*PENDING_REQUEST_FIELDS, "status", "approved_at", "approver_remarks")


@frappe.whitelist()
def list_decided_for_approver(limit: int = 50) -> list[dict]:
	"""Requests this approver has already decided — the History tab.

	Until this existed a decided request was visible NOWHERE: it left the
	pending queue on decision, and the notification card stopped linking
	anywhere. Same shape and — deliberately — the same company fence as
	`list_pending_for_approver`: assignment, queue and history must all answer
	from one scope, or a request can be decided in one view and unreviewable in
	the next.
	"""
	user = frappe.session.user
	query, RemoteCheckinRequest = _pending_for_approver_query(user, statuses=("Approved", "Rejected"))
	query, selfie = _with_checkin_selfie(query, RemoteCheckinRequest)
	rows = (
		query.select(*[RemoteCheckinRequest[field] for field in DECIDED_REQUEST_FIELDS], selfie)
		.orderby(RemoteCheckinRequest.approved_at, order=Order.desc)
		.limit(min(int(limit or 50), 200))
		.run(as_dict=True)
	)
	logger.info("[remote_checkin] list_decided_for_approver user=%s rows=%d", user, len(rows))
	return rows


@frappe.whitelist()
def get_pending_count() -> int:
	"""Badge count — must use the same fence as the list it opens."""
	user = frappe.session.user
	query, RemoteCheckinRequest = _pending_for_approver_query(user)
	result = query.select(Count(RemoteCheckinRequest.name)).run()
	count = result[0][0] if result else 0
	logger.info("[remote_checkin] pending_count user=%s -> %d", user, count)
	return int(count or 0)


def _decide(request: str, decision: str, approver_remarks: str) -> dict:
	row = _ensure_approver(request)
	if row.status != "Pending":
		frappe.throw(_("This request has already been decided."))

	doc = frappe.get_doc("Remote Checkin Request", request)
	doc.status = decision
	doc.approver_remarks = approver_remarks or ""
	# Audit stamp — when the approval happened on this system, not attendance
	# wall clock. Stays on the system clock (see hrms/utils/timezone.py).
	doc.approved_at = now_datetime()
	doc.flags.ignore_permissions = True
	doc.save()
	logger.info(
		"[remote_checkin] %s request=%s checkin=%s by=%s",
		decision.lower(),
		request,
		row.checkin,
		frappe.session.user,
	)
	return {"ok": True, "name": request, "status": decision}


@frappe.whitelist()
def approve(request: str, approver_remarks: str = "") -> dict:
	return _decide(request, "Approved", approver_remarks)


@frappe.whitelist()
def reject(request: str, approver_remarks: str = "") -> dict:
	return _decide(request, "Rejected", approver_remarks)


def _session_is_live(in_time, now) -> bool:
	"""A session stays open until 06:00 the morning after its check-in — the same
	cutoff `unresolved_stale_in` uses to decide when to raise the forgot-to-
	check-out banner. One rule, so the banner and the punch can never disagree
	about whether somebody is still on shift."""
	from datetime import timedelta

	cutoff = (in_time + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
	return now < cutoff


def resolve_punch_type(recent_rows, requested: str, now):
	"""The type a punch MUST carry, given the employee's recent log.

	`log_type` used to be whatever the browser said. CheckInPanel's nextAction
	falls back to "IN" whenever it cannot see a prior punch — an empty cache, a
	failed reload, a backgrounded PWA, a second device — and it recomputes while
	the confirm sheet is open, so somebody who read "Check Out" could submit an
	IN. Production carries the proof: one employee's log has IN 08:51 and IN
	18:31 on the same day with no OUT between, and IN 09:08 followed by IN 09:18
	on another.

	What that costs: an IN with no OUT is zero working hours and a Half Day; on
	an employee who also holds a night-shift assignment the 18:3x IN resolves to
	the 7PM shift and splits the day into two attendance rows; and the duplicate
	IN then blocks the late check-out that would have repaired it.

	A second IN inside a LIVE session is not a thing that can physically happen
	— nobody arrives twice without leaving — so it is read as the departure it
	must be. That is a reading, not a guess. It is deliberately NOT applied when
	the open session has gone stale or been swept as abandoned: there a fresh IN
	is exactly right, and turning this morning's arrival into a check-out would
	be the same mistake pointing the other way.

	Returns (log_type, closing_row | None). Pure, so the rule is testable
	without a bench; `punch` supplies the rows.
	"""
	if requested != "IN":
		return requested, None

	# A REJECTED late-OUT never closed its session — the same rule the banner
	# and the OT pairing engine already apply.
	rows = sorted(
		(
			r
			for r in recent_rows
			if not (r.log_type == "OUT" and r.get("remote_approval_status") == "Rejected")
		),
		key=lambda r: r.time,
	)

	open_in = None
	for i, row in enumerate(rows):
		if row.log_type != "IN":
			continue
		nxt = rows[i + 1] if i + 1 < len(rows) else None
		if nxt and nxt.log_type == "OUT":
			continue  # session closed
		open_in = row
	if not open_in or cint(open_in.get("is_abandoned")):
		return "IN", None
	if not _session_is_live(get_datetime(open_in.time), now):
		return "IN", None

	logger.warning(
		"[remote_checkin] IN requested while %s is still open — recording a check-out instead",
		open_in.name,
	)
	return "OUT", open_in


@frappe.whitelist()
def punch(
	employee: str,
	log_type: str,
	latitude=None,
	longitude=None,
	selfie_image: str | None = None,
	time: str | None = None,
	accuracy=None,
	fix_age_s=None,
	source=None,
) -> dict:
	"""PWA check-in/out — the only write path staff have into Employee Checkin."""
	# Staff desk permissions on Employee Checkin are read-only, so this endpoint
	# is the whole staff write path. The stored time is ALWAYS the server clock —
	# any client-supplied `time` is ignored, which kills typed-in and backdated
	# punches at the source.
	#
	# The stamp is the server clock *in the employee's attendance timezone*, not
	# the site's: shift windows, OT and attendance are all local wall clock, so
	# on a site whose System Settings timezone differs from where staff work
	# (Dubai vs Malaysia) now_datetime() would file every punch hours off.
	#
	# `accuracy` is the device's error estimate in metres for the coordinates it
	# sent. Unlike `time` it is taken at face value: it can only widen this
	# employee's own fence, by a capped amount, and anyone willing to forge it
	# could forge the coordinates themselves for a better result.
	logger.info(
		"[remote_checkin] punch %s %s by %s accuracy=%s",
		employee,
		log_type,
		frappe.session.user,
		accuracy,
	)
	employee_user = frappe.db.get_value("Employee", employee, "user_id")
	if not employee_user or employee_user != frappe.session.user:
		frappe.throw(_("You can only check in as yourself."), frappe.PermissionError)

	if log_type not in ("IN", "OUT"):
		frappe.throw(_("Invalid log type."))

	# The phone proposes; the server decides. Nothing existing is touched — this
	# only chooses the type of the row about to be created, so there is no
	# overwrite to get wrong and no punch is ever dropped.
	punch_time = employee_now(employee)
	# NEWEST first, then reversed for the walk. `time asc` with a limit keeps the
	# OLDEST rows, so a busy log would truncate away the very punch this rule
	# depends on — the open IN — and silently stop coercing. The walk below still
	# wants ascending order, so the reversal happens here rather than in the rule.
	recent = list(
		reversed(
			frappe.get_all(
				"Employee Checkin",
				filters={"employee": employee, "time": [">=", add_days(punch_time, -3)]},
				fields=["name", "time", "log_type", "is_abandoned", "remote_approval_status"],
				order_by="time desc",
				limit=100,
			)
		)
	)
	resolved_type, closing = resolve_punch_type(recent, log_type, get_datetime(punch_time))
	if resolved_type != log_type:
		logger.warning(
			"[remote_checkin] %s asked for %s, recorded %s (session %s still open)",
			employee,
			log_type,
			resolved_type,
			closing.name if closing else "?",
		)
		log_type = resolved_type

	doc = frappe.new_doc("Employee Checkin")
	doc.update(
		{
			"employee": employee,
			"log_type": log_type,
			"time": punch_time,
			"latitude": latitude,
			"longitude": longitude,
		}
	)
	# Parsed with the same helper the fence uses, so "what counts as a usable
	# accuracy" has one definition. Unusable is left unset, not zeroed: absent
	# means "unknown, no allowance", 0 would mean "perfect fix".
	accuracy_m = usable_accuracy(accuracy) or None
	if accuracy_m:
		doc.flags.location_accuracy_m = accuracy_m
	# How old the fix was and which provider gave it. Evidence for the row, not
	# inputs to the decision; junk is dropped rather than stored as a number.
	try:
		age = int(float(fix_age_s))
		if age >= 0:
			doc.flags.location_fix_age_s = age
	except (TypeError, ValueError):
		pass
	doc.flags.location_source = LOCATION_SOURCES.get(str(source or "").strip().lower(), "Unknown")

	if selfie_image:
		# only accept a file this user actually uploaded — a stale or borrowed
		# file_url must not stand in as proof of presence
		owner = frappe.db.get_value("File", {"file_url": selfie_image}, "owner")
		if owner != frappe.session.user:
			logger.warning(
				"[remote_checkin] rejected selfie %s (owner=%s) for %s",
				selfie_image,
				owner,
				frappe.session.user,
			)
			frappe.throw(_("Invalid selfie attachment."), frappe.PermissionError)
		doc.selfie_image = selfie_image
	doc.flags.ignore_permissions = True
	doc.insert()

	# minimal contract — don't expose the full doc as the endpoint's API
	return frappe._dict(
		name=doc.name,
		employee=doc.employee,
		employee_name=doc.employee_name,
		log_type=doc.log_type,
		time=doc.time,
		requires_remote_approval=doc.requires_remote_approval,
		remote_approval_status=doc.remote_approval_status,
		remote_reason=getattr(doc, "_remote_reason", None),
	)


@frappe.whitelist()
def get_unresolved_stale_in() -> dict:
	"""The session the 'Forgot to check out?' banner should offer to resolve:
	the employee's NEWEST IN with no OUT inside its session window that is
	already past the 06:00-next-day cutoff (employee wall clock).

	Walking the recent log — instead of only looking at the last row — is the
	point: checking in the next morning buries yesterday's forgotten checkout
	under a newer IN, and the sweeper's abandoned tag lands on the old row."""
	from datetime import timedelta

	from frappe.utils import add_days, cint, get_datetime

	employee = get_employee()
	if not employee:
		return {}

	now = employee_now(employee)
	# NEWEST first, then reversed: `time asc` with a limit truncates the newest
	# rows, which on a busy log are exactly the ones that say whether the session
	# is still open. Same shape as the punch lookup, for the same reason.
	rows = list(
		reversed(
			frappe.get_all(
				"Employee Checkin",
				filters={"employee": employee, "time": [">=", add_days(now, -10)]},
				fields=["name", "time", "log_type", "is_abandoned", "remote_approval_status"],
				order_by="time desc",
				limit=200,
			)
		)
	)
	# a REJECTED late-OUT doesn't close its session (mirrors the OT pairing
	# engine) — the employee must be able to resubmit a corrected time
	rows = [r for r in rows if not (r.log_type == "OUT" and r.remote_approval_status == "Rejected")]

	unresolved = {}
	for i, row in enumerate(rows):
		if row.log_type != "IN":
			continue
		next_row = rows[i + 1] if i + 1 < len(rows) else None
		if next_row and next_row.log_type == "OUT":
			continue  # session closed (a pending late-OUT also closes it)
		in_time = get_datetime(row.time)
		cutoff = (in_time + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
		if now < cutoff:
			continue  # still a live session (button shows Check Out)
		unresolved = {
			"name": row.name,
			"time": row.time,
			"is_abandoned": cint(row.is_abandoned),
		}

	logger.info(
		"[remote_checkin] unresolved stale IN for %s: %s",
		employee,
		unresolved.get("name") or "none",
	)
	return unresolved


@frappe.whitelist()
def submit_late_checkout(in_checkin: str, checkout_datetime: str, reason: str) -> dict:
	"""Retroactively submit a forgotten check-out.

	Validates that:
	  - `in_checkin` is an IN log belonging to the current user
	  - `checkout_datetime` is after the IN's time and not in the future
	  - if a LATER check-in exists (another record, never this one), the
	    check-out falls strictly before it — the error names that punch
	  - the IN isn't already followed by an OUT

	Creates an Employee Checkin with log_type=OUT at the given time
	(skipping geofence validation) and a Pending Remote Checkin Request
	with is_late_checkout=1 (via the after_insert hook).
	"""
	from frappe.utils import get_datetime

	if not in_checkin or not checkout_datetime or not (reason or "").strip():
		frappe.throw(_("Check-in reference, checkout time, and reason are required."))

	in_doc = frappe.db.get_value(
		"Employee Checkin",
		in_checkin,
		["name", "employee", "time", "log_type", "shift"],
		as_dict=True,
	)
	if not in_doc:
		frappe.throw(_("Original check-in not found."))

	employee_user = frappe.db.get_value("Employee", in_doc.employee, "user_id")
	if employee_user != frappe.session.user:
		frappe.throw(
			_("You can only submit a late check-out for your own session."),
			frappe.PermissionError,
		)

	if in_doc.log_type != "IN":
		frappe.throw(_("Selected record is not a check-in."))

	out_dt = get_datetime(checkout_datetime)
	in_dt = get_datetime(in_doc.time)
	if out_dt <= in_dt:
		frappe.throw(_("Check-out time must be after the check-in time ({0}).").format(in_doc.time))

	# Compare against the employee's own wall clock: the submitted time comes
	# from their device, and stored check-in times are in that same basis.
	if out_dt > employee_now(in_doc.employee):
		frappe.throw(_("Check-out time cannot be in the future."))

	# only OUTs inside THIS session window count: an OUT that belongs to a
	# newer session (after the employee's next IN) must not block resolving a
	# buried forgotten checkout
	from datetime import datetime, time, timedelta

	out_time_filter = [">=", in_doc.time]
	# The earliest IN that starts a NEW session, where "new session" means the
	# open one ENDED first. Two things end it:
	#   * an OUT — the session is closed, so the very next IN is a new one;
	#   * the day turning over — a forgotten check-out followed by the next
	#     morning's arrival is a new session even with no OUT between.
	# An IN before that boundary is the SAME open session, whether it landed a
	# second later (a double tap, a retried request) or eleven minutes later:
	# production carried a spurious 09:18:53 against a real 09:08 IN, and the
	# old 60-second window let it bound the check-out at the check-in itself,
	# refusing every submission that employee could ever make.
	#
	# ceiling: the day-turnover half of the boundary is calendar-date based, so
	# for a shift crossing midnight a duplicate punch after 00:00 is read as a
	# new session and bounds the window
	# upgrade: take the boundary from the IN's own shift window once
	# hrms.utils.shift_resolution is the single source for that
	session_close = frappe.db.get_value(
		"Employee Checkin",
		{"employee": in_doc.employee, "log_type": "OUT", "time": [">", in_dt]},
		["name", "time"],
		order_by="time asc",
		as_dict=True,
	)
	next_day = datetime.combine(in_dt.date() + timedelta(days=1), time.min)
	boundary = min(get_datetime(session_close.time), next_day) if session_close else next_day

	# Frappe v16 refuses "min(time)" as a SELECT string, so the row is taken
	# with an ordered limit. `name !=` stays: the record being resolved must
	# never come back as its own "next check-in".
	next_in = frappe.db.get_value(
		"Employee Checkin",
		{
			"employee": in_doc.employee,
			"log_type": "IN",
			"name": ["!=", in_doc.name],
			"time": [">=", boundary],
		},
		["name", "time"],
		order_by="time asc",
		as_dict=True,
	)
	if next_in:
		next_in_time = get_datetime(next_in.time)
		out_time_filter = ["between", [in_doc.time, next_in_time - timedelta(seconds=1)]]
		if out_dt >= next_in_time:
			frappe.throw(
				_("Check-out time must be before your next check-in {0} at {1}.").format(
					next_in.name, next_in_time
				)
			)
	# a rejected late-OUT must not block resubmitting a corrected time — but a
	# bare != filter would ALSO skip legacy rows with NULL status (SQL
	# three-valued logic), so probe non-rejected and never-set separately
	base_out_filters = {
		"employee": in_doc.employee,
		"log_type": "OUT",
		"time": out_time_filter,
	}
	later_out = frappe.db.exists(
		"Employee Checkin", {**base_out_filters, "remote_approval_status": ["!=", "Rejected"]}
	) or frappe.db.exists(
		"Employee Checkin", {**base_out_filters, "remote_approval_status": ["is", "not set"]}
	)
	if later_out:
		frappe.throw(_("A check-out for this session already exists."))

	out_doc = frappe.new_doc("Employee Checkin")
	out_doc.update(
		{
			"employee": in_doc.employee,
			"log_type": "OUT",
			"time": out_dt,
			"shift": in_doc.shift,
			"requires_remote_approval": 1,
			"remote_approval_status": "Pending",
		}
	)
	out_doc.flags.is_late_checkout = True
	# Name the IN being closed. Without it fetch_shift re-derives "the latest
	# unclosed IN", which can be a stale one from an earlier day, and the
	# forgotten check-out lands on the wrong session.
	out_doc.flags.late_checkout_in = in_doc.name
	out_doc._late_checkout_reason = reason.strip()
	out_doc.flags.ignore_permissions = True
	out_doc.insert()

	logger.info(
		"[remote_checkin] submit_late_checkout in=%s out=%s time=%s by=%s",
		in_checkin,
		out_doc.name,
		out_dt,
		frappe.session.user,
	)

	request_name = frappe.db.get_value(
		"Remote Checkin Request",
		{"checkin": out_doc.name},
		"name",
	)
	return {
		"ok": True,
		"checkin": out_doc.name,
		"request": request_name,
	}
