"""Tapping a notification marks it read through an endpoint staff may call.

The Notifications screen marked a tapped row read with frappe.client.set_value
on PWA Notification. Staff hold READ on that doctype and nothing else, so every
tap answered 403 — a "Could not load — Not permitted" toast over whatever the
tap had opened, an uncaught error in the console, and an unread count that
only ever grew (130 on the reporting user's phone). "Mark all as read" already
goes through a whitelisted method that scopes by to_user; a single row now does
the same.

Pinned here, bench-free (frappe stubbed when no bench is on the path):

  * the method is whitelisted and marks exactly the named row read;
  * only the addressee may mark it — anyone else is refused, nothing written;
  * an unknown row is refused rather than silently ignored.

    PYTHONPATH=. python3 hrms/tests/test_notification_mark_read.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

ME = "staff@example.com"
SOMEONE_ELSE = "other@example.com"


def _throw(msg, exc=Exception, *args, **kwargs):
	raise exc(msg)


class TestMarkNotificationAsRead(unittest.TestCase):
	def _call(self, name, addressee):
		import hrms.api as api

		db = MagicMock()
		db.get_value.side_effect = lambda doctype, n, field=None, **kw: (
			addressee if (doctype == "PWA Notification" and n == name and addressee) else None
		)
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user=ME)),
			patch.object(frappe, "throw", side_effect=_throw),
		):
			return api.mark_notification_as_read(name), db

	def test_the_addressee_marks_their_own_row_read(self):
		_, db = self._call("1706", addressee=ME)
		db.set_value.assert_called_once()
		self.assertEqual(db.set_value.call_args.args, ("PWA Notification", "1706", "read", 1))

	def test_someone_elses_row_is_refused_and_untouched(self):
		with self.assertRaises(frappe.PermissionError):
			self._call("1706", addressee=SOMEONE_ELSE)

	def test_an_unknown_row_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self._call("nope", addressee=None)

	def test_it_is_whitelisted(self):
		import ast
		import pathlib

		src = (pathlib.Path(__file__).resolve().parents[1] / "api" / "__init__.py").read_text()
		fn = next(
			n
			for n in ast.walk(ast.parse(src))
			if isinstance(n, ast.FunctionDef) and n.name == "mark_notification_as_read"
		)
		self.assertTrue(
			any("whitelist" in ast.unparse(d) for d in fn.decorator_list),
			"mark_notification_as_read must be @frappe.whitelist()ed — the PWA calls it",
		)


if __name__ == "__main__":
	unittest.main()
