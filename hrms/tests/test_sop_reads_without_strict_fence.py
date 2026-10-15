"""Staff saw an empty SOP list (owner, 15 Oct 2026).

With "Apply Strict User Permissions" on, frappe.get_list refuses a reader who
holds a Company User Permission every row whose company is blank, and every SOP
saved from Nadi has a blank company ("for the whole group"). The SOP API now
reads with get_all and applies its own rule (_sees -> record_visible), keeping
the role gate. Driven through the rule itself:

    python3 hrms/tests/test_sop_reads_without_strict_fence.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = ROOT / "api" / "sop.py"
SCOPE = ROOT / "overrides" / "sop_document_row_scope.py"


def _lift(path, *names):
	tree = ast.parse(path.read_text())
	return [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]


class TestTheRule(unittest.TestCase):
	def setUp(self):
		ns = {"logger": SimpleNamespace(debug=lambda *a, **k: None)}
		body = _lift(SCOPE, "company_matches", "record_visible") + _lift(API, "_sees")
		ns["company_visible"] = lambda company, user, allow_blank=False: True
		exec(compile(ast.Module(body=body, type_ignores=[]), "sop", "exec"), ns)
		self.sees = ns["_sees"]

	def row(self, **k):
		base = {"published": 1, "scope": "General", "department": None, "company": None}
		base.update(k)
		return SimpleNamespace(**base, get=lambda f, d=None: base.get(f, d))

	def test_a_group_wide_general_sop_reaches_every_employee(self):
		self.assertTrue(self.sees(self.row(), False, "u", "Ops - A", "A"))

	def test_own_department_yes_other_department_no(self):
		self.assertTrue(
			self.sees(self.row(scope="Department", department="Ops - A"), False, "u", "Ops - A", "A")
		)
		self.assertFalse(
			self.sees(self.row(scope="Department", department="Fin - A"), False, "u", "Ops - A", "A")
		)

	def test_another_companys_sop_and_a_draft_stay_hidden(self):
		self.assertFalse(self.sees(self.row(company="B"), False, "u", "Ops - A", "A"))
		self.assertFalse(self.sees(self.row(published=0), False, "u", "Ops - A", "A"))


class TestNoStrictFence(unittest.TestCase):
	def test_the_list_reads_with_get_all_behind_the_role_gate(self):
		src = API.read_text()
		body = src[src.index("def get_sops") : src.index("def _sees")]
		self.assertIn('frappe.has_permission("SOP Document", "read", throw=True)', body)
		self.assertIn('frappe.get_all(\n\t\t"SOP Document"', body)
		self.assertNotIn("frappe.get_list(", body)

	def test_the_reader_does_not_ask_the_per_document_check(self):
		src = API.read_text()
		body = src[src.index("def _get_visible_doc") : src.index("def get_sop(")]
		self.assertNotIn("doc=doc", body)
		self.assertIn("_sees(doc, is_hr, user, department, company)", body)


if __name__ == "__main__":
	unittest.main()
