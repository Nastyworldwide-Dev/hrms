"""`Employee.user_id` is the login, spelled the way the login is (v16_0).

15 September 2026, matrix probe: an employee whose `user_id` read
"  Amran@Example.com " for the user amran@example.com was refused every
request at the ROLE gate — erpnext's `validate_employee_role` compares that
column to the User name exactly and strips the Employee role on every User
save when it finds no match. The app resolves the person fine
(`hrms.utils.identity` normalizes), so nothing looked wrong until they
tried to file. The keeper in `hrms.overrides.employee_master` now restores
the role; this patch removes the drift itself so the two spellings agree.

Rule: for every Employee with a `user_id`, the stored value is
`normalize_login(user_id)` — `strip().lower()`, the same rule the resolver
applies. A normalized value already carried by ANOTHER Employee record is
left alone and logged (that is a duplicate claim to reconcile; writing it
would turn a visible drift into an AMBIGUOUS login). Written through
`db.set_value` with `update_modified=False`: not a change to HR data, and
invisible to the mirror's `modified >` watermark. Idempotent — safe to
re-run, and re-run nightly by `hrms.utils.request_access.heal_known_shapes`.
"""

import logging

import frappe

from hrms.utils.identity import normalize_login

logger = logging.getLogger(__name__)


def execute():
	logger.info("[normalize_user_id] patch start")
	rows = frappe.get_all(
		"Employee", filters={"user_id": ("is", "set")}, fields=["name", "user_id", "status"], order_by="name"
	)
	changed = normalize_rows(rows)
	logger.info("[normalize_user_id] patch done — %d row(s) normalized", changed)


def normalize_rows(rows) -> int:
	"""Normalize every drifted `user_id` whose normalized form nobody else claims; rows written."""
	by_login: dict[str, list] = {}
	for row in rows:
		login = normalize_login(row.user_id)
		if login:
			by_login.setdefault(login, []).append(row)
	written = 0
	for login, claims in sorted(by_login.items()):
		drifted = [row for row in claims if row.user_id != login]
		if not drifted:
			continue
		if len(claims) > 1:
			logger.warning(
				"[normalize_user_id] %s is claimed by %d Employee records (%s) — left alone, reconcile them",
				login,
				len(claims),
				", ".join(row.name for row in claims),
			)
			continue
		row = drifted[0]
		frappe.db.set_value("Employee", row.name, "user_id", login, update_modified=False)
		written += 1
		logger.info("[normalize_user_id] %s: user_id %r -> %r", row.name, row.user_id, login)
	return written
