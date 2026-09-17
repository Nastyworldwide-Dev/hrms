"""Create `Employee Checkin.skipped_as_noise` on already-installed sites.

Same gap and same shape as `ensure_extension_custom_fields`: the field is
defined once in `hrms.utils.extension_custom_fields.get_extension_custom_fields`
for the install path, and `bench migrate` on an existing site never calls that.

Why the field exists: `skip_auto_attendance` was carrying two different
meanings. A tap HR ignored is NOISE — the day reads straight across it. A
rejected punch, an off-shift punch, and the punches
`handle_attendance_exception` skip-stamps when a rebuild is refused by the
financial guard are NOT verified evidence, and counting time across them would
pay minutes nobody checked. `ShiftType.splits_the_day` needs to tell them apart.

The default is 0, which is the WALL — exactly how every row behaved before this
field existed. So this patch changes no day: it only gives the writers that mean
"noise" somewhere to say so.

Idempotent: `create_custom_fields(..., update=True)` is a no-op on a field that
is already present and correct.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.utils.extension_custom_fields import get_extension_custom_fields

FIELD = "skipped_as_noise"


def execute():
	fields = {
		"Employee Checkin": [
			row
			for row in get_extension_custom_fields().get("Employee Checkin", [])
			if row.get("fieldname") == FIELD
		]
	}
	if not fields["Employee Checkin"]:
		frappe.logger("hrms").error("[skipped_as_noise] definition missing; nothing to create")
		return
	create_custom_fields(fields, update=True)
	frappe.logger("hrms").info("[skipped_as_noise] Employee Checkin.%s ensured (default 0 = wall)", FIELD)
