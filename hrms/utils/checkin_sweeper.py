"""Nightly stale-IN sweeper.

sweep_stale_ins() -- daily 10:00 AM job (registered via hrms/hooks.py
scheduler_events) that tags Employee Checkin IN logs older than
STALE_HOURS hours without a matching OUT as is_abandoned=1, and pings
HR Manager(s) with a count.
"""

from __future__ import annotations

import logging

import frappe
from frappe.utils import add_to_date, now_datetime

logger = logging.getLogger(__name__)

STALE_HOURS = 36
HR_MANAGER_ROLE = "HR Manager"


def sweep_stale_ins() -> int:
	"""Find IN check-ins older than STALE_HOURS with no matching OUT and tag them.

	Skips:
	  - IN rows already tagged is_abandoned=1 (idempotent — re-running won't
	    re-tag the same row)
	  - IN rows that have a later OUT for the same employee
	  - IN rows whose session already has a Remote Checkin Request (i.e.
	    the employee has already submitted a late check-out)

	Notifies every active HR Manager with a single in-app alert per run
	if any rows were tagged.
	"""
	cutoff = add_to_date(now_datetime(), hours=-STALE_HOURS)
	logger.info("[scheduler] sweep_stale_ins cutoff=%s", cutoff)

	candidates = frappe.get_all(
		"Employee Checkin",
		filters=[
			["log_type", "=", "IN"],
			["time", "<=", cutoff],
			["is_abandoned", "!=", 1],
		],
		fields=["name", "employee", "time"],
		order_by="time asc",
		limit_page_length=500,
	)
	logger.info("[scheduler] sweep_stale_ins candidates=%d", len(candidates))

	tagged = 0
	for row in candidates:
		if _has_matching_close(row):
			continue
		frappe.db.set_value("Employee Checkin", row["name"], "is_abandoned", 1)
		tagged += 1
		logger.warning(
			"[scheduler] Tagged abandoned IN employee=%s checkin=%s time=%s",
			row["employee"],
			row["name"],
			row["time"],
		)

	if tagged > 0:
		_notify_hr(tagged)

	logger.info("[scheduler] sweep_stale_ins -> tagged %d", tagged)
	return tagged


def _has_matching_close(in_row: dict) -> bool:
	"""True if this IN session has either a paired OUT or a late-checkout request."""
	later_out = frappe.db.exists(
		"Employee Checkin",
		{
			"employee": in_row["employee"],
			"log_type": "OUT",
			"time": [">", in_row["time"]],
		},
	)
	if later_out:
		logger.info(
			"[scheduler] skip %s — later OUT exists for employee=%s",
			in_row["name"],
			in_row["employee"],
		)
		return True

	pending_request = frappe.db.exists(
		"Remote Checkin Request",
		{
			"employee": in_row["employee"],
			"log_type": "OUT",
			"checkin_time": [">", in_row["time"]],
		},
	)
	if pending_request:
		logger.info(
			"[scheduler] skip %s — late-checkout request exists for employee=%s",
			in_row["name"],
			in_row["employee"],
		)
		return True

	return False


def _notify_hr(count: int) -> None:
	"""One in-app alert per HR Manager per sweep run when abandoned INs exist."""
	hr_users = frappe.get_all(
		"Has Role",
		filters={"role": HR_MANAGER_ROLE, "parenttype": "User"},
		pluck="parent",
	)
	if not hr_users:
		logger.warning("[scheduler] No HR Manager users to notify about %d abandoned INs", count)
		return

	subject = f"{count} abandoned check-in(s) detected"
	body = (
		f"{count} employee check-in(s) older than {STALE_HOURS} hours have no "
		f"matching check-out and were not closed via the late-checkout flow. "
		f"Filter the Employee Checkin list by 'Is Abandoned = Yes' to review."
	)
	for user in set(hr_users):
		try:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"for_user": user,
					"type": "Alert",
					"document_type": "Employee Checkin",
					"subject": subject,
					"email_content": body,
				}
			).insert(ignore_permissions=True)
			logger.info("[scheduler] notified HR user=%s count=%d", user, count)
		except Exception as exc:
			logger.warning("[scheduler] HR notify failed user=%s: %s", user, exc)
