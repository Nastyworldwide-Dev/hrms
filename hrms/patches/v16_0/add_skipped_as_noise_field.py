"""Create `Employee Checkin.skipped_as_noise`, and tick the taps HR already judged.

Same gap and same shape as `ensure_extension_custom_fields`: the field is
defined once in `hrms.utils.extension_custom_fields.get_extension_custom_fields`
for the install path, and a migrate on an existing site never calls that.

Why the field exists: `skip_auto_attendance` was carrying two different
meanings. A tap HR ignored is NOISE — the day reads straight across it. A
rejected punch, an off-shift punch, and the punches
`handle_attendance_exception` skip-stamps when a rebuild is refused by the
financial guard are NOT verified evidence, and counting time across them would
pay minutes nobody checked. `ShiftType.splits_the_day` needs to tell them apart.

The column defaults to 0, which is the WALL — how every punch behaved before the
field existed.

THE BACKFILL. A tap HR ignored through Fix Day BEFORE this field existed is
skipped with no verdict, so it would read as a wall again and split the day the
way Norazlin's 4 September split — the defect this whole line of work fixed.
Re-running the Fix Day rebuild heals such a day by itself, but a day the hourly
job quietly reprocesses is never routed through that.

So the taps are ticked from the app's own audit record rather than guessed at:
every `HR Day Fix Log` entry whose action was `ignore_tap` or `rebuild_day`,
that was not undone, names the taps it acted on in `refs`. Of those, only the
ones still carrying `skip_auto_attendance = 1` are ticked — a tap that counts
again is not noise, and the session taps a rebuild KEPT are in `refs` too.

Nothing else is touched. A rejected punch, an off-shift punch and anything the
system deferred keep the wall, which is the reading they have always had.

Idempotent both ways: `create_custom_fields(..., update=True)` is a no-op on a
field that is already correct, and the backfill re-ticks rows that are already
ticked.
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.utils.extension_custom_fields import get_extension_custom_fields

logger = logging.getLogger(__name__)

FIELD = "skipped_as_noise"
#: the Fix Day actions that mean "this tap is not there", as recorded in the log
JUDGED_NOISE = ("ignore_tap", "rebuild_day")


def execute():
	fields = {
		"Employee Checkin": [
			row
			for row in get_extension_custom_fields().get("Employee Checkin", [])
			if row.get("fieldname") == FIELD
		]
	}
	if not fields["Employee Checkin"]:
		logger.error("[skipped_as_noise] definition missing; nothing to create")
		return
	create_custom_fields(fields, update=True)
	logger.info("[skipped_as_noise] Employee Checkin.%s ensured (default 0 = wall)", FIELD)
	_backfill_the_taps_hr_judged()


def _backfill_the_taps_hr_judged():
	names = set()
	for entry in frappe.get_all(
		"HR Day Fix Log",
		filters={"action": ["in", JUDGED_NOISE], "undone": 0},
		fields=["name", "refs"],
		limit_page_length=0,
	):
		names.update(ref.strip() for ref in (entry.get("refs") or "").split(",") if ref.strip())
	if not names:
		logger.info("[skipped_as_noise] no Fix Day ignores on record; nothing to backfill")
		return

	# Only the ones still skipped: a tap that counts again is not noise, and a
	# rebuild's `refs` names the session taps it KEPT alongside the ones it dropped.
	still_skipped = frappe.get_all(
		"Employee Checkin",
		filters={"name": ["in", sorted(names)], "skip_auto_attendance": 1},
		pluck="name",
	)
	logger.info(
		"[skipped_as_noise] %d of %d tap(s) named by a Fix Day ignore are still skipped and are "
		"ticked as noise; the rest count again or were never skipped",
		len(still_skipped),
		len(names),
	)
	for name in still_skipped:
		frappe.db.set_value("Employee Checkin", name, FIELD, 1, update_modified=False)
