"""HR reaches "Unclaimable Days" next to Shift Attendance (workspace card + sidebar).

PYTHONPATH=. python3 hrms/tests/test_unclaimable_days_link.py
"""

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKSPACE_JSON = ROOT / "hr/workspace/shift_&_attendance/shift_&_attendance.json"
SIDEBAR_JSON = ROOT / "workspace_sidebar/shift_&_attendance.json"
REPORT_NAME = "Unclaimable Days"
ANCHOR = "Shift Attendance"


def _cards(links):
	cards, current = {}, None
	for row in links:
		if row["type"] == "Card Break":
			current = row["label"]
			cards[current] = {"break": row, "links": []}
		elif current is not None:
			cards[current]["links"].append(row)
	return cards


class TestShippedJson(unittest.TestCase):
	def test_reports_card_links_it_once_right_after_shift_attendance(self):
		cards = _cards(json.loads(WORKSPACE_JSON.read_text())["links"])
		card = next(c for c in cards.values() if any(r["link_to"] == ANCHOR for r in c["links"]))
		targets = [r["link_to"] for r in card["links"]]
		self.assertEqual(targets.count(REPORT_NAME), 1)
		self.assertEqual(targets[targets.index(REPORT_NAME) - 1], ANCHOR)

	def test_every_card_count_matches_its_rows(self):
		for label, card in _cards(json.loads(WORKSPACE_JSON.read_text())["links"]).items():
			with self.subTest(card=label):
				self.assertEqual(card["break"]["link_count"], len(card["links"]))

	def test_it_is_a_script_report_row(self):
		row = next(
			r for r in json.loads(WORKSPACE_JSON.read_text())["links"] if r.get("link_to") == REPORT_NAME
		)
		self.assertEqual(
			(row["link_type"], row["is_query_report"], row["report_ref_doctype"]), ("Report", 1, "Attendance")
		)

	def test_sidebar_places_it_after_shift_attendance(self):
		targets = [i.get("link_to") for i in json.loads(SIDEBAR_JSON.read_text())["items"]]
		self.assertEqual(targets.count(REPORT_NAME), 1)
		self.assertEqual(targets[targets.index(REPORT_NAME) - 1], ANCHOR)

	def test_patch_registered_once(self):
		lines = (ROOT / "patches.txt").read_text().splitlines()
		self.assertEqual(
			sum(1 for l in lines if l.startswith("hrms.patches.v16_0.add_unclaimable_days_link")), 1
		)


if __name__ == "__main__":
	unittest.main()
