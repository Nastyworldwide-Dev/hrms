# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""alpha.7 announcement API (plan §4, §10.1).

- Cards carry the Summary, the Cover image, Urgent and the version.
- A must-read counts as confirmed only for the version the person confirmed:
  changed words ask again (4.3).
- must_read(): the notices this person must still confirm, urgent first, then
  oldest, so the app can open them full screen on launch (4.4).
- Publishing sends the push ONCE, to the notice's audience, with the title and
  the Summary (§10.1).
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.announcements import acknowledge, get_announcement, home_announcements, must_read
from hrms.tests.test_utils import create_company


class TestAnnouncementsAlpha7(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		self.company = create_company("_Test Announcements A7API").name
		self.user = "ann7_reader@example.com"
		self.employee = make_employee(self.user, company=self.company)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _announce(self, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": kwargs.pop("title", "Canteen closed"),
				"category": "Notice",
				"audience": "Everyone",
				"published": kwargs.pop("published", 1),
				"body": kwargs.pop("body", "<p>Tuesday</p>"),
				"summary": kwargs.pop("summary", "Closed on Tuesday."),
				"publish_from": kwargs.pop("publish_from", nowdate()),
				"notify_on_publish": kwargs.pop("notify_on_publish", 0),
				**kwargs,
			}
		).insert(ignore_permissions=True)

	def test_cards_carry_summary_cover_urgent_version(self):
		self._announce(cover_image="/files/c.png", urgent=1)
		frappe.set_user(self.user)
		card = home_announcements()["announcements"][0]
		self.assertEqual(card["summary"], "Closed on Tuesday.")
		self.assertEqual(card["cover_image"], "/files/c.png")
		self.assertTrue(card["urgent"])
		self.assertEqual(card["version"], 1)

	def test_changed_words_ask_again(self):
		doc = self._announce(acknowledge_required=1, body="<p>Rule.</p>")
		frappe.set_user(self.user)
		acknowledge(doc.name)
		self.assertFalse(home_announcements()["announcements"][0]["needs_acknowledgement"])
		frappe.set_user("Administrator")
		doc.reload()
		doc.body = "<p>Rule, changed.</p>"
		doc.save(ignore_permissions=True)
		frappe.set_user(self.user)
		self.assertTrue(home_announcements()["announcements"][0]["needs_acknowledgement"])
		self.assertFalse(get_announcement(doc.name)["acknowledged"])

	def test_must_read_is_urgent_first_then_oldest(self):
		old = self._announce(title="Old", acknowledge_required=1, publish_from=add_days(nowdate(), -3))
		new = self._announce(title="New", acknowledge_required=1)
		urgent = self._announce(title="Urgent", acknowledge_required=1, urgent=1)
		self._announce(title="Plain")
		frappe.set_user(self.user)
		self.assertEqual([r["name"] for r in must_read()], [urgent.name, old.name, new.name])
		acknowledge(old.name)
		self.assertEqual([r["name"] for r in must_read()], [urgent.name, new.name])

	def test_publishing_notifies_once(self):
		with patch("hrms.hr.doctype.hr_announcement.hr_announcement.frappe.enqueue") as enqueue:
			doc = self._announce(published=0, notify_on_publish=1)
			self.assertFalse(enqueue.called, "a draft notifies nobody")
			doc.published = 1
			doc.save(ignore_permissions=True)
			self.assertEqual(enqueue.call_count, 1)
			doc.title = "Canteen closed Tuesday"
			doc.save(ignore_permissions=True)
			self.assertEqual(enqueue.call_count, 1, "an edit after publishing does not notify again")

	def test_notify_off_sends_nothing(self):
		with patch("hrms.hr.doctype.hr_announcement.hr_announcement.frappe.enqueue") as enqueue:
			self._announce(notify_on_publish=0)
			self.assertFalse(enqueue.called)


class TestAnnouncementRemind(FrappeTestCase):
	"""HR chases the people who have not confirmed (alpha.7 4.6)."""

	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		self.company = create_company("_Test Announcements A7R").name
		self.done = make_employee("ann7_done@example.com", company=self.company)
		self.todo = make_employee("ann7_todo@example.com", company=self.company)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_remind_pushes_only_to_those_who_have_not_confirmed(self):
		from hrms.api.announcements import remind_outstanding

		doc = frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": "Policy",
				"category": "Policy",
				"audience": "Company",
				"audience_value": self.company,
				"published": 1,
				"acknowledge_required": 1,
				"notify_on_publish": 0,
				"summary": "Please confirm.",
				"body": "<p>x</p>",
			}
		).insert(ignore_permissions=True)
		frappe.set_user("ann7_done@example.com")
		acknowledge(doc.name)
		frappe.set_user("Administrator")
		with patch("hrms.api.announcements._push_to_users") as push:
			result = remind_outstanding(doc.name)
		users = push.call_args.args[1]
		self.assertIn("ann7_todo@example.com", users)
		self.assertNotIn("ann7_done@example.com", users)
		self.assertEqual(result["reminded"], len(users))

	def test_remind_is_for_hr_only(self):
		from hrms.api.announcements import remind_outstanding

		frappe.set_user("ann7_todo@example.com")
		with self.assertRaises(frappe.PermissionError):
			remind_outstanding("anything")


class TestConfirmationsReport(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		self.company = create_company("_Test Announcements A7Rep").name
		self.a = make_employee("ann7_rep_a@example.com", company=self.company)
		self.b = make_employee("ann7_rep_b@example.com", company=self.company)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_one_row_per_person_with_confirmed_state(self):
		from hrms.hr.report.announcement_confirmations.announcement_confirmations import execute

		doc = frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": "Policy",
				"category": "Policy",
				"audience": "Company",
				"audience_value": self.company,
				"published": 1,
				"acknowledge_required": 1,
				"notify_on_publish": 0,
				"summary": "Confirm.",
				"body": "<p>x</p>",
			}
		).insert(ignore_permissions=True)
		frappe.set_user("ann7_rep_a@example.com")
		acknowledge(doc.name)
		frappe.set_user("Administrator")
		_, rows = execute({"announcement": doc.name})
		by = {r["employee"]: r["confirmed"] for r in rows}
		self.assertEqual(by[self.a], "Yes")
		self.assertEqual(by[self.b], "No")
		_, todo = execute({"announcement": doc.name, "show": "Not confirmed"})
		self.assertEqual([r["employee"] for r in todo], [self.b])


class TestPreviewAsStaff(FrappeTestCase):
	"""HR sees the real app screen for a notice, even unpublished, and no read
	is recorded (alpha.7 4.2)."""

	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		self.company = create_company("_Test Announcements A7P").name
		self.staff = "ann7_prev_staff@example.com"
		make_employee(self.staff, company=self.company)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _draft(self):
		return frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": "Draft",
				"category": "Notice",
				"audience": "Everyone",
				"published": 0,
				"summary": "Not out yet.",
				"body": "<p>x</p>",
			}
		).insert(ignore_permissions=True)

	def test_hr_previews_a_draft_and_nothing_is_recorded(self):
		doc = self._draft()
		out = get_announcement(doc.name, preview=1)
		self.assertTrue(out["preview"])
		self.assertEqual(out["title"], "Draft")
		self.assertFalse(frappe.db.exists("HR Announcement Read", {"announcement": doc.name}))

	def test_staff_cannot_preview(self):
		doc = self._draft()
		frappe.set_user(self.staff)
		with self.assertRaises(frappe.PermissionError):
			get_announcement(doc.name, preview=1)
