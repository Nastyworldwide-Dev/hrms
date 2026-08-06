"""Row scope for Employee Issue: tickets are private between the reporting
employee and HR. No approver routing and no reports_to visibility — a manager
is not a party to their report's HR ticket. HR roles and Administrator are
unrestricted; everyone else sees only rows for their own Employee (plus docs
explicitly shared with them). Registered in hooks.py as
permission_query_conditions + has_permission (same model as ot_row_scope.py).
"""

import logging

import frappe
from frappe.share import get_shared

from hrms.hr.utils import HR_ROLES

logger = logging.getLogger(__name__)


def _unrestricted(user: str) -> bool:
	return user == "Administrator" or bool(HR_ROLES & set(frappe.get_roles(user)))


def get_permission_query_conditions(user: str | None = None) -> str:
	"""List scope: own rows and shared docs; HR unrestricted; fail closed."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""

	own = frappe.get_all("Employee", filters={"user_id": user}, pluck="name")
	conditions = []
	if own:
		values = ", ".join(frappe.db.escape(e) for e in own)
		conditions.append(f"`tabEmployee Issue`.`employee` in ({values})")

	shared = get_shared("Employee Issue", user)
	if shared:
		names = ", ".join(frappe.db.escape(n) for n in shared)
		conditions.append(f"`tabEmployee Issue`.`name` in ({names})")

	logger.debug(
		"[employee_issue_row_scope] query scope user=%s own=%d shared=%d",
		user,
		len(own),
		len(shared),
	)
	if not conditions:
		# fail closed: a user with no employee mapping sees nothing
		return "1=0"
	return "(" + " or ".join(conditions) + ")"


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Per-row check: HR unrestricted, otherwise only the reporting employee."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return True
	owner_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	allowed = owner_user == user
	logger.debug(
		"[employee_issue_row_scope] has_permission user=%s ptype=%s name=%s allowed=%s",
		user,
		ptype,
		getattr(doc, "name", None),
		allowed,
	)
	return allowed
