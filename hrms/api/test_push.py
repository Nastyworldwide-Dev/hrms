"""`hrms.api.push` wraps the framework's subscribe/unsubscribe and hooks.py
routes the framework's own endpoints through it — see hrms/utils/push_relay.py
for why (a cloned site inherits another site's relay credentials).

Bench-free: frappe is a stand-in. Run as a file:

    PYTHONPATH=. python3 hrms/api/test_push.py
"""

import ast
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

HRMS = pathlib.Path(__file__).resolve().parent.parent


class TestWrappersAndRouting(unittest.TestCase):
	def test_subscribe_returns_frappes_shape_through_relay_call(self):
		from hrms.api import push

		client = MagicMock()
		client.add_token.return_value = (True, "Token added")
		with (
			patch.object(push, "PushNotification", return_value=client),
			patch.object(frappe, "session", frappe._dict(user="u@example.com")),
		):
			out = push.subscribe(fcm_token="tok", project_name="hrms")
		self.assertEqual(out, {"success": True, "message": "Token added"})
		client.add_token.assert_called_once_with("u@example.com", "tok")

	def test_unsubscribe_returns_frappes_shape(self):
		from hrms.api import push

		client = MagicMock()
		client.remove_token.return_value = (True, "Token removed")
		with (
			patch.object(push, "PushNotification", return_value=client),
			patch.object(frappe, "session", frappe._dict(user="u@example.com")),
		):
			out = push.unsubscribe(fcm_token="tok", project_name="hrms")
		self.assertEqual(out, {"success": True, "message": "Token removed"})

	def test_hooks_route_frappes_endpoints_through_the_wrappers(self):
		tree = ast.parse((HRMS / "hooks.py").read_text())
		overrides = None
		for node in tree.body:
			if isinstance(node, ast.Assign) and any(
				isinstance(t, ast.Name) and t.id == "override_whitelisted_methods" for t in node.targets
			):
				overrides = ast.literal_eval(node.value)
		self.assertIsNotNone(overrides, "hooks.py must declare override_whitelisted_methods")
		self.assertEqual(overrides.get("frappe.push_notification.subscribe"), "hrms.api.push.subscribe")
		self.assertEqual(overrides.get("frappe.push_notification.unsubscribe"), "hrms.api.push.unsubscribe")

	def test_push_send_goes_through_relay_call(self):
		"""The send side fails identically on a cloned site; it must heal too."""
		src = (HRMS / "hr/doctype/pwa_notification/pwa_notification.py").read_text()
		tree = ast.parse(src)
		send = next(
			n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "send_push_notification"
		)
		called = {
			getattr(n.func, "id", None) or getattr(n.func, "attr", None)
			for n in ast.walk(send)
			if isinstance(n, ast.Call)
		}
		self.assertIn("relay_call", called, "send_push_notification must call through relay_call")


if __name__ == "__main__":
	unittest.main()
