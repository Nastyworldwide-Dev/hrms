"""Repair the OT hours the old rounding order threw away.

Nabil, 11 Sep 2026: "repair last 2 months."

2fc1db148 changed the order of two rules: the 30-minute ladder now runs BEFORE
the minimum-overtime-minutes gate, per HR ("at 50 minutes and above auto rounded
to 60m so i am eligible for OT Pay"). Every weekday that landed in the 50-59
minute band used to be discarded before the rounding could carry it to a full
hour, and paid nothing.

That fixed new days only. Old submitted rows still hold the discarded figure, so
`Attendance.ot_hours` reads 0 while `get_claimable_ot_summary` recomputes from
the punches and offers the same day as claimable — the record and the card
disagree on the employee's screen, and a day showing 0 is a day nobody opens.

SCOPE: the OT filing window, not all history. Anything older cannot be claimed
(`filing_window.earliest_filable_date`), so repairing it would rewrite submitted
rows nobody can act on — all of the risk, none of the benefit.

SAFETY: `recompute_ot_backfill` now consults the same financial-dependency guard
the attendance repair tool uses. A day an approved OT request, replacement leave
or a submitted payslip depends on is REPORTED and left exactly as it is; HR
corrects those by hand. It is also idempotent — a row whose recomputed figures
match what is stored is skipped, so a re-run writes nothing.
"""

import logging

import frappe
from frappe.utils import getdate

logger = logging.getLogger(__name__)


#: What actually happens to a day the guard refused. It used to tell HR to nudge
#: Out Time and re-save — a manual instruction on exactly the records Nabil asked
#: not to put manual work on. Now the repair recurs on every deploy, so the only
#: days that stay listed are the ones where money has already moved.
_WHAT_HAPPENS_NEXT = (
	"Nothing to do by hand. This repair now runs on every deploy, so any day here "
	"is retried automatically once whatever depends on it is settled — a pending OT "
	"request decided, a draft payslip submitted or cancelled. A day still listed "
	"after that is one where payroll has already PAID the old figure: correcting it "
	"is a payroll decision, not a record edit."
)


def execute():
	"""Patch entry point. Kept registered so a site that has never run the repair
	gets it at its next migrate even if the hook is ever removed; the real home
	is `after_migrate`, so the repair recurs instead of happening once."""
	run_repairs()


def run_repairs():
	from hrms.hr.doctype.attendance.attendance import (
		recompute_ot_backfill,
		repair_typed_working_hours,
	)
	from hrms.utils.filing_window import earliest_filable_date

	today = getdate()
	from_date = earliest_filable_date(today)
	logger.info("[ot_backfill] repairing the filing window %s..%s", from_date, today)

	_run(
		"overtime",
		recompute_ot_backfill(from_date, today, dry_run=0),
		from_date,
		today,
		"old_ot_hours",
		"new_ot_hours",
	)
	# The early-arrival rule (19c939278) also only applied going forward, and a
	# corrected row is never revisited — auto_attendance is 0 on it. Same window,
	# same guard.
	_run(
		"working hours",
		repair_typed_working_hours(from_date, today, dry_run=0),
		from_date,
		today,
		"old_working_hours",
		"new_working_hours",
	)


def _run(what, result, from_date, to_date, old_key, new_key):
	msg = (
		f"{what} repair {from_date}..{to_date}: scanned {result['scanned']}, "
		f"changed {result['changed']}, written {result['written']}, "
		f"left alone because a payout depends on them {result['locked']}"
	)
	logger.warning("[ot_backfill] %s", msg)
	print(f"[ot_backfill] {msg}")
	if result["locked"]:
		detail = "\n".join(
			f"{row['attendance']} — {row['employee']} on {row['date']}: "
			f"{row[old_key]} stored, {row[new_key]} correct"
			for row in result["skipped"]
		)
		frappe.log_error(
			title=f"{what.title()} repair: days a payout depends on",
			message=(
				f"These days hold the old {what} figure and were NOT rewritten, because "
				"an approved OT request, replacement leave or a submitted payslip "
				f"already depends on them.\n\n{_WHAT_HAPPENS_NEXT}\n\n" + detail
			),
		)


def after_migrate():
	"""Run the repairs on EVERY deploy, never breaking one.

	A patch runs once. A day this could not repair on the day it first ran —
	because an OT request was pending a decision, say — would otherwise hold the
	wrong figure for ever, and the only remedy on offer was asking HR to edit
	records by hand. Recurring, it repairs itself the next time the obstacle is
	gone, and nobody touches anything.

	Idempotent by construction: a row whose recomputed figures already match is
	skipped before any guard runs, so a healthy deploy writes nothing.
	"""
	try:
		run_repairs()
	except Exception:
		logger.error("[ot_backfill] repair run failed", exc_info=True)
		frappe.log_error(title="Attendance repair failed", message=frappe.get_traceback())
		print("[ot_backfill] repair run FAILED — see Error Log; the deploy itself is unaffected")
