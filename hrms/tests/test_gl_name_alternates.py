"""A claim type may name more than one spelling of its GL account.

HR's own mapping sheet (11 Sep 2026) and the configured mapping disagree on two
rows, and both disagreements are spelling:

  * sheet "Subsidary Parking"  vs configured "Subsidiary Parking" — one "i"
  * sheet "General & Administrartive" vs configured "General & Administrative"

Normalising case, "&" against "and", punctuation and spacing cannot bridge
those: "subsidary" and "subsidiary" are different WORDS, and deliberately so —
guessing across words is how a claim gets wired to the wrong GL account.

Neither side is obviously right. HR typed the sheet from the ERP, so the sheet
may be the truth; the ERP may equally carry the typo. What is certain is that
exactly one of them matches the chart, and a mapping that can only hold one
spelling forces someone to guess which.

So a claim type may list alternates. The first is what the type's description
shows; any of them resolves. The pull proved the same shape already — it found
"General And Administrative" in the source where the mapping said
"General & Administrative".

Pure.
"""

import unittest

from hrms.utils.expense_claim_type_mapping import MAPPING, gl_names_for, match_account_name


class TestGlNamesFor(unittest.TestCase):
	def test_a_single_name_still_works(self):
		self.assertEqual(gl_names_for("Travel Expenses"), ["Travel Expenses"])

	def test_alternates_are_all_offered(self):
		self.assertEqual(
			gl_names_for(("Subsidiary Parking", "Subsidary Parking")),
			["Subsidiary Parking", "Subsidary Parking"],
		)

	def test_the_first_alternate_is_the_one_to_display(self):
		# The type's description says "GL: <this>", so it must be the canonical one.
		self.assertEqual(gl_names_for(("Subsidiary Parking", "Subsidary Parking"))[0], "Subsidiary Parking")


class TestMatchingAcrossAlternates(unittest.TestCase):
	def test_either_spelling_resolves(self):
		for chart_name in ("Subsidiary Parking", "Subsidary Parking"):
			found = None
			for wanted in gl_names_for(("Subsidiary Parking", "Subsidary Parking")):
				found = found or match_account_name(wanted, {chart_name: "SP - NHSB"})
			self.assertEqual(found, "SP - NHSB", chart_name)

	def test_an_unrelated_account_still_does_not_match(self):
		found = None
		for wanted in gl_names_for(("Subsidiary Parking", "Subsidary Parking")):
			found = found or match_account_name(wanted, {"Parking & Toll": "PT - NHSB"})
		self.assertIsNone(found)


class TestTheMappingCoversHrsSheet(unittest.TestCase):
	def test_both_spellings_hr_has_used_are_accepted(self):
		parking = gl_names_for(MAPPING["Subsidy Parking Claim (S-PARKING CLAIM)"])
		self.assertIn("Subsidiary Parking", parking)
		self.assertIn("Subsidary Parking", parking, "HR's sheet spells it without the second i")

		ga = gl_names_for(MAPPING["General & Administrative (G&A)"])
		self.assertIn("General & Administrative", ga)
		self.assertIn("General & Administrartive", ga, "HR's sheet carries this typo")

	def test_every_claim_type_still_names_at_least_one_account(self):
		for claim_type, value in MAPPING.items():
			self.assertTrue(gl_names_for(value), claim_type)
