"""Expense claims: the manager approves, then HR (owner, 5 Nov 2026).

"hr will work like manager same thing all just that hr is after manager." The stage
rule is one pure module (hrms.utils.claim_stages) that decide(), the decision
buttons and the Approvals list all ask.

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/tests/test_an_expense_claim_is_approved_in_two_steps.py
"""

import importlib.util
import itertools
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "utils" / "claim_stages.py"
spec = importlib.util.spec_from_file_location("claim_stages", PATH)
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


class TestWhoDecidesAtEachStep(unittest.TestCase):
	def test_the_manager_decides_a_new_claim(self):
		self.assertTrue(cs.may_decide("Draft", on_line=True, is_hr=False))

	def test_hr_may_act_before_the_manager_as_today(self):
		# owner, 5 Nov 2026: "it will work as today only that now all hr will become second
		# approver". HR keeps deciding any claim at any time; that decision is final.
		self.assertTrue(cs.may_decide("Draft", on_line=False, is_hr=True))

	def test_hr_decides_once_the_manager_has_approved(self):
		self.assertTrue(cs.may_decide("Waiting for HR", on_line=False, is_hr=True))

	def test_the_manager_cannot_act_once_it_is_with_hr(self):
		self.assertFalse(cs.may_decide("Waiting for HR", on_line=True, is_hr=False))

	def test_an_hr_manager_on_the_line_still_does_one_step_at_a_time(self):
		# the same person can be both; each step is still taken on its own
		self.assertTrue(cs.may_decide("Draft", on_line=True, is_hr=True))
		self.assertTrue(cs.may_decide("Waiting for HR", on_line=True, is_hr=True))

	def test_a_decided_claim_is_decided_by_nobody(self):
		for status, on_line, is_hr in itertools.product(
			("Approved", "Rejected", "Cancelled", None), (True, False), (True, False)
		):
			self.assertFalse(cs.may_decide(status, on_line=on_line, is_hr=is_hr), status)


class TestWhereADecisionLeadsTheClaim(unittest.TestCase):
	def test_a_managers_approval_sends_it_to_hr_and_is_not_final(self):
		self.assertEqual(cs.next_status("Draft", "Approved"), "Waiting for HR")
		self.assertFalse(cs.is_final("Draft", "Approved"))

	def test_hr_deciding_before_the_manager_is_final(self):
		self.assertEqual(cs.next_status("Draft", "Approved", by_hr=True), "Approved")
		self.assertTrue(cs.is_final("Draft", "Approved", by_hr=True))

	def test_a_managers_rejection_ends_it(self):
		self.assertEqual(cs.next_status("Draft", "Rejected"), "Rejected")
		self.assertTrue(cs.is_final("Draft", "Rejected"))

	def test_hrs_approval_is_final(self):
		self.assertEqual(cs.next_status("Waiting for HR", "Approved"), "Approved")
		self.assertTrue(cs.is_final("Waiting for HR", "Approved"))

	def test_hrs_rejection_is_final(self):
		self.assertEqual(cs.next_status("Waiting for HR", "Rejected"), "Rejected")
		self.assertTrue(cs.is_final("Waiting for HR", "Rejected"))


class TestWhereANewClaimStarts(unittest.TestCase):
	def test_with_the_manager(self):
		self.assertEqual(cs.first_status(has_manager=True), "Draft")

	def test_straight_with_hr_when_nobody_is_above(self):
		self.assertEqual(cs.first_status(has_manager=False), "Waiting for HR")


class TestTheDoctypeKnowsTheNewStep(unittest.TestCase):
	def test_waiting_for_hr_is_an_approval_status(self):
		import json

		doc = json.loads((PATH.parents[1] / "hr/doctype/expense_claim/expense_claim.json").read_text())
		field = next(f for f in doc["fields"] if f["fieldname"] == "approval_status")
		self.assertIn("Waiting for HR", field["options"].split("\n"))
		self.assertGreaterEqual(doc["modified"], "2026-11-05", "the doctype re-syncs on migrate")


if __name__ == "__main__":
	unittest.main()
