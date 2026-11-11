"""An announcement for several companies, departments or branches (owner, 11 Nov 2026).

HR picks the targets from a list, as many as needed. They are kept one per line
in the existing "Which one" field, so an announcement saved before keeps its
single name and nothing is migrated.

    python3 -m pytest -q hrms/api/test_announcement_many_targets.py
"""

import json
import pathlib
import unittest

import frappe

from hrms.api.announcements import audience_matches, audience_targets

ROOT = pathlib.Path(__file__).resolve().parents[1]
READER = frappe._dict(company="Acme", department="Sales - A", branch="KL")


class TestManyTargets(unittest.TestCase):
	def test_one_name_as_before(self):
		self.assertEqual(audience_targets("Acme"), ["Acme"])
		self.assertTrue(audience_matches("Company", "Acme", READER))

	def test_several_companies_reach_each_of_them(self):
		value = "Other Co\nAcme"
		self.assertEqual(audience_targets(value), ["Other Co", "Acme"])
		self.assertTrue(audience_matches("Company", value, READER))
		self.assertFalse(audience_matches("Company", "Other Co\nThird Co", READER))

	def test_departments_and_branches_too(self):
		self.assertTrue(audience_matches("Department", "Ops - A\nSales - A", READER))
		self.assertTrue(audience_matches("Branch", "JB\nKL", READER))

	def test_blank_lines_and_spaces_are_ignored(self):
		self.assertEqual(audience_targets("  Acme \n\n Other Co \n"), ["Acme", "Other Co"])

	def test_an_empty_list_still_shows_it_to_nobody(self):
		self.assertFalse(audience_matches("Company", "\n \n", READER))

	def test_a_comma_inside_a_name_is_not_a_separator(self):
		self.assertEqual(
			audience_targets("Nora Luna (MY) Sdn. Bhd., Branch"), ["Nora Luna (MY) Sdn. Bhd., Branch"]
		)


class TestTheFormOffersAList(unittest.TestCase):
	def _field(self):
		meta = json.loads((ROOT / "hr/doctype/hr_announcement/hr_announcement.json").read_text())
		return {f["fieldname"]: f for f in meta["fields"]}["audience_value"]

	def test_which_one_is_a_text_field_holding_one_name_per_line(self):
		self.assertEqual(self._field()["fieldtype"], "Small Text")

	def test_the_form_draws_a_pick_list_of_the_real_records(self):
		js = (ROOT / "hr/doctype/hr_announcement/hr_announcement.js").read_text()
		self.assertIn("MultiSelectPills", js)
		self.assertIn("audience_value", js)


if __name__ == "__main__":
	unittest.main()
