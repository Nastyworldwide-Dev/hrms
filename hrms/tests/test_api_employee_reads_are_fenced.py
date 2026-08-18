"""Whitelisted API functions that read Employee via frappe.get_all must
restate the company fence.

`frappe.get_all` bypasses the row-scope hooks (it queries with permissions
ignored), and `frappe.only_for` / role checks answer "is this person HR?"
without asking WHICH companies' HR. Both halves existed and still leaked:
`get_managers` / `get_team_status` let an "HR (Company)" user browse another
company's team — members, punch times, leave — and `get_all_employees` handed
them the full 15-company directory, user_id included.

The rule this pins: inside hrms/api, any function whose body calls
`frappe.get_all("Employee", ...)` must reference `allowed_companies` (the
fence's single source of truth) somewhere in the same function. Deliberately
scoped to the "Employee" doctype constant and the get_all reader:
`frappe.get_list` and `frappe.qb.get_query(..., ignore_permissions=False)`
respect the hooks and stay out of scope.

An exemption must be argued for in a diff; the set starts empty.

AST only — no bench required.
"""

import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parent.parent / "api"

EXEMPT: set[str] = set()


def _employee_get_all_calls(func) -> list[int]:
	hits = []
	for node in ast.walk(func):
		if not isinstance(node, ast.Call) or getattr(node.func, "attr", None) != "get_all":
			continue
		if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "Employee":
			hits.append(node.lineno)
	return hits


def _references_fence(func) -> bool:
	for node in ast.walk(func):
		if isinstance(node, ast.Name) and node.id == "allowed_companies":
			return True
		if isinstance(node, ast.Attribute) and node.attr == "allowed_companies":
			return True
	return False


class TestApiEmployeeReadsAreFenced(unittest.TestCase):
	def _offenders(self):
		for path in sorted(API.rglob("*.py")):
			if path.name.startswith("test_"):
				continue
			for func in ast.walk(ast.parse(path.read_text())):
				if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
					continue
				if func.name in EXEMPT:
					continue
				lines = _employee_get_all_calls(func)
				if lines and not _references_fence(func):
					yield f"{path.name}:{func.name}", lines

	def test_scan_still_sees_the_known_readers(self):
		"""Guards the test: if the reads move or the reader changes shape, this
		must fail loudly instead of the main assertion passing on an empty scan."""
		readers = set()
		for path in sorted(API.rglob("*.py")):
			if path.name.startswith("test_"):
				continue
			for func in ast.walk(ast.parse(path.read_text())):
				if isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef) and _employee_get_all_calls(func):
					readers.add(func.name)
		self.assertIn("get_all_employees", readers)
		self.assertIn("get_team_status", readers)
		self.assertIn("get_managers", readers)

	def test_every_employee_get_all_reader_restates_the_fence(self):
		offenders = list(self._offenders())
		self.assertEqual(
			offenders,
			[],
			"These hrms/api functions read Employee via frappe.get_all (which "
			"bypasses the row-scope hooks) without referencing allowed_companies. "
			"Restate the fence — an 'HR (Company)' user passes every role check "
			"and must still not cross it:\n"
			+ "\n".join(f"  {name} (lines {lines})" for name, lines in offenders),
		)


if __name__ == "__main__":
	unittest.main()
