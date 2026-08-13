"""Employee Advance is read-only for every role — nobody requests advances.

Company policy (2026-08-13): staff may not request an advance and the company
does not issue them. The PWA entry points are gone, but UI removal alone
leaves the create API open, so no shipped permission row may grant anything
beyond read. Administrator still bypasses permissions in Frappe — that is the
deliberate escape hatch, not a gap.

The JSON check runs anywhere (no bench):
    python3 -m unittest hrms.tests.test_employee_advance_readonly
"""

import json
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]

MUTATING_FLAGS = ("create", "write", "submit", "cancel", "amend", "delete")


class TestEmployeeAdvanceReadOnly(unittest.TestCase):
	def test_shipped_permissions_grant_read_only(self):
		path = HRMS_ROOT / "hr" / "doctype" / "employee_advance" / "employee_advance.json"
		doc = json.loads(path.read_text(encoding="utf-8"))
		rows = doc["permissions"]
		self.assertTrue(rows, "Employee Advance must keep read rows for reporting")

		for row in rows:
			role = row.get("role")
			with self.subTest(role=role):
				self.assertTrue(row.get("read"), f"{role}: read must stay for existing records")
				for flag in MUTATING_FLAGS:
					self.assertFalse(
						row.get(flag), f"{role}: {flag} must be revoked — advances are not issued"
					)


if __name__ == "__main__":
	unittest.main()
