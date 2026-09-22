"""Repair the punches a neighbouring shift's GRACE window swallowed.

86f324f4b fixed the rule: a punch inside another assigned shift's own
SCHEDULED hours is no longer claimed by a neighbouring session whose check-out
grace merely reaches it. That fix changes nothing already written. Norazmi's 11
August 08:09 IN still carries the night's stamp, his 10 August still holds two
Attendance rows, and the Fix screen still refuses to rebuild a day with two
live rows — which is why the owner reported that Fix Attendance "appear no
useful. cant do anything".

Nabil, 22 September 2026: "if we can make 1 time job to run auto and fix these
is good, less manual work. manual if needed but auto must be done correctly."
So the deploy queues this and walks away.

HOW IT REPAIRS: through `hrms.utils.restamp.restamp`, the one resolution — the
SAME code a fresh tap runs (`fetch_shift` on a loaded doc), now carrying the
fixed rule. The repair therefore cannot drift from the rule: there is no second
copy of the judgement here, only the choice of WHO to re-resolve. restamp
rewrites the stamp, releases a punch whose resolution changed from the
Attendance row that was built on the old stamp, and queues the engine's guarded
re-mark of every shift day the punch left or joined. The duplicate row the
owner saw is cancelled by that re-mark, through the never-worse guard, not by
anything typed here.

WHO: only employees who held MORE THAN ONE distinct shift type in the window.
One assignment cannot be swallowed by another assignment's grace, so every
single-shift employee is work nobody needs — and on a full site that is most of
them.

IDEMPOTENT by construction, not by a marker: restamp writes only a stamp that
DIFFERS from the one a punch carries, so a repaired punch re-resolves to what
it already has and is skipped. Running it twice is a read.

NEVER touches a mirrored punch: restamp filters `synced_from_instance` is not
set, because a punch mirrored from another instance belongs to the instance
that owns it (post-cutover guardrail).

One employee's failure does not end the run: it is rolled back, logged, and
the next employee is attempted. An employee left unrepaired keeps the stamp it
has — the same state as before the run — and the nightly re-mark is unaffected.
"""

import logging

import frappe
from frappe.utils import add_days, getdate, nowdate

from hrms.utils.restamp import restamp

logger = logging.getLogger(__name__)

#: The glitch window. Punches before the cutover are the mirror's, not ours.
FROM_DATE = "2026-08-01"

REASON = "grace no longer owns another shift's hours (86f324f4b)"


def employees_at_risk(from_date, to_date) -> list:
	"""Employees who held more than one DISTINCT shift type in the window.

	A single assignment has nothing to be swallowed by: its own grace reaching
	into the next morning is exactly what a grace is for, and the fixed rule
	leaves it alone. Two or more is the precondition for the defect.
	"""
	rows = frappe.get_all(
		"Shift Assignment",
		filters={
			"docstatus": 1,
			"start_date": ("<=", getdate(to_date)),
		},
		or_filters=[
			["end_date", ">=", getdate(from_date)],
			["end_date", "is", "not set"],
		],
		fields=["employee", "shift_type"],
		limit_page_length=0,
	)
	shifts = {}
	for row in rows:
		shifts.setdefault(row["employee"], set()).add(row["shift_type"])
	at_risk = sorted(employee for employee, kinds in shifts.items() if len(kinds) > 1)
	logger.info(
		"[grace_restamp_repair] %d of %d assigned employee(s) held more than one shift in %s..%s",
		len(at_risk),
		len(shifts),
		from_date,
		to_date,
	)
	return at_risk


def run_repair(from_date=FROM_DATE, to_date=None, reason=REASON) -> dict:
	"""Re-resolve every at-risk employee's punches over the window.

	Returns {"employees": attempted, "punches": re-stamped, "released": links
	cleared, "failed": [employee, ...]}.
	"""
	# Yesterday, not today: today is still being punched, and a day whose OUT
	# has not happened yet would be re-marked from half a session.
	to_date = getdate(to_date) if to_date else getdate(add_days(nowdate(), -1))
	employees = employees_at_risk(from_date, to_date)
	out = {"employees": 0, "punches": 0, "released": 0, "failed": []}
	for employee in employees:
		out["employees"] += 1
		try:
			result = restamp(employee, from_date, to_date, reason=reason, dry_run=False)
			out["punches"] += len(result["planned"])
			out["released"] += len(result["released"])
			# One employee per transaction: a failure later must not undo the
			# people already repaired, and the queued re-marks fire on commit.
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			out["failed"].append(employee)
			logger.exception("[grace_restamp_repair] %s could not be repaired; continuing", employee)
			frappe.log_error(
				title=f"Grace re-stamp repair failed for {employee}",
				message=frappe.get_traceback(),
			)
	logger.warning(
		"[grace_restamp_repair] %s..%s: %d employee(s), %d punch(es) re-stamped, "
		"%d released from attendance, %d failed",
		from_date,
		to_date,
		out["employees"],
		out["punches"],
		out["released"],
		len(out["failed"]),
	)
	return out
