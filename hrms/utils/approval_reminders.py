"""Reminders to approvers: the first approver owns the request.

Owner, 29 Sep 2026: "we want to encourage the first approver to act ... our
reminder/notification is being deliberate ... even if they take approved
leave". So the first approver is nudged first, then told a backup can help,
and only then is the backup asked — and the owner is told before that
happens. One summary per person per day, never a ping per request.

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
	None). Returns [{to, message}], at most one message per person.
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
		ask_backup = bool(r.get("backup")) and (waited >= backup_at or urgent)
		if ask_backup:
			backup_asked.setdefault(r["backup"], []).append(r)
			owner_helped.setdefault(r["first"], []).append(r)
		else:
			owner_waiting.setdefault(r["first"], []).append(r)

	out = []
	for user in sorted(set(owner_waiting) | set(owner_helped)):
		out.append(
			{"to": user, "message": _owner_words(owner_waiting.get(user, []), owner_helped.get(user, []))}
		)
	for user in sorted(backup_asked):
		out.append({"to": user, "message": _backup_words(backup_asked[user])})
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
		if len(helped) == 1:
			parts.append(
				f"{r['backup_name']} has been asked to help with {r['employee_name']}'s {r['kind']}."
			)
		else:
			parts.append(f"{r['backup_name']} has been asked to help with {len(helped)} of your requests.")
	return " ".join(parts)


def _backup_words(asked: list[dict]) -> str:
	if len(asked) == 1:
		r = asked[0]
		days = "day" if r["waited"] == 1 else "days"
		return (
			f"{r['employee_name']}'s {r['kind']} has waited {r['waited']} {days} for "
			f"{r['first_name']}. You can decide it for them."
		)
	return f"{len(asked)} requests have waited for your team's approvers. You can decide them for them."


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


def _waiting_requests() -> list[dict]:
	"""Every request still waiting on a decision, with its line and age."""
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
