# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe import bold


class PWANotificationsMixin:
	"""Mixin class for managing PWA updates"""

	def notify_approval_status(self):
		"""Send Leave Application, Expense Claim & Shift Request Approval status notification - to employees"""
		status_field = self._get_doc_status_field()
		status = self.get(status_field)

		if self.has_value_changed(status_field) and status in ["Approved", "Rejected"]:
			from_user = frappe.session.user
			from_user_name = self._get_user_name(from_user)
			to_user = self._get_employee_user()

			if from_user == to_user:
				return

			notification = frappe.new_doc("PWA Notification")
			notification.from_user = from_user
			notification.to_user = to_user

			notification.message = f"{bold('Your')} {bold(self.doctype)} {self.name} has been {bold(status)} by {bold(from_user_name)}"

			notification.reference_document_type = self.doctype
			notification.reference_document_name = self.name
			notification.insert(ignore_permissions=True)

	def notify_approver(self):
		"""Send new Leave Application, Expense Claim & Shift Request request notification - to approvers"""
		from_user = self._get_employee_user()
		to_user = self._get_doc_approver()

		if not to_user or from_user == to_user:
			return

		notification = frappe.new_doc("PWA Notification")
		notification.message = (
			f"{bold(self.employee_name)} raised a new {bold(self.doctype)} for approval: {self.name}"
		)
		notification.from_user = from_user
		notification.to_user = to_user

		notification.reference_document_type = self.doctype
		notification.reference_document_name = self.name
		notification.insert(ignore_permissions=True)

	def _get_doc_status_field(self) -> str:
		APPROVAL_STATUS_FIELD = {
			"Leave Application": "status",
			"Expense Claim": "approval_status",
			"Shift Request": "status",
		}
		return APPROVAL_STATUS_FIELD[self.doctype]

	def _get_doc_approver(self) -> str | None:
		"""Who should be told. The field when there is one, otherwise resolved.

		This used to index APPROVER_FIELD directly, so a doctype without an
		approver field raised KeyError the moment it tried to notify — which is
		why OT Request notified nobody at all and a draft sat in a list until an
		HR user happened to scroll past it.

		The fallback is not invented. OT visibility already runs on `reports_to`
		(`overrides/ot_row_scope`: own + direct reports + HR), so the approver is
		resolved by the same chain remote check-in uses rather than a second one
		that could disagree about who approves for the same person.
		"""
		APPROVER_FIELD = {
			"Leave Application": "leave_approver",
			"Expense Claim": "expense_approver",
			"Shift Request": "approver",
		}
		field = APPROVER_FIELD.get(self.doctype)
		if field:
			return self.get(field)

		from hrms.overrides.remote_checkin_request_hooks import resolve_approver

		return resolve_approver(self.employee)

	def _get_employee_user(self) -> str:
		return frappe.db.get_value("Employee", self.employee, "user_id", cache=True)

	def _get_user_name(self, user) -> str:
		return frappe.db.get_value("User", user, "full_name", cache=True)
