# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""SOP Folder (owner request, 27 Oct 2026): a folder is a topic, one SOP sits in
one folder, and a folder that still holds SOPs cannot be deleted.

Pure unit tests (no bench): the controller is driven with `frappe` stubbed, the
doctype files are read as JSON.

    python3 -m pytest -q hrms/hr/doctype/sop_folder/test_sop_folder.py
"""

import json
import pathlib
import types
import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.hr.doctype.sop_folder.sop_folder import SOPFolder

DOCTYPES = pathlib.Path(__file__).resolve().parents[1]
FOLDER_JSON = json.loads((DOCTYPES / "sop_folder" / "sop_folder.json").read_text())
SOP_JSON = json.loads((DOCTYPES / "sop_document" / "sop_document.json").read_text())


def _field(doctype_json, fieldname):
	return next(f for f in doctype_json["fields"] if f["fieldname"] == fieldname)


class TestOnTrash(unittest.TestCase):
	def _trash(self, held):
		"""on_trash for a folder named Safety that holds `held` SOPs; -> (db, throw)."""
		doc = types.SimpleNamespace(name="Safety")
		db = MagicMock()
		db.count.return_value = held
		with (
			patch.object(frappe, "db", db),
			patch("hrms.hr.doctype.sop_folder.sop_folder._", lambda msg: msg),
			patch(
				"hrms.hr.doctype.sop_folder.sop_folder.frappe.throw", side_effect=frappe.ValidationError
			) as throw,
		):
			try:
				SOPFolder.on_trash(doc)
			except frappe.ValidationError:
				pass
		return db, throw

	def test_a_folder_that_holds_sops_cannot_be_deleted(self):
		_db, throw = self._trash(3)
		throw.assert_called_once()

	def test_the_refusal_says_what_to_do_and_how_many(self):
		_db, throw = self._trash(3)
		self.assertEqual(throw.call_args.args[0], "Move its SOPs first. 3 SOP(s) are in this folder.")

	def test_the_count_is_every_sop_in_the_folder_not_only_the_ones_the_caller_sees(self):
		# An HR user fenced to one company still must not delete a folder that
		# holds another company's SOP: the count reads the table, not a fenced list.
		db, _throw = self._trash(0)
		db.count.assert_called_once_with("SOP Document", {"folder": "Safety"})

	def test_an_empty_folder_deletes_quietly(self):
		_db, throw = self._trash(0)
		throw.assert_not_called()


class TestDoctypeFiles(unittest.TestCase):
	def test_the_folder_is_named_by_its_name_and_sorted_by_sort_order(self):
		self.assertEqual(FOLDER_JSON["autoname"], "field:folder_name")
		self.assertEqual(FOLDER_JSON["sort_field"], "sort_order")
		self.assertEqual(FOLDER_JSON["sort_order"], "ASC")
		self.assertEqual(FOLDER_JSON["module"], "HR")

	def test_folder_name_is_required_unique_and_in_the_list(self):
		field = _field(FOLDER_JSON, "folder_name")
		self.assertEqual(field["fieldtype"], "Data")
		self.assertEqual((field.get("reqd"), field.get("unique"), field.get("in_list_view")), (1, 1, 1))

	def test_sort_order_is_an_int_that_starts_at_zero(self):
		field = _field(FOLDER_JSON, "sort_order")
		self.assertEqual(field["fieldtype"], "Int")
		self.assertEqual(str(field.get("default")), "0")

	def test_description_is_small_text(self):
		self.assertEqual(_field(FOLDER_JSON, "description")["fieldtype"], "Small Text")

	def test_hr_manages_folders_and_employees_only_read(self):
		perms = {p["role"]: p for p in FOLDER_JSON["permissions"]}
		self.assertEqual(set(perms), {"System Manager", "HR Manager", "HR User", "Employee"})
		for role in ("System Manager", "HR Manager", "HR User"):
			for right in ("create", "read", "write", "delete"):
				self.assertEqual(perms[role].get(right), 1, f"{role} {right}")
		self.assertEqual(perms["Employee"].get("read"), 1)
		for right in ("create", "write", "delete"):
			self.assertFalse(perms["Employee"].get(right), f"Employee {right}")

	def test_a_folder_can_be_renamed_from_desk(self):
		self.assertEqual(FOLDER_JSON.get("allow_rename"), 1)

	def test_the_sop_carries_an_optional_folder_link_after_the_title(self):
		field = _field(SOP_JSON, "folder")
		self.assertEqual((field["fieldtype"], field["options"]), ("Link", "SOP Folder"))
		self.assertFalse(field.get("reqd"))
		self.assertEqual((field.get("in_list_view"), field.get("in_standard_filter")), (1, 1))
		order = SOP_JSON["field_order"]
		self.assertEqual(order.index("folder"), order.index("title") + 1)
		self.assertGreater(SOP_JSON["modified"], "2026-08-07 10:00:00.000000")


if __name__ == "__main__":
	unittest.main()
