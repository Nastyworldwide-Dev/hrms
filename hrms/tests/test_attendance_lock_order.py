"""One lock order for the two rows every day-rebuild touches.

16 Sep 2026, verifica-live: two Error Logs, both MariaDB 1213, both out of
`remark_day`. One transaction held the day's Attendance row (`SELECT … FOR
UPDATE` in `get_duplicate_attendance_record`, on its way to writing the row)
and then updated `tabEmployee Checkin`; the other had already updated
`tabEmployee Checkin` (`update_attendance_in_checkins`, called from
`_link_to_hr_row`) and then asked for the Attendance row. A textbook AB/BA
cycle, so one of them was chosen as the victim and the day was left unmarked.

The order settled on is the one the engine already takes on its main path:

    Attendance  ->  Employee Checkin

Pinned here over BOTH sites that write a punch's `attendance` column — the
marking path and the HR-row linking path — and by a source check that no third
site writes that column without the row lock.

    PYTHONPATH=. python3 hrms/tests/test_attendance_lock_order.py
"""

import pathlib
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.employee_checkin import employee_checkin as ec

SOURCE = pathlib.Path(ec.__file__).read_text()


class _Field:
	def __init__(self, table, name):
		self.table, self.name = table, name

	def isin(self, values):
		return ("isin", self.table, self.name, tuple(values))

	def __eq__(self, other):
		return ("eq", self.table, self.name, other)


class _Table:
	def __init__(self, name):
		self._name = name

	def __getattr__(self, field):
		return _Field(self._name, field)


class _Query:
	"""Records what it would run, in the order it is run."""

	def __init__(self, ops, kind, table):
		self.ops, self.kind, self.table, self.locked = ops, kind, table, False

	def select(self, *args):
		return self

	def where(self, *args):
		return self

	def set(self, *args):
		return self

	def for_update(self):
		self.locked = True
		return self

	def run(self, *args, **kwargs):
		self.ops.append((self.kind, self.table, self.locked))
		return []


class _QB:
	def __init__(self, ops):
		self.ops = ops

	def DocType(self, name):
		return _Table(name)

	def from_(self, table):
		return _Query(self.ops, "select", table._name)

	def update(self, table):
		return _Query(self.ops, "update", table._name)


class TestTheLockOrderIsAttendanceThenCheckin(unittest.TestCase):
	def _ops(self, call):
		ops = []
		db = MagicMock()
		db.get_value.return_value = "HR-ATT-1"
		with patch.object(frappe, "qb", _QB(ops), create=True), patch.object(frappe, "db", db):
			call()
		return ops

	def test_the_marking_path_locks_the_row_before_it_links_the_punches(self):
		ops = self._ops(lambda: ec.update_attendance_in_checkins(["CKIN-1", "CKIN-2"], "HR-ATT-1"))
		self.assertEqual(ops, [("select", "Attendance", True), ("update", "Employee Checkin", False)])

	def test_the_hr_row_path_locks_the_row_before_it_links_the_punches(self):
		logs = [frappe._dict(name="CKIN-1", attendance=None)]
		ops = self._ops(lambda: ec._link_to_hr_row("HR-EMP-00048", "2026-09-03", logs))
		self.assertEqual(ops, [("select", "Attendance", True), ("update", "Employee Checkin", False)])

	def test_the_row_lock_is_taken_for_update_not_a_plain_read(self):
		"""A read without FOR UPDATE takes no lock at all, so the cycle would stand."""
		ops = self._ops(lambda: ec.update_attendance_in_checkins(["CKIN-1"], "HR-ATT-1"))
		self.assertTrue(ops[0][2], "the Attendance row was read without FOR UPDATE")

	def test_nothing_writes_the_attendance_column_outside_that_one_writer(self):
		"""The order can only hold while every writer goes through the one seam."""
		blocks = re.split(r"^def ", SOURCE, flags=re.MULTILINE)
		writers = [block.split("(", 1)[0] for block in blocks if re.search(r'\.set\(\s*"attendance"', block)]
		self.assertEqual(writers, ["update_attendance_in_checkins"])

	def test_both_call_sites_go_through_that_writer(self):
		calls = re.findall(r"^\t*update_attendance_in_checkins\(", SOURCE, re.MULTILINE)
		self.assertGreaterEqual(len(calls), 2, "a call site stopped using the locking writer")

	def test_the_order_is_written_down_for_the_next_writer(self):
		self.assertIn("LOCK ORDER", SOURCE)


if __name__ == "__main__":
	unittest.main()
