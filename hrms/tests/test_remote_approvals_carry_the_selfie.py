"""The approver's queue must carry the check-in photo it is asked to judge.

The selfie lives on Employee Checkin (`selfie_image`), the request the
approver sees is a Remote Checkin Request, and the PWA list never joined the
two — so an out-of-radius punch reached the approver as a name, a time and a
distance, with the one piece of evidence the employee supplied left behind.
Both the pending queue and the decided history read the photo through the
request's `checkin` link.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_remote_approvals_carry_the_selfie.py
"""

import unittest

from hrms.api import remote_checkin
from hrms.tests.test_company_api_scope import ALPHA, FakeQuery, ScopedFrappe, fake_qb


class SelectingQuery(FakeQuery):
	"""FakeQuery that also remembers which columns were selected."""

	def __init__(self, rows=None):
		super().__init__(rows)
		self.selected: list[str] = []

	def select(self, *columns, **_kwargs):
		self.selected.extend(f"{c.table}.{c.field}" for c in columns if hasattr(c, "table"))
		return self


class TestApprovalsCarryTheSelfie(unittest.TestCase):
	def _query(self, fn, companies=()):
		query = SelectingQuery(rows=[])
		with ScopedFrappe(list(companies), qb=fake_qb(query)):
			fn()
		return query

	def test_pending_queue_joins_the_checkin_for_its_selfie(self):
		query = self._query(remote_checkin.list_pending_for_approver)
		self.assertIn("Employee Checkin", query.joins)
		self.assertIn("Employee Checkin.selfie_image", query.selected)

	def test_decided_history_joins_the_checkin_for_its_selfie(self):
		query = self._query(remote_checkin.list_decided_for_approver)
		self.assertIn("Employee Checkin", query.joins)
		self.assertIn("Employee Checkin.selfie_image", query.selected)

	def test_company_fence_survives_alongside_the_selfie_join(self):
		query = self._query(remote_checkin.list_pending_for_approver, companies=[ALPHA])
		self.assertEqual(query.predicate("Employee.company").value, [ALPHA])
		self.assertIn("Employee", query.joins)
		self.assertIn("Employee Checkin", query.joins)

	def test_badge_count_does_not_pay_for_the_join(self):
		query = self._query(remote_checkin.get_pending_count)
		self.assertNotIn("Employee Checkin", query.joins)


if __name__ == "__main__":
	unittest.main()
