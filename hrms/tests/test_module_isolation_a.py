"""First half of the module-isolation regression (see test_module_isolation_b).

This module does what several standalone harness files used to do: it swaps a
bare `frappe` into sys.modules while a test runs and walks away. The root
conftest must put the session's module back before the next module's tests
run, or `import frappe` in that module's setUp gets a stub with no db.
Alphabetical order makes this file run first; both halves are one test.
"""

import sys
import types
import unittest


class TestLeavesABareFrappeBehind(unittest.TestCase):
	def test_swaps_in_a_bare_module_and_never_restores_it(self):
		bare = types.ModuleType("frappe")
		bare.left_behind_by = "test_module_isolation_a"
		sys.modules["frappe"] = bare
		self.assertIs(sys.modules["frappe"], bare)
