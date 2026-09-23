"""Create `Employee.nadi_shift_reminders` (default ON) on existing sites.

The definition lives in `hrms.utils.extension_custom_fields` for the install
path; a migrate on an existing site never calls that, so this patch creates it.

A new Check column with default 1 is filled with 1 for every existing row by the
schema change itself, so everybody starts with reminders ON (owner ruling,
23 Sep 2026). Idempotent: `create_custom_fields(..., update=True)`.
"""

import logging

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.utils.extension_custom_fields import get_extension_custom_fields

logger = logging.getLogger(__name__)

FIELD = "nadi_shift_reminders"


def execute():
	rows = [row for row in get_extension_custom_fields().get("Employee", []) if row.get("fieldname") == FIELD]
	if not rows:
		logger.error("[shift_reminders] definition missing; nothing to create")
		return
	create_custom_fields({"Employee": rows}, update=True)
	logger.info("[shift_reminders] Employee.%s ensured (default 1 = on)", FIELD)
