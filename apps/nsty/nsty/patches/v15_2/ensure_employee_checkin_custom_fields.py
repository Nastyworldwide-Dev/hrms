"""Idempotent backfill for Employee Checkin custom fields.

Symptom on Frappe Cloud (v15.76.0): GET /api/method/frappe.client.get_list
returned `frappe.exceptions.DataError: Field not permitted in query:
requires_remote_approval`. The cause is that the Custom Field rows for
requires_remote_approval / remote_approval_status / is_abandoned were
never installed on the site, so the field isn't in the DocType meta and
Frappe's validate_fields rejects the SPA's list query.

Same approach as v15_0.ensure_restrict_user_permission_field — call
create_custom_fields with update=True so the patch is safe to run
repeatedly. If the fields are already present, this only refreshes
metadata; if they're missing, this creates them in place.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Employee Checkin": [
				{
					"fieldname": "requires_remote_approval",
					"fieldtype": "Check",
					"label": "Requires Remote Approval",
					"insert_after": "offshift",
					"default": "0",
					"read_only": 1,
					"in_standard_filter": 1,
					"module": "Nsty",
					"translatable": 0,
					"description": (
						"Set when the check-in was outside the shift geofence "
						"and is awaiting manager approval."
					),
				},
				{
					"fieldname": "remote_approval_status",
					"fieldtype": "Select",
					"label": "Remote Approval Status",
					"insert_after": "requires_remote_approval",
					"options": "\nPending\nApproved\nRejected",
					"depends_on": "eval:doc.requires_remote_approval || doc.remote_approval_status",
					"read_only": 1,
					"in_standard_filter": 1,
					"module": "Nsty",
					"translatable": 0,
				},
				{
					"fieldname": "is_abandoned",
					"fieldtype": "Check",
					"label": "Is Abandoned",
					"insert_after": "remote_approval_status",
					"default": "0",
					"read_only": 1,
					"in_standard_filter": 1,
					"module": "Nsty",
					"translatable": 0,
					"description": (
						"Auto-set by the nightly stale-IN sweeper when an IN log "
						"has no matching OUT and is older than the configured "
						"threshold (default 36 hours)."
					),
				},
			]
		},
		update=True,
	)
	frappe.db.commit()
