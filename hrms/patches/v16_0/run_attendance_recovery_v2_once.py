"""Queue the one automatic attendance recovery after the 15 Sep 2026 release.

The first run (run_attendance_recovery_once) already happened. This release
adds the rostered-shift, linked-Half-Day and ERP-closer steps, so the whole
window 1 Aug → yesterday is run once more. Only enqueues; never raises.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	frappe.enqueue(
		"hrms.utils.attendance_auto_recovery.run_once",
		queue="long",
		timeout=4 * 60 * 60,
		enqueue_after_commit=True,
		job_id="attendance_recovery_once",
		deduplicate=True,
	)
	logger.info("[attendance_recovery_v2] one-time recovery queued after deploy")
