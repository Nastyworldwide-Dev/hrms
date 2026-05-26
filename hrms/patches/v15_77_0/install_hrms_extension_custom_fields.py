"""Install / upsert the HRMS-extension custom fields that previously lived
in the nsty app.

Adds (idempotent — create_custom_fields with update=True):

  Employee
    - restrict_user_permission_to_hrms (Check)

  Employee Checkin
    - requires_remote_approval (Check)
    - remote_approval_status (Select: Pending / Approved / Rejected)
    - is_abandoned (Check)

These fields back four hrms-side features now bundled directly in this
app (no separate nsty dependency):
  - Employee.restrict_user_permission_to_hrms drives
    hrms.overrides.employee_hrms_scope.sync_hrms_only_user_permission
    (after_save).
  - The three Employee Checkin fields back the strict / lenient geofence
    flow + the nightly abandoned-IN sweeper.

Safe to re-run; only writes when DocField metadata is missing or stale.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "restrict_user_permission_to_hrms",
					"fieldtype": "Check",
					"label": "Restrict User Permission to HRMS Module Only",
					"insert_after": "create_user_permission",
					"default": "0",
					"description": (
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
					"label": "Requires Remote Approval",
					"insert_after": "offshift",
					"default": "0",
					"read_only": 1,
					"in_standard_filter": 1,
					"description": (
						"Set when the check-in was outside the shift geofence "
						"and is awaiting manager approval."
					),
					"module": "HR",
					"translatable": 0,
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
					"module": "HR",
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
					"description": (
						"Auto-set by the nightly stale-IN sweeper when an IN log "
						"has no matching OUT and is older than the configured "
						"threshold (default 36 hours)."
					),
					"module": "HR",
					"translatable": 0,
				},
			],
		},
		update=True,
	)
	frappe.db.commit()
