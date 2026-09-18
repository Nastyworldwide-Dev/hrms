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


def leave_existing_row_alone(doctype: str, exists: bool, unlocked: bool, create_only: bool) -> bool:
	"""Whether a pull must leave a row that is already here exactly as it is. Pure.

	Owner ruling, 18 Sep 2026, after a sync reverted live employees' shift and
	location to whatever the source holds: "its better to only pull what is
	absent not overwrite what is already exist".

	So once this site is unlocked, EVERY mirrored doctype behaves the way the
	master lists always have — added if missing, never rewritten. Not a list of
	protected doctypes and not a list of protected fields: the run that caused
	this touched Employee (default_shift, branch, holiday_list), Shift
	Assignment and Shift Schedule Assignment, and a rule written as a list is a
	rule that is wrong the next time somebody mirrors something new.

	What it gives up is corrections flowing from the source after cutover. That
	is the point — HR works here now.

	ONE CONSEQUENCE WORTH KNOWING, because it is not about shift data. The pull
	used to call `_reconcile_user_status` for every Employee row it rewrote, so
	somebody marked Left on the SOURCE had their hub login disabled on the next
	sync. A skipped row never reaches that call, so after cutover the source can
	no longer disable anyone here.

	It is covered in the model the owner described — HR marks a leaver in this
	site, and `Employee.on_update` disables the User through the ordinary save —
	and it is NOT covered if somebody is terminated only on the old ERP. Raised
	with the owner 18 Sep 2026; recorded here rather than fixed by quietly
	letting the source write again, which is the thing he asked to stop.
	"""
	if not exists:
		return False
	if create_only:
		return True
	if unlocked:
		logger.info("[sync] %s is already here and this site is unlocked: left untouched", doctype)
		return True
	return False


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
