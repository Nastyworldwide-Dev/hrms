"""Send home every punch a shift it does not belong to is holding.

THE DEFECT. "7PM - 3.30AM" was configured 19:30-07:00 with a check-out grace of
120 minutes, so it accepted punches until 09:00 — and until 86f324f4b a
neighbouring session's grace outranked another assignment's own scheduled
hours. A day worker's 07:38 IN was therefore stamped to the night shift of the
day before. The day then carried two Attendance rows, the Fix screen refused
every rebuild of a two-row day, and the owner reported the tool "appear no
useful. cant do anything" (22 Sep 2026).

THE RULE, in the owner's words, 22 Sep 2026: "if the fix on X isnt Y or Z then
X should revert to its original shift. because 7-3.30 shift only belongs to Y
and Z only. the rest has their own original shift assigned." Y and Z are the
two Shift Assignments that exist for it (HR-EMP-00028, HR-EMP-00063). So a
punch stamped to a GUARDED shift whose employee is not one of its owners is
wrong BY DEFINITION, whatever produced it, and the roster says what it should
be instead.

WHAT CORRECT MEANS (owner, 22 Sep 2026). One shift owns the day; one clean IN
and OUT; the OUT may fall on the next calendar date when the shift crosses
midnight, and what is past the shift's end is OT; exactly ONE Attendance row;
and the row is computed from the punches, never typed. This job restores the
first: the STAMP. The engine's re-mark does the rest from it — it is the only
thing here that decides an hour or a status.

HOW. `restamp`, the one resolution — the same `fetch_shift` a fresh tap runs,
carrying the fixed rule. There is no second copy of the judgement in this file,
only the choice of WHO.

TWO POWERS THIS JOB HAS AND THE ORDINARY PATHS DO NOT, both granted by the
owner for this repair and passed explicitly so nothing else inherits them:

* `mirrored_ok` — the punches the old ERP sent are in scope. "anything on 4th
  september and before, they are all check in out attendance pulled from erp.
  basically it needs to be fix." The post-cutover guardrail otherwise skips
  them, which would have left the whole 1 Aug - 4 Sep window untouched.
* `authoritative` — the re-mark carries HR's own authority, so a day a person
  keyed BY HAND is rebuilt rather than held. "despite manual hr effort, it
  might still do wrong due to this wrong mechanism." Option B, 22 Sep 2026.

WHAT IS STILL NEVER TOUCHED: money. A submitted Salary Slip covering the day,
or submitted Overtime Details on the row, holds it — neither flag waives that
(`attendance_recovery._repair_financial_dependency`). A held day is logged with
its reason and is the short list HR reads afterwards.

IDEMPOTENT by construction: `restamp` writes only a stamp that DIFFERS, so a
repaired punch re-resolves to what it already carries. A second run is a read.

One employee per transaction: a failure is rolled back and logged, and the next
employee is attempted.
"""

import logging

import frappe
from frappe.utils import add_days, getdate, nowdate

from hrms.utils.restamp import restamp

logger = logging.getLogger(__name__)

#: The glitch window's floor. Owner: "1 august to whatever the problem last".
FROM_DATE = "2026-08-01"

#: A shift only these employees may ever be stamped with. Read from the roster
#: would be circular — the roster is what a stray assignment corrupted, and the
#: owner named the two holders explicitly after checking the list himself
#: (Shift Assignment, filtered to this shift: 2 of 2). `roster_drifted` checks
#: at RUN time that the list still says that, and refuses the shift if not: the
#: job runs on the owner's schedule, not this commit's.
GUARDED_SHIFTS = {
	"7PM - 3.30AM": ("HR-EMP-00028", "HR-EMP-00063"),
}

REASON = "a shift that is not this employee's was holding the punch (owner rule, 22 Sep 2026)"


def roster_drifted(shift, owners) -> str | None:
	"""Why this shift's roster no longer says what the owner checked, or None.

	The owner list here is a constant because the roster is exactly what a
	stray assignment corrupted — reading it back would be circular. But the
	list was true when he read it, and this job runs later, on his schedule,
	against a site that has kept moving. A third person legitimately assigned
	the shift meanwhile is an OWNER, and reverting their punches would be this
	job committing the defect it exists to repair.

	So a drifted roster REFUSES the shift rather than repairing against a
	stale list. Doing nothing is recoverable; reverting a real owner's month
	is not.

	WHY THE WHOLE SHIFT, AND NOT JUST THE DRIFTED NAME (review of 29d56b08f).
	The obvious lighter answer is to treat an extra assignee as an owner too —
	exclude them, repair everyone else. That is precisely the circularity this
	constant exists to avoid: a STRAY assignment is what stamped these punches
	to the wrong shift in the first place, so reading ownership back out of the
	roster would let the defect grant itself an exemption and skip a person who
	should be repaired. The constant is the only reading of ownership taken
	while a human was looking at the list.

	Refusing costs nothing for the two known owners: their punches on their own
	shift are correct by definition and this job never touches them. What it
	defers is the repair of everyone else on that shift, until a human reads
	the Error Log and says who owns it now. That is the intended trade.
	"""
	assigned = {
		row["employee"]
		for row in frappe.get_all(
			"Shift Assignment",
			filters={"shift_type": shift, "docstatus": 1},
			fields=["employee"],
			limit_page_length=0,
		)
	}
	extra = sorted(assigned - set(owners))
	if extra:
		return f"{shift} is also assigned to {', '.join(extra)}, who this job would treat as wrong"
	return None


def employees_holding_a_shift_they_do_not_own(from_date, to_date) -> list:
	"""Employees carrying a punch stamped to a guarded shift they do not own.

	The window is read against the punch's own clock `time`, not its shift
	stamp: the stamp is the thing under suspicion, so selecting by it would
	trust the value being repaired.
	"""
	found = set()
	for shift, owners in GUARDED_SHIFTS.items():
		drifted = roster_drifted(shift, owners)
		if drifted:
			logger.error("[wrong_shift_repair] %s SKIPPED: %s", shift, drifted)
			frappe.log_error(
				title=f"Wrong-shift repair skipped {shift}",
				message=(
					f"{drifted}.\n\nThe owner named this shift's holders on 22 September 2026 "
					"after reading the assignment list himself. The list has changed since, so "
					"nothing was repaired for this shift: re-check who owns it and update "
					"GUARDED_SHIFTS before running the job again."
				),
			)
			continue
		rows = frappe.get_all(
			"Employee Checkin",
			filters={
				"shift": shift,
				"employee": ("not in", list(owners)),
				"time": ("between", [f"{getdate(from_date)} 00:00:00", f"{getdate(to_date)} 23:59:59"]),
			},
			fields=["employee"],
			limit_page_length=0,
		)
		for row in rows:
			found.add(row["employee"])
		logger.info(
			"[wrong_shift_repair] %s: %d punch(es) on %d employee(s) who do not own it, %s..%s",
			shift,
			len(rows),
			len({r["employee"] for r in rows}),
			from_date,
			to_date,
		)
	return sorted(found)


def run_repair(from_date=FROM_DATE, to_date=None, reason=REASON) -> dict:
	"""Re-resolve every affected employee's punches over the whole window.

	The employee is the unit, not the punch: a wrong stamp moves a punch between
	shift days, and both days have to be re-marked in order, oldest first, which
	is what `restamp` does for a range. Returns {"employees", "punches",
	"released", "failed"}.
	"""
	# Yesterday, not today: today is still being punched, and a day whose OUT
	# has not happened yet would be re-marked from half a session.
	to_date = getdate(to_date) if to_date else getdate(add_days(nowdate(), -1))
	from_date = getdate(from_date)
	employees = employees_holding_a_shift_they_do_not_own(from_date, to_date)
	out = {"employees": 0, "punches": 0, "released": 0, "failed": []}
	for employee in employees:
		out["employees"] += 1
		try:
			result = restamp(
				employee,
				from_date,
				to_date,
				reason=reason,
				dry_run=False,
				mirrored_ok=True,
				authoritative=True,
			)
			out["punches"] += len(result["planned"])
			out["released"] += len(result["released"])
			# One employee per transaction: a failure later must not undo the
			# people already repaired, and the queued re-marks fire on commit.
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			out["failed"].append(employee)
			logger.exception("[wrong_shift_repair] %s could not be repaired; continuing", employee)
			frappe.log_error(
				title=f"Wrong-shift repair failed for {employee}",
				message=frappe.get_traceback(),
			)
	logger.warning(
		"[wrong_shift_repair] %s..%s: %d employee(s), %d punch(es) re-stamped, "
		"%d released from attendance, %d failed",
		from_date,
		to_date,
		out["employees"],
		out["punches"],
		out["released"],
		len(out["failed"]),
	)
	return out
