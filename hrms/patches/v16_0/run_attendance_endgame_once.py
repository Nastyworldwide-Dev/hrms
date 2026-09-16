"""Queue the endgame repair once after deploy — Nabil, 16 Sep 2026.

"too much mechanical work for us and for HR — it should be done automatically by
the system at once." So the deploy asks for the whole repair and walks away:
ownership relabel, the ERP punch copy, every recovery step, the OT recount and
one HR summary, for 1 August → yesterday.

ONLY enqueues. The work must never run inside `bench migrate`: it takes hours on
a full month, and a migrate that holds the deploy open that long is killed with
it, leaving the repair half done and no marker saying where. The job itself is
chunked and resumable, and the nightly scheduler entry finishes anything a
restart interrupts.

Never raises: a deploy must not fail because a background job could not be
queued. If the enqueue is lost, the nightly picks the run up.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	try:
		from hrms.utils.attendance_endgame import queue_endgame

		queue_endgame(reason="deploy")
	except Exception:
		logger.exception("[attendance_endgame] could not queue the run; the nightly will pick it up")
		frappe.log_error(title="Attendance endgame could not be queued", message=frappe.get_traceback())
