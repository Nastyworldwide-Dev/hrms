"""What a pull may still bring after this site has taken over writing.

During the parallel run the hub mirrored Attendance and Employee Checkin from
the source. After cutover (`unlock_mirrored_writes` on the HRMS ERP Instance)
this site records punches and marks attendance itself, and the source no
longer receives punches at all — so its own auto-attendance marks everyone
Absent. A pull that still carries those two doctypes copies that Absent
straight over the rows this site owns: on 9 September 2026 a whole month of
attendance read Absent for every employee after one press of "Sync Employee
Data".

Pure, no frappe import, so the rule is testable as a file.
"""

import logging

logger = logging.getLogger(__name__)

#: Written here, by punches and the hourly job, once the instance is unlocked.
LOCALLY_OWNED_AFTER_CUTOVER = ("Attendance", "Employee Checkin")


def plan_pull_doctypes(requested, unlocked: bool) -> tuple[list, list]:
	"""(doctypes to pull, doctypes held back) for one run."""
	requested = list(requested)
	if not unlocked:
		return requested, []
	held = [d for d in requested if d in LOCALLY_OWNED_AFTER_CUTOVER]
	kept = [d for d in requested if d not in LOCALLY_OWNED_AFTER_CUTOVER]
	if held:
		logger.warning(
			"[sync] instance unlocked (cutover): not pulling %s — this site writes them now",
			", ".join(held),
		)
	return kept, held
