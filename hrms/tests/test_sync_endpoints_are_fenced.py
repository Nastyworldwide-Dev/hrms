"""Every hub-wide sync/parity endpoint must refuse a company-fenced operator.

`frappe.only_for` answers "is this person HR?" and stops there. On a
multi-company hub that is half the question: an "HR (Company)" user is HR for
ONE company, and these endpoints act on every company the hub serves — a sync
pulls all seven, `parity_check` and `source_survey` count rows across the whole
source instance.

`hrms.sync.company_shells` has guarded that since SEC-01. The sync and parity
endpoints were left role-checked only, so the fence stopped at the registry and
not at the pull. This pins every whitelisted endpoint in hrms/sync so the next
one added cannot quietly skip it.

AST only — no bench required.
"""

import ast
import pathlib
import unittest

SYNC = pathlib.Path(__file__).resolve().parent.parent / "sync"

#: Endpoints that are deliberately NOT hub-wide would go here, with a reason.
#: Empty on purpose: everything whitelisted in hrms/sync today acts on the whole
#: instance, so an exemption should have to be argued for in a diff.
EXEMPT: set[str] = set()


def _whitelisted(tree):
	for node in ast.walk(tree):
		if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
			continue
		for dec in node.decorator_list:
			target = dec.func if isinstance(dec, ast.Call) else dec
			if getattr(target, "attr", None) == "whitelist":
				yield node


def _calls_by_name(func) -> set[str]:
	names = set()
	for node in ast.walk(func):
		if not isinstance(node, ast.Call):
			continue
		names.add(getattr(node.func, "id", None) or getattr(node.func, "attr", None))
	return names


class TestSyncEndpointsAreFenced(unittest.TestCase):
	def _endpoints(self):
		for path in sorted(SYNC.glob("*.py")):
			if path.name.startswith("test_"):
				continue
			for func in _whitelisted(ast.parse(path.read_text())):
				yield path.name, func

	def test_found_the_endpoints(self):
		"""Guards the test: a refactor must not turn this into a no-op."""
		names = {f.name for _, f in self._endpoints()}
		self.assertIn("enqueue_sync", names)
		self.assertIn("parity_check", names)
		self.assertGreaterEqual(len(names), 5)

	def test_every_endpoint_checks_roles(self):
		for filename, func in self._endpoints():
			if func.name in EXEMPT:
				continue
			with self.subTest(endpoint=f"{filename}:{func.name}"):
				self.assertIn("only_for", _calls_by_name(func), "missing frappe.only_for role check")

	def test_every_endpoint_refuses_a_company_fenced_caller(self):
		for filename, func in self._endpoints():
			if func.name in EXEMPT:
				continue
			with self.subTest(endpoint=f"{filename}:{func.name}"):
				calls = _calls_by_name(func)
				self.assertTrue(
					"require_unfenced" in calls or "_ensure_unfenced_operator" in calls,
					f"{filename}:{func.name} is hub-wide but only role-checked. Call "
					f"hrms.overrides.company_scope.require_unfenced — an HR (Company) "
					f"user must not act on companies outside their fence.",
				)


if __name__ == "__main__":
	unittest.main()
