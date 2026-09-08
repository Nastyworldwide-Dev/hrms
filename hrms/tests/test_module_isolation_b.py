"""Second half of the module-isolation regression (see test_module_isolation_a).

Runs after the module that left a bare `frappe` in sys.modules. Without the
conftest guard, `import frappe` here is that bare module — no db, no get_doc —
and the assertion fails the way the sync runner harness did on 8 Sep 2026.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_module_isolation_a.py hrms/tests/test_module_isolation_b.py
"""

import unittest


class TestTheNextModuleGetsTheSessionsFrappeBack(unittest.TestCase):
	def test_import_frappe_is_the_session_stub_again(self):
		import frappe

		# the session stub answers unknown names with a MagicMock, so compare
		# against the marker the polluting module set, not against truthiness
		self.assertNotEqual(
			getattr(frappe, "left_behind_by", None),
			"test_module_isolation_a",
			"a module that swapped frappe at run time leaked it into this module",
		)
		self.assertTrue(hasattr(frappe, "db"), "the session's frappe (stub or real) carries db")
