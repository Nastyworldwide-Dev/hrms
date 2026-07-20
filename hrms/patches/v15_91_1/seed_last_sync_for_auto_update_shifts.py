"""Repair Shift Types stranded by the last-sync field-wiping bug.

The Shift Type form JS used to clear last_sync_of_checkin whenever
auto_update_last_sync was ticked, and a null last sync makes
process_auto_attendance skip the shift silently. Seed now() for every
shift left in that state so the hourly pipeline resumes; from this
release onward ShiftType.validate() keeps it seeded.

Shifts with the checkbox OFF and a null last sync are left alone — a
manual value there is an HR decision, not a repair.
"""

import logging

import frappe
from frappe.utils import now_datetime

logger = logging.getLogger(__name__)


def execute():
	stranded = frappe.get_all(
		"Shift Type",
		filters={"auto_update_last_sync": 1, "last_sync_of_checkin": ["is", "not set"]},
		pluck="name",
	)
	for name in stranded:
		frappe.db.set_value("Shift Type", name, "last_sync_of_checkin", now_datetime(), update_modified=False)
		logger.info("[patch] seeded last_sync_of_checkin for Shift Type %s", name)

	logger.info("[patch] seeded last_sync_of_checkin on %d shift type(s)", len(stranded))
