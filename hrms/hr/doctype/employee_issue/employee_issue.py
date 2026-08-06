# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _, bold
from frappe.model.document import Document

from hrms.hr.utils import validate_active_employee, validate_filing_for_self

logger = logging.getLogger(__name__)

STATUSES = ("Open", "In Progress", "Completed")


class EmployeeIssue(Document):
	def validate(self):
		validate_active_employee(self.employee)
		validate_filing_for_self(self)
		self.validate_status()

	def validate_status(self):
		"""New tickets always start Open; the status field is HR's alone afterwards
		(employees have no write perm, this just keeps direct API calls honest)."""
		logger.debug("[employee_issue] validate_status %s -> %s", self.name, self.status)
		if self.status not in STATUSES:
			frappe.throw(_("Invalid status: {0}").format(self.status))
		if self.is_new() and self.status != "Open":
			logger.info(
				"[employee_issue] forcing initial status Open (was %s) for %s",
				self.status,
				self.employee,
			)
			self.status = "Open"

	def after_insert(self):
		self.align_owner_with_employee()
		self.notify_hr_users()

	def align_owner_with_employee(self):
		"""When HR files on behalf, hand ownership to the subject employee —
		the Employee role reads via if_owner, which keys on owner, while the
		row-scope hooks key on employee.user_id; without this an HR-filed
		ticket is invisible to the very employee it is about."""
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
		if employee_user and employee_user != self.owner:
			logger.info(
				"[employee_issue] %s: reassigning owner %s -> %s",
				self.name,
				self.owner,
				employee_user,
			)
			self.db_set("owner", employee_user, update_modified=False)

	def on_update(self):
		before = self.get_doc_before_save()
		if before and before.status != self.status:
			self.notify_employee_status_change()

	def notify_hr_users(self):
		"""New ticket → bell + push for every enabled HR User / HR Manager."""
		hr_users = self.get_hr_users()
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
		notified = 0
		for user in hr_users:
			if user == employee_user:
				continue  # HR person reporting their own issue
			notification = frappe.new_doc("PWA Notification")
			notification.from_user = employee_user or frappe.session.user
			notification.to_user = user
			notification.message = _("{0} reported a new {1} issue: {2}").format(
				bold(frappe.utils.escape_html(self.employee_name or self.employee)),
				bold(self.issue_type),
				self.name,
			)
			notification.reference_document_type = self.doctype
			notification.reference_document_name = self.name
			notification.insert(ignore_permissions=True)
			notified += 1
		logger.info("[employee_issue] %s: notified %d HR users", self.name, notified)

	def notify_employee_status_change(self):
		"""HR moved the status → tell the reporter."""
		to_user = frappe.db.get_value("Employee", self.employee, "user_id")
		logger.info("[employee_issue] %s status -> %s, notifying %s", self.name, self.status, to_user)
		if not to_user or to_user == frappe.session.user:
			return
		notification = frappe.new_doc("PWA Notification")
		notification.from_user = frappe.session.user
		notification.to_user = to_user
		notification.message = _("Your issue {0} is now {1}").format(bold(self.name), bold(self.status))
		notification.reference_document_type = self.doctype
		notification.reference_document_name = self.name
		notification.insert(ignore_permissions=True)

	@staticmethod
	def get_hr_users() -> list[str]:
		"""Enabled, real users holding HR User or HR Manager."""
		role_holders = frappe.get_all(
			"Has Role",
			filters={"role": ("in", ["HR User", "HR Manager"]), "parenttype": "User"},
			pluck="parent",
			distinct=True,
		)
		if not role_holders:
			return []
		recipients = [u for u in role_holders if u not in ("Administrator", "Guest")]
		if not recipients:
			return []
		return frappe.get_all(
			"User",
			filters={"name": ("in", recipients), "enabled": 1},
			pluck="name",
		)
