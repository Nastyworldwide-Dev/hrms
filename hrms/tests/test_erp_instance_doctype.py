"""Structural guards for the HRMS ERP Instance doctype pair.

This doctype backs the PWA's "Open my ERP" button: each ERPNext instance is
registered once with the companies it serves, and an employee is redirected to
the instance serving their own company.

The checks here are the ones that would otherwise only surface as a failed
`bench migrate` on a live site — a Table field pointing at a child doctype that
does not exist, or an `autoname` referencing a missing field, both abort install.

Pure static check over the repo's JSON — no bench, no site.
"""

import json
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]

PARENT = HRMS_ROOT / "hr/doctype/hrms_erp_instance/hrms_erp_instance.json"
CHILD = HRMS_ROOT / "hr/doctype/hrms_erp_instance_company/hrms_erp_instance_company.json"


def _load(path):
	return json.loads(path.read_text(encoding="utf-8"))


class TestERPInstanceDoctype(unittest.TestCase):
	def setUp(self):
		self.parent = _load(PARENT)
		self.child = _load(CHILD)

	def test_child_table_is_marked_istable(self):
		# A Table target without istable=1 installs but can never hold rows.
		self.assertEqual(self.child.get("istable"), 1)

	def test_table_field_points_at_the_child_doctype(self):
		table_fields = [f for f in self.parent["fields"] if f["fieldtype"] == "Table"]
		self.assertTrue(table_fields, "parent must carry the companies table")
		for field in table_fields:
			self.assertEqual(
				field.get("options"),
				self.child["name"],
				f"{field['fieldname']} points at a doctype that is not the child table",
			)

	def test_autoname_field_exists(self):
		autoname = self.parent.get("autoname", "")
		if not autoname.startswith("field:"):
			return
		target = autoname.split(":", 1)[1]
		fieldnames = {f["fieldname"] for f in self.parent["fields"]}
		self.assertIn(target, fieldnames, "autoname references a field that does not exist")

	def test_autoname_field_is_required_and_unique(self):
		# Frappe silently produces colliding names otherwise.
		target = self.parent["autoname"].split(":", 1)[1]
		field = next(f for f in self.parent["fields"] if f["fieldname"] == target)
		self.assertTrue(field.get("reqd"), "autoname field must be mandatory")
		self.assertTrue(field.get("unique"), "autoname field must be unique")

	def test_field_order_matches_fields(self):
		ordered = set(self.parent.get("field_order") or [])
		defined = {f["fieldname"] for f in self.parent["fields"]}
		self.assertEqual(ordered, defined, "field_order and fields disagree")

	def test_staff_can_read_but_not_write(self):
		# Staff only need to resolve their own instance URL.
		employee = [p for p in self.parent["permissions"] if p.get("role") == "Employee"]
		self.assertTrue(employee, "Employee role needs read access for the PWA button")
		for perm in employee:
			self.assertTrue(perm.get("read"))
			self.assertFalse(perm.get("write"), "staff must not edit instance config")
			self.assertFalse(perm.get("create"))
			self.assertFalse(perm.get("delete"))


if __name__ == "__main__":
	unittest.main()
