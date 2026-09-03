"""Re-heal naming counters across the full migration set, on deploy.

`repair_mirrored_naming_series` (2026-08-26) advanced the counters that were behind
THEN, over the sync's mirror set. Two things have happened since: HR has imported
employees through Desk (explicit names, tabSeries untouched), so "Employee
HR-EMP-00318 already exists" is back; and the repair now needs to cover the request
and master doctypes HR imports directly, not only the mirror set.

A patch runs once, so a fresh one is how the current state gets re-healed; the new
after-Data-Import hook (hrms.utils.naming_series_repair.after_data_import) then keeps
every future import healed without anyone running a command. Same shared,
forward-only repair — safe to re-run, moves nothing once every counter is ahead.
"""

import frappe


def execute():
	from hrms.utils.naming_series_repair import repair_naming_series

	moved = repair_naming_series()
	if moved:
		frappe.db.commit()
		lines = "\n".join(f"  {dt}: {counters}" for dt, counters in sorted(moved.items()))
		print(f"[resync_naming_series_after_import] advanced counters on {len(moved)} doctype(s):\n{lines}")
	else:
		print("[resync_naming_series_after_import] every counter already past its rows")
