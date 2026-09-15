"""A staff self User Permission names the employee the login resolves to (v16_0).

15 September 2026: an employee filing an Attendance Request in Nadi was told
"You need the 'create' permission on Attendance Request". That wording is
Frappe's DOC-level refusal — the role had create, the document failed the
User Permission check on its `employee` link, and Frappe fell back to the
owner-only permissions, which never include create. Reproduced on the bench
with one variable changed: the user's `allow=Employee` User Permission named
a different Employee record than the one Nadi sent.

ERPNext creates that permission once, when the Employee is linked to the
User, and never moves it. A duplicate Employee, a re-created record after an
offboarding, or a mirror that re-linked the login leaves the row pointing at
the old record while `hrms.utils.identity.own_employees` — the one identity
rule the app and every row-scope fence use — resolves the login to the new
one. Two answers to "who is this?" and the narrower one wins.

Rule: for every enabled User whose login resolves to exactly ONE active
Employee, every `allow=Employee` User Permission on that user points at that
employee. `applicable_for` and `is_default` are kept as they are. A login
resolving to zero or several employees is left alone and logged (that is a
reconciliation, not a repair), as is an HR-sight user (the
`drop_self_employee_permission_for_hr` hook owns that case). Nothing is
created, nothing is deleted, no other `allow` is touched.

Idempotent — safe to re-run.
"""

import logging

import frappe

from hrms.hr.utils import sees_all_employee_data
from hrms.utils.identity import own_employees

logger = logging.getLogger(__name__)


def execute():
	logger.info("[realign_self_up] patch start")
	enabled = set(frappe.get_all("User", filters={"enabled": 1}, pluck="name"))
	by_user: dict[str, list] = {}
	for row in frappe.get_all(
		"User Permission", filters={"allow": "Employee"}, fields=["name", "user", "for_value"]
	):
		by_user.setdefault(row.user, []).append(row)

	changed = 0
	for user, rows in sorted(by_user.items()):
		changed += realign_user(user, rows, enabled)
	logger.info("[realign_self_up] patch done — %d row(s) re-pointed", changed)


def realign_user(user: str, rows: list, enabled: set) -> int:
	"""Point `user`'s allow=Employee rows at their resolved employee; rows written."""
	if user not in enabled or user == "Administrator":
		logger.info("[realign_self_up] %s: disabled or system — left alone", user)
		return 0
	if sees_all_employee_data(user):
		logger.info("[realign_self_up] %s: HR sight — left to the drop hook", user)
		return 0
	own = own_employees(user)
	if len(own) != 1:
		logger.warning(
			"[realign_self_up] %s resolves to %d active employee(s) — left alone, reconcile the Employee records",
			user,
			len(own),
		)
		return 0

	employee = own[0]
	written = 0
	for row in rows:
		if row.for_value == employee:
			continue
		frappe.db.set_value("User Permission", row.name, "for_value", employee)
		written += 1
		logger.info(
			"[realign_self_up] %s: User Permission %s for_value %s -> %s",
			user,
			row.name,
			row.for_value,
			employee,
		)
	if written:
		frappe.clear_cache(user=user)
	return written
