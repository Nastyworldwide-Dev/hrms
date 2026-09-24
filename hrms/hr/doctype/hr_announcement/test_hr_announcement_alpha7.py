# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""alpha.7 announcement fields (plan §4, §10.1; owner answers 25 Sep).

HR controls each place a notice appears: a Summary (Home preview AND the push
body, plain text, max 140), an optional Cover image, Urgent, Notify on
publish. A required notice's version is raised when its words change, so
people confirm the new text; "Minor fix" skips that. Pasted images are public
(owner Q7) so staff can see them.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.tests.test_utils import create_company


class TestAnnouncementAlpha7(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		create_company("_Test Announcement A7")

	def _announce(self, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": kwargs.pop("title", "Notice"),
				"category": kwargs.pop("category", "Notice"),
				"audience": kwargs.pop("audience", "Everyone"),
				"summary": kwargs.pop("summary", "A short line."),
				**kwargs,
			}
		).insert(ignore_permissions=True)

	def test_pasted_images_are_public(self):
		self.assertTrue(frappe.get_meta("HR Announcement").make_attachments_public)

	def test_summary_is_capped_and_filled_from_the_body_when_empty(self):
		with self.assertRaises(frappe.ValidationError):
			self._announce(summary="x" * 141)
		self.assertEqual(self._announce(summary="Plain words.").summary, "Plain words.")
		# A notice from before the field, or a hurried save: the body's
		# opening words, never an empty preview or a blocked edit.
		long = "<p>" + ("word " * 60) + "</p>"
		doc = self._announce(summary="", published=1, body=long)
		self.assertTrue(doc.summary.endswith("…"))
		self.assertLessEqual(len(doc.summary), 140)

	def test_summary_is_plain_text(self):
		doc = self._announce(summary="<b>Bold</b> & <i>it</i>")
		self.assertEqual(doc.summary, "Bold & it")

	def test_notify_on_publish_is_on_by_default_urgent_off(self):
		doc = self._announce()
		self.assertEqual(doc.notify_on_publish, 1)
		self.assertEqual(doc.urgent, 0)

	def test_changing_a_published_required_notice_raises_its_version(self):
		doc = self._announce(acknowledge_required=1, published=1, body="<p>Rule one.</p>")
		self.assertEqual(doc.version, 1)
		doc.body = "<p>Rule one, changed.</p>"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.version, 2)

	def test_a_minor_fix_keeps_the_version_and_clears_itself(self):
		doc = self._announce(acknowledge_required=1, published=1, body="<p>Rule one.</p>")
		doc.body = "<p>Rule one.</p><p>(typo)</p>"
		doc.minor_fix = 1
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.version, 1)
		self.assertEqual(doc.minor_fix, 0, "a minor fix applies to one save only")

	def test_one_read_row_per_person(self):
		meta = frappe.get_meta("HR Announcement Read")
		self.assertTrue(
			any(set(i) == {"announcement", "employee"} for i in _unique_indexes()),
			"unique (announcement, employee)",
		)
		self.assertTrue(meta.get_field("acknowledged_version"))


def _unique_indexes():
	rows = frappe.db.sql("SHOW INDEX FROM `tabHR Announcement Read` WHERE Non_unique = 0", as_dict=True)
	by = {}
	for r in rows:
		by.setdefault(r.Key_name, []).append(r.Column_name)
	return [v for k, v in by.items() if k != "PRIMARY"]
