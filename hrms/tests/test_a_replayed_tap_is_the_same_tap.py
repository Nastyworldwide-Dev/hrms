"""A retry after a lost response is the same tap, not a new one.

The phone taps IN at 09:00; the server stores it; the 200 never reaches the
phone. The phone shows "Check In" again, the employee taps at 09:02, and the
server — seeing an open IN — records that second tap as the OUT. The day is
two minutes long. The employee did everything right (audit E-H2, 21 Sep 2026).

The cure is an idempotency key on the tap itself: the phone generates a
`client_tap_id` per INTENDED tap and keeps sending the same one until a 2xx
arrives. A punch that carries an id the employee's log already holds is a
REPLAY — the stored row is answered, nothing is inserted. Only a genuinely
new id goes through burst detection and type resolution. Taps without an id
(Desk, imports, old clients) behave exactly as before.

    PYTHONPATH=. python3 hrms/tests/test_a_replayed_tap_is_the_same_tap.py
"""

from __future__ import annotations

import datetime
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import remote_checkin

EMPLOYEE = "EMP-0001"
USER = "jane@example.com"


class _FakeDoc(SimpleNamespace):
	def __init__(self, site):
		store = site.rows
		super().__init__(
			name=f"EMP-CKIN-{len(store) + 1:04d}",
			employee=None,
			employee_name="Jane",
			log_type=None,
			time=None,
			latitude=None,
			longitude=None,
			client_tap_id=None,
			skip_auto_attendance=0,
			requires_remote_approval=0,
			remote_approval_status=None,
			geofence_outcome=None,
			comments=[],
			flags=SimpleNamespace(),
		)
		self._store = store
		self._site = site

	def update(self, values):
		for key, value in values.items():
			setattr(self, key, value)

	def insert(self):
		if self._site.refuse_next_insert_as_duplicate:
			self._site.refuse_next_insert_as_duplicate = False
			raise self._site.stub.UniqueValidationError("Employee Checkin", self.name)
		if self._site.flag_inserts_as_imprecise:
			# What the geofence override does on an unplaceable reading: the
			# stored outcome, and the in-memory reason for this request only.
			self.requires_remote_approval = 1
			self.remote_approval_status = "Pending"
			self.geofence_outcome = "Imprecise"
			self._remote_reason = "imprecise_location"
		self._store.append(self)

	def add_comment(self, comment_type, text):
		self.comments.append((comment_type, text))

	def as_row(self):
		return frappe._dict(
			name=self.name,
			time=datetime.datetime.strptime(self.time, "%Y-%m-%d %H:%M:%S"),
			log_type=self.log_type,
			is_abandoned=0,
			remote_approval_status=None,
			synced_from_instance=None,
			shift_actual_end=None,
			device_id=None,
			client_tap_id=self.client_tap_id,
		)


class _Site:
	"""An in-memory Employee Checkin table behind the `frappe` name punch uses.

	The clock advances two minutes per punch — the audit's exact shape — so a
	second tap is a coercion candidate, never a burst.
	"""

	def __enter__(self):
		self.rows: list[_FakeDoc] = []
		self.clock = iter(["2026-08-24 09:00:00", "2026-08-24 09:02:00", "2026-08-24 09:04:00"])
		self.locks: list[tuple] = []
		self.flag_inserts_as_imprecise = False
		self.refuse_next_insert_as_duplicate = False
		self.stub = stub = SimpleNamespace(
			db=SimpleNamespace(get_value=self._get_value),
			session=SimpleNamespace(user=USER),
			new_doc=lambda doctype: _FakeDoc(self),
			UniqueValidationError=type("UniqueValidationError", (Exception,), {}),
			DuplicateEntryError=type("DuplicateEntryError", (Exception,), {}),
			get_doc=lambda doctype, name: next(r for r in self.rows if r.name == name),
			get_all=lambda doctype, filters=None, **k: [
				r.as_row() for r in reversed(self.rows) if r.employee == filters["employee"]
			],
			conf={},
			PermissionError=frappe.PermissionError,
			_dict=frappe._dict,
		)
		self._patches = [
			patch.object(remote_checkin, "frappe", stub),
			patch.object(remote_checkin, "employee_now", side_effect=lambda employee: next(self.clock)),
			patch.object(remote_checkin, "own_employees", side_effect=lambda user: [EMPLOYEE]),
		]
		for p in self._patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self._patches:
			p.stop()
		return False

	def _get_value(self, doctype, filters=None, fieldname=None, **kw):
		"""Rows are matched on every filter given; anything else answers the
		session user, as the punch harness in hrms/api/test_remote_checkin.py does."""
		if kw.get("for_update"):
			self.locks.append((doctype, filters))
		if doctype != "Employee Checkin" or not isinstance(filters, dict):
			return USER
		match = next(
			(r for r in self.rows if all(getattr(r, key, None) == value for key, value in filters.items())),
			None,
		)
		return match.name if match else None


class ReplayedTapCase(unittest.TestCase):
	def test_the_same_id_twice_is_one_row_and_the_same_answer(self):
		with _Site() as site:
			first = remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
			again = remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
		self.assertEqual(len(site.rows), 1, "a replayed tap inserts nothing")
		self.assertEqual(again.name, first.name)
		self.assertEqual(again.log_type, "IN", "the replay answers the stored row, not a coerced OUT")
		self.assertEqual(again.time, first.time)

	def test_a_different_id_is_a_new_tap_and_is_coerced_as_today(self):
		with _Site() as site:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
			second = remote_checkin.punch(
				EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-2"
			)
		self.assertEqual(len(site.rows), 2)
		self.assertEqual(second.log_type, "OUT", "a genuinely new IN inside an open session is still the OUT")

	def test_the_id_is_stored_on_the_row(self):
		with _Site() as site:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
		self.assertEqual(site.rows[0].client_tap_id, "tap-1")

	def test_a_tap_without_an_id_is_never_a_replay(self):
		"""Desk and imports send no id; two id-less taps are two rows, as before."""
		with _Site() as site:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6)
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6)
		self.assertEqual(len(site.rows), 2)

	def test_the_replay_says_why_the_punch_needed_approving(self):
		"""`_remote_reason` lives only on the doc that was inserted; a replay
		must read the reason back from the row, or the PWA shows the
		"outside radius" wording for a reading that could not be placed."""
		with _Site() as site:
			site.flag_inserts_as_imprecise = True
			first = remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
			again = remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
		self.assertEqual(first.remote_reason, "imprecise_location")
		self.assertEqual(again.remote_reason, first.remote_reason)
		self.assertEqual(again.requires_remote_approval, first.requires_remote_approval)

	def test_a_retry_that_overtakes_its_first_post_is_answered_with_the_winner(self):
		"""Two POSTs of the same tap in flight together: the pre-check misses
		for both, the unique index refuses the second insert, and the second
		answers the row that won instead of a 500."""
		with _Site() as site:
			first = remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
			site.refuse_next_insert_as_duplicate = True
			site.rows[0].client_tap_id = "hidden"  # the pre-check's snapshot cannot see the winner yet
			site.locks.clear()
			original = site.stub.db.get_value

			def reveal(*args, **kwargs):
				if args[0] == "Employee Checkin" and kwargs.get("for_update"):
					site.rows[0].client_tap_id = "tap-1"
				return original(*args, **kwargs)

			site.stub.db.get_value = reveal
			again = remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
		self.assertEqual(len(site.rows), 1)
		self.assertEqual(again.name, first.name)
		self.assertEqual(again.log_type, "IN")
		self.assertIn(("Employee Checkin", {"employee": EMPLOYEE, "client_tap_id": "tap-1"}), site.locks)

	def test_the_pre_check_never_locks(self):
		"""A locking read that misses gap-locks the index; two employees
		tapping at once could deadlock. The fast path is a plain read."""
		with _Site() as site:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
		self.assertEqual([lock[0] for lock in site.locks], ["Employee", "Employee"])

	def test_another_employees_id_is_not_this_employees_replay(self):
		"""The lookup is fenced to the employee's own log."""
		with _Site() as site:
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
			site.rows[0].employee = "EMP-9999"
			remote_checkin.punch(EMPLOYEE, "IN", latitude=3.1, longitude=101.6, client_tap_id="tap-1")
		self.assertEqual(len(site.rows), 2)


class ReplayHappensBeforeTheRulesCase(unittest.TestCase):
	"""The replay lookup must run BEFORE burst detection and type resolution,
	or a replayed IN would be re-judged against the row it IS."""

	def test_the_lookup_precedes_burst_and_type_resolution(self):
		import ast
		import pathlib

		tree = ast.parse(pathlib.Path(remote_checkin.__file__).read_text())
		punch = ast.unparse(
			next(
				node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "punch"
			)
		)
		self.assertIn("_stored_tap(", punch)
		replay = punch.index("_stored_tap(")
		self.assertLess(replay, punch.index("resolve_punch_type("))
		self.assertLess(replay, punch.index("is_burst_tap("))

	def test_punch_takes_no_locking_read_on_employee_checkin(self):
		"""The only FOR UPDATE in punch is the Employee row (claim 3). The
		duplicate fallback locks an EXISTING row inside _stored_tap; a lock
		on a lookup that may miss is what gap-locks the index."""
		import ast
		import pathlib
		import re

		source = pathlib.Path(remote_checkin.__file__).read_text()
		tree = ast.parse(source)
		fn = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
		punch = ast.unparse(fn["punch"])
		for call in re.findall(r"frappe\.db\.get_value\((.*?)for_update=True", punch, re.S):
			self.assertIn("'Employee'", call)
			self.assertNotIn("Employee Checkin", call)
		stored = ast.unparse(fn["_stored_tap"])
		self.assertIn("for_update=lock", stored)
		self.assertIn("lock=False", stored, "the default is a plain read")
		locked = punch.index("lock=True")
		self.assertLess(punch.index("except (frappe.UniqueValidationError"), locked)


class FieldCase(unittest.TestCase):
	def test_the_doctype_carries_the_field_hidden_and_indexed(self):
		import json

		path = Path(remote_checkin.__file__).parents[1] / "hr/doctype/employee_checkin/employee_checkin.json"
		fields = {f["fieldname"]: f for f in json.loads(path.read_text())["fields"]}
		self.assertIn("client_tap_id", fields)
		field = fields["client_tap_id"]
		self.assertEqual(field["fieldtype"], "Data")
		self.assertIsNone(field.get("search_index"), "unique already builds the index; not two on one column")
		self.assertEqual(field.get("hidden"), 1)
		self.assertEqual(field.get("read_only"), 1)
		self.assertEqual(field.get("unique"), 1, "the index, not a lock, settles two inserts of one tap")


if __name__ == "__main__":
	unittest.main()
