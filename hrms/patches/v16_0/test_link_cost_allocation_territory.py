"""Rows saved as a Cost Center take the Territory of the same name (owner, 11 Nov 2026).

python3 -m pytest -q hrms/patches/v16_0/test_link_cost_allocation_territory.py
"""

import unittest

from hrms.patches.v16_0.link_cost_allocation_territory import plan_links

ROWS = [
	{"name": "R1", "cost_center": "MALAYSIA - NHSB"},
	{"name": "R2", "cost_center": "CEOF - NHSB"},
	{"name": "R3", "cost_center": "PFME - NHSB"},
]
NAMES = {"MALAYSIA - NHSB": "MALAYSIA", "CEOF - NHSB": "CEOF", "PFME - NHSB": "PFME"}


class TestPlanLinks(unittest.TestCase):
	def test_the_same_name_in_any_case_is_linked(self):
		plan = plan_links(ROWS, NAMES, ["Malaysia", "CEOF"])
		self.assertEqual(plan, {"R1": "Malaysia", "R2": "CEOF"})

	def test_no_match_is_left_alone(self):
		self.assertNotIn("R3", plan_links(ROWS, NAMES, ["Malaysia", "CEOF"]))

	def test_two_territories_with_the_name_are_not_guessed(self):
		self.assertEqual(plan_links(ROWS[:1], NAMES, ["Malaysia", "MALAYSIA"]), {})

	def test_an_empty_territory_list_links_nothing(self):
		# migrate runs before the first sync fills the list
		self.assertEqual(plan_links(ROWS, NAMES, []), {})


if __name__ == "__main__":
	unittest.main()
