"""Expense Claim Type Cost Center: one row = one company's cost center for a type.

Both fields are required, so a half-filled row cannot reach the claim rule
(hrms.hr.doctype.expense_claim.expense_claim.type_cost_centers).

    python3 hrms/hr/doctype/expense_claim_type_cost_center/test_expense_claim_type_cost_center.py
"""

import json
import pathlib
import unittest

SCHEMA = pathlib.Path(__file__).resolve().parent / "expense_claim_type_cost_center.json"


class TestSchema(unittest.TestCase):
	def setUp(self):
		self.doc = json.loads(SCHEMA.read_text())
		self.fields = {f["fieldname"]: f for f in self.doc["fields"]}

	def test_a_child_table_of_company_and_cost_center(self):
		self.assertEqual(self.doc["istable"], 1)
		self.assertEqual(self.fields["company"]["options"], "Company")
		self.assertEqual(self.fields["cost_center"]["options"], "Cost Center")

	def test_both_fields_are_required(self):
		self.assertEqual(self.fields["company"].get("reqd"), 1)
		self.assertEqual(self.fields["cost_center"].get("reqd"), 1)

	def test_the_type_holds_it_as_cost_centers(self):
		parent = json.loads(
			(SCHEMA.parent.parent / "expense_claim_type" / "expense_claim_type.json").read_text()
		)
		table = next(f for f in parent["fields"] if f["fieldname"] == "cost_centers")
		self.assertEqual(table["options"], self.doc["name"])


if __name__ == "__main__":
	unittest.main()
