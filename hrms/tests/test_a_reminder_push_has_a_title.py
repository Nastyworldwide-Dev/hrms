"""A push with no reference doctype still carries a title.

Daily approval/shift reminders are PWA Notification rows with no
reference_document_type. The relay's `user()` requires `title`, so a None title
came back as `TypeError: user() missing 1 required positional argument: 'title'`
and the reminder never reached the phone (Verifica live, 12 Oct 2026).

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_a_reminder_push_has_a_title.py
"""

import importlib
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()


class ReminderPushTitle(unittest.TestCase):
	def _sent_title(self, reference_document_type):
		module = importlib.import_module("hrms.hr.doctype.pwa_notification.pwa_notification")
		sender = MagicMock()
		client = MagicMock(send_notification_to_user=sender)
		client.is_enabled.return_value = True
		fake_module = types.SimpleNamespace(PushNotification=lambda app: client)
		doc = types.SimpleNamespace(
			to_user="a@example.com",
			reference_document_type=reference_document_type,
			message="3 requests are waiting",
			get_notification_link=lambda: "https://x/hrms",
			log_error=MagicMock(),
			name="PN-1",
		)
		with patch.dict(sys.modules, {"frappe.push_notification": fake_module}):
			module.PWANotification.send_push_notification(doc)
		sender.assert_called_once()
		return sender.call_args.args[1]

	def test_a_reminder_with_no_reference_doctype_is_titled(self):
		self.assertTrue(self._sent_title(None))

	def test_a_request_push_keeps_its_doctype_as_title(self):
		self.assertEqual(self._sent_title("Leave Application"), "Leave Application")


if __name__ == "__main__":
	unittest.main()
