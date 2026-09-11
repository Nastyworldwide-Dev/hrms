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

An exemption must be argued for in a diff, and every exemption below carries
its argument. A stale one fails loudly: test_every_exemption_is_still_a_reader
asserts each name is still a function that actually reads Employee, so an
exemption cannot outlive the code it was written for.

The set is not a place to park a red result. It was empty and the test was red
for three readers, which is worse than having no test — a permanently-failing
guard is one nobody reads, and offender #4 arrives unnoticed.

AST only — no bench required.
"""

import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parent.parent / "api"

#: name -> why this reader does not need to restate the company fence.
EXEMPT_REASONS = {
	# THE RULING (Nabil, 11 Sep 2026): Team KPI is group-level sight by
	# definition — any HR sees every company, the CEO (by designation, because
	# in Desk he holds no HR role at all) sees every company, and nobody else
	# reaches the page. This is the ONE endpoint on the hub where an
	# allow=Company User Permission does not narrow an HR user. Pinned from the
	# other side by test_a_company_user_permission_does_not_narrow_team_kpi in
	# hrms/api/test_kpi.py; if the ruling is reversed, both change together.
	"get_team_kpi": "group-level by ruling — see hrms/api/kpi.py::_team_kpi_viewer",
	# Identity, not a directory read: it asks which Employee rows claim the
	# SESSION user, to answer "does this session hold the office?". A company
	# predicate here would be asking whether you are allowed to be yourself.
	"_holds_the_office": "reads only the session user's own Employee rows",
	# Name decoration over rows the caller was ALREADY permitted to read:
	# list_tickets fetches HD Ticket through frappe.get_list, which honours the
	# row-scope hooks, and this only maps each row's existing `raised_by` email
	# to a display name. It cannot surface an employee whose email the caller
	# does not already hold.
	"_attach_raiser_names": "decorates rows already fenced by frappe.get_list",
}
EXEMPT: set[str] = set(EXEMPT_REASONS)


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

	def test_every_exemption_is_still_a_reader(self):
		"""An exemption that outlives its code is rot: it silently pre-approves
		whatever later takes that function name. Every EXEMPT entry must still
		name a function that actually reads Employee via get_all."""
		readers = set()
		for path in sorted(API.rglob("*.py")):
			if path.name.startswith("test_"):
				continue
			for func in ast.walk(ast.parse(path.read_text())):
				if isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef) and _employee_get_all_calls(func):
					readers.add(func.name)
		self.assertEqual(
			sorted(EXEMPT - readers),
			[],
			"these exemptions no longer name an Employee reader — delete them",
		)

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
