"""Backfill break_hours on existing Fixed Shift Break rows (v15.112.1).

break_hours was a Flexible-only input, so every Fixed row showed
"Break Duration (Hours) 0.00" in the grid even while its Start-End window
was deducting correctly — HR read that as "the break is not registered".
ShiftType.validate_breaks now mirrors the window length into break_hours on
save; this patch does the same one-time sweep for rows saved before the fix.

Idempotent — safe to re-run.
"""

import logging

import frappe

from hrms.utils.break_calculation import fixed_break_hours

logger = logging.getLogger(__name__)


def execute():
	rows = frappe.get_all(
		"Shift Break",
		filters={"parenttype": "Shift Type"},
		fields=["name", "parent", "break_type", "break_hours", "start_time", "end_time"],
	)
	logger.info("[backfill_fixed_break_hours] scanning %d Shift Break rows", len(rows))
	synced = 0
	for row in rows:
		if (row.break_type or "Fixed") == "Flexible":
			continue
		hours = fixed_break_hours(row.start_time, row.end_time)
		if hours <= 0:
			# validate_breaks now rejects this row — surface it at migrate
			# time so HR is not ambushed on their next unrelated save.
			logger.warning(
				"[backfill_fixed_break_hours] %s on Shift Type %r has an unusable window %s-%s; "
				"fix this row or its parent will not save",
				row.name,
				row.parent,
				row.start_time,
				row.end_time,
			)
			continue
		if row.break_hours != hours:
			frappe.db.set_value("Shift Break", row.name, "break_hours", hours, update_modified=False)
			logger.info(
				"[backfill_fixed_break_hours] %s (%s): %s-%s -> %sh",
				row.name,
				row.parent,
				row.start_time,
				row.end_time,
				hours,
			)
			synced += 1
	logger.info("[backfill_fixed_break_hours] synced %d rows", synced)
