"""Reminders to approvers: the first approver owns the request, and only they are reminded.

Owner, 27 Oct 2026: "we want to encourage the first and only approver, approve.
that's their job." The first approver is reminded every working day from the
reminder day until they decide, on leave or not; the backup is never asked or
named. This replaces the 29 Sep backup step and ruling R2 (6 Oct, an approver
on leave handed over after 2 days). The person above may still approve if they
open the request themselves (HR Settings "Backup approval levels"); the
reminders simply never send them. One summary per person per day, never a ping
per request.

HR sets the reminder day in HR Settings (approval_reminder_after_days, default
1). Days are WORKING days.

`plan_reminders` is pure (unit-tested); `send_daily_reminders` is the
scheduler entry that gathers what is waiting and delivers the plan as PWA
Notifications (their after_insert queues the push).
"""

from __future__ import annotations

import logging

import frappe
from frappe.utils import add_days, getdate, now_datetime

logger = logging.getLogger(__name__)

#: From this many working days the reminder says how long it has waited.
SAY_HOW_LONG_FROM_DAYS = 3

#: The request types an approver decides, and the words for each.
KIND_WORDS = {
	"Leave Application": "leave",
	"Expense Claim": "expense",
	"OT Request": "overtime claim",
	"Shift Request": "shift change",
	"Attendance Request": "day fix",
	"Compensatory Leave Request": "time-off-in-lieu request",
	"Manpower Request": "manpower request",
}


def plan_reminders(requests: list[dict], settings: dict) -> list[dict]:
	"""Who hears what today. Pure.

	`requests`: one dict per waiting request — name, waited (working days),
	first (login), employee_name, kind (word).
	Returns [{to, message}], one message per first approver.
	"""
	remind_at = max(int(settings.get("reminder_after") or 1), 1)

	waiting: dict[str, list[dict]] = {}
	for r in requests:
		if r["waited"] >= remind_at:
			waiting.setdefault(r["first"], []).append(r)
	return [{"to": user, "message": _owner_words(waiting[user])} for user in sorted(waiting)]


def _owner_words(waiting: list[dict]) -> str:
	if len(waiting) == 1:
		r = waiting[0]
		line = f"{r['employee_name']}'s {r['kind']} is waiting for you."
		if r["waited"] >= SAY_HOW_LONG_FROM_DAYS:
			line += f" It has waited {r['waited']} days."
		return line
	line = f"{len(waiting)} requests are waiting for you."
	oldest = max(r["waited"] for r in waiting)
	if oldest >= SAY_HOW_LONG_FROM_DAYS:
		line += f" The oldest has waited {oldest} days."
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


def _waiting_requests() -> list[dict]:
	"""Every request still waiting on a decision, with its first approver and age."""
	from hrms.api.approval import DECIDE_THEN_SUBMIT, DESIGNATED_APPROVER_DOCTYPES
	from hrms.hr.utils import get_designated_approvers

	today = getdate(now_datetime())
	out = []
	for doctype, words in KIND_WORDS.items():
		if doctype not in DECIDE_THEN_SUBMIT or not frappe.db.exists("DocType", doctype):
			continue
		field, pending = DECIDE_THEN_SUBMIT[doctype]
		fields = ["name", "employee", "employee_name", "creation"]
		for doc in frappe.get_all(
			doctype, filters={field: pending, "docstatus": 0}, fields=fields, limit_page_length=0
		):
			pair = DESIGNATED_APPROVER_DOCTYPES.get(doctype)
			if not pair or not doc.employee:
				continue
			chain = get_designated_approvers(doc.employee, *pair)
			if not chain:
				continue
			first = chain[0]
			out.append(
				{
					"name": doc.name,
					"waited": _working_days_between(doc.employee, getdate(doc.creation), today),
					"first": first,
					"employee_name": (doc.employee_name or "").split(" ")[0] or doc.employee,
					"kind": words,
				}
			)
	return out


def send_daily_reminders() -> int:
	"""Scheduler entry, once each morning. Weekends and public holidays are
	skipped by the working-day count (a request made on Friday has waited 1 day
	on Monday). Returns how many notifications were sent."""
	settings = {"reminder_after": _setting("approval_reminder_after_days", 1)}
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
