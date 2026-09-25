"""Remote Checkin Request doc_event handlers + notification helpers.

Late check-out repair, for other callers (the attendance recovery's rebuild
step, section e):

    reprocess_late_checkout_attendance(out_checkin: str, attempt: int = 0, from_recovery: bool = False) -> frappe._dict

The OUT punch's name is all it needs. It rebuilds the whole shift day the OUT
closes (linked + unlinked punches, hours and overtime through the Shift Type's
own rule) inside a savepoint, and never commits. Side effects on refusal: a
Desk message, a retry job after commit for a transient blocker, and — for a
final refusal — one Error Log + HR alert per request and a machine-readable
Comment on the request (below). Result keys:

    repaired        bool
    reason_code     None on success, else one of the codes below
    message         plain text for a person
    attendance      the Attendance name involved, or None
    status          the rebuilt row's status (success only)
    working_hours   the rebuilt row's hours (success only)
    attendance_date the shift day (success only)
    will_retry      a job (or the hourly job) will apply it later
    hr_notified     HR was told this once

Refusal codes and who clears them:

    today                the shift may still be running — queued after the shift ends (E19)
    pending_punch        another punch of the shift awaits approval — retried when decided
    locked               another write held the day — retried after commit
    financial_lock       approved OT / RL / payroll uses the day — HR
    hr_marked            HR corrected the day by hand, or another site owns it — HR
    hr_removed           HR removed the day in Shift Attendance — HR
    not_eligible         the OUT is not an approved local punch — HR
    no_open_shift        the IN it closes is not on a shift — HR
    duplicate_attendance two rows cover the shift — HR
    attendance_mismatch  the row belongs to another shift — HR
    cross_boundary       linked punches from another shift or site — HR
    other_attendance     a punch is already counted elsewhere — HR
    incomplete_pairs     the punches do not pair up — HR
    not_markable         the shift does not mark this day (holiday) — HR
    rebuild_failed       the rebuild raised; the old row was kept — HR
    not_found            the OUT punch no longer exists — HR

A final refusal (anything but `today`, and a transient one once its retries
are spent) is written on the request as a Comment
"REFUSAL_COMMENT_PREFIX <code> — <message>" so a later pass can read the
blocker back (`last_refusal_code(request)`) and re-apply when it clears (E30).
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime

from hrms.hr.doctype.attendance.attendance import mark_automation_rebuild
from hrms.overrides.company_scope import company_visible
from hrms.utils.attendance_day_audit import SKIP_PREFIX
from hrms.utils.email_flush import flush_email_queue_after_commit
from hrms.utils.hr_removed_day import removed_by_hr
from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)

HR_MANAGER_ROLE = "HR Manager"
#: who gets a Desk alert for something HR must fix (Error Log is System Manager only)
HR_ALERT_ROLES = ("HR Manager", "HR User")


# ---------------------------------------------------------------------------
# Approver resolution + notifications
# ---------------------------------------------------------------------------


def resolve_approver(employee: str) -> str | None:
	"""Resolve the approver user for an employee.

	Priority:
	  1. the employee's own approver chain, bottom-up — the approver named on
	     their Employee record, then their reporting manager, then the same two
	     questions of each person that reaches;
	  2. an HR Manager, preferring the employee's own company (below).

	OWNER RULING, 21 Sep 2026 — applied to every other request type that day and
	missed here, because this function calls none of the symbols that changed so
	a call-site family hunt could not see it. Two things were wrong:

	  * it stopped after ONE hop, so the escalation an employee actually has
	    when their approver forgets did not exist for a remote punch;
	  * tier 2 read a `Department Approver` row — the blanket the owner refused
	    ("no, dont"), which names no employee, so nothing in anyone's record
	    routes to it.

	Only the FIRST entry is stamped on the request: the notification and the
	badge need one addressee. Everyone else on the chain may still decide it
	(`may_decide` -> `_is_routed_approver`) and sees it in their pending queue
	(`_pending_for_approver_query`) — the three surfaces read this one list, and
	`test_remote_checkin_routes_up_the_chain` pins that they agree.

	The shift pair names the request TYPE: a remote punch is a shift matter, and
	`shift_request_approver` is the field HR already fills for it.
	"""
	from hrms.hr.utils import get_designated_approvers

	chain = get_designated_approvers(employee, "shift_request_approver", "shift_request_approver")
	if chain:
		logger.info(
			"[remote_checkin_request] approver=chain employee=%s -> %s (of %d on the chain)",
			employee,
			chain[0],
			len(chain),
		)
		return chain[0]

	# The HR fallback prefers an HR Manager WITHIN the employee's own company.
	# Assignment and visibility must use the same rule: the approver queue
	# (list_pending_for_approver) is fenced by the viewer's permitted
	# companies, so a request assigned to an HR Manager fenced to a DIFFERENT
	# company landed in a queue its owner could never see — Pending forever,
	# surfaced by nobody. The site-wide oldest-HR-Manager pick stays as the
	# last resort so a request is never left approver-less.
	company = frappe.db.get_value("Employee", employee, "company")
	for scope_to_company in [True, False] if company else [False]:
		company_join = (
			"""
        INNER JOIN `tabEmployee` e ON e.user_id = r.parent
          AND e.status = 'Active'
          AND e.company = %(company)s
        """
			if scope_to_company
			else ""
		)
		hr_user = frappe.db.sql(
			f"""
        SELECT r.parent
        FROM `tabHas Role` r
        INNER JOIN `tabUser` u ON u.name = r.parent
        {company_join}
        WHERE r.role = %(role)s
          AND r.parenttype = 'User'
          AND u.enabled = 1
        ORDER BY u.creation ASC
        LIMIT 1
        """,
			{"role": HR_MANAGER_ROLE, "company": company},
			as_dict=True,
		)
		if hr_user:
			logger.info(
				"[remote_checkin_request] approver=hr_manager_fallback employee=%s -> %s (company_scoped=%s)",
				employee,
				hr_user[0]["parent"],
				scope_to_company,
			)
			return hr_user[0]["parent"]

	logger.warning(
		"[remote_checkin_request] no approver resolvable for employee=%s",
		employee,
	)
	return None


def notify_approver(request) -> None:
	"""In-app + email + push notification to the approver."""
	if not request.approver:
		return

	subject = _("Remote check-in awaiting your approval — {0}").format(
		request.employee_name or request.employee
	)
	body = _(
		"{employee} submitted a {log_type} check-in {distance:.0f}m outside the office geofence "
		"at {time}. Open the HRMS PWA to approve or reject."
	).format(
		employee=request.employee_name or request.employee,
		log_type=request.log_type or "",
		distance=request.distance_m or 0.0,
		time=request.checkin_time,
	)

	from_user = frappe.db.get_value("Employee", request.employee, "user_id") or None

	_share_request_with_approver(request)
	_create_notification_log(request.approver, subject, body, request)
	_create_pwa_notification(request.approver, from_user, body, request)
	_send_email(request.approver, subject, body, request)
	_send_push(request.approver, subject, body, request)
	logger.info(
		"[remote_checkin_request] notified approver=%s request=%s",
		request.approver,
		request.name,
	)


def _notify_employee(request, decision: str) -> None:
	"""In-app + email + push notification to the employee."""
	user_id = frappe.db.get_value("Employee", request.employee, "user_id")
	if not user_id:
		return

	subject = _("Your remote check-in was {0}").format(decision.lower())
	body = _("Your {log_type} check-in at {time} was {decision} by {approver}.{remark}").format(
		log_type=request.log_type or "",
		time=request.checkin_time,
		decision=decision.lower(),
		approver=request.approver or "HR",
		remark=f"\n\nRemarks: {request.approver_remarks}" if request.approver_remarks else "",
	)
	outcome = _repair_outcome_text(request.flags.get("late_checkout_repair"))
	if outcome:
		body = f"{body}\n\n{outcome}"

	_create_notification_log(user_id, subject, body, request)
	_create_pwa_notification(user_id, request.approver, body, request)
	_send_email(user_id, subject, body, request)
	_send_push(user_id, subject, body, request)
	logger.info(
		"[remote_checkin_request] notified employee user=%s request=%s decision=%s",
		user_id,
		request.name,
		decision,
	)


def _repair_outcome_text(repair) -> str:
	"""What a late check-out approval did to the day, in the employee's words (E20).
	Empty for an ordinary approval, which has no repair."""
	if not repair:
		return ""
	if repair.get("repaired"):
		return _("Your day {0} was rebuilt: {1} h.").format(
			repair.get("attendance_date"), flt(repair.get("working_hours"), 2)
		)
	if repair.get("reason_code") == "today":
		return _("Your day will be rebuilt after your shift ends.")
	text = _("Your check-out was approved, but the day could not be rebuilt: {0}").format(
		repair.get("message") or ""
	)
	if repair.get("hr_notified"):
		return f"{text} — {_('HR has been told.')}"
	if repair.get("will_retry"):
		return f"{text} — {_('It will be rebuilt automatically once that clears.')}"
	return text


def _create_notification_log(user: str, subject: str, body: str, request) -> None:
	_insert_notification_log(user, subject, body, "Remote Checkin Request", request.name)


def _insert_notification_log(user, subject, body, document_type=None, document_name=None) -> bool:
	"""One Desk Alert for `user`. False (logged) when it could not be written; never raises."""
	try:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": document_type,
				"document_name": document_name,
				"subject": subject,
				"email_content": body,
			}
		).insert(ignore_permissions=True)
	except Exception as exc:
		logger.warning("[remote_checkin_request] notification_log for %s failed: %s", user, exc)
		return False
	return True


def hr_alert_recipients(company=None) -> list:
	"""Enabled HR Manager / HR User accounts whose company fence shows `company`
	(company_scope.company_visible): an unfenced user sees every company, a
	fenced one only theirs. With no company — a hub-wide alert — only unfenced
	HR qualifies, the same rule require_unfenced applies to hub-wide reads."""
	holders = frappe.get_all(
		"Has Role",
		filters={"role": ["in", list(HR_ALERT_ROLES)], "parenttype": "User"},
		pluck="parent",
	)
	if not holders:
		logger.info("[remote_checkin_request] no user holds %s", HR_ALERT_ROLES)
		return []
	enabled = frappe.get_all(
		"User", filters={"name": ["in", sorted(set(holders))], "enabled": 1}, pluck="name"
	)
	# ceiling: one fence read per HR user, upgrade: batch the User Permission read if HR accounts grow past ~50
	users = [user for user in sorted(set(enabled)) if user != "Guest" and company_visible(company, user)]
	logger.info("[remote_checkin_request] HR alert for company=%s reaches %d user(s)", company, len(users))
	return users


def notify_hr(subject, body, document_type=None, document_name=None, company=None) -> int:
	"""A Desk Notification Log for each HR user who may see `company`, so an alert
	kept in Error Log (System Manager only) reaches HR too. Returns how many were
	written; never raises — an alert must not undo the work around it."""
	try:
		users = hr_alert_recipients(company)
	except Exception:
		logger.exception("[remote_checkin_request] could not resolve HR recipients for %s", subject)
		return 0
	sent = sum(_insert_notification_log(user, subject, body, document_type, document_name) for user in users)
	logger.info("[remote_checkin_request] HR alert %r sent to %d of %d user(s)", subject, sent, len(users))
	return sent


def _company_of_checkin(checkin):
	"""The company of the punch's employee, or None when it cannot be read."""
	try:
		employee = frappe.db.get_value("Employee Checkin", checkin, "employee")
		company = frappe.db.get_value("Employee", employee, "company") if isinstance(employee, str) else None
	except Exception:
		logger.exception("[remote_checkin_request] company of %s could not be read", checkin)
		return None
	logger.debug("[remote_checkin_request] %s belongs to company %s", checkin, company)
	return company


def _create_pwa_notification(to_user: str, from_user: str | None, body: str, request) -> None:
	"""Create a PWA Notification row so the mobile Notifications feed can
	render the message — and, for Pending requests, inline Approve/Reject
	buttons keyed off reference_document_type=Remote Checkin Request.

	The Notification Log row above feeds the Desk bell; this one feeds the
	PWA. They're separate doctypes by design.
	"""
	if not body:
		logger.warning(
			"[remote_checkin_request] empty body for PWA notification request=%s",
			request.name,
		)
		body = _("Remote check-in update for {0}").format(request.name)

	# PWA Notification.message is a Text Editor (rich-HTML) field. Plain text
	# gets sanitised to an empty string by the editor's allow-list, which is
	# why earlier rows showed up unread but blank. Escape + wrap before save.
	html_body = "<p>{}</p>".format(frappe.utils.escape_html(body).replace("\n", "<br>"))

	try:
		notification = frappe.new_doc("PWA Notification")
		notification.to_user = to_user
		if from_user:
			notification.from_user = from_user
		notification.message = html_body
		notification.reference_document_type = "Remote Checkin Request"
		notification.reference_document_name = request.name
		notification.insert(ignore_permissions=True)
		logger.info(
			"[remote_checkin_request] pwa_notification created request=%s to=%s",
			request.name,
			to_user,
		)
	except Exception as exc:
		logger.warning("[remote_checkin_request] pwa_notification failed: %s", exc)


def _share_request_with_approver(request) -> None:
	"""Approvers may not have a role with read perm on Remote Checkin Request;
	share the doc directly so frappe.client.get_list returns it from the PWA
	(needed for the inline Approve/Reject status check)."""
	if not request.approver:
		return
	try:
		# Skip if approver already has permission via role.
		if frappe.has_permission(
			doctype=request.doctype, doc=request.name, ptype="read", user=request.approver
		):
			return
		frappe.share.add_docshare(
			request.doctype,
			request.name,
			request.approver,
			read=1,
			write=1,
			flags={"ignore_share_permission": True},
		)
	except Exception as exc:
		logger.warning("[remote_checkin_request] share-with-approver failed: %s", exc)


def _send_email(user: str, subject: str, body: str, request) -> None:
	try:
		frappe.sendmail(
			recipients=[user],
			subject=subject,
			message=body.replace("\n", "<br>"),
			reference_doctype="Remote Checkin Request",
			reference_name=request.name,
			now=False,
		)
		flush_email_queue_after_commit()
	except Exception as exc:
		logger.warning("[remote_checkin_request] email send failed user=%s: %s", user, exc)


def _send_push(user: str, subject: str, body: str, request) -> None:
	"""Emit a realtime socket event for the PWA.

	The PWA subscribes to `hrms:remote_checkin_request` on the current user's
	socket — this keeps the approver inbox and employee badge live without
	relying on push being configured. Native web push is NOT sent here: the
	PWA Notification row created by _create_pwa_notification already sends it
	on after_insert when the push relay is enabled.
	"""
	payload = {
		"request": request.name,
		"status": request.status,
		"log_type": request.log_type,
		"is_late_checkout": int(request.get("is_late_checkout") or 0),
		"subject": subject,
		"body": body,
	}
	try:
		# After commit: the approver's screen reloads its queues on this event,
		# so emitting inside the transaction let it read before the row was
		# visible — or announce a request that then rolled back (N08).
		frappe.publish_realtime(
			event="hrms:remote_checkin_request",
			message=payload,
			user=user,
			after_commit=True,
		)
	except Exception as exc:
		logger.warning("[remote_checkin_request] realtime push failed: %s", exc)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def propagate_approval_decision(doc, method=None):
	"""Sync the linked Employee Checkin's flags and notify the employee."""
	previous = doc.get_doc_before_save()
	previous_status = previous.status if previous else None
	if previous_status == doc.status:
		return
	if doc.status not in ("Approved", "Rejected"):
		return

	if not doc.approved_at:
		doc.approved_at = now_datetime()

	if doc.status == "Approved":
		frappe.db.set_value(
			"Employee Checkin",
			doc.checkin,
			{"requires_remote_approval": 0, "remote_approval_status": "Approved"},
		)
		if cint(doc.get("is_late_checkout")):
			# The approve endpoint reads this back so the approver sees what the
			# approval did to the day (E1) instead of an unconditional "notified".
			doc.flags.late_checkout_repair = reprocess_late_checkout_attendance(doc.checkin)
			_announce_repair(doc.flags.late_checkout_repair)
		else:
			reapply_late_checkouts_unblocked_by(doc)
			# Approved work after the day's shift is that day's overtime (owner,
			# 25 Sep 2026): the off-shift punch and its session take the day's
			# shift, so the claim list can see it. Paid only when claimed and
			# approved; never raises, a stamp that fails leaves the old behaviour.
			try:
				from hrms.utils.callback_session import stamp_approved_callback

				stamp_approved_callback(doc.checkin)
			except Exception:
				logger.exception("[remote_checkin_request] call-back stamp failed for %s", doc.name)
			_remark_decided_day(doc)
	else:  # Rejected
		# skip_auto_attendance as well, or the rejection is cosmetic: the OT
		# pairing engine and the PWA banner both read remote_approval_status,
		# but attendance marking (ShiftType.get_employee_checkins) filters on
		# skip_auto_attendance alone — so a punch HR explicitly rejected still
		# marked the employee Present with working hours. A rejection that
		# lands AFTER the hourly attendance job has already marked the day
		# still needs a manual attendance correction; this closes the
		# from-now-on path, which is the one that ran on every punch.
		_skip_rejected_punch(doc)
		if not cint(doc.get("is_late_checkout")):
			# W2: a rejected pending punch is skip-stamped and leaves the shift,
			# which clears a late OUT's pending_punch blocker as surely as an
			# approval does.
			reapply_late_checkouts_unblocked_by(doc)
		_remark_decided_day(doc)

	logger.info(
		"[remote_checkin_request] %s -> %s checkin=%s by=%s",
		doc.name,
		doc.status,
		doc.checkin,
		frappe.session.user,
	)
	_notify_employee(doc, doc.status)


def _remark_decided_day(doc) -> None:
	"""Re-mark the decided punch's day right after commit (hrms.utils.day_remark).

	15 Sep 2026 (Nor Syamira, weekly-off Saturday): the decision flipped the punch
	flags and waited for the hourly job, so an approved rest-day pair showed nothing
	for up to an hour, and a punch rejected after its day was marked never changed
	the day at all — every punch was linked, so no job read it again. Never raises:
	a refresh that cannot be queued must not undo the decision."""
	try:
		from hrms.utils.day_remark import punch_day, remark_day_after_commit

		employee, day = punch_day(doc.checkin)
		remark_day_after_commit(employee or doc.employee, day, f"{doc.name} {doc.status}")
	except Exception:
		logger.exception("[remote_checkin_request] could not queue the re-mark for %s", doc.name)


def _skip_rejected_punch(doc) -> None:
	"""Skip-stamp the rejected punch WITH its reason (E17): a Comment the day
	audit reads (SKIP_PREFIX) and `doc.flags.skip_reason` for the Employee
	Checkin guard that refuses a reason-less skip write."""
	kind = (
		_("forgotten check-out request")
		if cint(doc.get("is_late_checkout"))
		else _("remote check-in request")
	)
	reason = _("Skipped: {0} {1} rejected by {2}").format(kind, doc.name, frappe.session.user)
	doc.flags.skip_reason = reason
	frappe.db.set_value(
		"Employee Checkin",
		doc.checkin,
		{
			"requires_remote_approval": 0,
			"remote_approval_status": "Rejected",
			"skip_auto_attendance": 1,
		},
	)
	try:
		frappe.get_doc("Employee Checkin", doc.checkin).add_comment("Comment", f"{SKIP_PREFIX}: {reason}")
	except Exception:
		logger.exception("[remote_checkin_request] skip reason could not be written on %s", doc.checkin)
	logger.info("[remote_checkin_request] %s skip-stamped: %s", doc.checkin, reason)


def _announce_repair(repair) -> None:
	"""Desk approvers save the form and get no JSON back: a rebuilt day is
	announced the way a refused one already is (E20)."""
	if not repair or not repair.get("repaired"):
		return
	frappe.msgprint(
		_("Day {0} rebuilt: {1}, {2} h.").format(
			repair.get("attendance_date"), _(repair.get("status") or ""), flt(repair.get("working_hours"), 2)
		),
		title=_("Attendance updated"),
		indicator="green",
	)


_REPAIR_CHECKIN_FIELDS = [
	"name",
	"employee",
	"log_type",
	"time",
	"shift",
	"shift_start",
	"shift_end",
	"shift_actual_start",
	"shift_actual_end",
	"device_id",
	"overtime_type",
	"attendance",
	"skip_auto_attendance",
	"offshift",
	"synced_from_instance",
	"remote_approval_status",
	"requires_remote_approval",
]


#: A punch still awaiting approval, or a row lock held by a concurrent write,
#: clears on its own; everything else needs a person, so it goes to HR once.
_TRANSIENT_REFUSALS = frozenset({"pending_punch", "locked"})
MAX_REPAIR_RETRIES = 3
REPAIR_NOT_APPLIED_TITLE = "Late check-out not applied"
_RETRY_METHOD = "hrms.overrides.remote_checkin_request_hooks.retry_late_checkout_repair"


def _repair_result(repaired, reason_code=None, message="", marked=None, attendance=None, **flags):
	"""What an approval did to the day, shaped for the approver's screen."""
	return frappe._dict(
		repaired=repaired,
		reason_code=reason_code,
		message=message,
		attendance=marked.name if marked else attendance,
		status=marked.get("status") if marked else None,
		working_hours=marked.get("working_hours") if marked else None,
		attendance_date=marked.get("attendance_date") if marked else None,
		will_retry=flags.get("will_retry", False),
		hr_notified=flags.get("hr_notified", False),
	)


def _shift_day_is_today(employee, attendance_date, shift_actual_end=None) -> bool:
	"""Owner ruling: the employee may still be working, so the day is left
	alone rather than rebuilt from an approval. "Still working" is the shift's
	actual end (buffer included) not yet reached — a day shift approved at
	20:00 is over and rebuilt at once; a night shift approved at 00:30 is
	still running although its day is yesterday's date (caught on
	fresh.local). The calendar date is only the fallback when the IN carries
	no shift end (E19)."""
	now = employee_now(employee)
	if shift_actual_end:
		return now < get_datetime(shift_actual_end)
	return getdate(attendance_date) >= now.date()


def _request_for(checkin):
	return frappe.db.get_value("Remote Checkin Request", {"checkin": checkin}, "name")


REFUSAL_COMMENT_PREFIX = "late-checkout-repair-refused:"


def parse_refusal(text) -> str | None:
	"""The reason code in a refusal Comment, or None for any other comment."""
	text = re.sub(r"<[^>]+>", "", text or "").strip()
	if not text.startswith(REFUSAL_COMMENT_PREFIX):
		return None
	return text[len(REFUSAL_COMMENT_PREFIX) :].split("—", 1)[0].strip() or None


def last_refusal_code(request) -> str | None:
	"""The newest recorded refusal on a request (E30), for a pass that re-applies
	once the blocker is gone."""
	rows = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Remote Checkin Request",
			"reference_name": request,
			"comment_type": "Comment",
			"content": ["like", f"{REFUSAL_COMMENT_PREFIX}%"],
		},
		fields=["content"],
		order_by="creation desc",
		limit_page_length=1,
	)
	code = parse_refusal(rows[0].content) if rows else None
	logger.debug("[remote_checkin_request] last refusal on %s: %s", request, code)
	return code


def _record_refusal(checkin, reason_code, reason) -> None:
	"""One machine-readable Comment per distinct final refusal on the request."""
	request = _request_for(checkin)
	if not request:
		return
	if last_refusal_code(request) == reason_code:
		return
	frappe.get_doc("Remote Checkin Request", request).add_comment(
		"Comment", f"{REFUSAL_COMMENT_PREFIX} {reason_code} — {reason}"
	)
	logger.info("[remote_checkin_request] refusal recorded on %s: %s", request, reason_code)


def _tell_hr_once(checkin, reason) -> bool:
	"""One Error Log per request, so a stuck day is on HR's list without repeats."""
	request = _request_for(checkin)
	if not request:
		logger.warning("[remote_checkin_request] no request to report for checkin=%s", checkin)
		return False
	reference = {"reference_doctype": "Remote Checkin Request", "reference_name": request}
	if frappe.db.exists("Error Log", {"method": REPAIR_NOT_APPLIED_TITLE, **reference}):
		return True
	message = _("Approved late check-out {0} did not update attendance: {1}").format(checkin, reason)
	frappe.log_error(title=REPAIR_NOT_APPLIED_TITLE, message=message, **reference)
	frappe.get_doc("Remote Checkin Request", request).add_comment(
		"Comment", _("Check-out approved, but attendance needs correction: {0}").format(reason)
	)
	# HR cannot open Error Log; the Desk alert is what reaches them (W6)
	notify_hr(
		_(REPAIR_NOT_APPLIED_TITLE), message, "Remote Checkin Request", request, _company_of_checkin(checkin)
	)
	logger.info("[remote_checkin_request] HR told: request=%s checkin=%s", request, checkin)
	return True


def _refuse(checkin, reason_code, reason, attempt=0, attendance=None, from_recovery=False):
	"""Record why the day was not rebuilt, and make sure it is not forgotten:
	a transient blocker is retried after commit, a permanent one goes to HR.

	`from_recovery` (I4, integration review): the nightly attendance recovery
	calls the repair itself and classifies a transient refusal as "retried next
	run" — its own retry job and the approver's msgprint would be duplicates,
	so it only records the refusal on the request.
	"""
	logger.warning(
		"[remote_checkin_request] attendance repair refused checkin=%s code=%s attempt=%s recovery=%s",
		checkin,
		reason_code,
		attempt,
		from_recovery,
	)
	if reason_code == "today":
		# E19: not dropped. The job runs right after commit and rebuilds the day
		# if the shift has ended by then; a shift still running is left to the
		# hourly job, which rebuilds from every punch once the shift is over.
		# attempt > 0 is that job itself: it must not queue itself again.
		# ceiling: no delayed jobs (Frappe disables the RQ scheduler), upgrade: enqueue at shift end if workers gain one
		if attempt == 0 and not from_recovery:
			frappe.enqueue(
				_RETRY_METHOD,
				queue="short",
				out_checkin=checkin,
				attempt=1,
				enqueue_after_commit=True,
				job_id=f"late-checkout-repair::{checkin}",
				deduplicate=True,
			)
			frappe.msgprint(
				_("Approved — the day will be rebuilt after the shift ends."),
				title=_("Attendance queued"),
				indicator="blue",
			)
		return _repair_result(False, reason_code, reason, attendance=attendance, will_retry=True)
	if not from_recovery:
		frappe.msgprint(
			_("Check-out approved, but attendance was not updated: {0}").format(reason),
			title=_("Attendance not updated"),
			indicator="orange",
		)
	if reason_code not in _TRANSIENT_REFUSALS:
		_record_refusal(checkin, reason_code, reason)
		return _repair_result(
			False, reason_code, reason, attendance=attendance, hr_notified=_tell_hr_once(checkin, reason)
		)
	if attempt >= MAX_REPAIR_RETRIES:
		# Out of retries: HR hears about it once. pending_punch also keeps its own
		# trigger (deciding that punch re-runs the repair), but a punch nobody
		# decides must not leave the day stuck in silence (W2).
		_record_refusal(checkin, reason_code, reason)
		hr_notified = _tell_hr_once(checkin, reason)
		return _repair_result(False, reason_code, reason, attendance=attendance, hr_notified=hr_notified)
	if from_recovery:
		# the recovery's next run is the retry (late_checkout_hold: "retried next run")
		return _repair_result(False, reason_code, reason, attendance=attendance, will_retry=True)
	# ceiling: retries run right after commit with no backoff, upgrade: a delayed queue if lock refusals recur
	frappe.enqueue(
		_RETRY_METHOD,
		queue="short",
		out_checkin=checkin,
		attempt=attempt + 1,
		enqueue_after_commit=True,
	)
	return _repair_result(False, reason_code, reason, attendance=attendance, will_retry=True)


def retry_late_checkout_repair(out_checkin: str, attempt: int = 1):
	"""Background retry of a repair refused for a transient reason."""
	row = frappe.db.get_value("Employee Checkin", out_checkin, ["attendance"], as_dict=True)
	applied = row.attendance if row else None
	if applied:
		logger.info(
			"[remote_checkin_request] retry skipped, OUT=%s already on Attendance=%s", out_checkin, applied
		)
		return _repair_result(True, attendance=applied)
	return reprocess_late_checkout_attendance(out_checkin, attempt=attempt)


def reapply_late_checkouts_unblocked_by(doc) -> None:
	"""E3: a late OUT approved while another punch of its shift was still pending
	was refused. Approving that punch clears the blocker, so re-run the repair for
	the employee's approved late OUTs that are still not on an Attendance."""
	punch_time = frappe.db.get_value("Employee Checkin", doc.checkin, "time")
	if not punch_time:
		return
	punch_time = get_datetime(punch_time)
	outs = frappe.get_all(
		"Remote Checkin Request",
		filters={
			"employee": doc.employee,
			"is_late_checkout": 1,
			"status": "Approved",
			"checkin_time": ["between", [punch_time, punch_time + timedelta(days=1)]],
		},
		pluck="checkin",
	)
	for out in outs:
		row = frappe.db.get_value(
			"Employee Checkin", out, ["attendance", "remote_approval_status"], as_dict=True
		)
		if not row or row.attendance or row.remote_approval_status != "Approved":
			continue
		logger.info("[remote_checkin_request] %s approved; re-applying late OUT=%s", doc.name, out)
		reprocess_late_checkout_attendance(out)


def _repair_financial_dependency(
	employee, attendance_date, attendance_name, for_update: bool = True, requests_ok: bool = False
):
	"""Claims accepted by existing payout rules and submitted payroll require explicit correction.

	`for_update` holds row locks so a repair decides against a payout that
	cannot then be submitted underneath it. A read-only caller — a preview or a
	dry run — must pass False: locking Salary Slip rows from a report would
	block payroll while somebody reads a screen.

	`requests_ok` (Fix days, owner ruling 21 Sep 2026): an approved OT Request
	is a request, not money — it keeps its approval while the row is rebuilt
	from the punches. Only what is PAID answers: a submitted Salary Slip
	covering the day, or submitted Overtime Details on the row.
	"""
	logger.debug("[remote_checkin_request] checking attendance repair dependencies")
	return (
		(
			not requests_ok
			and frappe.db.get_value(
				"OT Request",
				{
					"employee": employee,
					"ot_date": attendance_date,
					"status": ["!=", "Rejected"],
					"docstatus": 1,
				},
				"name",
				for_update=for_update,
			)
		)
		or frappe.db.get_value(
			"Salary Slip",
			{
				"employee": employee,
				"start_date": ["<=", attendance_date],
				"end_date": [">=", attendance_date],
				"docstatus": 1,
			},
			"name",
			for_update=for_update,
		)
		or (
			attendance_name
			and frappe.db.get_value(
				"Overtime Details",
				{"reference_document": attendance_name, "docstatus": 1},
				"name",
				for_update=for_update,
			)
		)
	)


def reprocess_late_checkout_attendance(
	out_checkin: str, attempt: int = 0, from_recovery: bool = False
) -> frappe._dict:
	"""Repair the complete original shift, preserving the old record if rebuilding fails.

	`out_checkin` is the approved late OUT's name; `attempt` counts background
	retries (0 = a direct approval); `from_recovery` is the nightly attendance
	recovery calling — it retries and reports refusals itself, so no retry job
	or Desk message is raised here (I4). Returns what happened (see
	_repair_result and the module docstring for the keys and reason codes); a
	refusal is retried or reported. Never commits: the caller's transaction owns it.
	"""
	from functools import partial

	from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours
	from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import get_previous_session_checkin

	refuse = partial(_refuse, from_recovery=from_recovery)
	logger.info(
		"[remote_checkin_request] repairing whole shift for late OUT=%s (recovery=%s)",
		out_checkin,
		from_recovery,
	)
	out = frappe.db.get_value(
		"Employee Checkin", out_checkin, _REPAIR_CHECKIN_FIELDS, as_dict=True, for_update=True
	)
	if not out:
		logger.warning("[remote_checkin_request] late OUT not found: %s", out_checkin)
		return _repair_result(False, "not_found", _("The check-out punch no longer exists."))
	previous = get_previous_session_checkin(out.employee, out.time)
	in_row = (
		frappe.db.get_value("Employee Checkin", previous.name, _REPAIR_CHECKIN_FIELDS, as_dict=True)
		if previous
		else None
	)
	if not in_row or not in_row.shift or not in_row.shift_start:
		return refuse(
			out_checkin,
			"no_open_shift",
			_("The check-in this check-out closes is not on a shift."),
			attempt,
			None,
		)
	anchor = get_datetime(in_row.shift_start)
	attendance_date = anchor.date()
	if _shift_day_is_today(out.employee, attendance_date, in_row.shift_actual_end):
		return refuse(
			out_checkin,
			"today",
			_("This shift is still running; the day is rebuilt after it ends."),
			attempt,
			None,
		)
	if (
		out.log_type != "OUT"
		or out.remote_approval_status != "Approved"
		or out.synced_from_instance
		or cint(out.skip_auto_attendance)
	):
		return refuse(
			out_checkin,
			"not_eligible",
			_("This check-out is not an approved local punch that attendance can use."),
			attempt,
			None,
		)

	# Resolve the whole shift's Attendance, including an unlinked provisional draft.
	existing = frappe.get_all(
		"Attendance",
		filters={"employee": out.employee, "attendance_date": attendance_date, "docstatus": ["<", 2]},
		fields=["name", "shift"],
	)
	existing = [row for row in existing if not row.shift or row.shift == in_row.shift]
	if len(existing) > 1:
		return refuse(
			out_checkin,
			"duplicate_attendance",
			_("More than one attendance record covers this shift."),
			attempt,
			None,
		)
	attendance = frappe.get_doc("Attendance", existing[0].name, for_update=True) if existing else None
	if attendance and (not cint(attendance.auto_attendance) or attendance.get("synced_from_instance")):
		return refuse(
			out_checkin,
			"hr_marked",
			_("HR corrected this day by hand, or another site owns it."),
			attempt,
			attendance.name if attendance else None,
		)
	# C1: a day HR removed in Shift Attendance has no row left to refuse on; its
	# marker punch is the HR decision, permanent like hr_marked (never retried).
	if removed_by_hr(out.employee, attendance_date):
		return refuse(
			out_checkin,
			"hr_removed",
			_("HR removed this day in Shift Attendance; it is not marked again."),
			attempt,
			None,
		)
	if attendance and (
		attendance.employee != out.employee
		or attendance.shift != in_row.shift
		or getdate(attendance.attendance_date) != attendance_date
	):
		return refuse(
			out_checkin,
			"attendance_mismatch",
			_("The attendance record for this day belongs to a different shift."),
			attempt,
			attendance.name if attendance else None,
		)

	# Gather before cancellation: the old record may own earlier sessions.
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": out.employee, "shift": in_row.shift, "shift_start": anchor},
		fields=_REPAIR_CHECKIN_FIELDS,
		order_by="time asc",
	)
	linked = (
		frappe.get_all(
			"Employee Checkin",
			filters={"attendance": attendance.name},
			fields=_REPAIR_CHECKIN_FIELDS,
			order_by="time asc",
		)
		if attendance
		else []
	)
	if any(
		row.employee != out.employee
		or row.synced_from_instance
		or (
			row.name != out_checkin
			and (row.shift != in_row.shift or not row.shift_start or get_datetime(row.shift_start) != anchor)
		)
		for row in linked
	):
		return refuse(
			out_checkin,
			"cross_boundary",
			_("Some punches of this day belong to another shift or another site."),
			attempt,
			attendance.name if attendance else None,
		)
	candidates = {row.name: row for row in [*logs, *linked, out]}
	local = [
		row
		for row in candidates.values()
		if not row.synced_from_instance and not cint(row.skip_auto_attendance)
	]
	if any(row.remote_approval_status == "Pending" or cint(row.requires_remote_approval) for row in local):
		return refuse(
			out_checkin,
			"pending_punch",
			_("Another punch in this shift is still awaiting approval."),
			attempt,
			attendance.name if attendance else None,
		)
	logs = sorted(
		(
			row
			for row in local
			if row.remote_approval_status in (None, "", "Approved")
			and (not cint(row.offshift) or row.name == out_checkin)
		),
		key=lambda row: (get_datetime(row.time), row.name),
	)
	if any(row.attendance and (not attendance or row.attendance != attendance.name) for row in logs):
		return refuse(
			out_checkin,
			"other_attendance",
			_("A punch of this shift is already counted on another attendance record."),
			attempt,
			attendance.name if attendance else None,
		)
	shift = frappe.get_doc("Shift Type", in_row.shift)
	pairing = shift.determine_check_in_and_check_out
	# Use the configured canonical pairing: duplicate INs are valid in strict
	# mode, while alternating mode intentionally ignores labels.
	_hours, first_in, last_out = (
		calculate_working_hours(logs, pairing, shift.working_hours_calculation_based_on)
		if logs
		else (0, None, None)
	)
	if (
		first_in is None
		or last_out is None
		or last_out <= first_in
		or first_in != get_datetime(logs[0].time)
		or last_out != get_datetime(logs[-1].time)
		or not any(row.name == out_checkin for row in logs)
		or (pairing == "Alternating entries as IN and OUT during the same shift" and len(logs) % 2)
	):
		return refuse(
			out_checkin,
			"incomplete_pairs",
			_("The check-ins and check-outs of this shift do not pair up."),
			attempt,
			attendance.name if attendance else None,
		)
	if _repair_financial_dependency(out.employee, attendance_date, attendance.name if attendance else None):
		return refuse(
			out_checkin,
			"financial_lock",
			_("Approved overtime, replacement leave or submitted payroll already uses this day."),
			attempt,
			attendance.name if attendance else None,
		)
	if not shift.should_mark_attendance(out.employee, attendance_date):
		return refuse(
			out_checkin,
			"not_markable",
			_("This shift's rules do not mark attendance on this day, for example a holiday."),
			attempt,
			attendance.name if attendance else None,
		)

	frappe.db.savepoint("late_checkout_repair")
	try:
		# An approved retroactive OUT can be beyond today's shift lookup buffer.
		# Bind it to its original IN only inside the rollback-protected repair.
		if out.shift != in_row.shift or out.shift_start != in_row.shift_start or cint(out.offshift):
			bounds = {
				field: in_row.get(field)
				for field in (
					"shift",
					"shift_start",
					"shift_end",
					"shift_actual_start",
					"shift_actual_end",
					# same set as CustomEmployeeCheckin._stamp_shift: an OUT bound to
					# its IN's shift without the IN's overtime type makes the whole
					# day's overtime vanish when the OUT is the first eligible punch
					"overtime_type",
				)
			}
			bounds["offshift"] = 0
			frappe.db.set_value("Employee Checkin", out.name, bounds)
			out.update(bounds)
		if attendance and cint(attendance.docstatus) == 1:
			attendance.flags.ignore_permissions = True
			attendance.cancel()
			repair = None
		else:
			repair = attendance
		if repair is None:
			repair = frappe.new_doc("Attendance")
			repair.update(
				{
					"employee": out.employee,
					"attendance_date": attendance_date,
					"shift": in_row.shift,
					"auto_attendance": 1,
				}
			)
		# Automation is rebuilding this day, not a person: without the flag an
		# amendment claims HR ownership and every later fix leaves the day alone
		# (hrms/hr/doctype/attendance/attendance.py mark_automation_rebuild).
		mark_automation_rebuild(repair)
		marked = shift.mark_attendance_for_shift_logs(
			out.employee, attendance_date, logs, repair_attendance=repair
		)
		if not marked:
			# The engine writes nothing for a day with no IN→OUT pair — here, an
			# approved OUT more than 20 h after its IN is not that IN's closer
			# (owner's rule, 21 Sep 2026): the day stays open for HR, the
			# previous row is kept, and the message must say so, not "failed".
			frappe.db.rollback(save_point="late_checkout_repair")
			return refuse(
				out_checkin,
				"day_left_open",
				_(
					"This check-out does not close the check-in of that day (the shift's rules left the day open, e.g. more than 20 hours apart); HR closes it in Shift Attendance."
				),
				attempt,
				attendance.name if attendance else None,
			)
	except Exception as exc:
		frappe.db.rollback(save_point="late_checkout_repair")
		logger.exception("[remote_checkin_request] shift repair rolled back for OUT=%s", out_checkin)
		if _is_lock_timeout(exc):
			return refuse(
				out_checkin,
				"locked",
				_("Someone else was changing this day at the same moment."),
				attempt,
				attendance.name if attendance else None,
			)
		return refuse(
			out_checkin,
			"rebuild_failed",
			_("Rebuilding the day failed; the previous attendance was kept."),
			attempt,
			attendance.name if attendance else None,
		)
	logger.info("[remote_checkin_request] repaired Attendance=%s from %s punches", marked.name, len(logs))
	return _repair_result(True, marked=marked)


def _is_lock_timeout(exc) -> bool:
	"""A lock wait timeout undoes only the statement, so the approval can stand and
	the repair can be retried. A deadlock rolls back the whole transaction and is
	deliberately not treated as retryable here."""
	timeout = getattr(frappe, "QueryTimeoutError", None)
	return isinstance(timeout, type) and isinstance(exc, timeout)
