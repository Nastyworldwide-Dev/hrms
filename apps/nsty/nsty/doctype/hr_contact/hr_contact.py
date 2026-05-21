# Copyright (c) 2026, Nsty and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document

logger = logging.getLogger(__name__)

HR_ROLES = {"HR Manager", "HR User"}


class HRContact(Document):
	def validate(self):
		if not self.employee:
			frappe.throw(_("Employee is required."))

		user_id = frappe.db.get_value("Employee", self.employee, "user_id")
		if not user_id:
			frappe.throw(_("Employee {0} has no linked User account.").format(self.employee))

		roles = set(frappe.get_roles(user_id))
		if not roles & HR_ROLES:
			frappe.throw(
				_(
					"Employee {0} (user {1}) does not have an HR role. "
					"Assign 'HR Manager' or 'HR User' to that user first."
				).format(self.employee, user_id)
			)

		logger.info(
			"[hr_contact] validate employee=%s user=%s active=%s order=%s",
			self.employee,
			user_id,
			self.is_active,
			self.display_order,
		)
