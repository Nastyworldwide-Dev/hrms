"""The GL pull must find an account whose name differs by punctuation or wording.

Nabil, 11 Sep 2026, third failed attempt: "pull gl from erp didnt do anything to
fill those 2 except the rest... everyone can claim yet its missing in the nadi
pwa. because in desk its missing."

`account_shells.wanted_account_names()` returned the mapped names plus three
capitalisation variants, and the source was queried with
`account_name in (that list)`. So the pull could only ever find an account whose
name it had already guessed EXACTLY. One character out — "General and
Administrative" for "General & Administrative", a trailing "Expenses", a double
space — and the account is invisible to the pull, which then reports "Nothing to
create. Already here: 49" perfectly truthfully, because it never looked.

The consequence runs all the way to the phone: no account, so no Expense Claim
Account row, so `configured_expense_claim_types` drops the type, so Subsidy
Parking and G&A are absent from Nadi and nobody can claim them.

Matching is normalised now: case, "&" against "and", punctuation and repeated
spaces. Anything beyond that is NOT guessed — wiring a claim to the wrong GL
account is worse than leaving it unwired — so a name that resolves to several
candidates is reported with those candidates named.

Pure.
"""

import unittest

from hrms.utils.expense_claim_type_mapping import match_account_name, normalise_account_name


class TestNormaliseAccountName(unittest.TestCase):
	def test_case_and_spacing_do_not_matter(self):
		self.assertEqual(
			normalise_account_name("  Subsidiary   Parking "), normalise_account_name("subsidiary parking")
		)

	def test_ampersand_and_the_word_and_are_the_same_thing(self):
		self.assertEqual(
			normalise_account_name("General & Administrative"),
			normalise_account_name("General and Administrative"),
		)

	def test_punctuation_is_ignored(self):
		self.assertEqual(
			normalise_account_name("Fuel/Mileage Expenses"), normalise_account_name("Fuel Mileage Expenses")
		)

	def test_different_words_stay_different(self):
		self.assertNotEqual(
			normalise_account_name("Subsidiary Parking"), normalise_account_name("Subsidy Parking")
		)


class TestMatchAccountName(unittest.TestCase):
	def test_an_exact_name_matches(self):
		self.assertEqual(
			match_account_name("Subsidiary Parking", {"Subsidiary Parking": "SP - NHSB"}), "SP - NHSB"
		)

	def test_an_ampersand_spelled_out_still_matches(self):
		self.assertEqual(
			match_account_name("General & Administrative", {"General and Administrative": "GA - NHSB"}),
			"GA - NHSB",
		)

	def test_a_case_and_spacing_difference_still_matches(self):
		self.assertEqual(
			match_account_name("Subsidiary Parking", {"SUBSIDIARY  PARKING": "SP - NHSB"}), "SP - NHSB"
		)

	def test_a_genuinely_different_account_is_not_guessed(self):
		self.assertIsNone(match_account_name("Subsidiary Parking", {"Parking & Toll": "PT - NHSB"}))

	def test_an_exact_name_wins_even_when_others_normalise_alike(self):
		# An exact hit is not a guess, so ambiguity below it is irrelevant.
		self.assertEqual(
			match_account_name(
				"General & Administrative",
				{"General & Administrative": "A - NHSB", "General and Administrative": "B - NHSB"},
			),
			"A - NHSB",
		)

	def test_two_near_misses_and_no_exact_hit_are_refused_not_guessed(self):
		# Wiring a claim to the wrong GL account is worse than leaving it unwired.
		self.assertIsNone(
			match_account_name(
				"General & Administrative",
				{"General and Administrative": "A - NHSB", "GENERAL AND ADMINISTRATIVE": "B - NHSB"},
			)
		)

	def test_nothing_to_match_against_is_not_a_match(self):
		self.assertIsNone(match_account_name("Subsidiary Parking", {}))
