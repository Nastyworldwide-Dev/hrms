"""Nadi shows the near-duplicate expense warning (alpha.38, owner 6 Oct 2026).

Saving a claim msgprints an orange "You already claimed a Travel on ..." warning
for a same-type, same-day claim with another amount. Nadi never shows it:
frappe-ui drops `_server_messages` on a successful request. So the PWA asks
`hrms.api.near_duplicate_expenses(name)` after a create and toasts what comes
back. The rule itself lives in expense_claim.py and is tested in
test_expense_claim_duplicates.py; this file pins the endpoint's seam:

  * a caller who may not read the claim is refused BEFORE the claim is loaded,
    so the sentences (they name other claims and dates) never reach a stranger;
  * the endpoint answers with what the claim's own rule says, and nothing else.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_near_duplicate_expenses_api.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

SENTENCE = "You already claimed a Travel on 01-10-2026 in HR-EXP-0001. Check it is not the same expense."


class TestNearDuplicateExpensesEndpoint(unittest.TestCase):
	def endpoint(self):
		import hrms.api as api

		return api.near_duplicate_expenses

	def test_it_returns_what_the_claims_own_rule_says(self):
		claim = MagicMock()
		claim.near_duplicate_notes.return_value = [SENTENCE]
		with (
			patch.object(frappe, "has_permission") as has_permission,
			patch.object(frappe, "get_doc", return_value=claim) as get_doc,
		):
			self.assertEqual(self.endpoint()("HR-EXP-0002"), [SENTENCE])
		has_permission.assert_called_once_with("Expense Claim", ptype="read", doc="HR-EXP-0002", throw=True)
		get_doc.assert_called_once_with("Expense Claim", "HR-EXP-0002")
		claim.near_duplicate_notes.assert_called_once()

	def test_it_names_only_the_other_claims_the_caller_may_open(self):
		# review of N1 (6 Oct): an approver of THIS claim must not learn the names
		# of the employee's other claims that are routed to someone else
		claim = MagicMock()
		claim.near_duplicate_notes.return_value = [SENTENCE]
		allowed = {"HR-EXP-0002": True, "HR-EXP-0001": True, "HR-EXP-0007": False}

		def has_permission(doctype, ptype="read", doc=None, throw=False, **kwargs):
			ok = allowed.get(doc, False)
			if throw and not ok:
				raise frappe.PermissionError(doc)
			return ok

		with (
			patch.object(frappe, "has_permission", side_effect=has_permission),
			patch.object(frappe, "get_doc", return_value=claim),
		):
			self.endpoint()("HR-EXP-0002")
			may_open = claim.near_duplicate_notes.call_args.kwargs["may_open"]
			self.assertTrue(may_open("HR-EXP-0001"))
			self.assertFalse(may_open("HR-EXP-0007"))

	def test_a_claim_with_nothing_near_it_answers_an_empty_list(self):
		claim = MagicMock()
		claim.near_duplicate_notes.return_value = []
		with patch.object(frappe, "has_permission"), patch.object(frappe, "get_doc", return_value=claim):
			self.assertEqual(self.endpoint()("HR-EXP-0002"), [])

	def test_a_stranger_is_refused_before_the_claim_is_loaded(self):
		with (
			patch.object(frappe, "has_permission", side_effect=frappe.PermissionError("not yours")),
			patch.object(frappe, "get_doc") as get_doc,
		):
			with self.assertRaises(frappe.PermissionError):
				self.endpoint()("HR-EXP-0002")
		get_doc.assert_not_called()

	def test_an_unknown_claim_is_refused_not_answered_empty(self):
		with (
			patch.object(frappe, "has_permission", side_effect=frappe.DoesNotExistError("no such claim")),
			patch.object(frappe, "get_doc") as get_doc,
		):
			with self.assertRaises(frappe.DoesNotExistError):
				self.endpoint()("HR-EXP-9999")
		get_doc.assert_not_called()


if __name__ == "__main__":
	unittest.main()
