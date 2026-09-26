"""The HR list of days the 16-hour button saved a check-out as a check-in.
PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/hr/report/missed_checkouts_after_midnight/test_missed_checkouts_after_midnight.py
"""

import unittest
from datetime import date, datetime

from hrms.tests import _erpnext_stub

_erpnext_stub.install()

from hrms.hr.report.missed_checkouts_after_midnight.missed_checkouts_after_midnight import find_missed


def p(emp, t, lt, **kw):
	return {"employee": emp, "employee_name": emp, "time": t, "log_type": lt, **kw}


class TestFindMissed(unittest.TestCase):
	def rows(self, punches):
		return list(find_missed(punches, date(2026, 9, 1), date(2026, 9, 30)))

	def test_an_in_then_an_in_at_3am_is_listed(self):
		out = self.rows([p("A", datetime(2026, 9, 24, 9), "IN"), p("A", datetime(2026, 9, 25, 3), "IN")])
		self.assertEqual([(r["employee"], r["day"]) for r in out], [("A", date(2026, 9, 24))])

	def test_a_real_check_out_is_not_listed(self):
		self.assertEqual(
			self.rows([p("A", datetime(2026, 9, 24, 9), "IN"), p("A", datetime(2026, 9, 25, 3), "OUT")]), []
		)

	def test_the_next_mornings_arrival_after_06_00_is_not_listed(self):
		self.assertEqual(
			self.rows([p("A", datetime(2026, 9, 24, 9), "IN"), p("A", datetime(2026, 9, 25, 8, 30), "IN")]),
			[],
		)

	def test_two_people_are_never_paired(self):
		self.assertEqual(
			self.rows([p("A", datetime(2026, 9, 24, 9), "IN"), p("B", datetime(2026, 9, 25, 3), "IN")]), []
		)

	def test_a_rejected_punch_is_not_evidence(self):
		punches = [
			p("A", datetime(2026, 9, 24, 9), "IN"),
			p("A", datetime(2026, 9, 25, 3), "IN", remote_approval_status="Rejected"),
		]
		self.assertEqual(self.rows(punches), [])


class TestTheSuggestion(unittest.TestCase):
	"""alpha.11: each row carries a suggested check-out HR confirms, never applies."""

	def test_the_suggested_check_out_is_the_tap_that_was_saved_as_a_check_in(self):
		out = list(
			find_missed(
				[p("A", datetime(2026, 9, 24, 9), "IN"), p("A", datetime(2026, 9, 25, 3, 12), "IN")],
				date(2026, 9, 1),
				date(2026, 9, 30),
			)
		)
		self.assertEqual(out[0]["suggested_out"], datetime(2026, 9, 25, 3, 12))
		self.assertIn("Punches", out[0]["what_to_do"])
		self.assertIn("confirm", out[0]["what_to_do"])
