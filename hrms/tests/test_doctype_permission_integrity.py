"""Every permlevel>0 permission row needs a permlevel-0 row for the same role.

Frappe enforces this in `check_level_zero_is_set`, and it validates the *whole*
doctype whenever anything calls `add_permission()` on it. So a single invalid
row in a shipped doctype JSON aborts any migrate that touches that doctype's
permissions — even when the row being added is perfectly fine.

That is what failed nasty-sg-dev's migrate twice: `leave_type.json` row 6
granted System Manager permlevel 1 with no permlevel-0 row, so the lockdown
patch's own (valid) HR grants could never be applied.

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


class TestDoctypePermissionIntegrity(unittest.TestCase):
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
