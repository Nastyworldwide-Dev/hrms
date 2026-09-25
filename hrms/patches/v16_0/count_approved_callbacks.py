"""Approved work after the shift, since 16 Sep 2026, becomes claimable (owner, 25 Sep 2026).

"Include approved after-shift work from 16 Sep onward in Claim OT? — yes."
Every APPROVED remote check-in in the current pay period that was filed
off-shift after its day's shift gets the day's shift stamp (the rule
hrms.utils.callback_session applies on approval from now on), so the claim
list can offer it. Nothing is paid: a claim still needs its approver.
Days before 16 Sep, and days a payout already depends on, are left alone.
Idempotent: a stamped punch is no longer off-shift.
"""

import logging

import frappe

from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency
from hrms.utils.callback_session import stamp_approved_callback

logger = logging.getLogger(__name__)

SINCE = "2026-09-16"


def execute():
	rows = frappe.get_all(
		"Remote Checkin Request",
		filters={"status": "Approved", "creation": [">=", SINCE]},
		fields=["name", "checkin", "employee"],
	)
	stamped = held = 0
	for row in rows:
		punch = frappe.db.get_value("Employee Checkin", row.checkin, ["time", "offshift"], as_dict=True)
		if not punch or not punch.offshift or str(punch.time) < SINCE:
			continue
		if _repair_financial_dependency(
			row.employee, punch.time.date(), None, for_update=False, requests_ok=True
		):
			held += 1
			continue
		if stamp_approved_callback(row.checkin):
			stamped += 1
			from hrms.utils.day_remark import remark_day_after_commit

			remark_day_after_commit(row.employee, punch.time.date(), f"call-back {row.name}")
	logger.info("[patch] approved call-backs since %s: stamped %s, held (paid) %s", SINCE, stamped, held)
