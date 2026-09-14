"""Queue the one automatic attendance recovery after this deploy.

Only enqueues — the migrate stays fast and can never fail because of the
recovery itself (hrms/utils/attendance_auto_recovery.py never raises).
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
	logger.info("[attendance_auto_recovery] one-time recovery queued after deploy")
