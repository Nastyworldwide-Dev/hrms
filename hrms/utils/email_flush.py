# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe

logger = logging.getLogger(__name__)

FLUSH_JOB_ID = "hrms-instant-email-flush"


def flush_email_queue_after_commit() -> None:
	"""Send queued notification emails as soon as the current transaction commits.

	frappe.sendmail parks mail in the Email Queue until the scheduler's periodic
	flush (up to a few minutes on the tick). PWA/realtime notifications fire
	instantly, so the paired email should leave the server instantly too. The
	flush runs in a short-queue worker — never inline in the web request — and
	is deduplicated so bursts of notifications schedule a single flush.

	Never raises: if scheduling fails the email still goes out on the next
	scheduler flush, so the notification flow must not break.
	"""
	try:
		frappe.enqueue(
			"frappe.email.queue.flush",
			queue="short",
			job_id=FLUSH_JOB_ID,
			deduplicate=True,
			enqueue_after_commit=True,
		)
		logger.info("[email_flush] scheduled instant Email Queue flush after commit")
	except Exception:
		logger.warning("[email_flush] could not schedule instant flush", exc_info=True)
