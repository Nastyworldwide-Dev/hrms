# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The document's own rules.

The API's fence — who may SEE an announcement — lives with the API, in
hrms/api/test_announcements.py, because that is where the decision is made.
What is here is what the document enforces regardless of who is asking: the
dates, the single pin, and the target.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.tests.test_utils import create_company


class TestHRAnnouncement(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		self.company = create_company("_Test Announcement Doc").name

	def _announce(self, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": kwargs.pop("title", "Notice"),
				"category": kwargs.pop("category", "Notice"),
				"audience": kwargs.pop("audience", "Everyone"),
				**kwargs,
			}
		).insert(ignore_permissions=True)

	def test_dates_default_so_nobody_has_to_remember_expiry(self):
		"""The reason publish_until is mandatory. A noticeboard where somebody
		has to remember to take things down is a noticeboard that rots, and
		nobody ever remembers."""
		doc = self._announce()
		self.assertEqual(str(doc.publish_from), nowdate())
		self.assertEqual(str(doc.publish_until), add_days(nowdate(), 14))

	def test_it_cannot_stop_before_it_starts(self):
		self.assertRaises(
			frappe.ValidationError,
			self._announce,
			publish_from=nowdate(),
			publish_until=add_days(nowdate(), -1),
		)

	def test_only_one_announcement_is_pinned(self):
		"""Two pinned notices are two things claiming to be the most important,
		which is the same as none — and the PWA gives the pin one slot, so a
		second would displace the first with no way to tell which won."""
		first = self._announce(title="First", pinned=1)
		second = self._announce(title="Second", pinned=1)
		self.assertFalse(frappe.db.get_value("HR Announcement", first.name, "pinned"))
		self.assertTrue(frappe.db.get_value("HR Announcement", second.name, "pinned"))

	def test_unpinning_does_not_re_run_the_other_document(self):
		"""The unpin is a db_set rather than a save: saving would re-run the
		other document's validate, which would re-enforce this same rule and
		recurse."""
		first = self._announce(title="First", pinned=1)
		before = frappe.db.get_value("HR Announcement", first.name, "modified")
		self._announce(title="Second", pinned=1)
		self.assertEqual(
			before,
			frappe.db.get_value("HR Announcement", first.name, "modified"),
			"unpinning must not touch the other document's timestamp",
		)

	def test_a_targeted_announcement_needs_a_target(self):
		self.assertRaises(frappe.ValidationError, self._announce, audience="Company")

	def test_a_target_that_does_not_exist_is_refused(self):
		"""`audience_value` is a typed name, not a Link — a Dynamic Link cannot
		work here because Frappe resolves its target during _validate_links(),
		before any controller hook runs. So the existence check is ours, and
		without it a typo publishes a notice addressed to nobody, silently,
		which HR cannot tell apart from "not read yet"."""
		self.assertRaises(
			frappe.ValidationError,
			self._announce,
			audience="Department",
			audience_value="No Such Department - XX",
		)

	def test_switching_back_to_everyone_clears_the_target(self):
		"""Otherwise a company-wide notice silently keeps the filter from
		before the audience was changed."""
		doc = self._announce(audience="Company", audience_value=self.company)
		doc.audience = "Everyone"
		doc.save(ignore_permissions=True)
		self.assertFalse(doc.audience_value)

	def test_deleting_takes_its_read_rows_with_it(self):
		"""Left behind they are an unreadable audit trail: a name, a date and a
		dangling link."""
		doc = self._announce()
		frappe.get_doc(
			{
				"doctype": "HR Announcement Read",
				"announcement": doc.name,
				"employee": make_employee("ann_doc_del@example.com", company=self.company),
			}
		).insert(ignore_permissions=True)
		doc.delete(ignore_permissions=True)
		self.assertEqual(frappe.db.count("HR Announcement Read", {"announcement": doc.name}), 0)
