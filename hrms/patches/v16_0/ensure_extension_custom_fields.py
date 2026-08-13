"""Create the HR extension custom fields on already-installed sites.

Same gap, same shape, as `add_sync_provenance_fields`. The four fields
(`restrict_user_permission_to_hrms`, `requires_remote_approval`,
`remote_approval_status`, `is_abandoned`) are now defined once in
`hrms.utils.extension_custom_fields.get_extension_custom_fields()` and merged
into `hrms.setup.get_custom_fields()` — which runs from `after_install` only.
`bench migrate` on an existing site never calls it.

That leaves two kinds of site without the fields:

  * anything installed straight from v16, because `install_app` records every
    patch as already applied, so the original
    `v15_77_0.install_hrms_extension_custom_fields` never ran there;
  * and, until this patch, any site upgraded after the install-path fix landed.

Both were reproduced on a disposable bench: a v16 site installed before the fix
reported 0 of the 4 fields even after a successful `bench migrate`, and the OT
suite failed with `Unknown column 'remote_approval_status' in 'SELECT'`. The
geofenced check-in flow, `hrms.utils.ot_calculation`, the stale-IN sweeper and
`hrms.overrides.employee_hrms_scope` all read these columns at runtime.

Imports the SAME definitions the install path uses rather than restating them,
so the two cannot drift.

Idempotent: `create_custom_fields(..., update=True)` is a no-op on a field that
is already present and correct, so re-running it — or running it on a site the
fresh-install path already served — changes nothing.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.utils.extension_custom_fields import get_extension_custom_fields


def execute():
	fields = get_extension_custom_fields()
	frappe.logger("hrms").info(
		"[extension_custom_fields] ensuring HR extension fields on %s", ", ".join(sorted(fields))
	)
	create_custom_fields(fields, update=True)
	frappe.db.commit()
