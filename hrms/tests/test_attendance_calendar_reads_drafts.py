"""An attendance keyed in on Desk and Saved — not yet Submitted — must show on
the PWA calendar.

Desk's own Attendance calendar (`attendance.get_events`) lists Draft rows next
to Submitted ones; the PWA calendar read `docstatus = 1` only, so a row HR
created on Desk and left unsubmitted was visible to HR and invisible to the
employee it was about. Cancelled rows stay out on both surfaces.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_attendance_calendar_reads_drafts.py
"""

import unittest
from unittest.mock import patch

import frappe

from hrms.api import get_attendance_for_calendar


def _admits(predicate, docstatus: int) -> bool:
	"""Evaluate the frappe filter value the query hands to `docstatus`."""
	if not isinstance(predicate, (list, tuple)):
		return docstatus == predicate
	op, value = predicate
	return {
		"=": lambda: docstatus == value,
		"!=": lambda: docstatus != value,
		"<": lambda: docstatus < value,
		"<=": lambda: docstatus <= value,
		"in": lambda: docstatus in value,
		"not in": lambda: docstatus not in value,
	}[op]()


class TestCalendarReadsDrafts(unittest.TestCase):
	def _docstatus_filter(self):
		captured = {}

		def get_all(_doctype, filters=None, *_args, **_kwargs):
			captured.update(filters or {})
			return []

		with patch.object(frappe, "get_all", get_all):
			get_attendance_for_calendar("HR-EMP-001", "2026-09-01", "2026-09-30")
		return captured["docstatus"]

	def test_draft_rows_are_read(self):
		self.assertTrue(_admits(self._docstatus_filter(), 0))

	def test_submitted_rows_are_still_read(self):
		self.assertTrue(_admits(self._docstatus_filter(), 1))

	def test_cancelled_rows_stay_out(self):
		self.assertFalse(_admits(self._docstatus_filter(), 2))

	def test_a_submitted_row_wins_the_date_over_a_draft(self):
		import datetime

		day = datetime.date(2026, 9, 7)
		rows = [
			{"attendance_date": day, "status": "Absent", "docstatus": 0},
			{"attendance_date": day, "status": "Present", "docstatus": 1},
		]
		captured = {}

		def get_all(_doctype, _filters=None, _fields=None, order_by=None, **_kwargs):
			captured["order_by"] = order_by
			# rows arrive in the requested order: drafts first, submitted last
			return sorted(rows, key=lambda r: r["docstatus"])

		with patch.object(frappe, "get_all", get_all):
			events = get_attendance_for_calendar("HR-EMP-001", "2026-09-01", "2026-09-30")
		self.assertEqual(captured["order_by"], "docstatus asc")
		self.assertEqual(events[day], "Present")


if __name__ == "__main__":
	unittest.main()
