# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Guard for the sync permission preflight (hrms.sync.preflight).

The probe must split every synced doctype into readable / blocked (403) / other,
never abort the whole report on one doctype, and only flag a 403 as a permission
block (a 500 or a network error is a different problem). Mocked so it needs no
reachable source.
"""

import unittest
from unittest.mock import patch

from hrms.sync.client import RemoteInstanceError


class _FakeClient:
	"""Reads succeed except where `blocked`/`erroring` say otherwise."""

	def __init__(self, instance_name, blocked=(), erroring=()):
		self.blocked = set(blocked)
		self.erroring = set(erroring)

	def get_list(self, doctype, **_kwargs):
		if doctype in self.blocked:
			raise RemoteInstanceError(
				"no read permission", status_code=403, endpoint=f"/api/resource/{doctype}"
			)
		if doctype in self.erroring:
			raise RemoteInstanceError(
				"remote returned 500", status_code=500, endpoint=f"/api/resource/{doctype}"
			)
		return []


class TestSyncPreflight(unittest.TestCase):
	def _run(self, blocked=(), erroring=()):
		from hrms.sync import preflight

		def _client(name):
			return _FakeClient(name, blocked=blocked, erroring=erroring)

		with (
			patch.object(preflight, "DEFAULT_SYNC_DOCTYPES", ["Leave Type", "Shift Type", "Attendance"]),
			patch.object(preflight, "RemoteInstanceClient", _client),
			patch.object(preflight.frappe, "only_for", lambda *a, **k: None),
			patch.object(preflight, "_", lambda s: s),
		):
			return preflight.check_source_permissions("Handa")

	def test_403_is_a_permission_block_500_is_not(self):
		out = self._run(blocked=["Leave Type"], erroring=["Shift Type"])
		self.assertEqual(out["blocked_403"], ["Leave Type"])
		self.assertEqual(out["readable"], ["Attendance"])
		self.assertEqual([e["doctype"] for e in out["other_errors"]], ["Shift Type"])
		self.assertIn("grant the API user read", out["remedy"])

	def test_all_readable_reports_clean(self):
		out = self._run()
		self.assertEqual(out["blocked_403"], [])
		self.assertEqual(len(out["readable"]), 3)
		self.assertIn("readable at the source", out["remedy"])


if __name__ == "__main__":
	unittest.main()
