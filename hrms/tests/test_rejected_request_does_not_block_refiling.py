"""A rejected request must not stand in the way of filing it again.

Rejection is a decision, not a cancellation: a rejected Shift Request, OT
Request or Attendance Request reaches docstatus 1 (test_decision_before_
consequence). Their overlap / duplicate checks, though, still selected on
`docstatus < 2` alone, so the refused row went on reserving its dates. Walked
on fresh.local, 15 Sep 2026:

    Shift Request  re-file after rejection  REFUSED OverlappingShiftRequestError
    OT Request     re-file after rejection  REFUSED "An OT Request for 2026-09-09 already exists"

An employee whose request was refused for a fixable reason (wrong shift,
claimed too many hours) could not correct and re-file: the only way out was
HR cancelling the rejection in Desk. Leave Application already excludes
rejected rows (status in Open / Approved) — the same rule, applied to the
three siblings.

Bench-free: the query methods are lifted from each controller by AST and run
against the in-memory query builder (_qb_stub) or a recording frappe.db.

    python3 hrms/tests/test_rejected_request_does_not_block_refiling.py
"""

import ast
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub
import _qb_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

HR = pathlib.Path(__file__).resolve().parents[1] / "hr/doctype"


def _lift(path, class_name, method, namespace):
	tree = ast.parse(path.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
	fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), namespace)
	return namespace[method]


class _Overlap(Exception):
	pass


def _existing(status, **row):
	base = {"name": f"OLD-{status}", "employee": "HR-EMP-1", "docstatus": 1, "status": status}
	base.update(row)
	return base


class TestShiftRequest(unittest.TestCase):
	PATH = HR / "shift_request/shift_request.py"

	def _overlapping(self, rows):
		_qb_stub.install({"Shift Request": rows})
		get_overlapping_dates = _lift(self.PATH, "ShiftRequest", "get_overlapping_dates", {"frappe": frappe})
		doc = SimpleNamespace(name="NEW", employee="HR-EMP-1", from_date="2026-10-05", to_date="2026-10-09")
		return [r.name for r in get_overlapping_dates(doc)]

	def test_a_rejected_request_on_the_same_dates_is_not_an_overlap(self):
		rows = [_existing("Rejected", shift_type="Evening", from_date="2026-10-05", to_date="2026-10-09")]
		self.assertEqual(self._overlapping(rows), [])

	def test_an_open_or_approved_request_still_is(self):
		rows = [
			_existing("Draft", shift_type="Evening", from_date="2026-10-05", to_date="2026-10-09"),
			_existing("Approved", shift_type="Evening", from_date="2026-10-07", to_date=None),
		]
		self.assertEqual(sorted(self._overlapping(rows)), ["OLD-Approved", "OLD-Draft"])


class TestAttendanceRequest(unittest.TestCase):
	PATH = HR / "attendance_request/attendance_request.py"

	def _validate(self, rows):
		_qb_stub.install({"Attendance Request": rows})
		validate = _lift(self.PATH, "AttendanceRequest", "validate_request_overlap", {"frappe": frappe})
		doc = SimpleNamespace(
			name="NEW",
			employee="HR-EMP-1",
			from_date="2026-09-11",
			to_date="2026-09-11",
			shift=None,
			throw_overlap_error=lambda name: (_ for _ in ()).throw(_Overlap(name)),
		)
		validate(doc)

	def test_a_rejected_request_on_the_same_day_does_not_block(self):
		self._validate([_existing("Rejected", from_date="2026-09-11", to_date="2026-09-11")])

	def test_an_open_request_on_the_same_day_still_blocks(self):
		with self.assertRaises(_Overlap):
			self._validate([_existing("Open", from_date="2026-09-11", to_date="2026-09-11")])


class TestOTRequest(unittest.TestCase):
	PATH = HR / "ot_request/ot_request.py"

	def _validate(self, rows):
		frappe = MagicMock()

		def get_values(doctype, filters, fieldname, **kwargs):
			def matches(row):
				for key, wanted in filters.items():
					if isinstance(wanted, tuple):
						op, value = wanted
						actual = row.get(key)
						ok = {"<": actual < value, "!=": actual != value}[op]
					else:
						ok = row.get(key) == wanted
					if not ok:
						return False
				return True

			return [(r["name"],) for r in rows if matches(r)]

		frappe.db.get_values.side_effect = get_values
		frappe.throw.side_effect = lambda msg, *a, **k: (_ for _ in ()).throw(_Overlap(msg))
		frappe.bold = lambda v: v
		ns = {"frappe": frappe, "_": lambda s: s}
		validate = _lift(self.PATH, "OTRequest", "validate_duplicate_request", ns)
		validate(SimpleNamespace(name="NEW", employee="HR-EMP-1", ot_date="2026-09-09"))

	def test_a_rejected_request_for_the_same_day_is_not_a_duplicate(self):
		self._validate([_existing("Rejected", ot_date="2026-09-09")])

	def test_an_open_or_approved_request_for_the_same_day_still_is(self):
		for status in ("Open", "Approved"):
			with self.subTest(status=status), self.assertRaises(_Overlap):
				self._validate([_existing(status, ot_date="2026-09-09")])


if __name__ == "__main__":
	unittest.main()
