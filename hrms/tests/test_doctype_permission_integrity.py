"""Shipped doctype JSONs must satisfy Frappe's permission-row validators.

Frappe validates the *whole* doctype whenever anything calls `add_permission()`
on it. So a single invalid row in a shipped doctype JSON aborts any migrate —
or any fresh install — that touches that doctype's permissions, even when the
row being added is perfectly fine.

Two rules are covered here, one per past outage:

1. `check_level_zero_is_set` — every permlevel>0 row needs a permlevel-0 row for
   the same role. This failed nasty-sg-dev's migrate twice: `leave_type.json`
   row 6 granted System Manager permlevel 1 with no permlevel-0 row, so the
   lockdown patch's own (valid) HR grants could never be applied.

2. `check_permission_dependency` — `cancel` and `amend` each require `submit` on
   the same row. This aborted the first v16 fresh install on verifica-live:
   v15.106.3 gave the Employee role `cancel` on Leave Application, Expense Claim
   and Shift Request without `submit`. It stayed invisible on nasty-live because
   Custom DocPerm rows make doctype JSON permissions inert there, and because
   the runtime grant goes through
   `update_permission_property(..., validate=False)`. Only a *fresh* install
   loads these rows and validates them, so grant cancel at runtime, never in JSON.

Pure static check over the repo's JSON — no bench, no site.
"""

import json
import pathlib
import unittest

# Frappe exempts these from the rule (frappe/permissions.py).
EXEMPT_ROLES = {"All", "Desk User"}

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _invalid_rows():
	for path in sorted(HRMS_ROOT.rglob("*.json")):
		try:
			doc = json.loads(path.read_text(encoding="utf-8"))
		except (json.JSONDecodeError, UnicodeDecodeError):
			continue
		if not isinstance(doc, dict):
			continue

		permissions = doc.get("permissions") or []
		if not permissions:
			continue

		roles_at_zero = {p.get("role") for p in permissions if not p.get("permlevel")}
		for row, perm in enumerate(permissions, start=1):
			role = perm.get("role")
			if (perm.get("permlevel") or 0) <= 0 or role in EXEMPT_ROLES:
				continue
			if role not in roles_at_zero:
				yield doc.get("name"), role, perm.get("permlevel"), row


def _dependency_violations():
	"""Rows granting cancel/amend without submit — Frappe refuses these outright."""
	for path in sorted(HRMS_ROOT.rglob("*.json")):
		try:
			doc = json.loads(path.read_text(encoding="utf-8"))
		except (json.JSONDecodeError, UnicodeDecodeError):
			continue
		if not isinstance(doc, dict):
			continue

		for row, perm in enumerate(doc.get("permissions") or [], start=1):
			if perm.get("submit"):
				continue
			for dependent in ("cancel", "amend"):
				if perm.get(dependent):
					yield doc.get("name"), perm.get("role"), dependent, row


class TestDoctypePermissionIntegrity(unittest.TestCase):
	def test_no_cancel_or_amend_without_submit(self):
		offenders = list(_dependency_violations())
		self.assertEqual(
			offenders,
			[],
			"Doctype JSONs grant cancel/amend without submit on the same row. "
			"Frappe refuses this and it will abort a fresh install: "
			+ ", ".join(f"{name} row {row}: {role} has {dep}" for name, role, dep, row in offenders),
		)

	def test_no_permlevel_row_without_its_level_zero(self):
		offenders = list(_invalid_rows())
		self.assertEqual(
			offenders,
			[],
			"Doctype JSONs grant a permlevel>0 row to a role with no permlevel-0 row. "
			"Frappe refuses this and it will abort migrate: "
			+ ", ".join(f"{name} row {row}: {role} at level {lvl}" for name, role, lvl, row in offenders),
		)


if __name__ == "__main__":
	unittest.main()
