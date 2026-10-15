"""General SOPs reach every company (owner, 15 Oct 2026).

SOPs posted from Nadi before alpha.51 carried the HR user's own company, so a
General SOP reached one company. The patch clears the company of General SOPs
only, and logs the company each had. The SOP list also records why a reader
with published SOPs sees none.

    python3 hrms/tests/test_general_sops_group_wide.py
"""

import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATCH = ROOT / "patches" / "v16_0" / "make_general_sops_group_wide.py"
API = ROOT / "api" / "sop.py"


class TestPatch(unittest.TestCase):
	def setUp(self):
		self.src = PATCH.read_text()

	def test_only_general_sops_that_name_a_company(self):
		self.assertIn('filters={"scope": "General", "company": ("is", "set")}', self.src)

	def test_clears_the_company_and_keeps_the_modified_time(self):
		self.assertIn(
			'frappe.db.set_value("SOP Document", row.name, "company", "", update_modified=False)', self.src
		)

	def test_logs_what_each_had_so_it_can_be_put_back(self):
		self.assertIn("(was company %s)", self.src)

	def test_registered(self):
		self.assertIn("hrms.patches.v16_0.make_general_sops_group_wide", (ROOT / "patches.txt").read_text())


class TestWhyEmpty(unittest.TestCase):
	def test_the_list_records_why_it_is_empty_once_a_day(self):
		tree = ast.parse(API.read_text())
		fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_record_why_empty")
		src = ast.unparse(fn)
		self.assertIn("expires_in_sec=86400", src)
		self.assertIn("frappe.log_error", src)
		get_sops = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_sops")
		self.assertIn("if rows and (not visible_rows):", ast.unparse(get_sops))


if __name__ == "__main__":
	unittest.main()
