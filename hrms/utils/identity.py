"""Canonical `User -> Employee` identity resolution.

Every HRMS surface that asks "who is the caller?" has to answer it the same way,
or the fail-closed model has holes. Before this module the answer was a raw
`Employee.user_id == frappe.session.user` query copy-pasted into 13 places, and
7 of those spelled `status = "Active"` while 6 did not — so an inactive employee
was refused a login and still resolved for attendance, leave-block lists,
appraisal feedback, chart methods and report scope.

Worse, nothing ever *established* that link. Microsoft SSO
(`frappe.utils.oauth.login_oauth_user`) loads-or-creates a `User` from the ID
token's email and logs the person in; HRMS then never reconciles that User with
the Employee whose `company_email` is the very same address. An ERP master that
manages staff without portal users — the normal case — therefore mirrors
Employees here with `user_id` empty, and every one of those people authenticates
successfully and is bounced to `/hrms/invalid-employee` forever.

The rules, in order, and nothing else:

1. **Normalize.** `strip().lower()`. `User.autoname` already lowercases, but
   `Employee.user_id` written by the mirror goes through `frappe.db.set_value`,
   which does not, so case drift is reachable on mirrored rows.
2. **Exactly one Active Employee claiming that user.** Two is
   `AMBIGUOUS` — never "pick the first", which would hand one person another's
   record. Zero active but some inactive is `INACTIVE`, which is a *different*
   denial from "you have no record" and the caller deserves to be told which.
3. **Company-email fallback, once, to create the permanent link.** Only when no
   Employee claims the user at all, only on an exact normalized match, only when
   that match is unique, and only when the Employee's `user_id` is still empty.
   It writes `user_id` and audit-logs it; from then on rule 2 answers.

`personal_email` is deliberately NOT matched. `company_email` is the
employer-controlled address an IdP assertion actually corresponds to;
`personal_email` is self-declared, and matching it would let whoever controls a
free mailbox inherit an employee record.

The write goes through `frappe.db.set_value`, which is the residual documented in
`hrms.sync.write_block`: doc events do not fire, so the mirror's read-only block
does not refuse it. That is correct here rather than a loophole — the login
mapping is owned by *this* hub, not by the source instance, which is also why
`hrms.sync.runner` no longer mirrors `user_id` at all. Nothing else about the
Employee is touched.

What this module never does: grant a role, infer authority from a designation or
an email domain, or widen anyone's scope. It answers one question — which
Employee is this session — and authorization is layered on top of the answer
elsewhere.
"""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.query_builder.functions import Lower, Trim

logger = logging.getLogger(__name__)

#: Resolution outcomes. `OK` is the only one that permits entry.
OK = "ok"
NOT_AUTHENTICATED = "not_authenticated"
NO_EMPLOYEE = "no_employee"
INACTIVE_EMPLOYEE = "inactive_employee"
AMBIGUOUS_EMPLOYEE = "ambiguous_employee"

#: Sessions that can never map to an employee. `Administrator` is a framework
#: identity, not a person; it is deliberately NOT special-cased into some
#: employee, because "the admin is everyone" is exactly the kind of implicit
#: authority the authorization model rules out.
_NON_EMPLOYEE_USERS = frozenset({"Guest", ""})

#: Fields `get_current_employee_info` has always returned. Kept as one tuple so
#: the PWA payload cannot drift from what the resolver reads.
EMPLOYEE_INFO_FIELDS = (
	"name",
	"first_name",
	"employee_name",
	"designation",
	"department",
	"company",
	"reports_to",
	"user_id",
)


def normalize_login(value) -> str:
	"""The comparable form of a login identity. Empty string for anything unusable."""
	if not value or not isinstance(value, str):
		return ""
	return value.strip().lower()


def _employees_claiming(user: str) -> list[frappe._dict]:
	"""Every Employee whose `user_id` normalizes to `user`, active ones first.

	Normalized in SQL rather than by fetching the table and filtering in Python:
	`user_id` is indexed, and the alternative reads every employee row on a site
	with thousands of them.
	"""
	employee = frappe.qb.DocType("Employee")
	return (
		frappe.qb.from_(employee)
		.select(employee.name, employee.status, employee.company, employee.user_id)
		.where(Lower(Trim(employee.user_id)) == user)
		.orderby(employee.name)
		.run(as_dict=True)
	)


def _linkable_by_company_email(user: str) -> list[frappe._dict]:
	"""Active Employees whose `company_email` normalizes to `user` and are unlinked.

	`user_id` must still be empty: an Employee already pointing at somebody else's
	User is not a candidate for adoption, whatever its company email says.
	"""
	employee = frappe.qb.DocType("Employee")
	return (
		frappe.qb.from_(employee)
		.select(employee.name, employee.company)
		.where(
			(Lower(Trim(employee.company_email)) == user)
			& (employee.status == "Active")
			& (employee.user_id.isnull() | (employee.user_id == ""))
		)
		.orderby(employee.name)
		.run(as_dict=True)
	)


def _link(employee: str, user: str) -> bool:
	"""Record the permanent `User <-> Employee` mapping, audibly.

	`update_modified=False` on purpose: this is not a change to the employee's HR
	data and must not look like one to the mirror's `modified >` watermark.

	Returns False without writing when the request cannot write at all (read-only
	mode, or a replica). Resolution still succeeds for that request and the link
	is established on the next writable one — the whole operation is idempotent,
	so a skipped write costs nothing but a repeat.
	"""
	if getattr(frappe.flags, "read_only", False):
		logger.info("[identity] read-only request: not persisting the %s -> %s link yet", user, employee)
		return False

	frappe.db.set_value("Employee", employee, "user_id", user, update_modified=False)
	logger.info("[identity] linked employee %s to user %s by company email", employee, user)
	frappe.logger("hrms").info("[identity] linked employee %s to user %s by company email", employee, user)
	frappe.log_error(
		title=f"Employee identity linked: {employee}",
		message=(
			f"User {user} authenticated with no linked Employee. Exactly one Active Employee "
			f"({employee}) carries that address as its company email and had no user_id, so the "
			f"link was established. No role or permission was granted."
		),
	)
	return True


def resolve_employee_identity(user: str | None = None) -> frappe._dict:
	"""Which Employee is this session, and if none, precisely why.

	Returns `{employee, reason, company, linked}`. `employee` is set only when
	`reason == OK`; every other reason denies. Read-only apart from the one
	`user_id` write the company-email fallback makes.
	"""
	user = user if user is not None else frappe.session.user
	normalized = normalize_login(user)

	if not normalized or user in _NON_EMPLOYEE_USERS:
		return frappe._dict(employee=None, reason=NOT_AUTHENTICATED, company=None, linked=False)

	claims = _employees_claiming(normalized)
	active = [row for row in claims if row.status == "Active"]

	if len(active) == 1:
		return frappe._dict(employee=active[0].name, reason=OK, company=active[0].company, linked=False)

	if len(active) > 1:
		# Never resolve this by picking one: the two records may belong to
		# different people, and guessing hands one of them the other's data.
		logger.warning(
			"[identity] %s is claimed by %s active employees (%s) — denied",
			user,
			len(active),
			", ".join(row.name for row in active),
		)
		return frappe._dict(employee=None, reason=AMBIGUOUS_EMPLOYEE, company=None, linked=False)

	if claims:
		logger.info(
			"[identity] %s maps only to non-active employee(s) (%s) — denied",
			user,
			", ".join(f"{row.name}:{row.status}" for row in claims),
		)
		return frappe._dict(employee=None, reason=INACTIVE_EMPLOYEE, company=None, linked=False)

	candidates = _linkable_by_company_email(normalized)
	if len(candidates) == 1:
		linked = _link(candidates[0].name, normalized)
		return frappe._dict(
			employee=candidates[0].name, reason=OK, company=candidates[0].company, linked=linked
		)

	if len(candidates) > 1:
		logger.warning(
			"[identity] %s matches the company email of %s active employees (%s) — denied",
			user,
			len(candidates),
			", ".join(row.name for row in candidates),
		)
		return frappe._dict(employee=None, reason=AMBIGUOUS_EMPLOYEE, company=None, linked=False)

	logger.info("[identity] no employee resolves for %s — denied", user)
	return frappe._dict(employee=None, reason=NO_EMPLOYEE, company=None, linked=False)


def get_employee(user: str | None = None) -> str | None:
	"""The caller's Employee name, or None. The replacement for every hand-rolled
	`get_value("Employee", {"user_id": frappe.session.user, ...})`."""
	return resolve_employee_identity(user).employee


def get_employee_info(user: str | None = None, fields: tuple[str, ...] | None = None) -> dict | None:
	"""The caller's Employee as a dict of `fields`, or None when denied."""
	employee = get_employee(user)
	if not employee:
		return None
	return frappe.db.get_value("Employee", employee, list(fields or EMPLOYEE_INFO_FIELDS), as_dict=True)


def require_employee(user: str | None = None) -> str:
	"""The caller's Employee, or a PermissionError naming the reason.

	The message is safe to show the caller: it says what is wrong with *their*
	account and never names another employee, company or record.
	"""
	identity = resolve_employee_identity(user)
	if identity.employee:
		return identity.employee
	frappe.throw(denial_message(identity.reason), frappe.PermissionError)


#: One message per denial, none of which leak anybody else's identity. The caller's
#: own email is the only account named, and they already know it.
_DENIAL_MESSAGES = {
	NOT_AUTHENTICATED: lambda: _("Please sign in to continue."),
	NO_EMPLOYEE: lambda: _(
		"Your account is not linked to an employee record. Ask your HR team to set your "
		"company email on your employee record, then sign in again."
	),
	INACTIVE_EMPLOYEE: lambda: _(
		"Your employee record is not active, so you cannot use HR right now. Contact your HR manager."
	),
	AMBIGUOUS_EMPLOYEE: lambda: _(
		"Your account matches more than one employee record, so we cannot tell which one is "
		"yours. Your HR team needs to resolve the duplicate before you can sign in."
	),
}


def denial_message(reason: str) -> str:
	builder = _DENIAL_MESSAGES.get(reason)
	return builder() if builder else _("Employee not found")
