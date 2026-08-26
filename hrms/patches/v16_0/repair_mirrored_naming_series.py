"""Move every naming counter past the rows already on disk.

THE FAILURE, from production, and reproduced on a bench before this was written:

    Employee Checkin EMP-CKIN-08-2026-000001 already exists

An employee taps Check In and the app hands them a document name the mirror has
already used. Nobody on this hub can check in for any month the sync has
populated, and the same holds for every mirrored doctype that numbers itself.

WHY THE RUNNER FIX IS NOT ENOUGH
`runner.advance_series_past` now moves the counter past whatever a run inserts,
so no NEW sync can open this hole. It cannot close the one already open: the
damage was done by runs that have finished, and a counter only moves on the next
run that happens to insert a row with a high number. HR is blocked now, not at
the next sync.

So this walks what is actually on disk. For each mirrored doctype it finds the
highest numeric suffix per prefix and advances the counter to it.

FORWARD ONLY, and never destructive: it reads names, writes counters, and
touches no document. A counter that is already ahead is left exactly where it
is — winding one back would free numbers that are in use and recreate the
collision pointing the other way, that time overwriting rows instead of failing
loudly.

Safe to re-run. The second pass finds every counter already correct and moves
nothing.
"""

import frappe

from hrms.sync.runner import STAMPED_DOCTYPES, series_matchers, split_series_name


def execute():
	from frappe.model.naming import NamingSeries

	moved = {}
	for doctype in STAMPED_DOCTYPES:
		if not frappe.db.table_exists(doctype):
			continue

		# Patterns come from the DOCTYPE, never from guessing at names. An earlier
		# version split any name at its last non-digit and turned the hash-named
		# row `77r5o9d1b4` into prefix `77r5o9d1b` counter 4, writing that into
		# tabSeries. Doctypes that hash their names (Leave Ledger Entry, Employee)
		# now yield no matchers and are skipped outright.
		matchers = series_matchers(doctype)
		if not matchers:
			continue

		# Highest number per prefix, computed here rather than in SQL: the rule
		# has to be the one the runner uses, and MariaDB cannot express these
		# patterns without a second dialect of the same thing. Names only — no
		# document is loaded.
		highest: dict[str, int] = {}
		for name in frappe.get_all(doctype, pluck="name"):
			split = split_series_name(name, matchers)
			if split:
				prefix, number = split
				highest[prefix] = max(highest.get(prefix, 0), number)

		for prefix, number in highest.items():
			try:
				series = NamingSeries(prefix)
				current = series.get_current_value()
				if number > current:
					series.update_counter(number)
					moved[prefix] = (current, number)
			except Exception as e:  # one bad prefix must not strand the rest
				frappe.log_error(
					title="Could not repair naming counter",
					message=f"{doctype} prefix {prefix} -> {number}: {e}",
				)

	if moved:
		frappe.db.commit()
		lines = "\n".join(f"  {p}: {old} -> {new}" for p, (old, new) in sorted(moved.items()))
		print(f"[repair_mirrored_naming_series] advanced {len(moved)} counter(s):\n{lines}")
	else:
		print("[repair_mirrored_naming_series] every counter already past its rows")
