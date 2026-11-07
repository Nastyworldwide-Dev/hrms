"""Letters Issued on Employee (HR, 7 Nov 2026).

* Each row's SharePoint link must be https:// on a sharepoint.com host.
* Rows are kept newest first by Date Issued.
* The table sits after the Cost Tag/Center Allocation table at permlevel 1, the
  level HR roles already hold on Employee (re-asserted every migrate by
  hrms.utils.permlevel_guard), so staff never see letters.

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_employee_letters.py
"""

import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
from _fake_document import FakeDocument

import frappe

from hrms.utils import employee_letters as letters

HRMS = pathlib.Path(__file__).resolve().parent.parent
GOOD = "https://verifica.sharepoint.com/sites/hr/letter.pdf"


def _row(idx, date, link=GOOD):
	return FakeDocument(
		"Employee Letter Issued", idx=idx, date_issued=date, letter_type="Offer Letter", sharepoint_link=link
	)


def _employee(*rows):
	return FakeDocument("Employee", name="EMP-1", letters_issued=list(rows))


class TestSharePointLink(unittest.TestCase):
	def refused(self, link):
		with self.assertRaises(frappe.ValidationError):
			letters.validate_letters(_employee(_row(1, "2026-11-01", link)))

	def test_a_sharepoint_link_is_accepted(self):
		letters.validate_letters(_employee(_row(1, "2026-11-01")))

	def test_the_bare_sharepoint_host_is_accepted(self):
		letters.validate_letters(_employee(_row(1, "2026-11-01", "https://sharepoint.com/x")))

	def test_http_is_refused(self):
		self.refused("http://verifica.sharepoint.com/x")

	def test_another_site_is_refused(self):
		self.refused("https://drive.google.com/x")

	def test_sharepoint_only_in_the_path_is_refused(self):
		self.refused("https://evil.com/sharepoint.com/x")

	def test_a_lookalike_host_is_refused(self):
		self.refused("https://sharepoint.com.evil.com/x")

	def test_a_host_merely_ending_in_the_name_is_refused(self):
		self.refused("https://notsharepoint.com/x")

	def test_a_blank_link_is_refused(self):
		self.refused("")

	def test_surrounding_spaces_are_trimmed(self):
		row = _row(1, "2026-11-01", "  https://verifica.sharepoint.com/x  ")
		letters.validate_letters(_employee(row))
		self.assertEqual(row.sharepoint_link, "https://verifica.sharepoint.com/x")

	def test_the_error_names_the_row(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			letters.validate_letters(_employee(_row(4, "2026-11-01", "https://x.com")))
		self.assertIn("4", str(ctx.exception))


class TestNewestFirst(unittest.TestCase):
	def test_rows_are_sorted_newest_first_and_renumbered(self):
		old, new, mid = _row(1, "2026-01-05"), _row(2, "2026-11-01"), _row(3, "2026-06-10")
		doc = _employee(old, new, mid)
		letters.validate_letters(doc)
		self.assertEqual(doc.letters_issued, [new, mid, old])
		self.assertEqual([r.idx for r in doc.letters_issued], [1, 2, 3])

	def test_an_empty_table_is_fine(self):
		letters.validate_letters(_employee())


class TestFieldsAndAccess(unittest.TestCase):
	def setUp(self):
		self.fields = {f["fieldname"]: f for f in letters.get_letter_fields()["Employee"]}

	def test_section_then_table_after_the_cost_allocation_table(self):
		section, table = self.fields["letters_issued_section"], self.fields["letters_issued"]
		self.assertEqual(section["fieldtype"], "Section Break")
		self.assertEqual(section["label"], "Letters Issued")
		self.assertEqual(section["insert_after"], "interco_cost_allocation")
		self.assertTrue(section["collapsible"])
		self.assertEqual(table["fieldtype"], "Table")
		self.assertEqual(table["options"], "Employee Letter Issued")
		self.assertEqual(table["insert_after"], "letters_issued_section")

	def test_both_fields_sit_at_permlevel_1(self):
		for field in self.fields.values():
			self.assertEqual(field["permlevel"], 1)

	def test_the_guard_restores_level_1_on_employee(self):
		# level 1 is NOT owned elsewhere, so permlevel_guard keeps HR's rows
		from hrms.utils import permlevel_guard

		self.assertIn("Employee", permlevel_guard.GUARDED_DOCTYPES)
		self.assertNotIn(("Employee", 1), permlevel_guard.OWNED_ELSEWHERE)

	def test_install_path_carries_the_fields(self):
		self.assertIn("get_letter_fields", (HRMS / "setup.py").read_text())

	def test_validate_hook_is_wired(self):
		self.assertIn("hrms.utils.employee_letters.validate_letters", (HRMS / "hooks.py").read_text())

	def test_the_rollout_patch_is_registered(self):
		self.assertIn("hrms.patches.v16_0.add_employee_letters_issued", (HRMS / "patches.txt").read_text())


class TestDoctypes(unittest.TestCase):
	def _load(self, folder):
		return json.loads((HRMS / "hr" / "doctype" / folder / f"{folder}.json").read_text())

	def test_letter_type_is_named_by_its_field(self):
		d = self._load("hr_letter_type")
		self.assertEqual(d["autoname"], "field:letter_type")
		self.assertEqual(d["module"], "HR")
		self.assertFalse(d.get("istable"))
		field = d["fields"][0]
		self.assertEqual((field["fieldname"], field["reqd"], field["unique"]), ("letter_type", 1, 1))

	def test_only_hr_manager_and_system_manager_edit_the_letter_types(self):
		perms = self._load("hr_letter_type")["permissions"]
		writers = {p["role"] for p in perms if p.get("write")}
		self.assertEqual(writers, {"HR Manager", "System Manager"})

	def test_hr_user_can_pick_a_letter_type(self):
		# HR User holds Employee level 1, so they can add rows; the Link needs read
		perms = {p["role"]: p for p in self._load("hr_letter_type")["permissions"]}
		self.assertTrue(perms["HR User"].get("read"))
		self.assertFalse(perms["HR User"].get("write"))

	def test_child_table_fields(self):
		d = self._load("employee_letter_issued")
		self.assertEqual((d["istable"], d["editable_grid"], d["module"]), (1, 1, "HR"))
		f = {x["fieldname"]: x for x in d["fields"]}
		self.assertEqual(
			list(f),
			[
				"date_issued",
				"letter_type",
				"reference_no",
				"subject",
				"sharepoint_link",
				"acknowledged",
				"acknowledged_on",
				"effective_date",
				"issued_by",
				"remarks",
			],
		)
		self.assertEqual(d["field_order"], list(f))
		self.assertEqual(f["letter_type"]["options"], "HR Letter Type")
		self.assertEqual(f["sharepoint_link"]["options"], "URL")
		self.assertEqual(f["acknowledged_on"]["depends_on"], "eval:doc.acknowledged")
		self.assertEqual(f["issued_by"]["options"], "Employee")
		self.assertEqual(f["remarks"]["fieldtype"], "Small Text")
		for name in ("date_issued", "letter_type", "sharepoint_link"):
			self.assertEqual(f[name]["reqd"], 1, name)
		in_list = {n: x.get("columns") for n, x in f.items() if x.get("in_list_view")}
		self.assertEqual(
			in_list,
			{
				"date_issued": 1,
				"letter_type": 2,
				"reference_no": 2,
				"subject": 2,
				"sharepoint_link": 2,
				"acknowledged": 1,
			},
		)


class TestSeed(unittest.TestCase):
	def test_the_sixteen_types_hr_listed(self):
		self.assertEqual(len(letters.LETTER_TYPES), 16)
		self.assertEqual(letters.LETTER_TYPES[0], "Offer Letter")
		self.assertIn("Interim / Pemangku Appointment", letters.LETTER_TYPES)
		self.assertIn("Release / Experience Letter", letters.LETTER_TYPES)
		self.assertEqual(letters.LETTER_TYPES[-1], "Other")

	def test_seed_adds_only_the_missing_ones(self):
		existing = set(letters.LETTER_TYPES) - {"Other"}
		db = MagicMock()
		db.exists.side_effect = lambda dt, name: name in existing
		doc = MagicMock()
		with patch.object(frappe, "db", db), patch.object(frappe, "get_doc", return_value=doc) as get_doc:
			added = letters.seed_letter_types()
		self.assertEqual(added, ["Other"])
		get_doc.assert_called_once_with({"doctype": "HR Letter Type", "letter_type": "Other"})
		doc.insert.assert_called_once_with(ignore_permissions=True)


if __name__ == "__main__":
	unittest.main()
