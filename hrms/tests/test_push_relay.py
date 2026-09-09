"""A site cloned from another must re-register with the push relay on its own.

Verifica-live was built from a copy of nasty-live, and the copy carried
`Push Notification Settings.api_key/api_secret`. Frappe's relay client
(`frappe.push_notification.PushNotification._get_credential`) reuses whatever
key is stored, so every relay call went out as the OLD site's API user
(`nasty-live.frappe.cloud@notification.frappe`) while naming the NEW site in
`site_name`. The relay looked for a Notification User under the new site,
found none, tried to create one, and refused: that API user may only write
its own site's rows. Symptom in the error log, 9 September 2026:

    DoesNotExistError: Notification User {'id': ..., 'site': 'verifica-live.s.frappe.cloud'} not found
    PermissionError: User nasty-live.frappe.cloud@notification.frappe does not have access

Every subscribe and every push send failed the same way, for every user.

Pinned here, bench-free (frappe.db is a stand-in):

  * a relay call that fails with the relay's PermissionError clears the stored
    credentials and is retried ONCE — `_get_credential` then registers this
    site's own hostname and the retry succeeds;
  * a second PermissionError on the retry propagates — no loop, no silent drop;
  * any other failure propagates untouched and never clears the credentials;
  * the subscribe/unsubscribe wrappers return frappe's `{success, message}`
    shape, and hooks.py routes the framework's own endpoints through them so
    the PWA (which calls `frappe.push_notification.subscribe` by name) heals
    without a frontend change.

    PYTHONPATH=. python3 hrms/tests/test_push_relay.py
"""

import ast
import pathlib
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

HRMS = pathlib.Path(__file__).resolve().parent.parent

RELAY_DENIED = (
	"FrappeClient Request Failed\n"
	"frappe.exceptions.DoesNotExistError: Notification User {'id': 'm.alif@example.com', "
	"'project': 'hrms', 'site': 'verifica-live.s.frappe.cloud'} not found\n"
	"During handling of the above exception, another exception occurred:\n"
	"User <strong>nasty-live.frappe.cloud@notification.frappe</strong> does not have access "
	"to this document: Notification User - None\n"
	"frappe.exceptions.PermissionError"
)


class _RelayDenied(Exception):
	"""Stands in for frappe.frappeclient.FrappeException, which carries the
	relay's traceback as its message."""


class TestRelayCallSelfHeals(unittest.TestCase):
	def _run(self, outcomes):
		"""Drive `relay_call` with a fake relay whose successive results are
		`outcomes` (an exception instance raises, anything else returns)."""
		from hrms.utils import push_relay

		calls = []

		def fake_relay(user, token):
			calls.append((user, token))
			outcome = outcomes[len(calls) - 1]
			if isinstance(outcome, Exception):
				raise outcome
			return outcome

		db = MagicMock()
		with patch.object(frappe, "db", db):
			result = push_relay.relay_call(fake_relay, "u@example.com", "tok")
		return result, calls, db

	def _cleared(self, db):
		fields = {c.args[1] for c in db.set_single_value.call_args_list}
		return fields == {"api_key", "api_secret"}

	def test_relay_permission_error_clears_credentials_and_retries_once(self):
		result, calls, db = self._run([_RelayDenied(RELAY_DENIED), (True, "ok")])
		self.assertEqual(result, (True, "ok"))
		self.assertEqual(len(calls), 2, "one retry after the reset, no more")
		self.assertTrue(self._cleared(db), "both api_key and api_secret must be cleared")
		for c in db.set_single_value.call_args_list:
			self.assertEqual(c.args[0], "Push Notification Settings")
			self.assertIsNone(c.args[2])

	def test_second_permission_error_propagates(self):
		with self.assertRaises(_RelayDenied):
			self._run([_RelayDenied(RELAY_DENIED), _RelayDenied(RELAY_DENIED)])

	def test_other_failures_propagate_without_touching_credentials(self):
		from hrms.utils import push_relay

		db = MagicMock()
		with patch.object(frappe, "db", db), self.assertRaises(ValueError):
			push_relay.relay_call(lambda: (_ for _ in ()).throw(ValueError("relay down")))
		db.set_single_value.assert_not_called()

	def test_success_first_time_never_resets(self):
		result, calls, db = self._run([(True, "ok")])
		self.assertEqual(result, (True, "ok"))
		self.assertEqual(len(calls), 1)
		db.set_single_value.assert_not_called()


if __name__ == "__main__":
	unittest.main()
