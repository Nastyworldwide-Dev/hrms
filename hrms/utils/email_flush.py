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
	instantly, so the paired email should leave the server instantly too.

	The enqueue itself is deferred to commit time (frappe.db.after_commit) so
	the job-id dedup check runs when jobs actually exist — enqueue(...,
	enqueue_after_commit=True) checks dedup at call time, which lets multiple
	calls in one transaction schedule duplicate flushes.

	Never raises, at scheduling time or at commit time: if the flush can't be
	scheduled the email still goes out on the next scheduler tick, and a redis
	hiccup must not surface as an error after the SQL commit succeeded.
	"""
	try:
		frappe.db.after_commit.add(_enqueue_flush)
	except Exception:
		logger.warning("[email_flush] could not register after-commit flush", exc_info=True)


def _enqueue_flush() -> None:
	"""Runs inside frappe.db.after_commit — must swallow every failure."""
	try:
		frappe.enqueue(
			"frappe.email.queue.flush",
			queue="short",
			job_id=FLUSH_JOB_ID,
			deduplicate=True,
		)
		logger.info("[email_flush] scheduled instant Email Queue flush")
	except Exception:
		logger.warning("[email_flush] could not schedule instant flush", exc_info=True)
