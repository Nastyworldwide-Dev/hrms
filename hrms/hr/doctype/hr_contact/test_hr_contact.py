"""Guard: which roles qualify someone to be PUBLISHED as an HR contact is one
list, owned by hrms.api.hr_contacts (HR_CONTACT_ROLES). The doctype's
validate and the API's listing filter must read the same list — they were two
private copies before, one set and one tuple, agreeing only by luck. This is
a curation rule, deliberately distinct from the authorization predicates in
hr/utils.py. Run as `python3 hrms/hr/doctype/hr_contact/test_hr_contact.py`."""

import ast
import unittest
from pathlib import Path

DOCTYPE_SOURCE = Path(__file__).resolve().parent / "hr_contact.py"
API_SOURCE = Path(__file__).resolve().parents[3] / "api" / "hr_contacts.py"


class TestContactRolesAreOneList(unittest.TestCase):
	def test_doctype_imports_the_api_list(self):
		tree = ast.parse(DOCTYPE_SOURCE.read_text())
		imported = any(
			isinstance(node, ast.ImportFrom)
			and node.module == "hrms.api.hr_contacts"
			and any(alias.name == "HR_CONTACT_ROLES" for alias in node.names)
			for node in ast.walk(tree)
		)
		self.assertTrue(imported, "hr_contact.py must import HR_CONTACT_ROLES, not redefine it")

	def test_doctype_keeps_no_private_copy(self):
		tree = ast.parse(DOCTYPE_SOURCE.read_text())
		assigns = [
			node
			for node in ast.walk(tree)
			if isinstance(node, ast.Assign)
			and any(
				isinstance(t, ast.Name) and t.id in ("HR_ROLES", "HR_CONTACT_ROLES") for t in node.targets
			)
		]
		self.assertEqual(assigns, [])

	def test_api_owns_the_list(self):
		tree = ast.parse(API_SOURCE.read_text())
		owned = any(
			isinstance(node, ast.Assign)
			and any(isinstance(t, ast.Name) and t.id == "HR_CONTACT_ROLES" for t in node.targets)
			for node in ast.walk(tree)
		)
		self.assertTrue(owned, "hrms.api.hr_contacts must define HR_CONTACT_ROLES")


if __name__ == "__main__":
	unittest.main()
