"""Guard: opening a request form must never demand Desk doctype access.

The senior hit this live on 2026-08-19: "User … does not have doctype access
via role permission for document Department" as a toast on the PWA, because
the three approver-selector endpoints demanded `Department` read before
answering. That check is an UPSTREAM v16 addition — v15 production never had
it, so no staff member had ever seen it — and a self-service user on this
hub holds only the bare Employee role, which has no Department read.

The check was also redundant: each endpoint's FIRST line is
`_ensure_own_employee_or_permitted(employee)` — the real authorization —
and the data returned is the list of people the caller is ALLOWED to route a
request to, the very list `get_designated_approvers` reads permissionlessly
for the save-time fence. Requiring Desk read for it is the same disease as
the holiday-list 403 fixed earlier: a Desk permission gate strangling a
fenced self-service read.

Rule pinned here: these three endpoints answer with the own-employee fence
alone. Never re-add a `has_permission` demand to them without deciding how
every bare-Employee user is supposed to file a request.

AST-based and bench-free: run as
`python3 hrms/tests/test_self_service_department_reads.py`.
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "api" / "__init__.py"

SELF_SERVICE_SELECTORS = (
	"get_shift_request_approvers",
	"get_leave_approval_details",
	"get_expense_approval_details",
)


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {SOURCE}")


class TestApproverSelectorsServeBareEmployees(unittest.TestCase):
	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())

	def test_no_desk_permission_demand(self):
		for name in SELF_SERVICE_SELECTORS:
			fn = _function(self.tree, name)
			for node in ast.walk(fn):
				if (
					isinstance(node, ast.Call)
					and isinstance(node.func, ast.Attribute)
					and node.func.attr == "has_permission"
				):
					self.fail(
						f"{name} demands a Desk doctype permission "
						f"({ast.unparse(node)}) — a bare-Employee user cannot "
						"pass it and their request form breaks with a toast"
					)

	def test_the_real_fence_stays_first(self):
		for name in SELF_SERVICE_SELECTORS:
			fn = _function(self.tree, name)
			calls = {
				node.func.id
				for node in ast.walk(fn)
				if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
			}
			self.assertIn(
				"_ensure_own_employee_or_permitted",
				calls,
				f"{name} lost its own-employee fence — that IS the authorization",
			)


if __name__ == "__main__":
	unittest.main()
