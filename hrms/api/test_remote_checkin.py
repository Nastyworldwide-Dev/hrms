# Copyright (c) 2026, Nastyworldwide and contributors
# See license.txt
"""Regression tests for what hrms.api.remote_checkin.punch puts on the document.

The endpoint's own guards (self-only, selfie ownership, server clock) are
exercised against a real site elsewhere. What is pinned here is the plumbing
that is invisible when it breaks: the device's accuracy estimate must land on
the document as a flag, because that is the only thing the geofence override
reads it from. Drop the assignment and every punch is measured as if its
coordinates were surveyed — with no error, no log line and no failing test.

Pure unit tests: frappe's document and session layers are mocked, so these run
without a bench or site, as well as under `bench run-tests`.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from hrms.api import remote_checkin

EMPLOYEE = "EMP-0001"
USER = "jane@example.com"


class _FakeDoc(SimpleNamespace):
	"""Stands in for a new Employee Checkin document."""

	def __init__(self):
		super().__init__(
			name="EMP-CKIN-0001",
			employee=None,
			employee_name="Jane",
			log_type=None,
			time=None,
			latitude=None,
			longitude=None,
			requires_remote_approval=0,
			remote_approval_status=None,
			flags=SimpleNamespace(),
			inserted=False,
		)

	def update(self, values):
		for key, value in values.items():
			setattr(self, key, value)

	def insert(self):
		self.inserted = True


class _PunchHarness:
	"""Runs punch() against mocks and hands back the document it built.

	The whole `frappe` name is swapped inside the module rather than patching
	`frappe.db` — outside a request that is an unbound thread-local proxy and
	cannot be patched at all.
	"""

	def __enter__(self):
		self.doc = _FakeDoc()
		stub = SimpleNamespace(
			db=SimpleNamespace(get_value=lambda *args, **kwargs: USER),
			session=SimpleNamespace(user=USER),
			new_doc=lambda doctype: self.doc,
			PermissionError=frappe.PermissionError,
			_dict=frappe._dict,
		)
		self._patches = [
			patch.object(remote_checkin, "frappe", stub),
			patch.object(remote_checkin, "employee_now", return_value="2026-08-24 09:00:00"),
		]
		for p in self._patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self._patches:
			p.stop()
		return False


class TestPunchCarriesDeviceAccuracy(unittest.TestCase):
	def test_accuracy_lands_on_the_document_flags(self):
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, accuracy=37.5)
		self.assertEqual(h.doc.flags.location_accuracy_m, 37.5)
		self.assertTrue(h.doc.inserted)

	def test_accuracy_survives_arriving_as_a_string(self):
		# Whitelisted endpoints receive form-encoded values; everything is text.
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, accuracy="37.5")
		self.assertEqual(h.doc.flags.location_accuracy_m, 37.5)

	def test_a_punch_without_accuracy_leaves_the_flag_unset(self):
		# Unset means "unknown", which the geofence reads as no allowance.
		# Setting it to 0 here would read as a perfect fix and widen nothing —
		# same outcome today, opposite meaning, so it stays absent.
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6)
		self.assertIsNone(getattr(h.doc.flags, "location_accuracy_m", None))

	def test_junk_accuracy_is_dropped_rather_than_carried(self):
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, accuracy="not-a-number")
		self.assertIsNone(getattr(h.doc.flags, "location_accuracy_m", None))

	def test_a_negative_accuracy_is_not_carried(self):
		# No device reports this; a caller hand-rolling the endpoint might.
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, accuracy=-1)
		self.assertIsNone(getattr(h.doc.flags, "location_accuracy_m", None))


if __name__ == "__main__":
	unittest.main()
