"""A dry run is the default; only an explicit "off" writes.

Security review of 51902996c: `cint("true")` is 0, so `dry_run=true` from a form
or query string became a live write on endpoints that insert punches and cancel
attendance. Run: PYTHONPATH=. python3 hrms/tests/test_dry_run.py
"""

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

from hrms.utils.dry_run import wants_dry_run

HRMS = Path(__file__).resolve().parents[1]


class TestWantsDryRun(unittest.TestCase):
	def test_explicit_off_values_write(self):
		for value in (0, 0.0, False, "0", "false", "False", " no ", "OFF"):
			with self.subTest(value=value):
				self.assertFalse(wants_dry_run(value))

	def test_everything_else_is_a_dry_run(self):
		for value in (1, True, "1", "true", "True", "yes", "on", "", None, "garbage", 2):
			with self.subTest(value=value):
				self.assertTrue(wants_dry_run(value))


class TestNoEndpointReadsDryRunWithCint(unittest.TestCase):
	"""Invariant for the class: no module parses `dry_run` with cint/bool again."""

	def test_no_cint_or_bool_of_dry_run_argument(self):
		offenders = []
		for path in HRMS.rglob("*.py"):
			if "/tests/" in str(path) or path.name.startswith("test_"):
				continue
			tree = ast.parse(path.read_text(encoding="utf-8"))
			for node in ast.walk(tree):
				if (
					isinstance(node, ast.Call)
					and getattr(node.func, "id", None) in ("cint", "sbool")
					and node.args
					and isinstance(node.args[0], ast.Name)
					and node.args[0].id == "dry_run"
				):
					offenders.append(f"{path.relative_to(HRMS)}:{node.lineno}")
		self.assertEqual(offenders, [], "parse dry_run with hrms.utils.dry_run.wants_dry_run")


if __name__ == "__main__":
	unittest.main()
