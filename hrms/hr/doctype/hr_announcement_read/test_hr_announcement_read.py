# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""One row per employee per announcement, and only one."""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.tests.test_utils import create_company


class TestHRAnnouncementRead(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		self.company = create_company("_Test Announcement Read").name
		self.employee = make_employee("ann_read@example.com", company=self.company)
		self.other = make_employee("ann_read_two@example.com", company=self.company)
		self.announcement = frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": "Notice",
				"category": "Notice",
				"audience": "Everyone",
			}
		).insert(ignore_permissions=True)

	def _read(self, employee):
		return frappe.get_doc(
			{
				"doctype": "HR Announcement Read",
				"announcement": self.announcement.name,
				"employee": employee,
			}
		).insert(ignore_permissions=True)

	def test_reading_twice_is_not_two_readings(self):
		"""An employee who opens a card on their phone and again on a laptop
		must count once, or "read by 31 of 44" is a number nobody can trust."""
		self._read(self.employee)
		self.assertRaises(frappe.DuplicateEntryError, self._read, self.employee)

	def test_two_people_reading_is_two_rows(self):
		"""The uniqueness is per PAIR. A rule that keyed on the announcement
		alone would record the first reader and silently drop everybody else."""
		self._read(self.employee)
		self._read(self.other)
		self.assertEqual(frappe.db.count("HR Announcement Read", {"announcement": self.announcement.name}), 2)

	def test_it_is_not_a_child_table(self):
		"""Deliberate: a child table is rewritten wholesale on every parent
		save, so an HR edit to the wording would drop every read record."""
		meta = frappe.get_meta("HR Announcement Read")
		self.assertFalse(meta.istable, "read rows must survive an edit to the announcement")
