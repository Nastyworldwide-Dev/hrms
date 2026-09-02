"""Create the Shift Supervisor role and let it manage shift rosters.

A branch leader (F&B / operations) rosters their own team from Nadi or Desk.
This role is the IT-assigned capability — admins grant or revoke it per user.
The role alone is not authority: hrms.api.roster._ensure_can_roster fences every
roster write to the leader's OWN direct reports and permitted companies, so the
capability can never reach another leader's team or another company's staff.
Idempotent (safe to re-run and on fresh installs).
"""

import logging

import frappe
from frappe.permissions import add_permission, update_permission_property

logger = logging.getLogger(__name__)

ROLE = "Shift Supervisor"
# doctype -> permlevel-0 capabilities the roster UI needs. Writes on the roster
# doctypes; read on the lookups. The per-employee fence in roster.py is what
# scopes these to the leader's own team — not these grants.
GRANTS = {
	"Shift Assignment": ("read", "write", "create", "submit"),
	"Shift Schedule Assignment": ("read", "write", "create", "delete"),
	"Shift Schedule": ("read", "write", "create"),
	"Shift Type": ("read",),
	"Shift Location": ("read",),
}


def execute():
	logger.info("[patch] creating %s role and roster permissions", ROLE)
	if not frappe.db.exists("Role", ROLE):
		role = frappe.new_doc("Role")
		role.role_name = ROLE
		role.desk_access = 1
		role.insert(ignore_permissions=True)

	for doctype, caps in GRANTS.items():
		add_permission(doctype, ROLE, 0)
		for cap in caps:
			update_permission_property(doctype, ROLE, 0, cap, 1)

	frappe.clear_cache()
