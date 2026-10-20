"""alpha.60: an approval sheet sat grey forever on a senior's phone and never
reproduced locally. The PWA reports a load stuck past 10 s; the server keeps one
Error Log per user and document a day, so the live cause is visible without
asking staff (never-ask-employees-to-diagnose). Source-asserted like the SOP
why-empty check (bench run-tests is unusable here).
Run: python -m pytest hrms/tests/test_a_stuck_load_reports_itself.py
"""

import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parent.parent / "api" / "__init__.py"


class TestStuckLoad(unittest.TestCase):
	def setUp(self):
		tree = ast.parse(API.read_text())
		self.fn = next(
			n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "report_stuck_load"
		)
		self.src = ast.unparse(self.fn)

	def test_post_only(self):
		deco = ast.unparse(self.fn.decorator_list[0])
		self.assertIn("methods=['POST']", deco)

	def test_once_a_day_per_user_and_document(self):
		self.assertIn("expires_in_sec=86400", self.src)
		self.assertIn("frappe.session.user", self.src)
		self.assertIn("frappe.log_error", self.src)

	def test_input_is_bounded(self):
		# a client string never reaches the log unbounded
		self.assertIn("[:140]", self.src)
		self.assertIn("cint(ms)", self.src)
		# a client cannot flood the Error Log by varying the name
		self.assertIn("frappe.cache.incr(daily)", self.src)
		self.assertIn("count > 20", self.src)

	def test_listed_as_a_write(self):
		self.assertIn(
			'"report_stuck_load"',
			(API.parent.parent / "tests" / "test_api_writes_are_post_only.py").read_text(),
		)


if __name__ == "__main__":
	unittest.main()
