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

from hrms.hr.utils import is_hr_operator
from hrms.overrides.company_scope import allowed_companies, company_condition
from hrms.utils.identity import own_employees

logger = logging.getLogger(__name__)


def _unrestricted(user: str) -> bool:
	return is_hr_operator(user)


def _own_employees(user: str) -> list[str]:
	"""The user's own Active Employee, fenced to the companies they may reach.

	Resolved through the canonical identity primitive — normalized, Active-only,
	and refusing ambiguity — the same single employee the app resolves (a login
	maps to at most one Active Employee; two is denied at login, so the old
	multi-company-per-user branch here was already unreachable via the PWA). A
	company-fenced session still only surfaces a record inside its fence;
	unfenced users (no allow=Company User Permission) keep it."""
	own = own_employees(user)
	companies = allowed_companies(user)
	if own and companies:
		own = [e for e in own if frappe.db.get_value("Employee", e, "company") in companies]
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


# employees only ever look at their tickets — every mutating ptype is HR's,
# except the one act that opens a ticket in the first place: `create` of a
# row naming the caller's own Employee. See has_permission.
READ_PTYPES = frozenset({"read", "select", "print", "email"})


def _row_companies(doc) -> set[str]:
	"""The companies a ticket belongs to — every one must be inside HR's fence.

	A saved row answers with its stored `company`. An UNSAVED row cannot:
	`Document.insert` runs `check_permission("create")` before
	`_validate_links()`, which is where `fetch_from: employee.company` is
	written, and the PWA never sends `company`. At check time the field holds
	whatever Frappe's user default supplied — None for an "HR (Instance)" user
	(several Company User Permissions, so no single default), which refused HR
	their OWN ticket with "You need the 'create' permission"; or the fenced
	company for an "HR (Company)" user whatever employee the row names. So an
	unsaved row is fenced on its employee's company — the value the save will
	write — as well as any company it already carries. Same shape as
	hrms.overrides.employee_owned_row_scope._row_companies; nothing here can
	widen the fence.
	"""
	companies: set[str] = set()
	stored = doc.get("company")
	if stored:
		companies.add(stored)
	unsaved = bool(doc.get("__islocal")) or not doc.get("name")
	if not stored or unsaved:
		employee = doc.get("employee")
		via_employee = frappe.db.get_value("Employee", employee, "company") if employee else None
		if via_employee:
			companies.add(via_employee)
	return companies


def _inside_company_fence(doc, user: str) -> bool:
	"""No allow=Company User Permission: unrestricted. Fenced: every company
	the row belongs to must be permitted; a row with no resolvable company
	fails closed for a fenced user."""
	fence = allowed_companies(user)
	if not fence:
		return True
	companies = _row_companies(doc)
	inside = bool(companies) and all(company in fence for company in companies)
	logger.debug("[employee_issue_row_scope] fence %s row companies %s inside=%s", fence, companies, inside)
	return inside


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Per-row check: HR unrestricted inside their company fence; the reporting
	employee may READ their own tickets and CREATE one in their own name, and
	never mutate — enforced here as defense-in-depth so the invariant survives
	even if someone later loosens the DocPerm matrix (SEC-01).

	`create` is answered for everyone below HR the same way, whatever extra
	roles they hold: a Leave Approver, an Expense Approver or a System Manager
	is still an employee, and filing a ticket about their own leave or pay is
	the basic act the owner's rule protects ("everyone must be able to do
	these basic things"). Before this the hook refused every non-HR `create`
	— the DocPerm row (Employee, if_owner, create=1) said yes and this hook
	said no, so the framework rendered "You need the 'create' permission on
	Employee Issue". A ticket in a COLLEAGUE'S name stays refused here, and
	`validate_filing_for_self` refuses it again on save.
	"""
	user = user or frappe.session.user
	# the company fence outranks every role: it applies before the HR shortcut
	# and is a no-op for users with no allow=Company User Permission
	if not _inside_company_fence(doc, user):
		logger.info(
			"[employee_issue_row_scope] denying %s on %s for %s — outside their company fence",
			ptype,
			getattr(doc, "name", None),
			user,
		)
		return False
	if _unrestricted(user):
		return True
	if ptype == "create":
		own = _own_employees(user)
		allowed = bool(own) and doc.get("employee") in own
		logger.info(
			"[employee_issue_row_scope] create by %s for employee %s: %s",
			user,
			doc.get("employee"),
			"own ticket, allowed" if allowed else "not their own employee, refused",
		)
		return allowed
	if ptype not in READ_PTYPES:
		logger.debug(
			"[employee_issue_row_scope] denying ptype=%s for %s on %s",
			ptype,
			user,
			getattr(doc, "name", None),
		)
		return False
	# ASKED THE SAME WAY THE LIST ASKS IT, which is the whole point.
	#
	# This used to read the Employee's user_id and compare it raw, while the LIST
	# query twelve lines up resolved identity through _own_employees. Two answers
	# to "who is this person" in one file, and the raw one FAILS OPEN in both
	# directions the canonical one exists to close: an offboarded employee whose
	# login is still enabled keeps reading their old tickets after the list has
	# stopped showing them, and where two Active Employees claim one login — which
	# the canonical resolver refuses outright, because guessing one hands over the
	# other's data — this compare says yes to BOTH people's rows.
	#
	# The list returns `1=0` for those callers. The document API did not, so a
	# ticket could be opened by name. Confidential HR cases: somebody else's
	# grievance, somebody else's disciplinary record.
	allowed = doc.get("employee") in _own_employees(user)
	logger.debug(
		"[employee_issue_row_scope] has_permission user=%s ptype=%s name=%s allowed=%s",
		user,
		ptype,
		getattr(doc, "name", None),
		allowed,
	)
	return allowed
