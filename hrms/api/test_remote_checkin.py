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
			comments=[],
			flags=SimpleNamespace(),
			inserted=False,
		)

	def update(self, values):
		for key, value in values.items():
			setattr(self, key, value)

	def insert(self):
		self.inserted = True

	def add_comment(self, comment_type, text):
		self.comments.append((comment_type, text))


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

	def _get_all(self, doctype, filters=None, fields=None, order_by=None, limit=None, **kw):
		"""Honours order_by and limit, because the defect this models is a
		TRUNCATION: `time asc` with a limit keeps the oldest rows and drops the
		newest, which are the ones that say whether a session is open."""
		self.get_all_calls.append({"order_by": order_by, "limit": limit})
		rows = sorted(self.recent, key=lambda r: r["time"], reverse=(order_by or "").endswith("desc"))
		return rows[:limit] if limit else rows

	def __enter__(self):
		self.doc = _FakeDoc()
		recent = self._recent
		# `recent` defaults to an empty log: these cases are about the flags a
		# punch carries, so the employee has no open session and resolve_punch_type
		# passes the requested type through untouched. Cases that DO exercise the
		# alternation rule set it (see TestPunchTypeIsNotTakenOnTrust, and
		# test_an_in_while_a_session_is_open_is_recorded_as_the_check_out below).
		self.recent = list(recent or [])
		self.get_all_calls = []
		stub = SimpleNamespace(
			db=SimpleNamespace(get_value=lambda *args, **kwargs: USER),
			session=SimpleNamespace(user=USER),
			new_doc=lambda doctype: self.doc,
			get_all=self._get_all,
			conf={},
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
		# The correction must not be silent. HR reading Employee Checkin has to
		# be able to tell a server-corrected OUT from a hand-tapped one, and a
		# disputed hour cannot rest on an application log that rotates.
		self.assertTrue(h.doc.comments, "a coerced punch must carry a durable trace")
		kind, text = h.doc.comments[0]
		self.assertEqual(kind, "Info")
		self.assertIn("EMP-CKIN-OPEN", text, "the trace must name the session that was open")

	def test_an_uncoerced_punch_carries_no_comment(self):
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6)
		self.assertEqual(h.doc.comments, [], "an ordinary punch is not annotated")

	def test_a_busy_log_does_not_truncate_away_the_open_session(self):
		"""The lookup is capped at 100 rows. Ordered ASCENDING that cap keeps the
		OLDEST punches and throws away the newest — so on a busy log the open IN
		would vanish from the rule's view and every duplicate would sail through,
		silently, exactly for the people punching most often."""
		base = datetime.datetime(2026, 8, 22, 6, 0)
		filler = [
			frappe._dict(
				{
					"name": f"CK-OLD-{i}",
					"log_type": "IN" if i % 2 == 0 else "OUT",
					"time": base + datetime.timedelta(minutes=i),
					"is_abandoned": 0,
					"remote_approval_status": None,
				}
			)
			for i in range(200)
		]
		open_in = frappe._dict(
			{
				"name": "EMP-CKIN-OPEN",
				"log_type": "IN",
				"time": datetime.datetime(2026, 8, 24, 8, 51),
				"is_abandoned": 0,
				"remote_approval_status": None,
			}
		)
		with _PunchHarness(recent=[*filler, open_in]) as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6)
		self.assertTrue(
			h.get_all_calls and h.get_all_calls[0]["order_by"].endswith("desc"),
			"the recent-log lookup must take the NEWEST rows, not the oldest",
		)
		self.assertEqual(h.doc.log_type, "OUT")

	def test_a_first_in_is_stored_as_an_in(self):
		with _PunchHarness() as h:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6)
		self.assertEqual(h.doc.log_type, "IN")


class TestLateCheckoutSessionBoundary(unittest.TestCase):
	"""Which later check-in counts as the NEXT session's, and therefore bounds a
	late check-out.

	The boundary used to be calendar midnight, which is correct for a shift that
	lives inside one date and wrong for every shift that crosses one. On a
	19:00-03:30 shift midnight lands in the middle of the session, so a spurious
	punch just after it was read as the next arrival and bounded the window at
	itself — and the employee was told their check-out "must be before your next
	check-in at 00:05", with no time they could enter that would be accepted.
	"""

	def setUp(self):
		from hrms.api import remote_checkin

		self.boundary = remote_checkin.session_boundary
		self.mon = datetime.datetime(2026, 9, 7)

	def at(self, day_offset, hour, minute=0):
		return self.mon + datetime.timedelta(days=day_offset, hours=hour, minutes=minute)

	def test_a_night_shift_turns_over_after_it_ends_not_at_midnight(self):
		"""The reported defect. IN 19:00, the shift runs to 03:30 with grace to
		05:00, so a punch at 00:05 is inside this session and must not bound it."""
		got = self.boundary(self.at(0, 19), self.at(1, 5), None)
		self.assertEqual(got, self.at(1, 5))
		self.assertGreater(got, self.at(1, 0, 5), "00:05 must fall INSIDE the session")

	def test_a_shift_whose_grace_closes_before_midnight_keeps_its_old_boundary(self):
		"""No regression for the shift that was always handled correctly: its
		own window closes before midnight, so midnight still wins."""
		self.assertEqual(self.boundary(self.at(0, 9), self.at(0, 19), None), self.at(1, 0))

	def test_an_evening_shift_whose_GRACE_crosses_midnight_moves_too(self):
		"""Stated because the first version of this claimed "a day shift keeps
		exactly the boundary it had", and that is not true.

		An evening shift ending 23:30, with the default hour of
		allow_check_out_after_shift_end_time, closes at 00:30 — so its boundary
		moves by that half hour. It is the same rule applied honestly: that
		session really does run past midnight, and the old boundary cut it off
		thirty minutes early. Pinned so nobody "restores" the day-shift case by
		flooring everything at midnight."""
		self.assertEqual(self.boundary(self.at(0, 14), self.at(1, 0, 30), None), self.at(1, 0, 30))

	def test_a_punch_with_no_shift_falls_back_to_the_calendar(self):
		"""Off-shift, or an assignment that no longer resolves: the calendar is
		all the evidence there is."""
		self.assertEqual(self.boundary(self.at(0, 9), None, None), self.at(1, 0))

	def test_a_real_check_out_closes_the_session_before_its_shift_would(self):
		"""An OUT is exact evidence and beats the shift window."""
		self.assertEqual(self.boundary(self.at(0, 19), self.at(1, 5), self.at(1, 3, 30)), self.at(1, 3, 30))

	def test_a_check_out_after_the_shift_window_does_not_extend_the_session(self):
		"""min(), not max(): a stray OUT belonging to a later session must not
		widen this one."""
		self.assertEqual(self.boundary(self.at(0, 19), self.at(1, 5), self.at(1, 9)), self.at(1, 5))

	def test_the_shift_close_is_accepted_as_a_string(self):
		"""It arrives straight off the database row, which hands back strings on
		some paths and datetimes on others."""
		self.assertEqual(self.boundary(self.at(0, 19), "2026-09-08 05:00:00", None), self.at(1, 5))


class TestALateCheckOutNeverLeavesTwoDepartures(unittest.TestCase):
	"""What separates a buried repair from a duplicate check-out.

	The two shapes are IDENTICAL in time order — an IN, another IN, an OUT — so
	no boundary drawn anywhere can tell them apart, and two attempts to do it
	with one traded places: the first blocked the legitimate repair, the second
	admitted the corrupting one and let a worker put two check-outs on a single
	session. The app's own "Forgot to check out?" banner offers that session, so
	an ordinary user was walked straight into it.

	What does separate them is the sequence AFTERWARDS. Filing an OUT into a
	session that was already closed leaves two departures adjacent with no
	arrival between — impossible, and the mirror of the rule the punch-type
	correction already enforces at the other end.
	"""

	def setUp(self):
		from hrms.api import remote_checkin

		self.check = remote_checkin.leaves_consecutive_outs
		self.day = datetime.datetime(2026, 9, 7)

	def at(self, hour, minute=0, day_offset=0):
		return self.day + datetime.timedelta(days=day_offset, hours=hour, minutes=minute)

	def row(self, log_type, when, **extra):
		return {"name": f"CK-{log_type}-{when:%d%H%M}", "log_type": log_type, "time": when, **extra}

	def test_a_plain_forgotten_check_out_is_allowed(self):
		seq = [self.row("IN", self.at(9))]
		self.assertFalse(self.check(seq, self.at(18)))

	def test_a_buried_repair_before_a_genuinely_new_session_is_allowed(self):
		"""IN 19:00 forgotten; a real new session 01:00-02:00 after it. An OUT at
		00:30 closes the first and leaves the second intact."""
		seq = [
			self.row("IN", self.at(19)),
			self.row("IN", self.at(1, day_offset=1)),
			self.row("OUT", self.at(2, day_offset=1)),
		]
		self.assertFalse(self.check(seq, self.at(0, 30, day_offset=1)))

	def test_a_second_check_out_on_a_closed_session_is_refused(self):
		"""The production shape: IN 09:08 with a stray 09:18 double tap, closed
		normally at 18:00. An OUT at 12:08 would be the session's SECOND."""
		seq = [
			self.row("IN", self.at(9, 8)),
			self.row("IN", self.at(9, 18)),
			self.row("OUT", self.at(18)),
		]
		self.assertTrue(self.check(seq, self.at(12, 8)))

	def test_the_same_refusal_holds_on_a_night_shift(self):
		"""Not a day-shift quirk: IN 19:00, stray IN 00:05, closed 03:30."""
		seq = [
			self.row("IN", self.at(19)),
			self.row("IN", self.at(0, 5, day_offset=1)),
			self.row("OUT", self.at(3, 30, day_offset=1)),
		]
		self.assertTrue(self.check(seq, self.at(2, day_offset=1)))

	def test_a_rejected_late_check_out_never_closed_anything(self):
		"""Which is what lets somebody resubmit a corrected time after a refusal."""
		seq = [
			self.row("IN", self.at(9)),
			self.row("OUT", self.at(17), remote_approval_status="Rejected"),
		]
		self.assertFalse(self.check(seq, self.at(18)))

	def test_an_untyped_row_in_the_sequence_is_ignored_not_guessed(self):
		seq = [self.row("IN", self.at(9)), self.row("", self.at(10))]
		self.assertFalse(self.check(seq, self.at(18)))

	def test_an_in_at_the_same_instant_orders_before_the_proposed_out(self):
		"""An arrival cannot follow its own departure — the same tie-break the
		punch-type rule uses, so the two cannot disagree about one second.

		The shape matters: with an OUT and an IN at the SAME instant before the
		filed time, the tie-break decides which of them ends up next to it.
		Sorting the arrival first leaves the 12:00 departure adjacent to the
		13:00 one, so the filing is a second check-out and is refused. Invert the
		key and the arrival slides in between, and it is wrongly allowed. The
		simpler [IN, IN] version of this test was vacuous — it passed either way,
		which a mutation of the sort key proved."""
		seq = [self.row("IN", self.at(9)), self.row("OUT", self.at(12)), self.row("IN", self.at(12))]
		self.assertTrue(self.check(seq, self.at(13)))

	def test_a_pre_existing_pair_elsewhere_does_not_block_an_earlier_repair(self):
		"""This row must not answer for damage it did not cause.

		A log that ALREADY carries two adjacent check-outs — the damage an
		earlier version of this very rule could produce, and what the hub leaves
		behind when one punch is pulled twice — would, under a whole-sequence
		scan, block the repair of an unrelated EARLIER session, with a message
		about a check-out that has nothing to do with it. Only the neighbours of
		the row being inserted are its business."""
		seq = [
			self.row("IN", self.at(9)),
			self.row("IN", self.at(9, day_offset=1)),
			self.row("OUT", self.at(12, day_offset=1)),
			self.row("OUT", self.at(18, day_offset=1)),
		]
		self.assertFalse(self.check(seq, self.at(12)))

	def test_an_out_at_the_same_instant_as_an_existing_one_is_still_a_duplicate(self):
		"""before_validate truncates to whole seconds, so a retried submission
		can land on the same second as the OUT it is retrying. That is a second
		departure however close it is."""
		seq = [self.row("IN", self.at(9)), self.row("OUT", self.at(17))]
		self.assertTrue(self.check(seq, self.at(17)))


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

	def test_an_untyped_row_stops_the_coercion(self):
		"""log_type is an OPTIONAL Select with a blank first option, and untyped
		rows are real here — hrms/sync/checkin_recovery.py exists to infer them.
		With one untyped punch between an IN and its OUT, the pairing walk reads
		a CLOSED session as open, so a genuine second-session arrival would be
		written as its check-out: the evening block never opens and those hours
		are lost, behind a row that looks perfectly ordinary.

		Incomplete evidence is not a licence to guess. When the window contains
		anything that is not IN or OUT, the requested type stands."""
		rows = [
			self.row("IN", self.at(8, 0)),
			self.row("", self.at(9, 0)),
			self.row("OUT", self.at(17, 0)),
		]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(18, 0))
		self.assertEqual(resolved, "IN", "an untyped row makes the session unreadable — do not coerce")

	def test_a_null_typed_row_stops_the_coercion_too(self):
		rows = [self.row("IN", self.at(8, 0)), self.row(None, self.at(9, 0))]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(18, 0))
		self.assertEqual(resolved, "IN")

	def test_a_punch_before_06_00_with_no_shift_evidence_is_not_coerced(self):
		"""The 06:00 cutoff was written for a READ — should the banner offer to
		resolve? A false "live" there costs a banner. Reused for a WRITE it
		destroys a real arrival: someone on an early shift who forgot yesterday's
		check-out has their 05:30 arrival silently recorded as yesterday's
		departure, and every detector then reads the day as healthy. With no
		shift window on the open row there is nothing to distinguish the two, so
		the row the user asked for stands."""
		rows = [self.row("IN", self.at(21, 0) - datetime.timedelta(days=1))]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(5, 30))
		self.assertEqual(resolved, "IN")

	def test_a_night_shift_is_protected_through_its_own_small_hours(self):
		"""The band left night shifts unguarded for the BACK HALF of their shift.

		A 19:00-03:30 worker who double-taps at 02:00 is inside their own shift,
		and the second tap is the same impossible event the rule exists to catch
		— nobody arrives twice without leaving. The blanket cutoff let it through
		anyway, so the very shape being corrected during the day came straight
		back after midnight, on the people whose shift lives there.

		The open row's OWN shift window is what separates this from the early
		arrival above: here the session is still running, there it ended hours
		ago."""
		rows = [
			self.row(
				"IN",
				self.at(19, 0) - datetime.timedelta(days=1),
				shift_actual_end=self.at(5, 0),
			)
		]
		resolved, closing = self.mod.resolve_punch_type(rows, "IN", self.at(2, 0))
		self.assertEqual(resolved, "OUT", "02:00 is inside a shift that runs to 05:00")
		self.assertIsNotNone(closing)

	def test_an_early_arrival_is_still_safe_when_the_old_shift_has_ended(self):
		"""The case the band was written for, now decided on evidence instead of
		on the clock: yesterday's day shift closed at 19:00, so a 05:30 arrival
		cannot belong to it and must be recorded as the arrival it is."""
		rows = [
			self.row(
				"IN",
				self.at(9, 0) - datetime.timedelta(days=1),
				shift_actual_end=self.at(19, 0) - datetime.timedelta(days=1),
			)
		]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(5, 30))
		self.assertEqual(resolved, "IN", "that shift ended 10 hours ago — this is a new day")

	def test_a_punch_after_06_00_does_not_need_shift_evidence(self):
		"""Outside the band nothing changed: the ordinary daytime duplicate is
		still coerced with no shift window on the row at all."""
		rows = [self.row("IN", self.at(8, 51))]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "OUT")

	def test_a_mirrored_open_session_does_not_coerce(self):
		"""A session pulled from the source instance can never be tagged
		abandoned here — the sweeper deliberately skips mirrored rows, single
		writer — so it would coerce local punches for up to 30h with nothing
		able to clear it. Scoped the same way the sweeper scopes itself."""
		rows = [self.row("IN", self.at(8, 51), synced_from_instance="NASTY")]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "IN")

	def test_a_closed_session_is_not_reopened_by_an_earlier_orphan(self):
		"""The rule must not make an already-damaged log worse.

		This is the log of somebody the defect has ALREADY hit: a stray IN at
		08:00, the real arrival at 09:00, and a genuine OUT at 12:00 that closed
		it. The session is closed — the last thing that happened was a
		departure. A second-session arrival at 14:00 is exactly what it says.

		The walk used to scan for "an IN whose next row is not an OUT", which on
		this log is the 08:00 ORPHAN, two rows back and long dead. It would have
		written the 14:00 arrival as a check-out of that orphan: a phantom
		six-hour block that nobody worked appears, and the real afternoon never
		opens. The rule would have been manufacturing hours on precisely the
		employees it exists to protect."""
		rows = [
			self.row("IN", self.at(8, 0)),
			self.row("IN", self.at(9, 0)),
			self.row("OUT", self.at(12, 0)),
		]
		resolved, closing = self.mod.resolve_punch_type(rows, "IN", self.at(14, 0))
		self.assertEqual(resolved, "IN", "the 12:00 OUT closed the session; 14:00 opens a new one")
		self.assertIsNone(closing)

	def test_a_trailing_out_closes_the_session_however_many_ins_precede_it(self):
		"""Same boundary, stated as the invariant rather than the incident: what
		decides whether a session is open is the LAST thing in the window, not
		the shape of the rows before it."""
		rows = [
			self.row("IN", self.at(7, 0)),
			self.row("IN", self.at(8, 0)),
			self.row("IN", self.at(9, 0)),
			self.row("OUT", self.at(17, 0)),
		]
		resolved, closing = self.mod.resolve_punch_type(rows, "IN", self.at(18, 0))
		self.assertEqual(resolved, "IN")
		self.assertIsNone(closing)

	def test_a_trailing_in_is_still_the_open_session(self):
		"""And the other side: a damaged log whose last row IS an IN is open,
		and the newest of those INs is the one a check-out closes."""
		rows = [
			self.row("IN", self.at(8, 0)),
			self.row("OUT", self.at(12, 0)),
			self.row("IN", self.at(13, 0)),
		]
		resolved, closing = self.mod.resolve_punch_type(rows, "IN", self.at(18, 0))
		self.assertEqual(resolved, "OUT")
		self.assertEqual(closing.name, "CK-IN-1300")

	def test_a_mirrored_untyped_row_does_not_stop_the_coercion(self):
		"""The untyped guard and the mirrored filter answer the same question in
		the wrong order.

		A mirrored row is ALREADY excluded from the pairing walk — deliberately,
		because a session pulled from the source instance can never be tagged
		abandoned here. So a mirrored row that also happens to be untyped tells
		the walk nothing it was going to read anyway. But the untyped guard runs
		over the raw window BEFORE the mirrored filter is applied, so one such
		row silently disables the correction for that employee for the whole
		three-day window, and the duplicate INs come back with no signal to any
		operator that protection is off.

		The guard must ask its question about the rows the walk will actually
		read."""
		rows = [
			self.row("IN", self.at(8, 51)),
			self.row("", self.at(10, 0), synced_from_instance="NASTY"),
		]
		resolved, closing = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(
			resolved,
			"OUT",
			"the untyped row is mirrored, so the walk already ignores it — it must not "
			"also switch the whole rule off",
		)
		self.assertIsNotNone(closing, "the 08:51 session is the one being closed")

	def test_a_local_untyped_row_still_stops_the_coercion(self):
		"""The other side of the same boundary: a LOCAL untyped row is one the
		walk would have read, so it genuinely makes the session unreadable and
		the requested type must stand. Pinned beside its sibling so a future
		reordering cannot quietly widen the exemption."""
		rows = [
			self.row("IN", self.at(8, 51)),
			self.row("", self.at(10, 0)),
		]
		resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "IN")

	def test_a_rejected_untyped_out_does_not_stop_the_coercion(self):
		"""Same ordering, the other excluded shape: a rejected late-OUT never
		closed its session and the walk drops it, so an untyped one must not
		disable the rule either."""
		rows = [
			self.row("IN", self.at(8, 51)),
			self.row("OUT", self.at(10, 0), remote_approval_status="Rejected"),
		]
		resolved, closing = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "OUT")
		self.assertIsNotNone(closing)

	def test_an_in_and_an_out_at_the_same_second_resolve_deterministically(self):
		"""before_validate truncates to whole seconds and validate_duplicate_log
		filters ON log_type, so an IN and an OUT at the identical second both
		insert. Sorting by time alone left the winner to whatever order MariaDB
		returned."""
		same = self.at(12, 0)
		forward = [self.row("IN", self.at(8, 0)), self.row("IN", same), self.row("OUT", same)]
		backward = [self.row("IN", self.at(8, 0)), self.row("OUT", same), self.row("IN", same)]
		self.assertEqual(
			self.mod.resolve_punch_type(forward, "IN", self.at(18, 0))[0],
			self.mod.resolve_punch_type(backward, "IN", self.at(18, 0))[0],
			"row order from the database must not decide the answer",
		)

	def test_the_site_config_kill_switch_restores_the_old_behaviour(self):
		"""One flag, no migration, no redeploy: site_config
		`disable_punch_type_correction` turns this rule off entirely. This is the
		only change in its batch that WRITES different data than before, so the
		remedy for a misread has to be cheaper than rolling back a stack of
		commits while people are trying to clock in."""
		rows = [self.row("IN", self.at(8, 51))]
		with patch.object(frappe, "conf", {"disable_punch_type_correction": 1}):
			resolved, closing = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "IN")
		self.assertIsNone(closing)

	def test_the_rule_is_on_by_default(self):
		rows = [self.row("IN", self.at(8, 51))]
		with patch.object(frappe, "conf", {}):
			resolved, _ = self.mod.resolve_punch_type(rows, "IN", self.at(18, 31))
		self.assertEqual(resolved, "OUT")

	def test_an_explicit_check_out_is_never_rewritten(self):
		rows = [self.row("IN", self.at(8, 51))]
		resolved, _ = self.mod.resolve_punch_type(rows, "OUT", self.at(18, 31))
		self.assertEqual(resolved, "OUT")


if __name__ == "__main__":
	unittest.main()
