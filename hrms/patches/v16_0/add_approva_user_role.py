"""Create the "Approva User" role (owner, 30 Sep 2026).

A special case: someone who needs Approva (purchase requests and approvals)
without the accounting or HR access that the roles already offered it carry.
Holding it only shows the Approva link in Nadi (hrms.api.app_links); what the
person can do inside Approva is Approva's own permission check. Grants no
doctype permission here. Idempotent.
"""

import logging

import frappe

from hrms.api.app_links import APPROVA_USER_ROLE

logger = logging.getLogger(__name__)


def execute():
	if frappe.db.exists("Role", APPROVA_USER_ROLE):
		return
	role = frappe.new_doc("Role")
	role.role_name = APPROVA_USER_ROLE
	role.desk_access = 0
	role.insert(ignore_permissions=True)
	logger.info("[patch] created role %s", APPROVA_USER_ROLE)
