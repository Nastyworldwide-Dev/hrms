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
		self.assertEqual(
			plan["missing"],
			[
				(
					"Petrol (PETROL)",
					"DS Distribution",
					"Fuel/Mileage expenses",
					"no account named Fuel/Mileage expenses in this company",
				)
			],
		)

	def test_a_group_heading_is_named_as_the_reason_not_left_silent(self):
		"""Live, 10 Sep: General & Administrative and Subsidy Parking Claim were
		the two types left unconfigured. A group cannot be a claim's default
		account, and HR can only act on that if the report says so."""
		mapping = {"General & Administrative (G&A)": "General & Administrative"}
		groups = {("General & Administrative", "Nasty Worldwide"): "General & Administrative - NW"}
		plan = plan_type_accounts(mapping, ["Nasty Worldwide"], {}, set(), groups)
		self.assertEqual(plan["rows"], {})
		claim_type, company, _gl_name, reason = plan["missing"][0]
		self.assertEqual((claim_type, company), ("General & Administrative (G&A)", "Nasty Worldwide"))
		self.assertIn("is a group, not a ledger", reason)
		self.assertIn("General & Administrative - NW", reason)

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


class TestThePreviewIsTheSameDecisionAsTheApply(unittest.TestCase):
	"""Splitting the read half out must not let the two answers drift.

	Nabil, 11 Sep 2026, on the third failed "Pull -> GL Accounts": the dialog
	said "Nothing to create. Already here: 49" while Subsidy Parking Claim and
	General & Administrative sat with an empty Accounts table.

	The reason was never hidden by accident — it was never asked for. The pull
	PREVIEW only planned ACCOUNTS; it never looked at claim types at all, and the
	create path put its answer in a key the dialog does not render. So the one
	line that says why — "no account named Subsidiary Parking in this company",
	or "that name is a group, not a ledger" — had never reached the person
	pressing the button.

	`preview_expense_claim_type_mapping` is now that read half, and
	`apply_expense_claim_type_mapping` calls it rather than repeating it. This
	pins that they cannot answer differently: one body, one decision.
	"""

	def test_apply_delegates_to_the_preview_rather_than_repeating_it(self):
		import inspect

		from hrms.utils import expense_claim_type_mapping as mod

		body = inspect.getsource(mod.apply_expense_claim_type_mapping)
		self.assertIn("preview_expense_claim_type_mapping(mapping)", body)
		# the query half must live in ONE place, not two
		for query in ('frappe.get_all(\n\t\t"Account"', "_spellings(mapping)"):
			self.assertNotIn(query, body, "the account lookup belongs to the preview alone")

	def test_the_preview_reports_a_reason_for_every_unwired_pair(self):
		from hrms.utils.expense_claim_type_mapping import plan_type_accounts

		plan = plan_type_accounts(
			{"Subsidy Parking Claim (S-PARKING CLAIM)": "Subsidiary Parking"},
			["Nsty Holding Sdn Bhd"],
			account_lookup={},
			existing_rows=set(),
			groups={},
		)
		self.assertEqual(len(plan["missing"]), 1)
		_claim_type, _company, gl_name, reason = plan["missing"][0]
		self.assertEqual(gl_name, "Subsidiary Parking")
		self.assertIn("no account named", reason)

	def test_a_group_heading_is_named_as_such_not_reported_as_absent(self):
		# The other half of the third-attempt mystery: an account that EXISTS but
		# cannot be posted to. "Missing" would send HR to create a duplicate.
		from hrms.utils.expense_claim_type_mapping import plan_type_accounts

		plan = plan_type_accounts(
			{"General & Administrative (G&A)": "General & Administrative"},
			["Nsty Holding Sdn Bhd"],
			account_lookup={},
			existing_rows=set(),
			groups={("General & Administrative", "Nsty Holding Sdn Bhd"): "G&A - NHSB"},
		)
		self.assertIn("is a group, not a ledger", plan["missing"][0][3])
