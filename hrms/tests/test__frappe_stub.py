"""The bench-free stub must not silently replace behaviour it is standing in for.

A MagicMock is a fine stand-in for a SEAM (a database read a test patches) and a
terrible one for a DECORATOR: `@request_cache` under a MagicMock does not wrap
the function, it swallows it and hands back a mock. The decorated helper then
answers every call with a MagicMock — truthy, comparable to nothing, and wrong —
so a test asserting on it reads `'HR-EMP-X' not found in <MagicMock ...>` and the
author spends the afternoon debugging their own fixture.

Met 21 Sep 2026 writing the approver-chain test:
`hrms.hr.utils.get_employees_routed_to` is `@request_cache`d, so under the stub
it was not the function at all.

Caching is a performance decision, never a behavioural one, so identity is the
honest stand-in and this file is the rope that keeps it one.

Bench-free:
    PYTHONPATH=. python3 hrms/tests/test__frappe_stub.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()


class TestTheStubsDecoratorsActuallyDecorate(unittest.TestCase):
	def test_request_cache_returns_the_function(self):
		from frappe.utils.caching import request_cache

		@request_cache
		def answer(value):
			return value * 2

		self.assertEqual(answer(21), 42)

	def test_the_parameterised_caches_decorate_too(self):
		from frappe.utils.caching import redis_cache, site_cache

		for decorator in (site_cache, redis_cache):
			with self.subTest(decorator=decorator.__name__ if hasattr(decorator, "__name__") else decorator):

				@decorator(ttl=60)
				def answer():
					return "real"

				self.assertEqual(answer(), "real")


class TestTheStubKeepsItsOtherPromises(unittest.TestCase):
	def test_throw_raises(self):
		"""A throw that returns makes every 'rejects X' assertion pass vacuously."""
		import frappe

		with self.assertRaises(frappe.ValidationError):
			frappe.throw("no")

	def test_conf_is_a_real_dict(self):
		"""A MagicMock conf makes every site-config kill switch read as enabled."""
		import frappe

		self.assertIsNone(frappe.conf.get("some_flag"))


if __name__ == "__main__":
	unittest.main(verbosity=2)
