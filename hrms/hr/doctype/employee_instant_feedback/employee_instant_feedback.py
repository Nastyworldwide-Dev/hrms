# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document

from hrms.hr.doctype.employee_one_on_one.employee_one_on_one import (
	_get_own_employees,
	_has_hr_access,
)

logger = logging.getLogger(__name__)

MIN_MESSAGE_LENGTH = 20


class EmployeeInstantFeedback(Document):
	def validate(self):
		self.set_giver()
		if self.employee == self.giver:
			frappe.throw(_("You cannot give feedback to yourself."))
		if len((self.message or "").strip()) < MIN_MESSAGE_LENGTH:
			frappe.throw(_("Feedback message must be at least {0} characters.").format(MIN_MESSAGE_LENGTH))
		logger.info(
			"[instant_feedback] user=%s giver=%s -> employee=%s type=%s",
			frappe.session.user,
			self.giver,
			self.employee,
			self.feedback_type,
		)

	def set_giver(self):
		"""The giver is always the session user's employee — the field is
		read-only in the form and overwritten here so feedback cannot be
		forged in someone else's name. HR may file on a giver's behalf."""
		user = frappe.session.user
		if _has_hr_access(user) and self.giver:
			return
		own = _get_own_employees(user)
		if not own:
			frappe.throw(_("No Employee record is linked to your user."), frappe.PermissionError)
		self.giver = own[0]


def get_permission_query_conditions(user: str | None = None) -> str:
	"""Scope list reads to feedback the user gave or received.

	The employee Link field ignores user permissions (a giver's
	own-employee user permission would otherwise block selecting a
	colleague), so row scope must be enforced here.
	"""
	user = user or frappe.session.user
	if _has_hr_access(user):
		return ""
	own = _get_own_employees(user)
	logger.debug("[instant_feedback] query scope user=%s employees=%d", user, len(own))
	if not own:
		return "1=0"
	values = ", ".join(frappe.db.escape(e) for e in own)
	return (
		f"(`tabEmployee Instant Feedback`.`employee` in ({values})"
		f" or `tabEmployee Instant Feedback`.`giver` in ({values}))"
	)


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Giver and recipient read; only the giver (or HR) writes."""
	user = user or frappe.session.user
	if _has_hr_access(user):
		return True
	if not doc.employee and not doc.giver:
		# new/unsaved doc — validate() pins the giver to the session user
		return True
	own = _get_own_employees(user)
	if ptype == "read":
		allowed = doc.employee in own or doc.giver in own
	else:
		allowed = doc.giver in own
	logger.debug(
		"[instant_feedback] has_permission user=%s ptype=%s doc=%s allowed=%s",
		user,
		ptype,
		doc.name,
		allowed,
	)
	return allowed
