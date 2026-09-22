"""Queue the grace re-stamp repair once after deploy — Nabil, 22 Sep 2026.

86f324f4b stopped a night shift's check-out grace from claiming the next
morning's IN. It repairs nothing already written, and the owner's ask was that
the system fix the existing damage itself: "1 time job to run auto and fix
these is good, less manual work."

ONLY enqueues. The work must never run inside `bench migrate`: it re-resolves
every punch of every multi-shift employee back to 1 August, and a migrate held
open that long is killed with the deploy, leaving the repair half done. The job
commits per employee, so a restart loses at most one person's work, and running
it again is a read for everyone already repaired.

Never raises: a deploy must not fail because a background job could not be
queued. If the enqueue is lost, `bench execute
hrms.utils.grace_restamp_repair.run_repair` runs the same job.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	try:
		frappe.enqueue(
			"hrms.utils.grace_restamp_repair.run_repair",
			queue="long",
			timeout=4 * 60 * 60,
			enqueue_after_commit=True,
			job_id="grace-restamp-repair",
			deduplicate=True,
		)
		logger.info("[grace_restamp_repair] queued after deploy")
	except Exception:
		logger.exception("[grace_restamp_repair] could not queue the repair")
		frappe.log_error(title="Grace re-stamp repair could not be queued", message=frappe.get_traceback())
