"""Reminders to approvers: the first approver owns the request.

Owner, 29 Sep 2026: "we want to encourage the first approver to act ... our
reminder/notification is being deliberate ... even if they take approved
leave". So the first approver is nudged first, then told a backup can help,
and only then is the backup asked — and the owner is told before that
happens. One summary per person per day, never a ping per request.

Owner ruling R2, 6 Oct 2026: an approver who is AWAY (approved leave covering
today) does not hold a request. The backup is asked after 2 working days, and
both people are told.

HR sets the days in HR Settings (approval_reminder_after_days, default 1;
approval_backup_after_days, default 3). Days are WORKING days. Leave that
starts within 2 days skips straight to asking the backup.

`plan_reminders` is pure (unit-tested); `send_daily_reminders` is the
scheduler entry that gathers what is waiting and delivers the plan as PWA
Notifications (their after_insert queues the push).
"""

from __future__ import annotations

import logging

import frappe
from frappe.utils import add_days, getdate, now_datetime

logger = logging.getLogger(__name__)

#: A request whose leave starts this soon (calendar days) cannot wait for the
#: normal steps: the backup is asked on the first reminder day.
URGENT_WITHIN_DAYS = 2

#: Working days an away first approver gets before the backup is asked (R2,
#: 6 Oct 2026): someone on approved leave cannot act, so waiting the full
#: approval_backup_after_days only delays the employee.
AWAY_BACKUP_AFTER_DAYS = 2

#: The request types an approver decides, and the words for each.
KIND_WORDS = {
	"Leave Application": "leave",
	"Expense Claim": "expense",
	"OT Request": "overtime claim",
	"Shift Request": "shift change",
	"Attendance Request": "day fix",
	"Compensatory Leave Request": "time-off-in-lieu request",
}


def plan_reminders(requests: list[dict], settings: dict) -> list[dict]:
	"""Who hears what today. Pure.

	`requests`: one dict per waiting request — name, waited (working days),
	first / backup (logins, backup may be None), first_name / backup_name,
	employee_name, kind (word), starts_in (calendar days until it starts, or
	None), first_away (the first approver is on approved leave today).
	Returns [{to, message}], at most one message per person.
	"""
	remind_at = max(int(settings.get("reminder_after") or 1), 1)
	backup_at = max(int(settings.get("backup_after") or 3), remind_at)

	owner_waiting: dict[str, list[dict]] = {}
	owner_helped: dict[str, list[dict]] = {}
	backup_asked: dict[str, list[dict]] = {}

	for r in requests:
		waited = r["waited"]
		if waited < remind_at:
			continue
		urgent = r.get("starts_in") is not None and r["starts_in"] <= URGENT_WITHIN_DAYS
		away = bool(r.get("first_away")) and waited >= AWAY_BACKUP_AFTER_DAYS
		ask_backup = bool(r.get("backup")) and (waited >= backup_at or urgent or away)
		if ask_backup:
			backup_asked.setdefault(r["backup"], []).append(r)
			owner_helped.setdefault(r["first"], []).append(r)
		else:
			owner_waiting.setdefault(r["first"], []).append(r)

	# One message per person: someone who owns one request and backs up another
	# hears both in the same summary, never two notifications.
	out = []
	for user in sorted(set(owner_waiting) | set(owner_helped) | set(backup_asked)):
		parts = []
		if user in owner_waiting or user in owner_helped:
			parts.append(_owner_words(owner_waiting.get(user, []), owner_helped.get(user, [])))
		if user in backup_asked:
			parts.append(_backup_words(backup_asked[user]))
		out.append({"to": user, "message": " ".join(parts)})
	return out


def _owner_words(waiting: list[dict], helped: list[dict]) -> str:
	parts = []
	if waiting:
		if len(waiting) == 1:
			r = waiting[0]
			line = f"{r['employee_name']}'s {r['kind']} is waiting for you."
		else:
			line = f"{len(waiting)} requests are waiting for you."
		# Day two onwards: say who can step in, so the owner knows it will not
		# wait forever — and still has the first move.
		nudge = [r for r in waiting if r.get("backup") and r["waited"] > 1]
		if nudge:
			line += f" If you can't, {nudge[0]['backup_name']} can act for you."
		parts.append(line)
	if helped:
		r = helped[0]
		away = all(h.get("first_away") for h in helped)
		if len(helped) == 1 and away:
			days = "day" if r["waited"] == 1 else "days"
			parts.append(
				f"{r['employee_name']}'s {r['kind']} waited {r['waited']} {days} while you are away; "
				f"{r['backup_name']} was asked to decide."
			)
		elif away:
			parts.append(
				f"{len(helped)} requests waited while you are away; "
				f"{r['backup_name']} was asked to decide them."
			)
		elif len(helped) == 1:
			parts.append(
				f"{r['backup_name']} has been asked to help with {r['employee_name']}'s {r['kind']}."
			)
		else:
			parts.append(f"{r['backup_name']} has been asked to help with {len(helped)} of your requests.")
	return " ".join(parts)


def _backup_words(asked: list[dict]) -> str:
	away = [r for r in asked if r.get("first_away")]
	if len(asked) == 1:
		r = asked[0]
		days = "day" if r["waited"] == 1 else "days"
		who = f"{r['first_name']}, who is away" if away else r["first_name"]
		return (
			f"{r['employee_name']}'s {r['kind']} has waited {r['waited']} {days} for "
			f"{who}. You can decide it for them."
		)
	line = f"{len(asked)} requests have waited for your team's approvers. You can decide them for them."
	if away:
		line += " Everyone is away." if len(away) == len(asked) else " Some of them are away."
	return line


# --- scheduler --------------------------------------------------------------


def _setting(field: str, default: int) -> int:
	rows = frappe.db.sql("select value from tabSingles where doctype='HR Settings' and field=%s", field)
	try:
		value = int(rows[0][0]) if rows and rows[0][0] not in (None, "") else 0
	except (TypeError, ValueError):
		value = 0
	return value if value >= 1 else default


def _working_days_between(employee: str, start, end) -> int:
	"""Working days after `start` up to and including `end`, on the employee's
	own calendar (rest days and holidays do not count)."""
	from hrms.utils.ot_calculation import _classify_day

	days = 0
	day = getdate(add_days(start, 1))
	end = getdate(end)
	while day <= end:
		try:
			if _classify_day(employee, day, "normal") == "normal":
				days += 1
		except Exception:
			days += 1
		day = getdate(add_days(day, 1))
	return days


def _away_approvers(today) -> set[str]:
	"""Logins of everyone on approved leave today. ONE read for the whole run,
	however many requests wait; compared lower-case, as logins are."""
	rows = frappe.get_all(
		"Leave Application",
		filters={
			"docstatus": 1,
			"status": "Approved",
			# a half day off still leaves half a day at work to decide in
			"half_day": 0,
			"from_date": ["<=", today],
			"to_date": [">=", today],
		},
		fields=["employee.user_id as user_id"],
		limit_page_length=0,
	)
	return {r.user_id.lower() for r in rows if r.user_id}


def _waiting_requests() -> list[dict]:
	"""Every request still waiting on a decision, with its line, age and whether
	its first approver is away today."""
	from hrms.api.approval import DECIDE_THEN_SUBMIT, DESIGNATED_APPROVER_DOCTYPES
	from hrms.hr.utils import get_designated_approvers

	today = getdate(now_datetime())
	out = []
	for doctype, words in KIND_WORDS.items():
		if doctype not in DECIDE_THEN_SUBMIT or not frappe.db.exists("DocType", doctype):
			continue
		field, pending = DECIDE_THEN_SUBMIT[doctype]
		start_field = "from_date" if doctype == "Leave Application" else None
		fields = ["name", "employee", "employee_name", "creation"] + ([start_field] if start_field else [])
		for doc in frappe.get_all(
			doctype, filters={field: pending, "docstatus": 0}, fields=fields, limit_page_length=0
		):
			pair = DESIGNATED_APPROVER_DOCTYPES.get(doctype)
			if not pair or not doc.employee:
				continue
			chain = get_designated_approvers(doc.employee, *pair)
			if not chain:
				continue
			first, backup = chain[0], (chain[1] if len(chain) > 1 else None)
			starts = doc.get(start_field) if start_field else None
			out.append(
				{
					"name": doc.name,
					"waited": _working_days_between(doc.employee, getdate(doc.creation), today),
					"first": first,
					"backup": backup,
					"first_name": frappe.db.get_value("User", first, "first_name") or first,
					"backup_name": (frappe.db.get_value("User", backup, "first_name") or backup)
					if backup
					else None,
					"employee_name": (doc.employee_name or "").split(" ")[0] or doc.employee,
					"kind": words,
					"starts_in": (getdate(starts) - today).days if starts else None,
				}
			)
	if out:
		away = _away_approvers(today)
		for r in out:
			r["first_away"] = r["first"].lower() in away
	return out


def send_daily_reminders() -> int:
	"""Scheduler entry, once each morning. Weekends and public holidays are
	skipped by the working-day count (a request made on Friday has waited 1 day
	on Monday). Returns how many notifications were sent."""
	settings = {
		"reminder_after": _setting("approval_reminder_after_days", 1),
		"backup_after": _setting("approval_backup_after_days", 3),
	}
	requests = _waiting_requests()
	plan = plan_reminders(requests, settings)
	sent = 0
	for item in plan:
		try:
			frappe.get_doc(
				{
					"doctype": "PWA Notification",
					"to_user": item["to"],
					"from_user": "Administrator",
					"message": item["message"],
					"read": 0,
				}
			).insert(ignore_permissions=True)
			frappe.db.commit()
			sent += 1
		except Exception:
			frappe.db.rollback()
			logger.exception("[approval_reminders] could not remind %s; skipped", item["to"])
	logger.info("[approval_reminders] %d waiting, %d reminder(s) sent", len(requests), sent)
	return sent
