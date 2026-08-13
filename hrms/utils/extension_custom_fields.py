"""Custom fields this fork's HR extensions depend on, for the INSTALL path.

`hrms/patches/v15_77_0/install_hrms_extension_custom_fields` created these, and
that is enough for a site that upgrades — but not for a new one. `install_app`
records every patch as already applied on a fresh site, so a patch-only field is
never created there, and the code that queries it fails with
`Unknown column '<field>' in 'SELECT'`.

That is not hypothetical: on a fresh v16 site the OT calculation, the remote
check-in API and the stale-IN sweeper all query `remote_approval_status` /
`is_abandoned`, and `hrms.overrides.employee_hrms_scope` reads
`restrict_user_permission_to_hrms`. Without these fields the whole geofenced
check-in feature and the HRMS-only User Permission scope are dead on arrival.

`hrms.sync.runner.get_provenance_custom_fields` already solved the same problem
the same way; this module extends it to the rest of the fork's custom fields.
The patch stays as it is — it remains the upgrade path for existing sites, and
`create_custom_fields(..., update=True)` is idempotent, so a field defined in
both places is created once and then updated in place.
"""

from __future__ import annotations

import logging

from frappe import _

logger = logging.getLogger(__name__)


def get_extension_custom_fields() -> dict:
	"""Definitions merged into `hrms.setup.get_custom_fields()`.

	Kept byte-compatible with the patch that introduced them so an upgraded site
	and a fresh site end up with identical fields.
	"""
	logger.debug("[extension_custom_fields] contributing HR extension fields to the install path")
	return {
		"Employee": [
			{
				"fieldname": "restrict_user_permission_to_hrms",
				"fieldtype": "Check",
				"label": _("Restrict User Permission to HRMS Module Only"),
				"insert_after": "create_user_permission",
				"default": "0",
				"description": _(
					"When checked, ALL User Permissions for this employee's user "
					"account are scoped to HRMS-related doctypes only (Employee, "
					"Attendance, Leave, Salary Slip, etc.). Other modules (Sales, "
					"Stock, Accounts, Purchase) are unaffected. Works independently "
					"of 'Create User Permission'."
				),
				"module": "HR",
				"translatable": 0,
			}
		],
		"Employee Checkin": [
			{
				"fieldname": "requires_remote_approval",
				"fieldtype": "Check",
				"label": _("Requires Remote Approval"),
				"insert_after": "offshift",
				"default": "0",
				"read_only": 1,
				"in_standard_filter": 1,
				"description": _(
					"Set when the check-in was outside the shift geofence and is awaiting manager approval."
				),
				"module": "HR",
				"translatable": 0,
			},
			{
				"fieldname": "remote_approval_status",
				"fieldtype": "Select",
				"label": _("Remote Approval Status"),
				"insert_after": "requires_remote_approval",
				"options": "\nPending\nApproved\nRejected",
				"depends_on": "eval:doc.requires_remote_approval || doc.remote_approval_status",
				"read_only": 1,
				"in_standard_filter": 1,
				"module": "HR",
				"translatable": 0,
			},
			{
				"fieldname": "is_abandoned",
				"fieldtype": "Check",
				"label": _("Is Abandoned"),
				"insert_after": "remote_approval_status",
				"default": "0",
				"read_only": 1,
				"in_standard_filter": 1,
				"description": _(
					"Auto-set by the nightly stale-IN sweeper when an IN log "
					"has no matching OUT and is older than the configured "
					"threshold (default 36 hours)."
				),
				"module": "HR",
				"translatable": 0,
			},
		],
	}
