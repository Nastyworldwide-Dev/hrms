"""One shared naming-counter repair, for the deploy patch and the import hook.

THE COLLISION THIS PREVENTS, seen in production on the hub:

    Employee HR-EMP-00318 already exists   (DuplicateEntryError 1062)

Rows arrive with explicit names — a sync mirror keeps the source's names, and an
HR xlsx import writes the names in the sheet — but neither path moves `tabSeries`.
The counter stays behind the highest name on disk, so the next Desk create is
handed a name that already exists.

`repair_mirrored_naming_series` (patch, 2026-08-26) fixed the state on disk THEN,
but a patch runs once. HR imports employees through Desk AFTER a deploy, which
re-opens the hole — which is why this also wires an after-import hook, the part a
one-off patch structurally cannot cover.

No new advance logic: every counter move goes through `runner.advance_series_past`,
the same forward-only, never-raises, never-winds-back routine the sync uses. This
module only decides WHICH doctypes to walk and reads their names.
"""

import logging

import frappe

from hrms.sync.runner import DEFAULT_SYNC_DOCTYPES, advance_series_past

logger = logging.getLogger(__name__)

#: Doctypes HR loads with explicit names on top of the sync's mirror set. Counter-
#: named ones get repaired; hash- and field-named ones cost nothing — advance_series_past
#: returns {} for them (no series_matchers).
_EXTRA_IMPORTED_DOCTYPES = (
	"OT Request",
	"Replacement Leave Claim",
	"Overtime Slip",
	"Attendance Request",
	"Shift Request",
	"Compensatory Leave Request",
	"Expense Claim",
	"Employee Advance",
	"Leave Encashment",
)


def migration_doctypes() -> tuple:
	"""The full set an HR migration loads by name — the mirror set plus the request
	doctypes HR imports directly. De-duplicated, order preserved."""
	seen = {}
	for dt in tuple(DEFAULT_SYNC_DOCTYPES) + _EXTRA_IMPORTED_DOCTYPES:
		seen[dt] = None
	return tuple(seen)


def repair_naming_series(doctypes=None) -> dict:
	"""Advance each doctype's counter past the highest name already on disk.

	Returns {doctype: {prefix: number}} for every counter moved. Does NOT commit —
	the caller (patch or hook) owns that. Idempotent and forward-only, so it is safe
	to run on every deploy and after every import; a counter already ahead is left
	exactly where it is.
	"""
	doctypes = doctypes or migration_doctypes()
	moved = {}
	for doctype in doctypes:
		if not frappe.db.table_exists(doctype):
			continue
		# ponytail: full name scan per doctype per import; fine at current row counts.
		# If mirrored tables (Attendance/Checkin) reach millions, scope to the batch's
		# reference_doctype rows via Data Import Log instead of re-deriving the max.
		result = advance_series_past(doctype, frappe.get_all(doctype, pluck="name"))
		if result:
			moved[doctype] = result
	logger.info("[naming_series_repair] repaired %d doctype(s): %s", len(moved), moved)
	return moved


def after_data_import(doc, method=None):
	"""Doc-event on Data Import: once an import lands rows, advance THAT doctype's
	counter so the next Desk create cannot collide with an imported name.

	This is the self-healing a one-off patch cannot provide — imports happen through
	the Desk UI after a deploy, and there is no command to run afterwards. Guarded to
	the terminal success states so it fires once per import, not on every status
	write. No commit here: the counter write rides the Data Import doc's own save
	commit, which has already persisted the imported rows by this point.
	"""
	if doc.get("status") not in ("Success", "Partial Success"):
		return
	reference_doctype = doc.get("reference_doctype")
	if not reference_doctype:
		return
	moved = repair_naming_series([reference_doctype])
	if moved:
		frappe.logger("hrms").info(
			"[naming_series_repair] after import of %s advanced %s", reference_doctype, moved
		)
