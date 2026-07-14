# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from hrms.hr.doctype.employee_one_on_one.employee_one_on_one import (
	_get_own_employees,
	_has_hr_access,
)

logger = logging.getLogger(__name__)


class ShiftSwapRequest(Document):
	"""One-way shift cover: on approval the requester's Shift Assignment is
	cancelled and an identical one is created for the covering employee.
	HR approval implies the covering employee's consent."""

	def validate(self):
		if self.requesting_employee == self.target_employee:
			frappe.throw(_("Requesting and covering employee cannot be the same person."))
		self.validate_requester_is_session_user()
		self.validate_frozen_after_finalization()
		self.validate_shift_assignment()
		self.validate_target_availability()
		self.validate_status_transition()

	def validate_requester_is_session_user(self):
		user = frappe.session.user
		if _has_hr_access(user) or not self.is_new():
			return
		if self.requesting_employee not in _get_own_employees(user):
			frappe.throw(_("You can only request swaps for your own shifts."), frappe.PermissionError)

	def validate_frozen_after_finalization(self):
		old = self.get_doc_before_save()
		if old and old.status != "Pending":
			frappe.throw(_("An {0} swap request cannot be modified.").format(_(old.status)))

	def validate_shift_assignment(self):
		assignment = frappe.db.get_value(
			"Shift Assignment",
			self.shift_assignment,
			["employee", "docstatus", "status", "start_date", "shift_type"],
			as_dict=True,
		)
		if not assignment or assignment.employee != self.requesting_employee:
			frappe.throw(
				_("Shift Assignment {0} does not belong to the requesting employee.").format(
					self.shift_assignment
				)
			)
		if assignment.docstatus != 1 or assignment.status != "Active":
			frappe.throw(_("Only active, submitted shift assignments can be swapped."))
		if getdate(assignment.start_date) < getdate(today()):
			frappe.throw(_("Past shifts cannot be swapped."))

	def validate_target_availability(self):
		"""The covering employee must not already hold an active assignment for
		the same shift on that date."""
		clash = frappe.db.exists(
			"Shift Assignment",
			{
				"employee": self.target_employee,
				"shift_type": self.shift_type,
				"start_date": self.shift_date,
				"status": "Active",
				"docstatus": 1,
			},
		)
		if clash:
			frappe.throw(
				_("{0} already has an active {1} assignment on {2} ({3}).").format(
					self.target_employee_name or self.target_employee,
					self.shift_type,
					frappe.format(self.shift_date, "Date"),
					clash,
				)
			)

	def validate_status_transition(self):
		if self.is_new():
			# every request starts pending, whoever files it
			self.status = "Pending"
			return
		old = self.get_doc_before_save()
		if old and old.status != self.status and not _has_hr_access(frappe.session.user):
			frappe.throw(_("Only HR can approve or reject swap requests."), frappe.PermissionError)

	def on_update(self):
		old = self.get_doc_before_save()
		if old and old.status == "Pending" and self.status == "Approved" and not self.new_shift_assignment:
			self.apply_swap()

	def apply_swap(self):
		assignment = frappe.get_doc("Shift Assignment", self.shift_assignment)

		replacement = frappe.copy_doc(assignment)
		replacement.employee = self.target_employee
		replacement.employee_name = None
		replacement.department = None
		replacement.shift_request = None
		replacement.insert()
		replacement.submit()

		assignment.cancel()

		self.db_set("new_shift_assignment", replacement.name)
		logger.info(
			"[shift_swap] %s approved: %s cancelled, %s created for %s",
			self.name,
			assignment.name,
			replacement.name,
			self.target_employee,
		)


def get_permission_query_conditions(user: str | None = None) -> str:
	"""Scope list reads to swap requests the user participates in. Both
	Employee Link fields ignore user permissions (a requester's own-employee
	user permission would otherwise block selecting a colleague), so row
	scope must be enforced here."""
	user = user or frappe.session.user
	if _has_hr_access(user):
		return ""
	own = _get_own_employees(user)
	logger.debug("[shift_swap] query scope user=%s employees=%d", user, len(own))
	if not own:
		return "1=0"
	values = ", ".join(frappe.db.escape(e) for e in own)
	return (
		f"(`tabShift Swap Request`.`requesting_employee` in ({values})"
		f" or `tabShift Swap Request`.`target_employee` in ({values}))"
	)


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Participants read; the requester writes (validate freezes finalized
	docs and blocks non-HR status changes); HR unrestricted."""
	user = user or frappe.session.user
	if _has_hr_access(user):
		return True
	if not doc.requesting_employee and not doc.target_employee:
		# new/unsaved doc — validate() pins the requester to the session user
		return True
	own = _get_own_employees(user)
	if ptype == "read":
		allowed = doc.requesting_employee in own or doc.target_employee in own
	else:
		allowed = doc.requesting_employee in own
	logger.debug(
		"[shift_swap] has_permission user=%s ptype=%s doc=%s allowed=%s",
		user,
		ptype,
		doc.name,
		allowed,
	)
	return allowed
