"""Remote check-in PWA endpoints.

hrms.api.remote_checkin.submit_remarks(request, employee_remarks)
hrms.api.remote_checkin.list_pending_for_approver()
hrms.api.remote_checkin.approve(request, approver_remarks)
hrms.api.remote_checkin.reject(request, approver_remarks)
hrms.api.remote_checkin.get_pending_count()  # for Profile badge
"""

from __future__ import annotations

import base64
import binascii
import logging
import re
import time as time_module
from datetime import timedelta

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Count
from frappe.utils import add_days, cint, get_datetime, now_datetime

from hrms.hr.utils import get_employees_routed_to
from hrms.utils.attendance_day_audit import SKIP_PREFIX
from hrms.utils.company_scope import permitted_company_filter
from hrms.utils.geofence import REASON_IMPRECISE_LOCATION, REASON_OUTSIDE_RADIUS, usable_accuracy
from hrms.utils.hr_removed_day import HR_REMOVED_DEVICE

#: The PWA names the provider it got the fix from; the row stores a word HR can read.
LOCATION_SOURCES = {"high": "GPS", "gps": "GPS", "coarse": "Network", "network": "Network"}
from hrms.utils.identity import get_employee, own_employees, require_employee
from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)

# What makes a later IN the start of a NEW session is not how long after this
# one it lands — it is whether an OUT closed this session first. This used to be
# a 60-second SAME_PUNCH_WINDOW, which caught a double tap and missed the real
# thing: production carried a duplicate IN 10m53s later with no OUT between, and
# that employee could never file a late check-out at all. No constant is right
# here, so there is no longer a constant.

#: Taps this close together are one tap. Nobody works twelve seconds: the shape
#: is somebody tapping again because the screen told them the wrong thing
#: (Norazlin, 4 Sep 2026 — IN 18:09:14, OUT 18:09:26, IN 18:09:30, read as a
#: twelve-second session and a dangling check-in). Deliberately much narrower
#: than the 60-second SAME_PUNCH_WINDOW this app once had and removed: that one
#: REFUSED the punch, and so refused real ones too.
BURST_WINDOW = timedelta(seconds=45)
#: A second IN this soon after an open IN is the SAME tap, not its check-out
#: (owner's rule, 21 Sep 2026: "a same-type tap within minutes is a duplicate,
#: not a session"). The one number `attendance_recovery.DUPLICATE_TAP_MINUTES`
#: uses to read a stored day; here it decides at tap time. Wider than
#: BURST_WINDOW and narrower in kind: the burst is any stutter, this is only
#: an IN repeating an open IN — OUT after OUT two minutes apart is still two
#: stored punches (Every Valid pays to the first).
DUPLICATE_TAP_WINDOW = timedelta(minutes=10)
#: Written on the skipped row in the form the Attendance Day Audit reads, so a
#: burst tap that was really a short session appears on HR's list with an
#: "unskip" beside it instead of sitting in a comment nobody opens.
BURST_SKIP_REASON = "Tapped again too soon after the punch before it"


def s3_key_from_public_url(url) -> str | None:
	"""The S3 object key inside a PUBLIC bucket url, or None. Pure.

	The S3 hook stores a public file as `{endpoint}/{bucket}/{key}` and a
	private one as the `generate_file` api url. Repairing the first into the
	second needs the key, and it must come back exactly as stored — it is
	already %-quoted and goes straight back into a url.

	Anything that is not a bucket url — a local /files path, an api url, an
	empty value — is not this function's business.
	"""
	text = (url or "").strip()
	if not text.startswith(("http://", "https://")):
		return None
	if "/api/method/" in text:
		# An ABSOLUTE url to this site's own endpoint is already the private
		# shape, just written with a host on the front. Splitting it on slashes
		# would read "api" as the bucket and rewrite a good photo's address to
		# nonsense — on a patch that runs once (review of 8c2f4c6eb).
		return None
	# scheme://host/bucket/key...
	parts = text.split("/", 4)
	if len(parts) < 5 or not parts[4]:
		return None
	return parts[4]


def _attach_selfie_to_punch(file_name, punch) -> None:
	"""Hang the photo on the punch it proves, so the right people can see it.

	A private File with no parent is readable by its owner and a System Manager
	and nobody else — which is the employee who took the selfie, and not the
	approver who has to look at it. Attached to the punch, `File.is_downloadable`
	grants anyone with read on that Employee Checkin, which is exactly the set
	that is allowed to judge it.

	It also gives the file a real `attached_to_doctype`. Without one the S3 hook
	reads the parent as "File", which no site's `ignore_s3_upload_for_doctype`
	lists — the path that took down every upload on 17 Sep 2026.
	"""
	if not file_name:
		logger.warning("[remote_checkin] punch %s has a selfie url with no File behind it", punch)
		return
	frappe.db.set_value(
		"File",
		file_name,
		{"attached_to_doctype": "Employee Checkin", "attached_to_name": punch},
		update_modified=False,
	)
	logger.info("[remote_checkin] selfie %s attached to punch %s", file_name, punch)


def is_burst_tap(previous, punch_time, log_type=None) -> bool:
	"""Is this punch a repeat of the one before it? Pure.

	`previous` is the newest punch this employee already has, as a row with
	`time` and `log_type` (and optionally `synced_from_instance` /
	`remote_approval_status`), or None. A mirrored row is not a finger on this
	phone, and a rejected punch is not a tap this one continues.

	Two shapes are one tap: any stutter inside BURST_WINDOW, and an IN within
	DUPLICATE_TAP_WINDOW of the IN before it. `log_type` is what the phone
	asked for; left out, the tap is read as a repeat of the previous one's type.
	"""
	if not previous or previous.get("synced_from_instance"):
		return False
	if (previous.get("remote_approval_status") or "") == "Rejected":
		return False
	earlier = get_datetime(previous.get("time"))
	if not earlier:
		return False
	gap = get_datetime(punch_time) - earlier
	if gap < timedelta(0):
		return False
	if gap < BURST_WINDOW:
		return True
	same_in = previous.get("log_type") == "IN" and (log_type or "IN") == "IN"
	return same_in and gap <= DUPLICATE_TAP_WINDOW


#: A forgotten check-out this long after the IN's shift actually ended (buffer
#: included) is a typo, not a session: refused at filing with advice (E28).
LATE_CHECKOUT_MAX_HOURS_AFTER_END = 12

#: What the camera may hand us. A punch photo is a JPEG frame; PNG is accepted
#: because a browser that cannot encode JPEG falls back to it.
SELFIE_MIMETYPES = {"image/jpeg": "jpg", "image/png": "png"}

#: A phone camera frame at the quality the sheet captures is well under this.
#: Anything larger is not a selfie, and the endpoint says so instead of
#: letting it through to the disk.
SELFIE_MAX_BYTES = 4 * 1024 * 1024


def _is_own_employee(employee: str | None) -> bool:
	"""Is `employee` the caller's own record — by the canonical resolver.

	The three self-checks in this module (edit my request, punch as myself,
	close my own session) compared `Employee.user_id` to the session raw. A
	mirror writes that column through `db.set_value` with case or whitespace
	drift; the app resolved the person, and these gates refused them their own
	forgotten check-out with "You can only submit a late check-out for your own
	session" (matrix probe, 15 Sep 2026). `own_employees` normalizes, is
	Active-only and fails closed on a duplicated login, like every row scope.
	"""
	allowed = bool(employee) and employee in own_employees(frappe.session.user)
	if not allowed:
		logger.info("[remote_checkin] %s is not %s's own employee", employee, frappe.session.user)
	return allowed


def _ensure_owner(request_name: str) -> dict:
	row = frappe.db.get_value(
		"Remote Checkin Request",
		request_name,
		["name", "employee", "status"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Request not found."))

	if not _is_own_employee(row.employee):
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

	# One rule with the Desk save gate: HR inside its fence, the approver on
	# file, the reports_to manager — never the request's own employee.
	from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import may_decide

	user = frappe.session.user
	if not may_decide(frappe._dict(row, doctype="Remote Checkin Request"), user):
		logger.warning(
			"[remote_checkin] DENY action by %s on %s (approver=%s)",
			user,
			request_name,
			row.approver,
		)
		frappe.throw(_("You are not the assigned approver for this request."), frappe.PermissionError)
	return row


@frappe.whitelist(methods=["POST"])
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

	ROUTED, not just STAMPED (21 Sep 2026). `resolve_approver` writes ONE name on
	the request when the punch is filed, but the whole chain above the employee
	may decide it — that is the owner's ruling, and the escalation an employee
	has when their approver forgets. Keying on the stamped name alone left a
	decidable request in nobody's queue: the senior approver could approve it and
	could not find it. `get_employees_routed_to` is the exact inverse of the list
	`may_decide` reads, so the queue and the decision gate cannot disagree.

	The company fence still applies to BOTH arms — it is applied once, below, to
	the whole query. An auto-routed queue stays fenced (see
	test_approval_scoping_invariant).
	"""
	RemoteCheckinRequest = frappe.qb.DocType("Remote Checkin Request")
	routed = get_employees_routed_to(user, "shift_request_approver", "shift_request_approver")
	addressed = RemoteCheckinRequest.approver == user
	if routed:
		addressed = addressed | RemoteCheckinRequest.employee.isin(routed)
		logger.debug("[api] remote_checkin pending for %s covers %d routed employee(s)", user, len(routed))
	query = (
		frappe.qb.from_(RemoteCheckinRequest)
		.where(RemoteCheckinRequest.status.isin(list(statuses)))
		.where(addressed)
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


@frappe.whitelist(methods=["GET", "POST"])
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


@frappe.whitelist(methods=["GET", "POST"])
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


@frappe.whitelist(methods=["GET", "POST"])
def get_pending_count() -> int:
	"""Badge count — must use the same fence as the list it opens."""
	user = frappe.session.user
	query, RemoteCheckinRequest = _pending_for_approver_query(user)
	result = query.select(Count(RemoteCheckinRequest.name)).run()
	count = result[0][0] if result else 0
	logger.info("[remote_checkin] pending_count user=%s -> %d", user, count)
	return int(count or 0)


def _decide(request: str, decision: str, approver_remarks: str) -> dict:
	# Lock the row BEFORE reading its state — the same gate approval.decide,
	# finalize and correction_cancel take. Without it Approve and Reject in the
	# same second both read Pending, both save, and the punch is propagated
	# twice. The second decider now waits and reads the settled status, so the
	# Pending check below is the idempotency gate (audit D-H2).
	frappe.db.get_value("Remote Checkin Request", request, "status", for_update=True)
	row = _ensure_approver(request)
	if row.status != "Pending":
		frappe.throw(_("This request has already been decided."))
	# The one decision rule (audit P0-10, as approval.decide): "Not approved"
	# says why, so the employee has something to act on. After the access and
	# state checks, so those still answer first.
	approver_remarks = (approver_remarks or "").strip()
	if decision == "Rejected" and not approver_remarks:
		frappe.throw(_("Say why this is not approved."), frappe.ValidationError)

	doc = frappe.get_doc("Remote Checkin Request", request)
	doc.status = decision
	doc.approver_remarks = approver_remarks
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
	# Set by the on_update hook when this was a late check-out: the approver
	# must see whether the day was actually rebuilt, not just "approved" (E1).
	repair = doc.flags.get("late_checkout_repair")
	return {
		"ok": True,
		"name": request,
		"status": decision,
		"attendance_repair": dict(repair) if repair else None,
	}


@frappe.whitelist(methods=["POST"])
def approve(request: str, approver_remarks: str = "") -> dict:
	return _decide(request, "Approved", approver_remarks)


@frappe.whitelist(methods=["POST"])
def reject(request: str, approver_remarks: str = "") -> dict:
	return _decide(request, "Rejected", approver_remarks)


def session_open_until(in_time, shift_actual_end=None):
	"""When a check-in's session stops being "still on shift": 06:00 the morning
	after it, or its shift's own check-out window if that ends later (a 22:00-
	06:00 shift checks out until 07:00). ONE rule for the button, Home's timer,
	the punch and the forgot-to-check-out banner (employee report, 25 Sep 2026:
	the phone gave up after 16 h and offered Check in at 01:00-03:00)."""
	from datetime import timedelta

	in_time = get_datetime(in_time)
	cutoff = (in_time + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
	if shift_actual_end:
		cutoff = max(cutoff, get_datetime(shift_actual_end))
	return cutoff


def _session_is_live(in_time, now, shift_actual_end=None) -> bool:
	"""Still the same session: before `session_open_until`."""
	return now < session_open_until(in_time, shift_actual_end)


def resolve_punch_type(recent_rows, requested: str, now, window_now=None):
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

	# KILL SWITCH, no migration and no restart of the decision anywhere else:
	# set `"disable_punch_type_correction": 1` in site_config.json and every
	# punch is stored exactly as the client asked, i.e. the behaviour before
	# this rule existed. It is here because this is the one change in the batch
	# that WRITES different data than before; if it ever misreads a real shift
	# pattern, the remedy should be one flag, not rolling back a stack of
	# commits while people are trying to clock in.
	if cint(frappe.conf.get("disable_punch_type_correction")):
		logger.warning("[remote_checkin] punch-type correction disabled by site config")
		return requested, None

	# A REJECTED late-OUT never closed its session — the same rule the banner
	# and the OT pairing engine already apply. Mirrored rows are excluded for
	# the reason the sweeper excludes them (checkin_sweeper, single writer): a
	# session pulled from the source instance can never be tagged abandoned
	# here, so it would coerce local punches with nothing able to clear it.
	rows = sorted(
		(
			r
			for r in recent_rows
			if not (r.log_type == "OUT" and r.get("remote_approval_status") == "Rejected")
			and not r.get("synced_from_instance")
			# The marker HR's Shift Attendance editor leaves on a removed day is not a
			# punch; untyped, it would switch this correction off for 3 days.
			and r.get("device_id") != HR_REMOVED_DEVICE
		),
		# Ties are reachable: before_validate truncates to whole seconds and
		# validate_duplicate_log filters ON log_type, so an IN and an OUT at the
		# same second both insert. Without the tie-break the answer came from
		# whatever order the database happened to return.
		key=lambda r: (get_datetime(r.time), 0 if r.log_type == "IN" else 1),
	)

	# INCOMPLETE EVIDENCE IS NOT A LICENCE TO GUESS. log_type is an OPTIONAL
	# Select with a blank first option, and untyped rows are real here —
	# hrms/sync/checkin_recovery.py exists to infer them. With one untyped punch
	# between an IN and its OUT the walk below reads a CLOSED session as open,
	# and a genuine second-session arrival becomes its check-out: the evening
	# block never opens and those hours vanish behind an ordinary-looking row.
	#
	# ASKED OF `rows`, NOT `recent_rows`, AND THE ORDER IS THE WHOLE POINT. The
	# filter above has already dropped the rows the walk will never read — a
	# mirrored punch, a rejected late-OUT. Asking the question before the filter
	# let one of those, if it also happened to be untyped, switch the correction
	# off for that employee's entire window, with nothing to tell an operator
	# that protection had stopped. The guard must judge the evidence the walk
	# actually reads.
	if any(r.log_type not in ("IN", "OUT") for r in rows):
		logger.info("[remote_checkin] untyped punch in the window — leaving %s as asked", requested)
		return requested, None

	# WHAT DECIDES WHETHER A SESSION IS OPEN IS THE LAST THING THAT HAPPENED.
	# The window is sorted, so the newest row answers it: an OUT means the
	# employee has left, whatever the shape of the rows before it.
	#
	# This used to scan for "an IN whose next row is not an OUT" and keep the
	# last such row, which is a different question and gives a different answer
	# on exactly the logs this rule exists to protect. On [IN 08:00, IN 09:00,
	# OUT 12:00] — a log the defect has ALREADY damaged, a stray arrival, the
	# real one, and a genuine departure — that scan returns the 08:00 ORPHAN,
	# two rows back and long dead. A 14:00 arrival was then written as its
	# check-out: a six-hour block nobody worked appears, and the real afternoon
	# session never opens. The rule was manufacturing hours on the very people
	# it was added for.
	open_in = rows[-1] if rows and rows[-1].log_type == "IN" else None
	if not open_in or cint(open_in.get("is_abandoned")):
		return "IN", None

	# THE SMALL HOURS, DECIDED ON EVIDENCE RATHER THAN ON THE CLOCK.
	#
	# A punch between midnight and 06:00 used to be exempt outright. The 06:00
	# cutoff was written for a READ — should the banner offer to resolve? —
	# where a false "live" costs a banner. Reused for a WRITE it destroys a real
	# arrival: someone on an early shift who forgot yesterday's check-out would
	# have their 05:30 arrival recorded as yesterday's DEPARTURE, and because
	# the session then looks properly closed, the banner, the sweeper and the
	# audit report would all read that day as healthy.
	#
	# But a blanket exemption also left NIGHT SHIFTS unguarded through the back
	# half of their own shift. A 19:00-03:30 worker who double-taps at 02:00 is
	# inside their session, and that second tap is the same impossible event
	# this rule exists to catch — nobody arrives twice without leaving. So the
	# shape being corrected all day came straight back after midnight, on
	# precisely the people whose working hours live there.
	#
	# The open row's OWN shift window separates the two cases: at 02:00 a shift
	# running to 05:00 is still going; at 05:30 yesterday's shift ended ten
	# hours ago. With no shift stamped there is no evidence either way, and the
	# row the user asked for stands — which is the old behaviour, kept for
	# exactly the situation it was right about.
	if now.hour < 6:
		shift_close = (
			get_datetime(open_in.get("shift_actual_end")) if open_in.get("shift_actual_end") else None
		)
		if not shift_close or now >= shift_close:
			# The open day shift is over but its session is not (06:00): is this
			# tap the check-out, or a NEW shift's arrival? `window_now` is the
			# shift occurrence whose check-in window covers `now`, found by the
			# caller: a later occurrence than the open IN's = an arrival (an
			# early shift, yesterday's check-out forgotten); none at all = the
			# person is still going and this ends the day (employee report,
			# 25 Sep 2026: "worked till 3 am, had to check in again").
			# Unknown (None, a caller that did not look) keeps the old rule.
			arrival = window_now and get_datetime(window_now.actual_start) > get_datetime(open_in.time)
			if window_now is None or arrival:
				logger.info(
					"[remote_checkin] %s in the 00:00-06:00 band, shift closed %s, new shift %s — leaving as asked",
					requested,
					shift_close,
					bool(arrival),
				)
				return requested, None
			logger.info("[remote_checkin] %s at %s ends the open session %s", requested, now, open_in.name)
	if not _session_is_live(get_datetime(open_in.time), now, open_in.get("shift_actual_end")):
		return "IN", None
	# A second IN minutes after the open one is the same tap, not a one-minute
	# session: stored as asked and stamped noise by `is_burst_tap`, so the day
	# reads straight across it (owner's rule, 21 Sep 2026).
	if now - get_datetime(open_in.time) <= DUPLICATE_TAP_WINDOW:
		logger.info(
			"[remote_checkin] IN repeats %s within %s — a duplicate tap", open_in.name, DUPLICATE_TAP_WINDOW
		)
		return "IN", None

	logger.warning(
		"[remote_checkin] IN requested while %s is still open — recording a check-out instead",
		open_in.name,
	)
	return "OUT", open_in


def _window_now(employee, when):
	"""The shift occurrence whose check-in window covers `when`, or False when
	none does. Only asked for in the small hours (the one place it decides)."""
	if get_datetime(when).hour >= 6:
		return None
	from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift

	window = get_actual_start_end_datetime_of_shift(employee, get_datetime(when), True)
	return window or False


@frappe.whitelist(methods=["POST"])
def upload_selfie(image: str) -> dict:
	"""Store one punch photo and return the URL the punch will carry.

	The PWA used to POST the frame to frappe's generic `upload_file` as a
	PUBLIC file. A site with System Settings ->
	`only_allow_system_managers_to_upload_public_files` on refuses that for
	every non-System-Manager, and frappe's friendly guard around it catches the
	BUILTIN PermissionError rather than `frappe.exceptions.PermissionError`, so
	the refusal never became a sentence — the phone showed the bare class name
	("Selfie failed / frappe.exceptions.PermissionError", live 15 Sep 2026;
	reproduced on a bench 17 Sep 2026). The photo was lost and the punch went
	in without its evidence.

	So the frame is stored here, the same way `punch()` stores the punch: staff
	hold no create rights of their own on either doctype, and this endpoint is
	the whole write path. The file is owned by the caller, and `punch()` only
	accepts a `selfie_image` whose File the caller owns — so nothing widens.

	The file is PRIVATE and is attached to its punch as soon as the punch exists
	(`_attach_selfie_to_punch`). Public was the shortcut, and it broke in the
	approver's app on 18 Sep 2026: with S3 configured, a public File's stored
	url is the bucket object itself, and the bucket does not serve objects to
	the public — so Remote Approvals showed a broken image where the face should
	be. A private File is streamed back through the site instead, which also
	stops a face photo being readable by anyone holding the link.
	"""
	employee = require_employee()

	header, _sep, payload = (image or "").partition(",")
	mimetype = header[5:].split(";")[0].strip().lower() if header.startswith("data:") else ""
	extension = SELFIE_MIMETYPES.get(mimetype)
	if not extension or not payload:
		logger.warning("[remote_checkin] selfie refused for %s: mimetype=%r", employee, mimetype)
		frappe.throw(_("A check-in photo must be a JPEG or PNG image."))

	try:
		content = base64.b64decode(payload, validate=True)
	except (binascii.Error, ValueError):
		logger.warning("[remote_checkin] selfie refused for %s: undecodable frame", employee)
		frappe.throw(_("The check-in photo could not be read. Try again."))

	if len(content) > SELFIE_MAX_BYTES:
		logger.warning(
			"[remote_checkin] selfie refused for %s: %d bytes over the %d limit",
			employee,
			len(content),
			SELFIE_MAX_BYTES,
		)
		frappe.throw(_("The check-in photo is too large."))

	# The employee id is server-resolved, not user input, but it reaches a
	# filename — a naming series or a mirrored record producing anything
	# stranger than HR-EMP-0001 must not be able to shape a path.
	slug = re.sub(r"[^A-Za-z0-9_-]", "", str(employee))[:40] or "employee"
	stored = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"selfie-{slug}-{int(time_module.time() * 1000)}.{extension}",
			"content": content,
			# Private, and attached to the punch by `_attach_selfie_to_punch`
			# the moment the punch exists: that is what makes it readable by the
			# approver and by nobody else with the link.
			"is_private": 1,
			"folder": "Home",
		}
	).insert(ignore_permissions=True)
	logger.info("[remote_checkin] selfie stored for %s: %s", employee, stored.file_url)
	return {"file_url": stored.file_url, "name": stored.name}


@frappe.whitelist(methods=["POST"])
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
	client_tap_id=None,
) -> dict:
	"""PWA check-in/out — the only write path staff have into Employee Checkin.

	`client_tap_id` is the phone's own id for the INTENDED tap, kept and re-sent
	until a 2xx lands. A punch carrying an id this employee's log already holds
	is the same tap again — the stored row is answered and nothing is inserted
	— so a retry after a lost response can never be read as a second tap and
	coerced into a two-minute session (audit E-H2). Taps without an id (Desk,
	imports, older clients) go through the burst rule exactly as before.
	"""
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
	if not _is_own_employee(employee):
		frappe.throw(_("You can only check in as yourself."), frappe.PermissionError)

	if log_type not in ("IN", "OUT"):
		frappe.throw(_("Invalid log type."))

	# The phone proposes; the server decides. Nothing existing is touched — this
	# only chooses the type of the row about to be created, so there is no
	# overwrite to get wrong and no punch is ever dropped.
	# Two taps in flight together must queue. Burst detection below is
	# read-then-insert: two POSTs that both read an empty log both count
	# (audit D-M1). The Employee row is the lock every attendance writer takes
	# (lock_employee_row); held until this request commits, so the second tap
	# reads the first one's row and is stored as the stutter it is.
	frappe.db.get_value("Employee", employee, "name", for_update=True)

	client_tap_id = (client_tap_id or "").strip() or None
	# The retry's fast path: the tap is already stored, so answer that row. A
	# PLAIN read — a locking read that MISSES takes a gap lock on the index,
	# and two employees tapping at once could deadlock on it. The race this
	# read can lose (same id, both POSTs in flight) is settled by the unique
	# index at insert time below.
	doc = _stored_tap(employee, client_tap_id) if client_tap_id else None
	accuracy_m = getattr(doc, "location_accuracy_m", None) if doc else None
	if doc is None:
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
					fields=[
						"name",
						"time",
						"log_type",
						"is_abandoned",
						"remote_approval_status",
						"synced_from_instance",
						"shift_actual_end",
						"device_id",
					],
					order_by="time desc",
					limit=100,
				)
			)
		)
		requested_type = log_type
		resolved_type, closing = resolve_punch_type(
			recent, log_type, get_datetime(punch_time), window_now=_window_now(employee, punch_time)
		)
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
				"client_tap_id": client_tap_id,
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

		selfie_file = None
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
			selfie_file = frappe.db.get_value("File", {"file_url": selfie_image}, "name")

		# Taps seconds apart are one tap. The row is STORED — its time, its type and
		# its selfie are evidence, and the old 60-second window that REFUSED such a
		# punch also refused real ones — but it does not count toward the day, so a
		# stutter can never write a twelve-second session. HR brings it back from
		# Fix Day in one click if it was real.
		burst = is_burst_tap(recent[-1] if recent else None, punch_time, requested_type)
		burst_gap_s = 0
		if burst:
			doc.skip_auto_attendance = 1
			# Noise by definition — a stutter on the same tap, or an IN repeating
			# the open IN minutes later. The day is read straight across it
			# (shift_type.splits_the_day).
			doc.skipped_as_noise = 1
			burst_gap_s = int((get_datetime(punch_time) - get_datetime(recent[-1].time)).total_seconds())
			logger.warning(
				"[remote_checkin] %s tapped again %ss after the punch before — stored, not counted",
				employee,
				burst_gap_s,
			)

		doc.flags.ignore_permissions = True
		try:
			doc.insert()
		except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
			# The phone's retry overtook its first POST: the unique index on
			# client_tap_id refused this second row. Answer the row that won —
			# locked, because it exists now and this transaction's snapshot may
			# predate it (a locking read of an EXISTING unique key takes no gap).
			logger.warning(
				"[remote_checkin] %s tap %s already stored — answering it", employee, client_tap_id
			)
			doc = _stored_tap(employee, client_tap_id, lock=True)
			if doc is None:
				raise
			accuracy_m = getattr(doc, "location_accuracy_m", None)
			selfie_image = burst = False
			resolved_type = requested_type

		if selfie_image:
			_attach_selfie_to_punch(selfie_file, doc.name)

		if burst:
			# "Comment", not "Info": add_comment's first argument IS the stored
			# Comment.comment_type, and every reader of a skip reason filters
			# comment_type == "Comment". Written as "Info" the row is never seen,
			# and the audit shows the punch skipped with no reason and no way back.
			doc.add_comment(
				"Comment",
				_("{0}: {1} ({2}s). Restore it from Fix Day if it was a real punch.").format(
					SKIP_PREFIX, BURST_SKIP_REASON, burst_gap_s
				),
			)

		if resolved_type != requested_type:
			# A DURABLE trace, not just a log line. HR reading Employee Checkin must
			# be able to tell a server-corrected OUT from a hand-tapped one — and
			# when somebody disputes their hours, the evidence cannot live only in an
			# application log that rotates.
			doc.add_comment(
				"Info",
				_("Recorded as {0}: {1} was requested while {2} was still open.").format(
					resolved_type, requested_type, closing.name if closing else "an earlier session"
				),
			)

	return _punch_result(doc, accuracy_m=accuracy_m)


def _approver_name(doc) -> str:
	"""The full name of whoever decides this punch's request, or ""."""
	if not cint(doc.get("requires_remote_approval")):
		return ""
	login = frappe.db.get_value("Remote Checkin Request", {"checkin": doc.name}, "approver")
	return (frappe.db.get_value("User", login, "full_name") or "") if login else ""


def _punch_result(doc, accuracy_m=None) -> dict:
	"""The endpoint's answer for a stored punch — minimal contract, never the
	full doc. One builder, so a replayed tap and a fresh one read the same."""
	return frappe._dict(
		name=doc.name,
		employee=doc.employee,
		employee_name=doc.employee_name,
		log_type=doc.log_type,
		time=doc.time,
		requires_remote_approval=doc.requires_remote_approval,
		remote_approval_status=doc.remote_approval_status,
		remote_reason=getattr(doc, "_remote_reason", None) or _reason_on_record(doc),
		# Who decides, by NAME: the toast read "Pending approval from
		# muhammadnurhafiz@…" (owner screenshot, 25 Sep 2026).
		approver_name=_approver_name(doc),
		# The accuracy the DECISION was made on, echoed like check_geofence
		# does. The phone must not re-read its own live fix to judge how coarse
		# the reading was: a newer one lands during the round trip, and the
		# dialog would then caveat — or fail to caveat — a verdict that was
		# reached on a different reading entirely.
		accuracy_m=accuracy_m or 0,
	)


#: Read back from the row what the override keeps in memory only: it writes
#: `geofence_outcome` "Imprecise" for REASON_IMPRECISE_LOCATION and "Outside"
#: for REASON_OUTSIDE_RADIUS (employee_checkin_override.py, `_remote_reason`).
_REASON_BY_OUTCOME = {"Imprecise": REASON_IMPRECISE_LOCATION, "Outside": REASON_OUTSIDE_RADIUS}


def _reason_on_record(doc) -> str | None:
	"""Why a stored punch needed approving, for a row answered again.

	`_remote_reason` lives on the in-memory doc of the request that inserted
	it; a replay reads the row back and would otherwise answer None, which the
	PWA renders as the "outside radius" wording for an unplaceable reading.
	"""
	if not cint(getattr(doc, "requires_remote_approval", 0)):
		return None
	return _REASON_BY_OUTCOME.get(getattr(doc, "geofence_outcome", None), REASON_OUTSIDE_RADIUS)


def _stored_tap(employee, client_tap_id, lock=False):
	"""The Employee Checkin this employee already stored for this tap id, or None.

	`lock` is for the one caller that KNOWS the row exists (the insert was
	just refused as a duplicate): FOR UPDATE reads the latest committed row
	past this transaction's snapshot, and on an existing unique key it takes a
	record lock only. Never lock a lookup that may miss — a miss gap-locks the
	index and two employees' punches can deadlock.
	"""
	name = frappe.db.get_value(
		"Employee Checkin",
		{"employee": employee, "client_tap_id": client_tap_id},
		"name",
		for_update=lock,
	)
	if not name:
		return None
	logger.info("[remote_checkin] %s replayed tap -> %s", employee, name)
	return frappe.get_doc("Employee Checkin", name)


@frappe.whitelist(methods=["GET", "POST"])
def get_unresolved_stale_in() -> dict:
	"""The session the 'Forgot to check out?' banner should offer to resolve:
	the employee's NEWEST IN with no OUT inside its session window that is
	already past the 06:00-next-day cutoff (employee wall clock).

	Walking the recent log — instead of only looking at the last row — is the
	point: checking in the next morning buries yesterday's forgotten checkout
	under a newer IN, and the sweeper's abandoned tag lands on the old row."""
	from collections import Counter

	from frappe.utils import add_days, cint, get_datetime

	from hrms.utils.shift_resolution import counts_toward_session, session_is_open

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
				fields=[
					"name",
					"time",
					"log_type",
					"is_abandoned",
					"remote_approval_status",
					"skip_auto_attendance",
					"shift",
					"shift_start",
					"shift_actual_end",
				],
				order_by="time desc",
				limit=200,
			)
		)
	)
	# a REJECTED punch neither closes nor is a session (mirrors the OT pairing
	# engine) — after a rejected late-OUT the employee must be able to resubmit
	rows = [r for r in rows if r.remote_approval_status != "Rejected"]

	# W3: live shifts pair "Alternating entries" within the shift group, so an
	# IN that is the group's even-numbered punch (08:55 IN, 18:31 IN) is the
	# check-out, and a later punch of the group closes the one before it. The
	# same open-session rule the shift stamp uses; unshifted punches keep the
	# log_type rule below.
	def group(row):
		if not row.get("shift") or not counts_toward_session(row):
			return None
		return (row.shift, str(row.shift_start))

	totals = Counter(key for key in map(group, rows) if key)
	seen = Counter()
	unresolved = {}
	for i, row in enumerate(rows):
		key = group(row)
		if key:
			seen[key] += 1
		if row.log_type != "IN":
			continue
		if key and (not session_is_open(seen[key], row.log_type) or totals[key] > seen[key]):
			continue  # the shift's own pairing already closed this session
		next_row = rows[i + 1] if i + 1 < len(rows) else None
		if next_row and next_row.log_type == "OUT":
			continue  # session closed (a pending late-OUT also closes it)
		if _session_is_live(get_datetime(row.time), now, row.get("shift_actual_end")):
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


def session_boundary(in_dt, shift_actual_end, session_close_time):
	"""When the session opened at `in_dt` is over, for deciding which later IN
	starts a NEW one.

	Two things end a session: an OUT, and the day turning over — a forgotten
	check-out followed by the next morning's arrival is a new session even with
	no OUT between. The first is exact. The second was calendar midnight, which
	is the right turnover for a shift living inside one date and the wrong one
	for every shift that crosses it.

	On a 19:00-03:30 shift midnight falls in the MIDDLE of the session, so a
	duplicate punch at 00:05 — the very shape the punch-type correction exists
	to prevent — was read as the next session's arrival and bounded the window
	at itself. The employee was then told their check-out "must be before your
	next check-in at 00:05", and no time they could enter would be accepted:
	every night-shift worker who forgot to clock out was locked out of the one
	repair available to them.

	So the turnover comes from the session's own shift window when the IN
	carries one, and is never earlier than midnight — a shift whose GRACE WINDOW
	closes before midnight keeps exactly the boundary it had, and one that runs
	past midnight gets a boundary sitting after it ends rather than inside it.
	Note the grace window, not the shift: an evening shift ending 23:30 with the
	default hour of `allow_check_out_after_shift_end_time` closes at 00:30, so
	its boundary moves by that half hour too. That is the same rule, applied
	honestly — the session really does run past midnight. A punch with no shift
	stamp (off shift, or an assignment that no longer resolves) falls back to
	the calendar, which is all the evidence there is.

	Pure, so the rule is testable without a bench.
	"""
	from datetime import datetime, time, timedelta

	next_day = datetime.combine(in_dt.date() + timedelta(days=1), time.min)
	shift_close = get_datetime(shift_actual_end) if shift_actual_end else None
	day_turnover = max(next_day, shift_close) if shift_close else next_day
	if session_close_time:
		return min(get_datetime(session_close_time), day_turnover)
	return day_turnover


def leaves_consecutive_outs(sequence, out_dt) -> bool:
	"""Would adding an OUT at `out_dt` leave two check-outs in a row?

	`sequence` is the employee's punches from the session's IN onward, ascending,
	as dicts with `time` and `log_type`. Rejected late check-outs are dropped:
	one never closed anything, which is what lets an employee resubmit a
	corrected time after a refusal.

	This is the test that separates a legitimate buried repair from a duplicate
	check-out, and no comparison of times can do it — both shapes read IN, IN,
	OUT in time order. Filing an OUT into the gap of a session that was later
	closed normally puts two departures next to each other with no arrival
	between them, which is impossible; filing one before a genuinely new session
	does not.

	The mirror of `resolve_punch_type`'s rule at the other end of the session:
	nobody leaves twice without arriving.

	Pure, so the rule is testable without a bench.
	"""
	entries = [
		("OUT" if row.get("log_type") == "OUT" else "IN", get_datetime(row.get("time")), False)
		for row in sequence
		if row.get("log_type") in ("IN", "OUT")
		and not (row.get("log_type") == "OUT" and row.get("remote_approval_status") == "Rejected")
	]
	entries.append(("OUT", get_datetime(out_dt), True))
	# An IN and an OUT at the same instant order IN first — the arrival cannot
	# follow its own departure — matching resolve_punch_type's tie-break.
	entries.sort(key=lambda e: (e[1], 0 if e[0] == "IN" else 1))

	# ONLY THE NEIGHBOURS OF THE ROW BEING INSERTED. Asking "does the whole
	# sequence contain an adjacent pair" is a different, stricter question, and
	# it refuses honest work: a log that ALREADY carries two adjacent OUTs
	# somewhere — which is exactly the damage an earlier version of this very
	# function could produce, and also what the hub leaves behind when the same
	# punch is pulled twice — would block the repair of an unrelated EARLIER
	# session, under a message about a check-out that has nothing to do with it.
	# This row may not create an adjacency. It is not responsible for the ones
	# it finds.
	i = next(k for k, entry in enumerate(entries) if entry[2])
	before = entries[i - 1][0] if i else None
	after = entries[i + 1][0] if i + 1 < len(entries) else None
	return before == "OUT" or after == "OUT"


@frappe.whitelist(methods=["POST"])
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
	from datetime import timedelta

	if not in_checkin or not checkout_datetime or not (reason or "").strip():
		frappe.throw(_("Check-in reference, checkout time, and reason are required."))

	in_doc = frappe.db.get_value(
		"Employee Checkin",
		in_checkin,
		["name", "employee", "time", "log_type", "shift", "shift_actual_end"],
		as_dict=True,
	)
	if not in_doc:
		frappe.throw(_("Original check-in not found."))

	if not _is_own_employee(in_doc.employee):
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

	# E28: any gap used to be accepted, so the next day's time or the wrong
	# month filed a 30-hour session and the day was rebuilt around it.
	if in_doc.shift_actual_end:
		latest = get_datetime(in_doc.shift_actual_end) + timedelta(hours=LATE_CHECKOUT_MAX_HOURS_AFTER_END)
		if out_dt > latest:
			logger.info(
				"[remote_checkin] late check-out %s refused: %s is past %s", in_doc.name, out_dt, latest
			)
			frappe.throw(
				_(
					"That check-out is more than {0} hours after your shift ended ({1}). "
					"Pick the time you really left, or ask HR to correct the day."
				).format(LATE_CHECKOUT_MAX_HOURS_AFTER_END, get_datetime(in_doc.shift_actual_end))
			)

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
	# What ends this session, and therefore which later IN starts a new one —
	# see session_boundary, which carries the rule and the reason.
	session_close = frappe.db.get_value(
		"Employee Checkin",
		{"employee": in_doc.employee, "log_type": "OUT", "time": [">", in_dt]},
		["name", "time"],
		order_by="time asc",
		as_dict=True,
	)
	boundary = session_boundary(in_dt, in_doc.shift_actual_end, session_close.time if session_close else None)
	logger.info(
		"[remote_checkin] late check-out session boundary for %s: %s (shift close %s)",
		in_doc.name,
		boundary,
		in_doc.shift_actual_end,
	)

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
	if next_in and out_dt >= get_datetime(next_in.time):
		frappe.throw(
			_("Check-out time must be before your next check-in {0} at {1}.").format(
				next_in.name, get_datetime(next_in.time)
			)
		)

	# THE REFUSAL AND THE SEARCH ANSWER DIFFERENT QUESTIONS, SO THEY TAKE
	# DIFFERENT EDGES.
	#
	# NO TIME EDGE SEPARATES THE TWO SHAPES, WHICH IS WHY TWO ATTEMPTS TRADED
	# PLACES. In time order they are identical — an IN, another IN, an OUT — and
	# a boundary drawn anywhere either blocks the legitimate repair or admits the
	# corrupting one:
	#
	#   REPAIR   IN 19:00 forgotten · IN 01:00 new session · OUT 02:00 closes it
	#            filing an OUT at 00:30 is correct and must be ALLOWED
	#   CORRUPT  IN 09:08 · stray IN 09:18 (a double tap) · OUT 18:00 closes it
	#            filing an OUT at 12:08 puts TWO check-outs on one session
	#
	# What tells them apart is not when the OUT lands but what the sequence looks
	# like afterwards. In the repair the new OUT closes the first IN and the
	# second IN still has its own OUT. In the corruption two OUTs end up adjacent
	# with no arrival between them — the exact mirror of the rule
	# `resolve_punch_type` already enforces at the other end: nobody leaves twice
	# without arriving, just as nobody arrives twice without leaving.
	#
	# Rejected late check-outs are excluded because a rejected one never closed
	# anything, which is what lets an employee resubmit a corrected time.
	# NO ROW LIMIT, AND NO FORWARD BOUND EITHER.
	#
	# The row limit came first and was the wrong axis: an ascending fetch with a
	# limit truncates the NEWEST rows, so past it the genuine closing OUT was
	# invisible and the guard failed open silently — measured, 204 stray INs
	# between an arrival and its 18:00 departure, and a second check-out was
	# accepted.
	#
	# Replacing it with a two-day forward window was the SAME defect on a new
	# axis, which is why it is gone too. `next_in` cannot justify such a bound:
	# it searches for ARRIVALS, and the row this guard must see is a DEPARTURE —
	# nothing requires an arrival to sit between the two. A Friday-to-Monday
	# weekend reaches it, and so does the production double-tap whose close
	# arrives days later; the banner offers exactly those rows. The feature's own
	# horizons disagree anyway (the pairing engine looks back fourteen days, the
	# stale-IN banner ten), so any number chosen here would have been arbitrary.
	#
	# Scoped to ONE employee from ONE arrival forward, this is single digits of
	# rows in practice.
	sequence = frappe.get_all(
		"Employee Checkin",
		filters={"employee": in_doc.employee, "time": [">=", in_doc.time]},
		fields=["name", "time", "log_type", "remote_approval_status"],
		order_by="time asc",
		limit_page_length=0,
	)
	later_out = leaves_consecutive_outs(sequence, out_dt)
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
