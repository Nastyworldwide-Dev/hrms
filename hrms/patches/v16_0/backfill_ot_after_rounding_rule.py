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


def execute():
	from hrms.hr.doctype.attendance.attendance import recompute_ot_backfill
	from hrms.utils.filing_window import earliest_filable_date

	today = getdate()
	from_date = earliest_filable_date(today)
	logger.info("[ot_backfill] repairing the filing window %s..%s", from_date, today)

	result = recompute_ot_backfill(from_date, today, dry_run=0)
	msg = (
		f"OT backfill {from_date}..{today}: scanned {result['scanned']}, "
		f"changed {result['changed']}, written {result['written']}, "
		f"left alone because a payout depends on them {result['locked']}"
	)
	logger.warning("[ot_backfill] %s", msg)
	print(f"[ot_backfill] {msg}")
	if result["locked"]:
		detail = "\n".join(
			f"{row['attendance']} — {row['employee']} on {row['date']}: "
			f"{row['old_ot_hours']} h stored, {row['new_ot_hours']} h correct"
			for row in result["skipped"]
		)
		frappe.log_error(
			title="OT backfill: days a payout depends on",
			message=(
				"These days hold the old OT figure and were NOT rewritten, because an "
				"approved OT request, replacement leave or a submitted payslip already "
				"depends on them. HR corrects these by hand.\n\n" + detail
			),
		)
