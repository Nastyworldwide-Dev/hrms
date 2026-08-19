# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document

from hrms.hr.utils import is_hr_operator

logger = logging.getLogger(__name__)


def _has_hr_access(user: str) -> bool:
	return is_hr_operator(user)


def _get_own_employees(user: str) -> list[str]:
	return frappe.get_all("Employee", filters={"user_id": user}, pluck="name")


class EmployeeOneOnOne(Document):
	def validate(self):
		if self.employee == self.manager:
			frappe.throw(_("Employee and manager cannot be the same person."))
		self.validate_manager_is_session_user()

	def validate_manager_is_session_user(self):
		"""HR can schedule on anyone's behalf; anyone else may only create
		one-on-ones they run themselves (both employee Link fields ignore
		user permissions, so this is the only guard on the manager field)."""
		user = frappe.session.user
		if _has_hr_access(user):
			return
		if self.manager not in _get_own_employees(user):
			frappe.throw(
				_("You can only schedule one-on-ones where you are the manager."),
				frappe.PermissionError,
			)
		logger.info(
			"[one_on_one] user=%s scheduled 1:1 manager=%s employee=%s on %s",
			user,
			self.manager,
			self.employee,
			self.date,
		)


def get_permission_query_conditions(user: str | None = None) -> str:
	"""Scope list reads to one-on-ones the user participates in.

	Doctype perms grant the Employee role blanket read and both Employee
	Link fields ignore user permissions (a manager's own-employee user
	permission would otherwise block selecting their reports), so without
	this every employee could browse everyone's 1:1 notes.
	"""
	user = user or frappe.session.user
	if _has_hr_access(user):
		return ""
	own = _get_own_employees(user)
	logger.debug("[one_on_one] query scope user=%s employees=%d", user, len(own))
	if not own:
		return "1=0"
	values = ", ".join(frappe.db.escape(e) for e in own)
	return (
		f"(`tabEmployee One On One`.`employee` in ({values})"
		f" or `tabEmployee One On One`.`manager` in ({values}))"
	)


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Participants read; only the manager (or HR) writes."""
	user = user or frappe.session.user
	if _has_hr_access(user):
		return True
	if not doc.employee and not doc.manager:
		# new/unsaved doc — let role perms and validate() decide
		return True
	own = _get_own_employees(user)
	if ptype == "read":
		allowed = doc.employee in own or doc.manager in own
	else:
		allowed = doc.manager in own
	logger.debug(
		"[one_on_one] has_permission user=%s ptype=%s doc=%s allowed=%s", user, ptype, doc.name, allowed
	)
	return allowed
