"""HR's eleven claim types get their GL account in every company, without hands.

PYTHONPATH=. python3 hrms/tests/test_expense_claim_type_mapping.py
"""

import ast
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

from hrms.utils.expense_claim_type_mapping import MAPPING, plan_type_accounts

HRMS = pathlib.Path(__file__).resolve().parent.parent


class TestMapping(unittest.TestCase):
	def test_hrs_sheet_is_carried_verbatim(self):
		self.assertEqual(len(MAPPING), 11)
		self.assertEqual(MAPPING["Petrol (PETROL)"], "Fuel/Mileage Expenses")
		self.assertEqual(MAPPING["Subsidy Parking Claim (S-PARKING CLAIM)"], "Subsidiary Parking")

	def test_rows_are_added_only_where_the_account_exists_and_no_row_does(self):
		mapping = {"Petrol (PETROL)": "Fuel/Mileage expenses", "Car Rental (CAR RENTAL)": "Travel Expenses"}
		# the chart spells it with a capital E; the match is case-insensitive
		lookup = {
			("Fuel/Mileage Expenses", "Nasty Worldwide"): "5100 - Fuel/Mileage expenses - NW",
			("Travel Expenses", "Nasty Worldwide"): "Travel Expenses - NW",
			("Travel Expenses", "DS Distribution"): "Travel Expenses - DS",
		}
		existing = {("Car Rental (CAR RENTAL)", "Nasty Worldwide")}
		plan = plan_type_accounts(mapping, ["Nasty Worldwide", "DS Distribution"], lookup, existing)
		self.assertEqual(
			plan["rows"]["Petrol (PETROL)"], [("Nasty Worldwide", "5100 - Fuel/Mileage expenses - NW")]
		)
		self.assertEqual(
			plan["rows"]["Car Rental (CAR RENTAL)"], [("DS Distribution", "Travel Expenses - DS")]
		)
		self.assertEqual(plan["missing"], [("Petrol (PETROL)", "DS Distribution", "Fuel/Mileage expenses")])

	def test_a_ledger_parent_on_the_hub_falls_back_to_the_root_group(self):
		"""Live: "Parent account Travel Expenses - DSDS can not be a ledger" — the
		shell's Standard chart has a ledger by the group's name."""
		src = (HRMS / "sync" / "account_shells.py").read_text()
		self.assertIn('if not frappe.db.get_value("Account", parent, "is_group"):', src)

	def test_the_gl_pull_job_wires_the_types_when_it_ends(self):
		tree = ast.parse((HRMS / "sync" / "account_shells.py").read_text())
		fn = next(
			n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run_account_shells_job"
		)
		names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
		self.assertIn("apply_expense_claim_type_mapping", names)

	def test_the_patch_is_registered(self):
		self.assertIn(
			"hrms.patches.v16_0.seed_expense_claim_types_from_hr_mapping", (HRMS / "patches.txt").read_text()
		)


if __name__ == "__main__":
	unittest.main()
