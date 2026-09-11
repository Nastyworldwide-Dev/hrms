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

import datetime
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Without a bench (the commit gate's interpreter) frappe and erpnext are
# fabricated; on a bench the real packages win and these are no-ops.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

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

	`recent` is the employee's recent Employee Checkin log, which punch() now
	reads to decide whether an "IN" actually opens a session.

	The whole `frappe` name is swapped inside the module rather than patching
	`frappe.db` — outside a request that is an unbound thread-local proxy and
	cannot be patched at all.
	"""

	def __init__(self, recent=None):
		self._recent = recent

	def __enter__(self):
		self.doc = _FakeDoc()
		recent = self._recent
		# `recent` defaults to an empty log: these cases are about the flags a
		# punch carries, so the employee has no open session and resolve_punch_type
		# passes the requested type through untouched. Cases that DO exercise the
		# alternation rule set it (see TestPunchTypeIsNotTakenOnTrust, and
		# test_an_in_while_a_session_is_open_is_recorded_as_the_check_out below).
		self.recent = list(recent or [])
		stub = SimpleNamespace(
			db=SimpleNamespace(get_value=lambda *args, **kwargs: USER),
			session=SimpleNamespace(user=USER),
			new_doc=lambda doctype: self.doc,
			get_all=lambda *args, **kwargs: self.recent,
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


# ---------------------------------------------------------------------------
# submit_late_checkout: the "next check-in" bound must be a GENUINE later punch
# ---------------------------------------------------------------------------
#
# HR reported that resolving a forgotten check-out was impossible: with the
# original IN at 08:55:44 and an entered OUT of 18:01 the form said
#
#     Check-out time must be before your next check-in (2026-09-01 08:55:44).
#
# The "next check-in" it named was the very record being resolved, so the rule
# collapsed to "check-out must be before check-in" — unsatisfiable. The lookup
# bounded the window by timestamp alone; it never said "and not this record".
#
# Pinned here, through the public whitelisted seam with a small fake of the
# rows the query touches:
#
#   * the next-IN lookup excludes the originating check-in BY NAME;
#   * with no later IN there is no upper bound beyond "not in the future";
#   * with a later IN the check-out must fall strictly between the two, and the
#     error names that later punch (its record and its time), never the original.
#
# Bench-free: frappe.db is replaced by an in-memory row matcher, and frappe
# itself is stubbed when no bench is on the path (hrms/tests/_frappe_stub.py).
# Run as a FILE with either interpreter:
#
#     PYTHONPATH=. python3 hrms/tests/test_remote_checkin.py


LC_EMPLOYEE = "HR-EMP-001"
LC_USER = "staff@example.com"
ORIGINAL_IN = "EMP-CKIN-ORIG"
LATER_IN = "EMP-CKIN-NEXT"


def _fresh_local():
	local = types.SimpleNamespace()
	local.flags = frappe._dict(in_test=False)
	return local


def _throw(msg, exc=Exception, *args, **kwargs):
	"""frappe.throw needs a bound request context to build its message log;
	here the message itself is the subject, so raise it plainly."""
	raise exc(msg)


class _FakeCheckinDB:
	"""Just enough of frappe.db to answer submit_late_checkout's queries from
	a list of Employee Checkin rows. Comparisons are exact — the fake does not
	reproduce any precision quirk; it exists so the FILTERS the code sends can
	be asserted and so the three acceptance cases run without a bench."""

	def __init__(self, rows):
		self.rows = [frappe._dict(r) for r in rows]
		self.next_in_lookups = []

	@staticmethod
	def _match(row, filters):
		for key, cond in filters.items():
			actual = row.get(key)
			if isinstance(cond, list | tuple):
				op, val = cond
				if op == "!=":
					ok = actual != val
				elif op == ">":
					ok = actual is not None and actual > val
				elif op == ">=":
					ok = actual is not None and actual >= val
				elif op == "<":
					ok = actual is not None and actual < val
				elif op == "between":
					ok = actual is not None and val[0] <= actual <= val[1]
				elif op == "is":
					ok = (actual is None) if val == "not set" else (actual is not None)
				else:
					raise AssertionError(f"fake db does not model operator {op!r}")
			else:
				ok = actual == cond
			if not ok:
				return False
		return True

	def _select(self, filters, order_by=None):
		rows = [r for r in self.rows if self._match(r, filters)]
		if order_by:
			field, _, direction = order_by.partition(" ")
			rows.sort(key=lambda r: r[field], reverse=direction.strip().lower() == "desc")
		return rows

	def get_value(self, doctype, name=None, fieldname=None, as_dict=False, order_by=None, **kw):
		if doctype == "Employee":
			return LC_USER
		if doctype != "Employee Checkin":
			return None  # the post-insert request lookup; not under test here
		if isinstance(name, dict):
			if name.get("log_type") == "IN":
				self.next_in_lookups.append(dict(name))
			rows = self._select(name, order_by)
			if not rows:
				return None
			row = rows[0]
		else:
			row = next((r for r in self.rows if r.name == name), None)
			if row is None:
				return None
		if as_dict:
			return frappe._dict(row)
		if isinstance(fieldname, list | tuple):
			return tuple(row.get(f) for f in fieldname)
		return row.get(fieldname)

	def exists(self, doctype, filters=None, **kw):
		if doctype == "Employee Checkin" and isinstance(filters, dict):
			rows = self._select(filters)
			return rows[0].name if rows else None
		return None


class TestLateCheckoutNextCheckinBound(unittest.TestCase):
	def setUp(self):
		self.in_time = datetime.datetime(2026, 9, 1, 8, 55, 44)
		self.now = self.in_time + datetime.timedelta(days=3)

	def _row(self, name, log_type, time, **extra):
		return {
			"name": name,
			"employee": LC_EMPLOYEE,
			"log_type": log_type,
			"time": time,
			"shift": "9AM - 6PM",
			"remote_approval_status": None,
			**extra,
		}

	def _submit(self, rows, checkout_time):
		from hrms.api import remote_checkin

		db = _FakeCheckinDB(rows)
		out_doc = MagicMock()
		out_doc.name = "EMP-CKIN-OUT"
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user=LC_USER)),
			patch.object(frappe, "local", _fresh_local()),
			patch.object(frappe, "new_doc", return_value=out_doc),
			patch.object(frappe, "throw", side_effect=_throw),
			patch.object(remote_checkin, "employee_now", return_value=self.now),
		):
			remote_checkin.submit_late_checkout(
				in_checkin=ORIGINAL_IN,
				checkout_datetime=checkout_time.strftime("%Y-%m-%d %H:%M:%S"),
				reason="forgot to check out",
			)
		return db, out_doc

	def test_next_checkin_lookup_excludes_the_originating_record_by_name(self):
		"""The reported defect: the window was bounded by timestamp alone, so
		the record being resolved could come back as its own 'next check-in'."""
		db, _ = self._submit(
			[self._row(ORIGINAL_IN, "IN", self.in_time)],
			self.in_time + datetime.timedelta(hours=9),
		)
		self.assertTrue(db.next_in_lookups, "expected a next-check-in lookup")
		lookup = db.next_in_lookups[0]
		self.assertEqual(
			lookup.get("name"),
			["!=", ORIGINAL_IN],
			"the next-check-in lookup must exclude the originating check-in by name, "
			f"not by timestamp alone — got filters {lookup}",
		)

	def test_no_later_checkin_means_no_upper_bound(self):
		"""An unclosed session with no later punch accepts ANY time after the IN."""
		_, out_doc = self._submit(
			[self._row(ORIGINAL_IN, "IN", self.in_time)],
			self.in_time + datetime.timedelta(hours=15, minutes=30),  # 00:25 next day
		)
		out_doc.insert.assert_called_once()

	def test_checkout_between_in_and_a_genuine_later_checkin_is_accepted(self):
		later = self.in_time + datetime.timedelta(days=1)
		_, out_doc = self._submit(
			[self._row(ORIGINAL_IN, "IN", self.in_time), self._row(LATER_IN, "IN", later)],
			self.in_time + datetime.timedelta(hours=9, minutes=6),  # 18:01
		)
		out_doc.insert.assert_called_once()

	def test_a_duplicate_punch_seconds_later_is_not_the_next_checkin(self):
		"""What the phone actually showed: "next check-in (2026-09-01 08:55:44)"
		for an IN displayed as 08:55 — a second IN row in the same minute, a
		double tap or a retried request, not a new session. It must not bound
		the window; the check-out at 18:01 is accepted."""
		duplicate = self.in_time + datetime.timedelta(seconds=20)
		_, out_doc = self._submit(
			[self._row(ORIGINAL_IN, "IN", self.in_time), self._row("EMP-CKIN-DUP", "IN", duplicate)],
			self.in_time + datetime.timedelta(hours=9, minutes=6),  # 18:01
		)
		out_doc.insert.assert_called_once()

	def test_a_duplicate_punch_MINUTES_later_is_not_the_next_checkin(self):
		"""Production, 7 Sep: a real IN at 09:08 and a second IN at 09:18:53 with
		NO OUT between them. The employee could never file a late check-out —
		"Check-out time must be before your next check-in EMP-CKIN-09-2026-000640
		at 2026-09-07 09:18:53."

		The old rule was a 60-SECOND window, so a duplicate 10m53s later sailed
		past it. No constant can be right here: what makes a later IN the start
		of a NEW session is not how long after it lands, it is whether an OUT
		separates it from this one. With no intervening OUT it is the same open
		session however late it arrives."""
		duplicate = self.in_time + datetime.timedelta(minutes=10, seconds=53)
		_, out_doc = self._submit(
			[self._row(ORIGINAL_IN, "IN", self.in_time), self._row("EMP-CKIN-DUP", "IN", duplicate)],
			self.in_time + datetime.timedelta(hours=9, minutes=6),  # 18:01
		)
		out_doc.insert.assert_called_once()

	def test_an_in_after_an_intervening_out_IS_the_next_checkin(self):
		"""The other side of the same rule: once an OUT closes the session, the
		next IN genuinely starts a new one and must bound the window."""
		out_at = self.in_time + datetime.timedelta(hours=4)
		second_in = self.in_time + datetime.timedelta(hours=5)
		rows = [
			self._row(ORIGINAL_IN, "IN", self.in_time),
			self._row("EMP-CKIN-MIDOUT", "OUT", out_at),
			self._row(LATER_IN, "IN", second_in),
		]
		with self.assertRaises(Exception) as caught:
			self._submit(rows, self.in_time + datetime.timedelta(hours=9))
		self.assertIn(LATER_IN, str(caught.exception))

	def test_checkout_at_or_after_the_later_checkin_is_rejected_and_names_that_punch(self):
		later = self.in_time + datetime.timedelta(days=1)
		rows = [self._row(ORIGINAL_IN, "IN", self.in_time), self._row(LATER_IN, "IN", later)]
		for attempt in (later, later + datetime.timedelta(minutes=1)):
			with self.assertRaises(Exception) as ctx:
				self._submit(rows, attempt)
			message = str(ctx.exception)
			self.assertIn(LATER_IN, message, "the error must name the genuine later punch")
			self.assertIn(str(later), message)
			self.assertNotIn(
				str(self.in_time),
				message,
				"the error must never present the originating check-in as the next one",
			)


class TestPunchCarriesFixQuality(unittest.TestCase):
	"""How old the fix was and which provider gave it travel with the punch."""

	def test_fix_age_and_a_gps_source_land_on_the_flags(self):
		with _PunchHarness() as h:
			remote_checkin.punch(
				EMPLOYEE, "IN", latitude=3.1, longitude=101.6, accuracy=12, fix_age_s="4", source="high"
			)
		self.assertEqual(h.doc.flags.location_fix_age_s, 4)
		self.assertEqual(h.doc.flags.location_source, "GPS")

	def test_a_coarse_fallback_is_named_network(self):
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, source="coarse")
		self.assertEqual(h.doc.flags.location_source, "Network")

	def test_junk_is_dropped_not_carried(self):
		with _PunchHarness() as h:
			remote_checkin.punch(
				EMPLOYEE, "IN", latitude=3.1, longitude=101.6, fix_age_s="soon", source="magic"
			)
		self.assertIsNone(getattr(h.doc.flags, "location_fix_age_s", None))
		self.assertEqual(getattr(h.doc.flags, "location_source", None), "Unknown")


class TestPunchHonoursTheResolvedType(unittest.TestCase):
	"""The rule is wired into punch(), not merely available beside it."""

	def test_an_in_while_a_session_is_open_is_recorded_as_the_check_out(self):
		open_in = frappe._dict(
			{
				"name": "EMP-CKIN-OPEN",
				"log_type": "IN",
				"time": datetime.datetime(2026, 8, 24, 8, 51),
				"is_abandoned": 0,
				"remote_approval_status": None,
			}
		)
		with _PunchHarness(recent=[open_in]) as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6)
		self.assertEqual(
			h.doc.log_type,
			"OUT",
			"a second IN inside a live session must be stored as the check-out it is",
		)
		self.assertTrue(h.doc.inserted, "the punch is still recorded — never dropped")

	def test_a_first_in_is_stored_as_an_in(self):
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6)
		self.assertEqual(h.doc.log_type, "IN")


class TestPunchTypeIsNotTakenOnTrust(unittest.TestCase):
	"""The server, not the phone, decides whether a punch opens or closes a session.

	`log_type` was chosen entirely by the browser and accepted unverified.
	CheckInPanel's nextAction defaults to "IN" whenever it cannot see a prior
	punch, and it recomputes while the confirm sheet is open — so a user who
	read "Check Out" could submit an IN. Production shows exactly that: Ahmad
	Fazwan's log carries IN 08:51 and IN 18:31 on one day with no OUT between,
	and on 7 Sep an IN at 09:08 and another at 09:18.

	The consequences are not cosmetic. An IN with no OUT is 0 working hours and
	a Half Day. On an employee who also holds a night-shift assignment the
	18:3x IN resolves to the 7PM shift instead, splitting the day into two
	attendance rows. And a duplicate IN blocks the late-check-out that would
	have fixed it.

	A second IN inside a LIVE session is not a thing that can happen: you
	cannot arrive twice without leaving. So it is read as the departure it
	must be — never guessed, never applied to a session that has already gone
	stale or been swept as abandoned, where a genuine new IN is correct.
	"""

	def setUp(self):
		from hrms.api import remote_checkin

		self.mod = remote_checkin
		self.day = datetime.datetime(2026, 9, 9)

	def at(self, hour, minute=0):
		return self.day.replace(hour=hour, minute=minute)

	def row(self, log_type, when, **extra):
		return frappe._dict(
			{"name": f"CK-{log_type}-{when:%H%M}", "log_type": log_type, "time": when, **extra}
		)

	def test_a_second_in_inside_a_live_session_is_the_check_out(self):
		rows = [self.row("IN", self.at(8, 51))]
		resolved, closing = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "OUT")
		self.assertEqual(closing.name, "CK-IN-0851")

	def test_a_duplicate_in_minutes_later_is_the_check_out_too(self):
		"""7 Sep: IN 09:08 then IN 09:18. The second one must not open a session."""
		rows = [self.row("IN", self.at(9, 8))]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(9, 18))
		self.assertEqual(resolved, "OUT")

	def test_the_first_in_of_the_day_opens_a_session(self):
		resolved, closing = self.mod.resolve_punch_type([], "IN", self.at(8, 51))
		self.assertEqual(resolved, "IN")
		self.assertIsNone(closing)

	def test_an_in_after_a_closed_session_opens_a_new_one(self):
		rows = [self.row("IN", self.at(8, 51)), self.row("OUT", self.at(12, 0))]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(13, 0))
		self.assertEqual(resolved, "IN")

	def test_an_in_after_a_stale_session_opens_a_new_one(self):
		"""Yesterday's forgotten check-out must not turn this morning's arrival
		into a check-out — that is the mirror mistake, and it would silently
		close a session the employee never worked."""
		rows = [self.row("IN", self.at(8, 51) - datetime.timedelta(days=1))]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(8, 51))
		self.assertEqual(resolved, "IN")

	def test_an_abandoned_session_never_swallows_a_new_check_in(self):
		rows = [self.row("IN", self.at(8, 51), is_abandoned=1)]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "IN")

	def test_a_rejected_late_checkout_does_not_close_the_session(self):
		rows = [
			self.row("IN", self.at(8, 51)),
			self.row("OUT", self.at(12, 0), remote_approval_status="Rejected"),
		]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "OUT", "a rejected OUT leaves the session open")

	def test_an_explicit_check_out_is_never_rewritten(self):
		rows = [self.row("IN", self.at(8, 51))]
		resolved, _ = self.mod.resolve_punch_type(rows, "OUT", self.at(18, 31))
		self.assertEqual(resolved, "OUT")


if __name__ == "__main__":
	unittest.main()
