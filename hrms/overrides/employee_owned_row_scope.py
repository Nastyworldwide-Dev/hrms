"""Row scope for employee-owned HR records.

These doctypes grant the Employee / Employee Self Service roles level-0 rights
so staff can work with their OWN records from the PWA and the Desk. Nothing in
the doctype definition narrows *which* rows, so before this module the grant
meant "every employee's rows": salary structure assignments, incentives,
bonuses, withholdings, promotions, transfers, payroll corrections, overtime
slips, PIPs, performance feedback, attendance, shift assignments and remote
check-in requests were listable, openable, printable and CSV-exportable by any
member of staff through `/api/resource/<DocType>`, `frappe.client.get_list`,
the Desk list view or the report view.

The only thing that used to narrow them was an `allow=Employee` User
Permission, and that binding is not dependable here — it disappears when
`create_user_permission` is unticked (ERPNext deletes the rows), and ticking
`restrict_user_permission_to_hrms` replaces the broad row with per-doctype rows
whose `applicable_for` covers only the HRMS scope list, leaving everything
outside that list open. `hrms/hr/utils.py` records the same lesson:
"that binding has broken before on this fork".

So the fence lives in code, and it is wired on BOTH hooks. A
`permission_query_conditions` entry filters list views and `get_list`; it does
nothing for `frappe.client.get`, a form load, a print/PDF render or an
attachment fetch. Those go through `has_permission`. A doctype wired to one and
not the other is half-fenced — `tests/test_employee_role_fence_integrity.py`
fails the build if that ever happens.

Effective scope, in precedence order:

* **Administrator** — exceptional framework authority, unrestricted, logged.
* **HR roles** (HR User / HR Manager, not System Manager) — broad access, but
  still inside their company / source-instance fence. HR is deliberately NOT
  implemented as "return everything": it composes with
  `hrms.overrides.company_scope`, so an HR (Company) or HR (Instance) user never
  reads another company's records through this path.
* **The employee themselves** — rows whose owner field points at one of their
  own Employee records.
* **Explicitly shared rows** — DocShare. This is how approver access already
  works for Remote Checkin Request (`remote_checkin_request_hooks.py` shares the
  row with the named approver so the PWA's `get_list` returns it).
* **Everyone else** — nothing. A user with no resolvable Employee and no shares
  gets `1=0`, never an open query: missing or stale authorization fails closed.

Manager/subordinate visibility is deliberately NOT granted here. Whether a
manager may read a report's salary structure assignment or PIP is an HR policy
question, and this module's job is to stop the cross-employee leak without
answering it. Approver-routed request doctypes keep their own, wider scope in
`hrms.overrides.approval_row_scope` / `ot_row_scope`.
"""

from __future__ import annotations

import logging

import frappe
from frappe.share import get_shared

from hrms.hr.utils import get_direct_report_employees, sees_all_employee_data
from hrms.overrides.company_scope import allowed_companies, company_visible
from hrms.utils.identity import own_employees

logger = logging.getLogger(__name__)

#: doctype -> the fields naming whose record it is. A row is "own" when ANY of
#: them resolves to one of the reader's Employee records; several doctypes have
#: two legitimate parties (the subject and the reviewer/appraiser).
OWNED_DOCTYPES: dict[str, tuple[str, ...]] = {
	# --- attendance & shift ---
	"Attendance": ("employee",),
	"Attendance Request": ("employee",),
	"Compensatory Leave Request": ("employee",),
	"Employee Checkin": ("employee",),
	"Remote Checkin Request": ("employee",),
	"Shift Assignment": ("employee",),
	"Shift Schedule Assignment": ("employee",),
	# --- money: pay, benefits, claims, corrections ---
	"Employee Advance": ("employee",),
	"Employee Benefit Application": ("employee",),
	"Employee Benefit Claim": ("employee",),
	"Employee Benefit Ledger": ("employee",),
	"Employee Incentive": ("employee",),
	"Employee Other Income": ("employee",),
	"Employee Tax Exemption Declaration": ("employee",),
	"Employee Tax Exemption Proof Submission": ("employee",),
	"Leave Encashment": ("employee",),
	"Overtime Slip": ("employee",),
	"Payroll Correction": ("employee",),
	"Retention Bonus": ("employee",),
	"Salary Structure Assignment": ("employee",),
	"Salary Withholding": ("employee",),
	# --- lifecycle & performance ---
	# Employee Transfer names the same person twice (the transfer mints a new id).
	"Employee Transfer": ("employee", "new_employee_id"),
	"Employee Promotion": ("employee",),
	# the reviewer must reach the feedback they are asked to write
	"Employee Performance Feedback": ("employee", "reviewer"),
	# the appraiser runs the plan with the employee
	"Performance Improvement Plan": ("employee", "appraiser"),
	"Goal": ("employee",),
	"Training Feedback": ("employee",),
	# The referrer owns the referral; the referred candidate is not an Employee.
	"Employee Referral": ("referrer",),
	# Grievances are scoped to the person who RAISED them (plus HR and anyone the
	# row is shared with). `employee_responsible` is deliberately excluded: giving
	# the subject of a grievance automatic read access is an HR policy call, and
	# the fail-closed reading is the safe one until HR confirms it.
	"Employee Grievance": ("raised_by",),
}

#: Doctypes with no `company` column of their own. HR's company fence still has
#: to apply, so it rides on the owning Employee instead — the same shape
#: `hrms/api/remote_checkin.py` already uses for its approver inbox.
_COMPANY_VIA_EMPLOYEE = {
	"Compensatory Leave Request",
	"Employee Checkin",
	"Employee Grievance",
	"Employee Referral",
	"Remote Checkin Request",
	"Training Feedback",
}

#: Doctypes an employee FILES and a manager REVIEWS. `hrms.api.get_filters`
#: builds a `for_approval` view over Attendance Request (docstatus 0, employee
#: != me) with no approver field, so the reviewer is the reporting manager —
#: the same shape hrms.overrides.ot_row_scope already grants for OT Request and
#: Replacement Leave Claim. Direct reports are added to the scope for these, and
#: for READ only: a manager reviews, HR decides.
#:
#: Everything else stays own + share + HR. A manager has no automatic claim on a
#: report's pay, benefits, promotion or PIP; that is an HR policy question, and
#: the fail-closed reading is the safe one.
TEAM_REVIEWED_DOCTYPES = {"Attendance Request"}

#: DocShare rows carry read/write/share/submit flags; anything destructive is
#: checked against `write`, matching hrms.overrides.approval_row_scope.
_SHARE_RIGHTS = {"read", "write", "share", "submit"}


def _is_administrator(user: str) -> bool:
	return user == "Administrator"


def _is_hr(user: str) -> bool:
	# HR User / HR Manager only (System Manager must not see pay/PIPs). The
	# delegate also answers True for Administrator, which the old body did not
	# — reachably identical, as both call sites check _is_administrator first.
	return sees_all_employee_data(user)


def _own_employees(user: str) -> list[str]:
	"""The reader's own Active Employee, via the canonical identity primitive.

	`own_employees` is already the user's own identity lookup, not a data read:
	it never touches Employee's permission query conditions (no re-entrancy from
	inside a query-condition hook) and never writes. It also fixes what the old
	`ignore_permissions` read did not — it normalizes the login (a case-drifted
	mirror `user_id` no longer empties the fence), it is Active-only (an
	offboarded employee no longer keeps row-level read the login denies), and it
	fails closed on ambiguity (two Active rows no longer expose both people).
	"""
	return own_employees(user)


def _company_condition(doctype: str, user: str) -> str:
	"""SQL fencing `doctype` to the user's permitted companies, or "" if unfenced."""
	companies = allowed_companies(user)
	if not companies:
		return ""
	values = ", ".join(frappe.db.escape(c) for c in companies)
	if doctype in _COMPANY_VIA_EMPLOYEE:
		owner_field = OWNED_DOCTYPES[doctype][0]
		return (
			f"`tab{doctype}`.`{owner_field}` in "
			f"(select `name` from `tabEmployee` where `company` in ({values}))"
		)
	return f"`tab{doctype}`.`company` in ({values})"


def _row_company(doc, doctype: str):
	"""The company a row belongs to, resolved through the employee when needed."""
	if doctype not in _COMPANY_VIA_EMPLOYEE:
		return doc.get("company")
	employee = doc.get(OWNED_DOCTYPES[doctype][0])
	if not employee:
		return None
	return frappe.db.get_value("Employee", employee, "company")


def get_permission_query_conditions(doctype: str, user: str | None = None) -> str:
	"""List scope: own records plus explicitly shared ones; HR sees their companies."""
	user = user or frappe.session.user
	owner_fields = OWNED_DOCTYPES[doctype]

	if _is_administrator(user):
		return ""

	if _is_hr(user):
		# broad, but never outside the company / source-instance fence
		return _company_condition(doctype, user)

	conditions = []
	visible = _own_employees(user)
	if doctype in TEAM_REVIEWED_DOCTYPES:
		visible = visible + get_direct_report_employees(user)
	if visible:
		values = ", ".join(frappe.db.escape(e) for e in visible)
		conditions.extend(f"`tab{doctype}`.`{field}` in ({values})" for field in owner_fields)

	shared = get_shared(doctype, user)
	if shared:
		names = ", ".join(frappe.db.escape(n) for n in shared)
		conditions.append(f"`tab{doctype}`.`name` in ({names})")

	if not conditions:
		# no employee record and nothing shared — fail closed rather than open
		logger.info("[employee_owned_row_scope] %s has no scope on %s", user, doctype)
		return "1=0"

	return "(" + " or ".join(conditions) + ")"


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Document scope: the same rule as the list, for REST/form/print/attachments."""
	user = user or frappe.session.user
	doctype = doc.get("doctype") if isinstance(doc, dict) else doc.doctype
	owner_fields = OWNED_DOCTYPES[doctype]

	if _is_administrator(user):
		return True

	if _is_hr(user):
		allowed = company_visible(_row_company(doc, doctype), user)
		if not allowed:
			logger.info(
				"[employee_owned_row_scope] HR user %s denied %s on %s %s — outside company fence",
				user,
				ptype,
				doctype,
				doc.get("name"),
			)
		return allowed

	own = set(_own_employees(user))
	if own and any(doc.get(field) in own for field in owner_fields):
		return True

	if ptype == "read" and doctype in TEAM_REVIEWED_DOCTYPES:
		# the reporting manager reviews, and only reads
		reports = set(get_direct_report_employees(user))
		if reports and any(doc.get(field) in reports for field in owner_fields):
			return True

	rights = [ptype] if ptype in _SHARE_RIGHTS else ["write"]
	name = doc.get("name")
	if name and name in get_shared(doctype, user, rights=rights):
		return True

	logger.warning(
		"[employee_owned_row_scope] %s denied %s on %s %s",
		user,
		ptype,
		doctype,
		name,
	)
	return False


# hooks.py needs a dotted path per doctype, and the query hook is called with
# (doctype, user) only for some framework paths and (user) for others, so each
# doctype gets a named wrapper. Generated rather than hand-written: 29 identical
# four-line functions would be 29 chances to typo a doctype name, and the guard
# test proves the generated set matches the hooks wiring exactly.
def _make_query_wrapper(doctype: str):
	def wrapper(user: str | None = None) -> str:
		return get_permission_query_conditions(doctype, user)

	wrapper.__name__ = "query_" + doctype.lower().replace(" ", "_")
	wrapper.__doc__ = f"Row scope for {doctype} list reads."
	return wrapper


for _doctype in OWNED_DOCTYPES:
	globals()["query_" + _doctype.lower().replace(" ", "_")] = _make_query_wrapper(_doctype)
del _doctype
