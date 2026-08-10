"""Row scope for Employee Issue: tickets are private between the reporting
employee and HR. No approver routing and no reports_to visibility — a manager
is not a party to their report's HR ticket. HR roles and Administrator are
unrestricted; everyone else sees only rows for their own Employee (plus docs
explicitly shared with them). On the multi-company hub every scope is
additionally fenced by company for users carrying an allow=Company User
Permission ("HR (Company)") — see hrms/overrides/company_scope.py. Registered
in hooks.py as
permission_query_conditions + has_permission (same model as ot_row_scope.py).
"""

import logging

import frappe
from frappe.share import get_shared

from hrms.hr.utils import HR_ROLES
from hrms.overrides.company_scope import allowed_companies, company_condition, company_visible

logger = logging.getLogger(__name__)


def _unrestricted(user: str) -> bool:
	return user == "Administrator" or bool(HR_ROLES & set(frappe.get_roles(user)))


def _own_employees(user: str) -> list[str]:
	"""The user's Employee records, fenced to the companies they may reach.

	A user can hold an Employee record in more than one company on the group
	hub; a company-fenced session must only surface the ones inside the fence.
	Unfenced users (no allow=Company User Permission) get every record, exactly
	as before."""
	filters = {"user_id": user}
	companies = allowed_companies(user)
	if companies:
		filters["company"] = ("in", companies)
	own = frappe.get_all("Employee", filters=filters, pluck="name")
	logger.debug("[employee_issue_row_scope] own employees for %s: %s (companies=%s)", user, own, companies)
	return own


def get_permission_query_conditions(user: str | None = None) -> str:
	"""List scope: own rows and shared docs; HR unrestricted apart from their
	company fence; fail closed."""
	user = user or frappe.session.user
	logger.debug("[employee_issue_row_scope] building query scope for %s", user)
	if _unrestricted(user):
		# company HR is fenced to their own company; group HR gets "" as before
		return company_condition("Employee Issue", user)

	own = _own_employees(user)
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


# employees only ever look at their tickets — every mutating ptype is HR's
READ_PTYPES = frozenset({"read", "select", "print", "email"})


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Per-row check: HR unrestricted; the reporting employee may read but
	never mutate — enforced here as defense-in-depth so the invariant survives
	even if someone later loosens the DocPerm matrix (SEC-01)."""
	user = user or frappe.session.user
	# the company fence outranks every role: it applies before the HR shortcut
	# and is a no-op for users with no allow=Company User Permission
	if not company_visible(getattr(doc, "company", None), user):
		logger.info(
			"[employee_issue_row_scope] denying %s on %s for %s — outside their company fence",
			ptype,
			getattr(doc, "name", None),
			user,
		)
		return False
	if _unrestricted(user):
		return True
	if ptype not in READ_PTYPES:
		logger.debug(
			"[employee_issue_row_scope] denying ptype=%s for %s on %s",
			ptype,
			user,
			getattr(doc, "name", None),
		)
		return False
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
