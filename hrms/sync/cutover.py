"""What a pull may still bring after this site has taken over writing.

During the parallel run the hub mirrored Attendance and Employee Checkin from
the source. After cutover (`unlock_mirrored_writes` on the HRMS ERP Instance)
this site marks attendance itself, and the source's own auto-attendance marks
anyone who punched here Absent. A pull that still carries Attendance copies
that Absent straight over the rows this site owns: on 9 September 2026 a whole
month of attendance read Absent for every employee after one press of "Sync
Employee Data".

Employee Checkin is different. Staff still punch on the source ERP after
cutover (owner decision, 14 September 2026), and those punches must reach this
hub — but only ADDED, through `hrms.sync.checkin_import`, never through the
name-keyed mirror that overwrote local punches in September 2026.

Pure, no frappe import, so the rule is testable as a file.
"""

import logging

logger = logging.getLogger(__name__)

#: Written here alone once the instance is unlocked: the hourly job marks it.
LOCALLY_OWNED_AFTER_CUTOVER = ("Attendance",)

#: Still pulled once unlocked, but append-only (`hrms.sync.checkin_import`).
APPEND_ONLY_AFTER_CUTOVER = ("Employee Checkin",)

#: Parity counts STAMPED rows. After cutover neither doctype gains any — the
#: import inserts unstamped punches — so grading either would report a widening
#: "mismatch" that is the intended state.
UNGRADED_AFTER_CUTOVER = LOCALLY_OWNED_AFTER_CUTOVER + APPEND_ONLY_AFTER_CUTOVER


def _hold_back(requested, unlocked: bool, owned, what: str) -> tuple[list, list]:
	requested = list(requested)
	if not unlocked:
		return requested, []
	held = [d for d in requested if d in owned]
	if held:
		logger.warning("[sync] instance unlocked (cutover): not %s %s", what, ", ".join(held))
	return [d for d in requested if d not in owned], held


def plan_pull_doctypes(requested, unlocked: bool) -> tuple[list, list]:
	"""(doctypes to pull, doctypes held back) for one run."""
	return _hold_back(requested, unlocked, LOCALLY_OWNED_AFTER_CUTOVER, "pulling — this site writes")


def plan_parity_doctypes(requested, unlocked: bool) -> tuple[list, list]:
	"""(doctypes to grade, doctypes left out) for one parity check."""
	return _hold_back(requested, unlocked, UNGRADED_AFTER_CUTOVER, "grading stamped counts of")
