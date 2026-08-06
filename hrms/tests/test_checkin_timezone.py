"""Regression tests: attendance clock vs system clock in the check-in path.

Production case these pin down — site System Settings timezone is Asia/Dubai
while staff punch in from Malaysia (UTC+8), a 4h skew that made
submit_late_checkout reject valid times and would have made punch() file every
check-in 4h early.

Pure unit tests: the module under test is exercised with `frappe` mocked, so
these run without a bench or site.
"""

import datetime
import importlib.abc
import importlib.util
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

import frappe


def _install_erpnext_stub():
	"""hrms.api's import chain reaches erpnext, which isn't installed outside a
	bench. Fabricate any erpnext.* module on demand so these stay pure unit
	tests; a real bench has the real package and this is skipped.
	"""
	try:
		import erpnext

		return
	except ImportError:
		pass

	class _Loader(importlib.abc.Loader):
		def create_module(self, spec):
			module = types.ModuleType(spec.name)
			module.__getattr__ = lambda _name: MagicMock()
			module.__path__ = []
			return module

		def exec_module(self, module):
			pass

	class _Finder(importlib.abc.MetaPathFinder):
		def find_spec(self, fullname, path=None, target=None):
			if fullname == "erpnext" or fullname.startswith("erpnext."):
				return importlib.util.spec_from_loader(fullname, _Loader())
			return None

	sys.meta_path.insert(0, _Finder())


_install_erpnext_stub()

KL = "Asia/Kuala_Lumpur"
DUBAI = "Asia/Dubai"


def _fresh_local():
	"""frappe.local stand-in: satisfies the whitelist decorator's checks and
	gives each test a clean resolver memo."""
	local = types.SimpleNamespace()
	local.flags = frappe._dict(in_test=False)
	return local


def _kl_now():
	return datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(hours=8)


def _dubai_now():
	return datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(hours=4)


class TestLateCheckoutUsesAttendanceClock(unittest.TestCase):
	"""The reported bug: 'Check-out time cannot be in the future' for a time
	that has already passed where the employee actually is."""

	def _submit(self, checkout_datetime, attendance_now):
		from hrms.api import remote_checkin

		in_time = _kl_now() - datetime.timedelta(hours=8)
		db = MagicMock()
		db.get_value.side_effect = lambda doctype, name, fields=None, **kw: (
			# filter-dict lookups (next-IN window probe) find nothing
			None
			if isinstance(name, dict)
			else {
				"Employee Checkin": frappe._dict(
					name="EMP-CKIN-1",
					employee="HR-EMP-001",
					time=in_time,
					log_type="IN",
					shift="9AM - 6PM",
				),
				"Employee": "staff@example.com",
			}.get(doctype)
		)
		db.exists.return_value = None

		session = frappe._dict(user="staff@example.com")
		out_doc = MagicMock()
		out_doc.name = "EMP-CKIN-2"

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", session),
			patch.object(frappe, "local", _fresh_local()),
			patch.object(frappe, "new_doc", return_value=out_doc),
			patch.object(remote_checkin, "employee_now", return_value=attendance_now) as employee_now,
		):
			remote_checkin.submit_late_checkout(
				in_checkin="EMP-CKIN-1",
				checkout_datetime=checkout_datetime.strftime("%Y-%m-%d %H:%M:%S"),
				reason="forgot to check out",
			)
			return employee_now

	def test_accepts_a_time_already_past_in_the_employees_timezone(self):
		"""Malaysian 'ten minutes ago' is still 'the future' on a Dubai clock —
		it must be accepted."""
		employee_now = self._submit(
			checkout_datetime=_kl_now() - datetime.timedelta(minutes=10),
			attendance_now=_kl_now(),
		)
		employee_now.assert_called_with("HR-EMP-001")

	def test_still_rejects_a_genuinely_future_time(self):
		"""The guard must keep working — this is anti-backdating, not a hole."""
		with self.assertRaises(Exception):
			self._submit(
				checkout_datetime=_kl_now() + datetime.timedelta(hours=2),
				attendance_now=_kl_now(),
			)

	def test_dubai_clock_would_have_rejected_the_same_valid_time(self):
		"""Documents the regression: with the old system-clock comparison the
		exact same submission fails."""
		with self.assertRaises(Exception):
			self._submit(
				checkout_datetime=_kl_now() - datetime.timedelta(minutes=10),
				attendance_now=_dubai_now(),
			)


class TestPunchStampsAttendanceClock(unittest.TestCase):
	def test_punch_stamps_employee_timezone_not_site_timezone(self):
		"""The v15.99 landmine: now_datetime() would file a 09:52 Malaysian
		punch as 05:52, breaking shift matching, attendance and OT."""
		from hrms.api import remote_checkin

		db = MagicMock()
		db.get_value.return_value = "staff@example.com"
		session = frappe._dict(user="staff@example.com")
		doc = MagicMock()
		doc.name = "EMP-CKIN-3"

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", session),
			patch.object(frappe, "local", _fresh_local()),
			patch.object(frappe, "new_doc", return_value=doc),
			patch.object(remote_checkin, "employee_now", return_value=_kl_now()) as employee_now,
		):
			remote_checkin.punch(employee="HR-EMP-001", log_type="IN")

		employee_now.assert_called_once_with("HR-EMP-001")
		stamped = doc.update.call_args[0][0]["time"]
		self.assertAlmostEqual(
			(stamped - _dubai_now()).total_seconds(),
			4 * 3600,
			delta=5,
			msg="punch must stamp the employee's wall clock, 4h ahead of the Dubai site clock",
		)


class TestSweeperUsesAttendanceClock(unittest.TestCase):
	"""The 36h abandoned-session cutoff is measured in the employee's zone;
	the SQL prefilter is only a coarse net."""

	def _sweep(self, checkin_age_hours, attendance_now):
		from hrms.utils import checkin_sweeper

		row = {
			"name": "EMP-CKIN-9",
			"employee": "HR-EMP-001",
			"time": attendance_now - datetime.timedelta(hours=checkin_age_hours),
		}
		db = MagicMock()

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "local", _fresh_local()),
			patch.object(frappe, "get_all", return_value=[row]),
			patch.object(checkin_sweeper, "employee_now", return_value=attendance_now),
			patch.object(checkin_sweeper, "now_datetime", return_value=_dubai_now()),
			patch.object(checkin_sweeper, "_has_matching_close", return_value=False),
			patch.object(checkin_sweeper, "_notify_hr"),
		):
			return checkin_sweeper.sweep_stale_ins()

	def test_tags_a_session_stale_in_the_employees_zone(self):
		self.assertEqual(self._sweep(checkin_age_hours=40, attendance_now=_kl_now()), 1)

	def test_leaves_a_session_that_is_not_yet_stale_there(self):
		"""Inside the prefilter net but under 36h on the employee's own clock."""
		self.assertEqual(self._sweep(checkin_age_hours=20, attendance_now=_kl_now()), 0)


class TestBuriedForgottenCheckout(unittest.TestCase):
	"""The reported bug: checking IN the next morning buried yesterday's
	forgotten checkout — the banner (last-log based) vanished and
	submit_late_checkout rejected the session because ANY later OUT counted."""

	def _rows(self, now):
		"""yesterday: IN never closed; today: normal IN+OUT session."""
		yesterday_in = now - datetime.timedelta(days=1, hours=2)
		return [
			frappe._dict(name="CKIN-OLD", time=yesterday_in, log_type="IN", is_abandoned=1),
			frappe._dict(
				name="CKIN-NEW", time=now - datetime.timedelta(hours=8), log_type="IN", is_abandoned=0
			),
			frappe._dict(
				name="CKOUT-NEW", time=now - datetime.timedelta(hours=1), log_type="OUT", is_abandoned=0
			),
		]

	def _unresolved(self, rows, now):
		from hrms.api import remote_checkin

		db = MagicMock()
		db.get_value.return_value = "HR-EMP-001"
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user="staff@example.com")),
			patch.object(frappe, "local", _fresh_local()),
			patch.object(frappe, "get_all", return_value=rows),
			patch.object(remote_checkin, "employee_now", return_value=now),
		):
			return remote_checkin.get_unresolved_stale_in()

	def test_buried_stale_in_is_found_despite_newer_session(self):
		now = _kl_now()
		result = self._unresolved(self._rows(now), now)
		self.assertEqual(result.get("name"), "CKIN-OLD")
		self.assertEqual(result.get("is_abandoned"), 1)

	def test_closed_sessions_are_not_flagged(self):
		now = _kl_now()
		yesterday_in = now - datetime.timedelta(days=1, hours=2)
		rows = [
			frappe._dict(name="CKIN-OLD", time=yesterday_in, log_type="IN", is_abandoned=0),
			frappe._dict(
				name="CKOUT-OLD",
				time=yesterday_in + datetime.timedelta(hours=9),
				log_type="OUT",
				is_abandoned=0,
			),
		]
		self.assertEqual(self._unresolved(rows, now), {})

	def test_fresh_open_in_is_not_flagged(self):
		now = _kl_now()
		rows = [
			frappe._dict(
				name="CKIN-TODAY", time=now - datetime.timedelta(hours=3), log_type="IN", is_abandoned=0
			)
		]
		self.assertEqual(self._unresolved(rows, now), {})

	def test_late_checkout_allowed_when_out_belongs_to_newer_session(self):
		"""submit_late_checkout: today's OUT must not close yesterday's IN."""
		from hrms.api import remote_checkin

		now = _kl_now()
		yesterday_in = now - datetime.timedelta(days=1, hours=4)
		next_in = now - datetime.timedelta(hours=8)

		def get_value(doctype, name, fields=None, **kw):
			if isinstance(name, dict):
				# the next-IN window probe finds today's IN
				return next_in if name.get("log_type") == "IN" else None
			return {
				"Employee Checkin": frappe._dict(
					name="CKIN-OLD",
					employee="HR-EMP-001",
					time=yesterday_in,
					log_type="IN",
					shift="9AM - 6PM",
				),
				"Employee": "staff@example.com",
			}.get(doctype)

		db = MagicMock()
		db.get_value.side_effect = get_value
		captured = {}
		db.exists.side_effect = lambda doctype, filters: captured.update(filters) or None

		out_doc = MagicMock()
		out_doc.name = "CKOUT-LATE"

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user="staff@example.com")),
			patch.object(frappe, "local", _fresh_local()),
			patch.object(frappe, "new_doc", return_value=out_doc),
			patch.object(remote_checkin, "employee_now", return_value=now),
		):
			remote_checkin.submit_late_checkout(
				in_checkin="CKIN-OLD",
				checkout_datetime=(yesterday_in + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
				reason="forgot to check out",
			)

		# the later-OUT probe must be bounded by the next IN, not open-ended
		self.assertEqual(captured["time"][0], "between")
		self.assertLess(captured["time"][1][1], next_in)


if __name__ == "__main__":
	unittest.main()
