# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import os
import unittest
from datetime import datetime

from hrms.regional.united_arab_emirates.wps import build_sif_content

EDR_ROWS = [
	{
		"labour_card_number": "12345678901234",
		"agent_id": "123456789",
		"account_number": "0012345678901",
		"start_date": "2026-06-01",
		"end_date": "2026-06-30",
		"days": 30,
		"fixed_income": 5700.0,
		"variable_income": 0,
	},
	{
		"labour_card_number": "98765432109876",
		"agent_id": "987654321",
		"account_number": "0098765432101",
		"start_date": "2026-06-01",
		"end_date": "2026-06-30",
		"days": 28,
		"fixed_income": 4300.5,
		"variable_income": 200.0,
	},
]


class TestWPSSIFBuilder(unittest.TestCase):
	"""Pure file-format assembly — no site needed."""

	def build(self):
		return build_sif_content(
			EDR_ROWS,
			employer_unique_id="1234567890123",
			payer_bank_code="123456789",
			creation_datetime=datetime(2026, 7, 14, 9, 30, 0),
			salary_month="2026-06-01",
		)

	def test_edr_record_format(self):
		lines = self.build().splitlines()
		self.assertEqual(len(lines), 3)  # 2 EDR + 1 SCR

		first = lines[0].split(",")
		self.assertEqual(first[0], "EDR")
		self.assertEqual(first[1], "12345678901234")
		self.assertEqual(first[2], "123456789")
		self.assertEqual(first[4], "01062026")  # ddmmyyyy
		self.assertEqual(first[5], "30062026")
		self.assertEqual(first[6], "30")
		self.assertEqual(first[7], "5700.00")
		self.assertEqual(first[8], "0.00")
		self.assertEqual(len(first), 10)

	def test_scr_record_totals_and_count(self):
		scr = self.build().splitlines()[-1].split(",")
		self.assertEqual(scr[0], "SCR")
		self.assertEqual(scr[1], "1234567890123")
		self.assertEqual(scr[3], "14072026")  # creation date ddmmyyyy
		self.assertEqual(scr[4], "0930")  # creation time HHMM
		self.assertEqual(scr[5], "062026")  # salary month MMYYYY
		self.assertEqual(scr[6], "2")  # EDR count
		self.assertEqual(scr[7], "10200.50")  # 5700.00 + 4300.50 + 200.00

	def test_empty_rows_still_produce_scr(self):
		content = build_sif_content(
			[],
			employer_unique_id="1234567890123",
			payer_bank_code="123456789",
			creation_datetime=datetime(2026, 7, 14, 9, 30, 0),
			salary_month="2026-06-01",
		)
		scr = content.splitlines()[-1].split(",")
		self.assertEqual(scr[6], "0")
		self.assertEqual(scr[7], "0.00")


class TestUAEComponentData(unittest.TestCase):
	def test_salary_components_file_is_well_formed(self):
		path = os.path.join(os.path.dirname(__file__), "data", "salary_components.json")
		with open(path) as f:
			components = json.load(f)

		names = {c["salary_component"] for c in components}
		self.assertIn("GPSSA Employee (UAE)", names)
		self.assertIn("GPSSA Employer (UAE)", names)
		for component in components:
			if "Employer" in component["salary_component"]:
				self.assertEqual(component.get("statistical_component"), 1)
				self.assertEqual(component.get("do_not_include_in_total"), 1)
