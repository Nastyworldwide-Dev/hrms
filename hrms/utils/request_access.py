"""Can every employee file their own requests? — the system checks, nobody asks.

Owner's rule (15 Sep 2026): we never ask an employee, or anyone, to run a
diagnostic; the system finds it itself. This module walks every enabled User
that resolves to an Active Employee, asks Frappe — as that user, on the
document Nadi's form would send — whether they may CREATE each self-service
request doctype, and keeps only the refusals with the gate that said no
(`hrms.api.diagnose`). Three consumers:

* the "Request Access Health" Script Report (HR Manager / System Manager,
  company-fenced like the other reports) lists the refusals;
* the daily attendance health log carries one line: "N users cannot file
  their own requests" with the top reasons;
* `heal_known_shapes` re-runs the idempotent site-data repairs for the shapes
  the matrix found (a stripped Custom DocPerm flag, a stale self User
  Permission, a case-drifted `Employee.user_id`) — a nightly job, so a shape
  that reappears is healed before anyone notices.

The doctypes are the ones the PWA files AS the employee. Employee Advance
and Travel Request are deliberately absent: their DocPerm rows grant staff
no `create` (v15.112 lock; HR files them) and Nadi ships no form for them,
so "refused" is the design, not a defect.

Cost: one query for the employees, one for the enabled users, then per user
`frappe.set_user` (cache reset) and one `has_permission` per doctype; the
gate walk runs only for refusals. Role and DocPerm lookups are Frappe-cached
per user. ~300 users x 10 doctypes probed in well under a minute on the
bench.
# ceiling: one process, users walked in sequence; upgrade: enqueue per
# company batch if a site ever carries thousands of linked users.
"""

from __future__ import annotations

import logging
from collections import Counter
from contextlib import contextmanager

import frappe
from frappe import _

from hrms.api.diagnose import create_allowed, diagnose_for_user
from hrms.utils.identity import normalize_login

logger = logging.getLogger(__name__)

#: Every doctype Nadi creates as the employee (FormView doctype=... and the
#: check-in surfaces), plus the request shapes an employee may file from Desk.
PWA_REQUEST_DOCTYPES: tuple[str, ...] = (
	"Leave Application",
	"Attendance Request",
	"Shift Request",
	"Compensatory Leave Request",
	"Expense Claim",
	"OT Request",
	"Replacement Leave Claim",
	"Shift Swap Request",
	"Remote Checkin Request",
	"Employee Issue",
)

#: Self-service create is not granted by design; listed so the report and the
#: invariant test can say why they are missing rather than silently skip them.
NOT_SELF_SERVICE: tuple[str, ...] = ("Employee Advance", "Travel Request")

GATE_IDENTITY = "identity"


@contextmanager
def impersonating(user: str):
	"""Run the block as `user`, then put the request's session back EXACTLY.

	`frappe.set_user` is what the permission stack keys its caches on, and it
	is also what `new_doc` reads for the user defaults that fill `company` —
	so a probe must run under it. But `set_user` overwrites `session.sid`
	with the username and empties `form_dict` and `session.data`; the response
	cookie is written from `session.sid`, so calling `set_user(original)`
	afterwards would log the HR user out of Desk. The three are restored by
	hand.
	"""
	session = frappe.local.session
	saved_user, saved_sid, saved_data = session.user, session.get("sid"), session.get("data")
	saved_form = frappe.local.form_dict
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(saved_user)
		session.sid = saved_sid
		session.data = saved_data
		frappe.local.form_dict = saved_form
		logger.debug("[request_access] session restored to %s", saved_user)


def linked_users(companies: list[str] | None = None) -> list[frappe._dict]:
	"""Enabled Users that an Active Employee claims, one row per login.

	Grouped on the NORMALIZED login the way `hrms.utils.identity` resolves it.
	A login claimed by two Active Employees comes back with `employee=None`
	and the claimants in `ambiguous`: that person can file nothing, and the
	report must say so rather than skip them. `companies` fences the walk to
	an HR (Company) / HR (Instance) caller's companies; empty means all.
	"""
	filters = {"status": "Active", "user_id": ("is", "set")}
	if companies:
		filters["company"] = ("in", list(companies))
	rows = frappe.get_all(
		"Employee", filters=filters, fields=["name", "employee_name", "user_id", "company"], order_by="name"
	)
	by_login: dict[str, list] = {}
	for row in rows:
		login = normalize_login(row.user_id)
		if login:
			by_login.setdefault(login, []).append(row)
	if not by_login:
		return []
	enabled = set(
		frappe.get_all("User", filters={"enabled": 1, "name": ("in", list(by_login))}, pluck="name")
	)
	users = []
	for login in sorted(by_login):
		if login not in enabled:
			continue
		claims = by_login[login]
		first = claims[0]
		users.append(
			frappe._dict(
				user=login,
				employee=first.name if len(claims) == 1 else None,
				employee_name=first.employee_name,
				company=first.company,
				ambiguous=[c.name for c in claims] if len(claims) > 1 else [],
			)
		)
	logger.info("[request_access] %d linked user(s) to walk (fence=%s)", len(users), companies or "none")
	return users


def scan(companies: list[str] | None = None, doctypes: tuple[str, ...] = PWA_REQUEST_DOCTYPES) -> list[dict]:
	"""Every (user, doctype) the user may NOT create for their own employee.

	Read-only: builds unsaved probe documents and asks the permission stack.
	Rows carry `user, employee, employee_name, company, doctype, refused_by,
	why` — the last two straight from `hrms.api.diagnose`.
	"""
	refusals: list[dict] = []
	metas = {doctype: frappe.get_meta(doctype) for doctype in doctypes}
	users = linked_users(companies)
	for person in users:
		if not person.employee:
			refusals.append(
				_row(
					person,
					doctype=None,
					refused_by=GATE_IDENTITY,
					why=_(
						"This login is claimed by {0} active Employee records ({1}); nothing can be filed "
						"until HR resolves the duplicate."
					).format(len(person.ambiguous), ", ".join(person.ambiguous)),
				)
			)
			continue
		with impersonating(person.user):
			for doctype in doctypes:
				if create_allowed(doctype, person.user, person.employee, meta=metas[doctype]):
					continue
				detail = diagnose_for_user(doctype, person.user, employee=person.employee)
				refusals.append(
					_row(person, doctype=doctype, refused_by=detail["refused_by"], why=detail["why"])
				)
	logger.info(
		"[request_access] walked %d user(s) x %d doctype(s): %d refusal(s)",
		len(users),
		len(doctypes),
		len(refusals),
	)
	return refusals


def _row(person, *, doctype, refused_by, why) -> dict:
	return {
		"user": person.user,
		"employee": person.employee,
		"employee_name": person.employee_name,
		"company": person.company,
		"doctype": doctype,
		"refused_by": refused_by,
		"why": why,
	}


def refusal_summary(companies: list[str] | None = None) -> dict:
	"""For the daily health log: how many people, and the top reasons."""
	rows = scan(companies)
	users = {row["user"] for row in rows}
	top = Counter(row["refused_by"] for row in rows).most_common(3)
	summary = {"users": len(users), "rows": len(rows), "top": top}
	logger.info("[request_access] summary: %s", summary)
	return summary


def summary_lines(summary: dict | None) -> list[str]:
	"""The health-log block, one line per fact, nothing when every user can file."""
	if not summary:
		return []
	lines = ["Request access:"]
	if not summary.get("users"):
		lines.append("  every linked user can file their own requests")
		return lines
	lines.append(f"  {summary['users']} users cannot file their own requests ({summary['rows']} refusals)")
	for gate, count in summary.get("top") or []:
		lines.append(f"    {gate}: {count}")
	lines.append("  see the Request Access Health report")
	return lines


#: The idempotent site-data repairs for the shapes the matrix found, in the
#: order they should run: role flags first (the role gate is checked first),
#: then the identity column, then the self permission that depends on it.
HEALERS: tuple[str, ...] = (
	"hrms.patches.v16_0.restore_staff_create_on_pwa_requests",
	"hrms.patches.v16_0.normalize_employee_user_ids",
	"hrms.patches.v16_0.realign_self_employee_permission",
)


def heal_known_shapes() -> dict:
	"""Nightly: re-run every known repair. Each is idempotent and safe on a
	healthy site; one failing never stops the next, and never raises into the
	scheduler. Returns {dotted path: "ok" | "error: ..."}."""
	outcome = {}
	for path in HEALERS:
		try:
			frappe.get_attr(path + ".execute")()
			outcome[path] = "ok"
			logger.info("[request_access] heal %s: ok", path)
		except Exception as exc:
			outcome[path] = f"error: {exc}"
			logger.exception("[request_access] heal %s failed", path)
			try:
				frappe.log_error(title=f"Request access heal failed: {path}", message=frappe.get_traceback())
			except Exception:
				logger.exception("[request_access] could not even log the failure")
	return outcome
