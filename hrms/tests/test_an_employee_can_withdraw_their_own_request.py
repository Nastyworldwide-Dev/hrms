"""An employee may take back their own approved request, and get their days back.

Owner, 17 Sep 2026: "approved leave or others made by request (the employee)
can be withdrawn and whatever the approved must be reverted back to its
original content... i have 14 days leave balance, i request for 1 day... once
approved, deduct... let say i had to cancel my leave despite the approved. i
withdrawn. it must reflect back to 14 days." Asked which shape he wanted, he
answered: "withdrawal. a." — the employee cancels it themselves.

This REVERSES his own 14 Sep ruling, which this guard's docstring records as
"The employee who raised it, and anyone else, still cannot."

The reverting half already existed and is untouched: every request type undoes
what it granted in its own `on_cancel` — the leave ledger entry, the allocated
days, the replacement leave, the Attendance row, the Shift Assignment. What was
missing was the door.

TWO refusals stay, and they are about money, not about roles:

* paid overtime on a submitted salary slip — already refused for everyone;
* a request whose days fall inside a submitted salary slip. Withdrawing leave
  that has already been paid would hand the days back while the money stays
  paid. HR keeps its own authority there and can still cancel it; the employee
  is told to talk to HR.

    PYTHONPATH=. python3 -m pytest -q \
        hrms/tests/test_an_employee_can_withdraw_their_own_request.py
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.utils import approved_request_guard as guard

ME = "staff@example.com"
MY_EMPLOYEE = "HR-EMP-00021"


def request(doctype="Leave Application", **over):
	row = frappe._dict(
		doctype=doctype,
		name="HR-LAP-0001",
		employee=MY_EMPLOYEE,
		from_date="2026-09-20",
		to_date="2026-09-20",
	)
	row.update(over)
	return row


class WithdrawalCase(unittest.TestCase):
	def _refusal(self, doc=None, own=True, approver=False, paid_slip=None):
		doc = doc or request()
		with (
			patch.object(guard, "is_own_request", return_value=own),
			patch("hrms.api.approval._is_routed_approver", return_value=approver),
			patch.object(guard, "_paying_salary_slip", return_value=None),
			patch.object(guard, "_withdrawal_block", return_value=paid_slip),
			patch.object(frappe, "session", frappe._dict(user=ME)),
		):
			return guard.cancel_refusal(doc, ME)

	def test_i_can_withdraw_my_own_approved_leave(self):
		self.assertIsNone(self._refusal())

	def test_my_approver_can_still_cancel_it(self):
		self.assertIsNone(self._refusal(own=False, approver=True))

	def test_a_stranger_still_cannot(self):
		refusal = self._refusal(own=False, approver=False)
		self.assertIsNotNone(refusal)

	def test_i_cannot_withdraw_days_that_are_already_paid(self):
		"""The days would come back while the money stays paid."""
		refusal = self._refusal(
			paid_slip="These days are already in a paid salary slip. Ask HR to cancel it for you."
		)
		self.assertIsNotNone(refusal)
		self.assertIn("HR", refusal, "it must say who can still do it")

	def test_the_approver_is_not_stopped_by_the_payslip(self):
		"""HR and the approver keep the authority they already had."""
		self.assertIsNone(
			self._refusal(
				own=False,
				approver=True,
				paid_slip="These days are already in a paid salary slip. Ask HR to cancel it for you.",
			)
		)

	def test_paid_overtime_is_still_refused_for_everyone(self):
		with (
			patch.object(guard, "is_own_request", return_value=True),
			patch.object(guard, "_paying_salary_slip", return_value="HR-SAL-0001"),
			patch.object(frappe, "session", frappe._dict(user=ME)),
		):
			refusal = guard.cancel_refusal(request("OT Request", name="HR-OTR-1"), ME)
		self.assertIsNotNone(refusal)
		self.assertIn("payroll", refusal.lower())


class SlipLookupCase(unittest.TestCase):
	"""`_withdrawal_block` reads each doctype's own dates, never a guessed field."""

	def test_every_decidable_doctype_is_answered_one_way_or_the_other(self):
		"""Amended 17 Sep 2026: a doctype may be absent from the map ON PURPOSE
		— Travel Request's dates live on a child table — as long as being absent
		REFUSES the employee rather than waving them through."""
		for doctype in guard.DECISION_FIELD_BY_DOCTYPE:
			with self.subTest(doctype=doctype):
				if doctype in guard.REQUEST_PERIOD_FIELDS:
					continue
				with patch.object(frappe, "db", MagicMock()):
					self.assertIsNotNone(
						guard._withdrawal_block(request(doctype)),
						f"{doctype} has no period named and is not refused — it would be waved through",
					)

	def test_a_doctype_with_no_period_is_never_silently_allowed(self):
		"""An unknown doctype must fail CLOSED, not skip the payroll check."""
		self.assertIsNotNone(guard.REQUEST_PERIOD_FIELDS.get("Leave Application"))
		with patch.object(frappe, "db", MagicMock()):
			self.assertIsNotNone(guard._withdrawal_block(request("Journal Entry")))

	def test_a_request_carrying_no_dates_fails_closed(self):
		"""Malformed, not unpaid — HR can still cancel it."""
		bare = frappe._dict(doctype="Leave Application", name="X", employee=MY_EMPLOYEE)
		with patch.object(frappe, "db", MagicMock()):
			self.assertIsNotNone(guard._withdrawal_block(bare))


class TheDoorIsReachableCase(unittest.TestCase):
	"""A permission nobody can reach is not a permission.

	The guard says the employee may withdraw. `finalize` is how the app cancels,
	and it elevated ONLY for a routed approver — `not is_own_request(doc)` — so
	the owner fell through to Frappe's own cancel permission, which staff do not
	hold on these doctypes (the staff lockdown strips it). The guard would have
	said yes and the endpoint no.
	"""

	def test_finalize_elevates_for_the_owner_too(self):
		import ast
		import pathlib

		from hrms.api import approval

		tree = ast.parse(pathlib.Path(approval.__file__).read_text())
		fn = next(
			node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "finalize"
		)
		body = ast.unparse(fn)
		# The fix is not "add the owner to the second copy of the rule" — it is
		# to stop keeping a second copy. `cancel_refusal` IS who may cancel.
		self.assertIn(
			"may_cancel",
			body,
			"the cancel branch must ask the one copy of the rule, not re-derive it",
		)
		self.assertNotIn(
			"_is_routed_approver(doc)",
			body.split("action == 'cancel'")[-1].split("else:")[0],
			"re-deriving routing here is how the owner got left out",
		)


class PeriodFieldsAreRealCase(unittest.TestCase):
	"""A wrong-but-present field name passes silently where a missing one shouts.

	`REQUEST_PERIOD_FIELDS["Travel Request"]` was `("creation",)` — Frappe's row
	timestamp, not any travel date — which meant a request filed today for a trip
	in a paid period would have compared today against that payslip, found no
	overlap, and let the employee withdraw something already paid. It passed the
	"is the doctype listed" test because the doctype WAS listed.
	"""

	def test_every_named_field_exists_on_its_doctype(self):
		import json
		import pathlib

		root = pathlib.Path(__file__).resolve().parents[1]
		for doctype, fields in guard.REQUEST_PERIOD_FIELDS.items():
			slug = doctype.lower().replace(" ", "_")
			path = next(root.rglob(f"doctype/{slug}/{slug}.json"), None)
			if path is None:
				continue  # an erpnext-owned doctype; its JSON is not in this app
			meta = json.loads(path.read_text())
			if not isinstance(meta, dict):
				continue
			dates = {
				f["fieldname"] for f in meta.get("fields", []) if f.get("fieldtype") in ("Date", "Datetime")
			}
			for field in fields:
				with self.subTest(doctype=doctype, field=field):
					self.assertIn(
						field,
						dates,
						f"{doctype}.{field} is not a date field on the doctype — it cannot be its period",
					)

	def test_a_doctype_with_no_usable_period_refuses_rather_than_guesses(self):
		self.assertNotIn(
			"Travel Request",
			guard.REQUEST_PERIOD_FIELDS,
			"its dates live on a child table; aiming at `creation` checked nothing",
		)
		blocked = guard._withdrawal_block(frappe._dict(doctype="Travel Request", name="T", employee="E"))
		self.assertIsNotNone(blocked)
		self.assertIn("HR", blocked, "the employee must be told who can still do it")
