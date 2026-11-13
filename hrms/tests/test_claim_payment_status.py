"""Expense Claim: HR mark a claim Paid themselves (owner, 13 Nov 2026).

Claims are paid out in another app, so no Payment Entry is ever made here and
ERPNext's own status stayed "Unpaid" for ever. "Is Paid" is ERPNext's
paid-at-submission tick, tied to payment accounts, and is locked after approval.
A plain Payment field (Pending / Paid), like OT Request's, is what HR keep up to
date: no accounts, no ledger.

    python3 -m pytest -q hrms/tests/test_claim_payment_status.py
"""

import json
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

HRMS = pathlib.Path(__file__).resolve().parents[1]
DOC = HRMS / "hr" / "doctype" / "expense_claim"


def _field():
	meta = json.loads((DOC / "expense_claim.json").read_text())
	return meta, {f["fieldname"]: f for f in meta["fields"]}["payment_status"]


class TestTheField(unittest.TestCase):
	def test_pending_or_paid_editable_after_approval(self):
		_, f = _field()
		self.assertEqual((f["fieldtype"], f["options"], f["default"]), ("Select", "Pending\nPaid", "Pending"))
		self.assertEqual(f.get("allow_on_submit"), 1)
		self.assertEqual(f.get("permlevel"), 1, "HR's level, like Approval Status")

	def test_a_list_column_and_a_filter(self):
		_, f = _field()
		self.assertEqual(f.get("in_list_view"), 1)
		self.assertEqual(f.get("in_standard_filter"), 1)

	def test_it_sits_after_approval_status(self):
		meta, _ = _field()
		order = meta["field_order"]
		self.assertEqual(order.index("payment_status"), order.index("approval_status") + 1)

	def test_it_only_shows_once_the_claim_is_approved(self):
		_, f = _field()
		self.assertIn("Approved", f.get("depends_on") or "")


class TestOnlyHRMarksItPaid(unittest.TestCase):
	def _doc(self, before, now):
		doc = SimpleNamespace(
			name="HR-EXP-1",
			payment_status=now,
			approval_status="Approved",
			get_doc_before_save=lambda: SimpleNamespace(payment_status=before) if before else None,
		)
		return doc

	def _check(self, doc, roles):
		from hrms.utils import claim_payment

		with (
			patch.object(claim_payment.frappe, "get_roles", return_value=roles, create=True),
			patch.object(claim_payment.frappe, "session", frappe._dict(user="u@x")),
		):
			claim_payment.validate_payment_status(doc)

	def test_hr_can_mark_it_paid(self):
		for role in ("HR User", "HR Manager"):
			self._check(self._doc("Pending", "Paid"), [role])

	def test_the_expense_approver_cannot(self):
		with self.assertRaises(frappe.PermissionError):
			self._check(self._doc("Pending", "Paid"), ["Expense Approver", "Employee"])

	def test_a_claim_not_yet_approved_cannot_be_paid(self):
		doc = self._doc("Pending", "Paid")
		doc.approval_status = "Waiting for HR"
		with self.assertRaises(frappe.ValidationError):
			self._check(doc, ["HR Manager"])

	def test_an_unchanged_payment_is_not_checked(self):
		self._check(self._doc("Pending", "Pending"), ["Employee"])


class TestEveryScreenSaysPaid(unittest.TestCase):
	def test_desk_list_shows_approved_paid(self):
		js = (DOC / "expense_claim_list.js").read_text()
		self.assertIn('doc.payment_status === "Paid"', js)
		self.assertIn("Approved · paid", js)

	def test_nadi_shows_approved_paid(self):
		js = (HRMS.parent / "frontend" / "src" / "utils" / "requestStatus.js").read_text()
		self.assertIn('doc.payment_status === "Paid"', js)
		self.assertIn("payment_status", (HRMS / "api" / "__init__.py").read_text())

	def test_existing_claims_start_pending_and_the_column_is_shown(self):
		patch_src = (HRMS / "patches" / "v16_0" / "add_claim_payment_status.py").read_text()
		self.assertIn("payment_status", patch_src)
		self.assertIn("hrms.patches.v16_0.add_claim_payment_status", (HRMS / "patches.txt").read_text())


if __name__ == "__main__":
	unittest.main()


class TestTheClaimCallsIt(unittest.TestCase):
	def test_on_every_save_and_on_the_approved_claim(self):
		source = (DOC / "expense_claim.py").read_text()
		self.assertIn("from hrms.utils.claim_payment import validate_payment_status", source)
		self.assertEqual(source.count("validate_payment_status(self)"), 2)
