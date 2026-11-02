"""Create Employee.additional_login_email on already-installed sites.

`get_custom_fields()` runs from `after_install` only; a migrate on an existing
site never calls it (same gap as `ensure_extension_custom_fields`). Imports the
same definition the install path uses, so they cannot drift.

The identity resolver reads this column on every request, so it MUST exist
before the new code serves traffic; this patch is that guarantee.

Idempotent: `create_custom_fields(..., update=True)` is a no-op on a field that
is already present and correct.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.utils.additional_login import get_additional_login_fields


def execute():
	frappe.logger("hrms").info("[additional_login] ensuring Employee.additional_login_email")
	create_custom_fields(get_additional_login_fields(), update=True)
	frappe.db.commit()
