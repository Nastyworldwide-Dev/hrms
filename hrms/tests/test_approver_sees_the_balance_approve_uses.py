"""The leave balance the approver reads is the balance the approve is judged by.

REPORTED 23 Sep 2026 (owner screenshot, live): the PWA approval sheet showed
"Leave Balance 1", "Total Leave Days 1"; the approver tapped Approve and got
"Insufficient leave balance for Leave Type Birthday Leave".

`leave_balance` on a Leave Application is a SNAPSHOT written when the employee
filed. Approving re-runs validate_balance_leaves, which recomputes the balance
FOR CONSUMPTION over the whole allocation period — lower once other leave was
taken, the allocation is expiring, or only part of it is usable by these dates.
So the sheet showed one number and the server judged another.

Now one helper, get_consumable_leave_balance, produces the number; validate uses
it, and get_decision_actions returns it to an already-authorised decider as
`leave_balance_now`. The refusal names the days left, in plain words.

Bench-free:  PYTHONPATH=. python3 -m pytest -q hrms/tests/test_approver_sees_the_balance_approve_uses.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
for module in ("pypika", "pypika.terms", "pypika.functions"):
	sys.modules.setdefault(module, MagicMock())
import frappe

from hrms.api import approval
from hrms.hr.doctype.leave_application import leave_application as la

FROM, TO = date(2026, 9, 24), date(2026, 9, 24)
APPROVER = "approver@example.invalid"


class _Refused(Exception):
	pass


def _throw(msg, *args, **kwargs):
	raise _Refused(msg)


def _application(status="Approved", leave_balance=1.0):
	doc = la.LeaveApplication.__new__(la.LeaveApplication)
	doc.__dict__.update(
		{
			"doctype": "Leave Application",
			"name": "HR-LAP-BDAY",
			"employee": "EMP-1",
			"leave_type": "Birthday Leave",
			"from_date": FROM,
			"to_date": TO,
			"half_day": 0,
			"half_day_date": None,
			"status": status,
			"docstatus": 0,
			"leave_balance": leave_balance,
		}
	)
	return doc


class TestOneHelperProducesTheNumber(unittest.TestCase):
	def test_it_is_the_consumption_balance_over_the_allocation_period(self):
		inner = MagicMock(return_value={"leave_balance": 1.0, "leave_balance_for_consumption": 0.5})
		access = MagicMock(side_effect=AssertionError("an authorised decider is not re-fenced here"))
		db = MagicMock()
		db.get_single_value.return_value = 2
		with (
			patch.object(la, "_leave_balance_on", inner),
			patch.object(la, "validate_leave_access", access),
			patch.object(frappe, "db", db),
		):
			self.assertEqual(la.get_consumable_leave_balance("EMP-1", "Birthday Leave", FROM, TO), 0.5)
		inner.assert_called_once_with(
			"EMP-1",
			"Birthday Leave",
			FROM,
			TO,
			consider_all_leaves_in_the_allocation_period=True,
			for_consumption=True,
		)

	def test_validate_judges_the_approve_by_that_same_helper(self):
		doc = _application()
		doc.show_insufficient_balance_message = MagicMock()
		helper = MagicMock(return_value=0.0)
		access = MagicMock()
		with (
			patch.object(la, "get_consumable_leave_balance", helper),
			patch.object(la, "validate_leave_access", access),
			patch.object(la, "get_number_of_leave_days", lambda *a, **k: 1.0),
			patch.object(la, "is_lwp", lambda leave_type: 0),
			patch.object(frappe, "db", MagicMock()),
		):
			la.LeaveApplication.validate_balance_leaves(doc)
		helper.assert_called_once_with("EMP-1", "Birthday Leave", FROM, TO)
		doc.show_insufficient_balance_message.assert_called_once_with(0.0)
		# the access rule on the filing path is unchanged
		access.assert_called_once_with("EMP-1")


class TestTheDeciderIsShownTheLiveBalance(unittest.TestCase):
	def _doc(self, status="Open"):
		doc = frappe._dict(
			doctype="Leave Application",
			name="HR-LAP-BDAY",
			docstatus=0,
			status=status,
			employee="EMP-1",
			leave_type="Birthday Leave",
			from_date=FROM,
			to_date=TO,
			leave_balance=1.0,
			modified="2026-09-23 10:00:00",
		)
		return doc

	def _ask(self, allowed=True, helper=None, doc=None):
		doc = doc or self._doc()
		helper = helper or MagicMock(return_value=0.0)
		db = MagicMock()
		db.exists.return_value = True
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(approval, "_decision_access", return_value=allowed),
			patch.object(la, "get_consumable_leave_balance", helper),
			patch.object(la, "is_lwp", lambda leave_type: 0),
		):
			return approval.get_decision_actions("Leave Application", doc.name), helper

	def test_the_approver_gets_the_number_validate_will_use(self):
		answer, helper = self._ask()
		self.assertEqual(answer["actions"], ["Approved", "Rejected"])
		self.assertEqual(answer["leave_balance_now"], 0.0)
		helper.assert_called_once_with("EMP-1", "Birthday Leave", FROM, TO)

	def test_someone_who_cannot_decide_is_told_no_balance(self):
		answer, helper = self._ask(allowed=False)
		self.assertEqual(answer["actions"], [])
		self.assertIsNone(answer.get("leave_balance_now"))
		helper.assert_not_called()

	def test_a_failed_lookup_is_none_not_an_error(self):
		answer, _ = self._ask(helper=MagicMock(side_effect=RuntimeError("ledger unavailable")))
		self.assertEqual(answer["actions"], ["Approved", "Rejected"])
		self.assertIsNone(answer["leave_balance_now"])


class TestTheRefusalSaysHowManyDaysAreLeft(unittest.TestCase):
	def test_plain_words_with_both_numbers(self):
		doc = _application()
		doc.total_leave_days = 1.0
		doc.get_allocation_based_on_application_dates = lambda: (None, None)
		db = MagicMock()
		db.get_value.return_value = 0  # allow_negative off
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "bold", str, create=True),
			patch.object(frappe, "throw", side_effect=_throw),
		):
			with self.assertRaises(_Refused) as refused:
				la.LeaveApplication.show_insufficient_balance_message(doc, 0.5)
		self.assertEqual(
			str(refused.exception),
			"Not enough Birthday Leave left for these dates: 0.5 day(s) left, 1.0 requested.",
		)

	def test_the_refusal_keeps_its_exception_and_title(self):
		doc = _application()
		doc.total_leave_days = 1.0
		doc.get_allocation_based_on_application_dates = lambda: (None, None)
		db = MagicMock()
		db.get_value.return_value = 0
		throw = MagicMock()
		with patch.object(frappe, "db", db), patch.object(frappe, "bold", str, create=True):
			with patch.object(frappe, "throw", throw):
				la.LeaveApplication.show_insufficient_balance_message(doc, 0.5)
		kwargs = throw.call_args.kwargs
		self.assertIs(kwargs["exc"], la.InsufficientLeaveBalanceError)
		self.assertEqual(kwargs["title"], "Insufficient Balance")


if __name__ == "__main__":
	unittest.main()
