# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import logging

import frappe
from frappe import bold

logger = logging.getLogger(__name__)


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
			"OT Request": "status",
			"Replacement Leave Claim": "status",
		}
		return APPROVAL_STATUS_FIELD[self.doctype]

	def _get_doc_approver(self) -> str | None:
		"""Who should be told. The field when there is one, otherwise resolved.

		This used to index APPROVER_FIELD directly, so a doctype without an
		approver field raised KeyError the moment it tried to notify — which is
		why OT Request notified nobody at all and a draft sat in a list until an
		HR user happened to scroll past it.

		OT follows reporting-manager authority. Shift assignment belongs to the
		remote check-in flow and does not grant OT visibility or decision rights.
		"""
		APPROVER_FIELD = {
			"Leave Application": "leave_approver",
			"Expense Claim": "expense_approver",
			"Shift Request": "approver",
		}
		field = APPROVER_FIELD.get(self.doctype)
		if field:
			return self.get(field)
		if self.doctype in ("OT Request", "Replacement Leave Claim"):
			# Same routing as approval.decide accepts for both: reports_to, then HR.
			return self._get_ot_approver()

		from hrms.overrides.remote_checkin_request_hooks import resolve_approver

		return resolve_approver(self.employee)

	def _get_ot_approver(self) -> str | None:
		"""Prefer the reporting manager, then an eligible HR Manager."""
		from hrms.utils.identity import normalize_login

		logger.debug("[pwa_notifications] resolving OT recipient")
		if self.get("docstatus") != 0:
			return None
		company = frappe.db.get_value("Employee", self.employee, "company")
		manager = frappe.db.get_value("Employee", self.employee, "reports_to")
		if manager:
			user = normalize_login(frappe.db.get_value("Employee", manager, "user_id"))
			if self._ot_approver_can_receive(user, company):
				return user

		hr_users = frappe.get_all(
			"Has Role", filters={"role": "HR Manager", "parenttype": "User"}, pluck="parent"
		)
		if not hr_users:
			return None
		candidates = frappe.get_all(
			"User",
			filters={"name": ("in", hr_users), "enabled": 1},
			pluck="name",
			order_by="creation asc, name asc",
		)
		# Preserve the existing preference for HR attached to this company.
		local_hr = {
			normalize_login(user)
			for user in frappe.get_all(
				"Employee", filters={"company": company, "status": "Active"}, pluck="user_id"
			)
		}
		for user in sorted(candidates, key=lambda candidate: candidate not in local_hr):
			if self._ot_approver_can_receive(user, company):
				return user
		return None

	def _ot_approver_can_receive(self, user: str, company: str | None) -> bool:
		"""A summary must neither widen source visibility nor invent authority."""
		from hrms.api.approval import _is_routed_approver
		from hrms.overrides.company_scope import company_visible
		from hrms.utils.identity import normalize_login

		allowed = bool(
			user
			and user != normalize_login(self._get_employee_user())
			and frappe.db.get_value("User", user, "enabled")
			and company_visible(company, user)
			and frappe.has_permission(self.doctype, "read", doc=self, user=user)
			and _is_routed_approver(self, user)
		)
		logger.debug("[pwa_notifications] OT recipient eligibility=%s", allowed)
		return allowed

	def _get_employee_user(self) -> str:
		return frappe.db.get_value("Employee", self.employee, "user_id", cache=True)

	def _get_user_name(self, user) -> str:
		return frappe.db.get_value("User", user, "full_name", cache=True)
