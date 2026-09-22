"""Queue the wrong-shift repair once, after the migrate — owner rule, 22 Sep 2026.

"7PM - 3.30AM" belongs to two people. Every punch of anyone else that carries
it is wrong, and goes back to that person's own assigned shift; the engine then
rebuilds the day from the corrected stamps. See hrms/utils/wrong_shift_repair.

ONLY enqueues. The work must never run inside `bench migrate`: it re-resolves
punches back to 1 August across the ERP-pulled window, and a migrate held open
that long is killed with the release, leaving the repair half done. The job
commits per employee, so a restart loses at most one person's work, and running
it again is a read for everyone already repaired.

Never raises: a migrate must not fail because a background job could not be
queued. If the enqueue is lost, `bench execute
hrms.utils.wrong_shift_repair.run_repair` runs the same job.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	try:
		frappe.enqueue(
			"hrms.utils.wrong_shift_repair.run_repair",
			queue="long",
			timeout=4 * 60 * 60,
			enqueue_after_commit=True,
			job_id="wrong-shift-repair",
			deduplicate=True,
		)
		logger.info("[wrong_shift_repair] queued after the migrate")
	except Exception:
		logger.exception("[wrong_shift_repair] could not queue the repair")
		frappe.log_error(title="Wrong-shift repair could not be queued", message=frappe.get_traceback())
