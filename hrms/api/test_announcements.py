# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The announcement board's fence and its counts.

The board is the first thing on Home, and it is the first feature in this app
where HR addresses a SUBSET of people by name. Two ways to get that wrong:
showing somebody another team's notice, and failing to show somebody their
own. Both are tested here, and the audience rule is a pure function precisely
so it can be exercised without a database.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.announcements import (
	acknowledge,
	audience_matches,
	get_announcement,
	get_outstanding,
	get_reach,
	home_announcements,
	list_announcements,
)
from hrms.tests.test_utils import create_company


class TestAudienceRule(FrappeTestCase):
	"""The fence as arithmetic. No site state, so a failure here is the rule
	being wrong rather than a fixture being odd."""

	def setUp(self):
		self.reader = frappe._dict(
			{"name": "HR-EMP-1", "company": "Acme", "department": "Sales - A", "branch": "KL"}
		)

	def test_everyone_means_everyone(self):
		self.assertTrue(audience_matches("Everyone", None, self.reader))
		# ...even if a value was left behind by an earlier edit.
		self.assertTrue(audience_matches("Everyone", "Other Co", self.reader))

	def test_a_target_must_match(self):
		self.assertTrue(audience_matches("Company", "Acme", self.reader))
		self.assertFalse(audience_matches("Company", "Other Co", self.reader))
		self.assertTrue(audience_matches("Department", "Sales - A", self.reader))
		self.assertFalse(audience_matches("Department", "Ops - A", self.reader))
		self.assertTrue(audience_matches("Branch", "KL", self.reader))
		self.assertFalse(audience_matches("Branch", "JB", self.reader))

	def test_a_targeted_announcement_with_no_target_is_hidden(self):
		"""A misconfiguration must fail CLOSED. Treating a blank target as
		"everyone" is how a department notice reaches the whole company."""
		for audience in ("Company", "Department", "Branch"):
			self.assertFalse(audience_matches(audience, None, self.reader))
			self.assertFalse(audience_matches(audience, "", self.reader))

	def test_an_unknown_audience_is_hidden(self):
		"""A new option added to the Select without a rule here must hide the
		announcement, never show it to everybody."""
		self.assertFalse(audience_matches("Region", "North", self.reader))

	def test_a_reader_missing_the_field_does_not_match(self):
		"""An employee with no department is not in every department."""
		bare = frappe._dict({"name": "X", "company": None, "department": None, "branch": None})
		self.assertFalse(audience_matches("Department", "Sales - A", bare))
		self.assertFalse(audience_matches("Company", "Acme", bare))


class TestAnnouncementBoard(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")

		self.company = create_company("_Test Announcements").name
		self.dept = self._department("Sales ANN")
		self.other_dept = self._department("Ops ANN")

		self.user = "ann_reader@example.com"
		self.other_user = "ann_other@example.com"
		self.employee = make_employee(self.user, company=self.company)
		self.other = make_employee(self.other_user, company=self.company)
		frappe.db.set_value("Employee", self.employee, "department", self.dept)
		frappe.db.set_value("Employee", self.other, "department", self.other_dept)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _department(self, name):
		existing = frappe.db.exists("Department", {"department_name": name, "company": self.company})
		if existing:
			return existing
		return (
			frappe.get_doc({"doctype": "Department", "department_name": name, "company": self.company})
			.insert(ignore_permissions=True)
			.name
		)

	def _announce(self, **kwargs):
		doc = frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": kwargs.pop("title", "Canteen closed"),
				"category": kwargs.pop("category", "Notice"),
				"audience": kwargs.pop("audience", "Everyone"),
				"published": kwargs.pop("published", 1),
				"body": kwargs.pop("body", "<p>Tuesday</p>"),
				**kwargs,
			}
		)
		return doc.insert(ignore_permissions=True)

	# --- what reaches whom -------------------------------------------------

	def test_an_employee_sees_a_general_announcement(self):
		self._announce(title="Payday moved")
		frappe.set_user(self.user)
		titles = [row["title"] for row in list_announcements()["announcements"]]
		self.assertIn("Payday moved", titles)

	def test_a_department_announcement_reaches_only_that_department(self):
		self._announce(title="Sales huddle", audience="Department", audience_value=self.dept)
		frappe.set_user(self.user)
		self.assertIn("Sales huddle", [r["title"] for r in list_announcements()["announcements"]])
		frappe.set_user(self.other_user)
		self.assertNotIn("Sales huddle", [r["title"] for r in list_announcements()["announcements"]])

	def test_an_unpublished_announcement_reaches_nobody(self):
		"""The draft state has to be real, or HR cannot write anything without
		it being live the moment they save."""
		self._announce(title="Still drafting", published=0)
		frappe.set_user(self.user)
		self.assertEqual(list_announcements()["announcements"], [])

	def test_it_disappears_on_its_own(self):
		"""The whole reason publish_until is mandatory: nobody has to remember
		to take a notice down, so the board never rots."""
		self._announce(
			title="Last week's notice",
			publish_from=add_days(nowdate(), -20),
			publish_until=add_days(nowdate(), -1),
		)
		frappe.set_user(self.user)
		self.assertEqual(list_announcements()["announcements"], [])

	def test_it_does_not_appear_before_its_date(self):
		self._announce(
			title="Next month",
			publish_from=add_days(nowdate(), 5),
			publish_until=add_days(nowdate(), 30),
		)
		frappe.set_user(self.user)
		self.assertEqual(list_announcements()["announcements"], [])

	def test_the_audience_is_not_disclosed(self):
		"""HOW the fence decided is not the reader's business — a department
		name is another team's information."""
		self._announce(title="Sales huddle", audience="Department", audience_value=self.dept)
		frappe.set_user(self.user)
		row = list_announcements()["announcements"][0]
		self.assertNotIn("audience", row)
		self.assertNotIn("audience_value", row)

	# --- reading -----------------------------------------------------------

	def test_opening_a_card_marks_it_read_once(self):
		doc = self._announce(title="Read me")
		frappe.set_user(self.user)
		self.assertEqual(list_announcements()["unread"], 1)
		get_announcement(doc.name)
		get_announcement(doc.name)
		self.assertEqual(list_announcements()["unread"], 0)
		self.assertEqual(
			frappe.db.count("HR Announcement Read", {"announcement": doc.name, "employee": self.employee}),
			1,
			"reading twice is not two readings",
		)

	def test_the_body_is_refused_for_an_announcement_not_addressed_to_you(self):
		doc = self._announce(title="Ops only", audience="Department", audience_value=self.other_dept)
		frappe.set_user(self.user)
		self.assertRaises(frappe.PermissionError, get_announcement, doc.name)

	def test_a_refused_read_leaves_no_trace(self):
		"""A read row for something the caller cannot see would hand HR a
		compliance number about a person who never saw the notice."""
		doc = self._announce(title="Ops only", audience="Department", audience_value=self.other_dept)
		frappe.set_user(self.user)
		with self.assertRaises(frappe.PermissionError):
			get_announcement(doc.name)
		self.assertEqual(frappe.db.count("HR Announcement Read", {"announcement": doc.name}), 0)

	def test_a_non_string_name_is_refused_at_the_boundary(self):
		frappe.set_user(self.user)
		for value in ({"name": ("like", "%")}, [], "", "   ", None):
			with self.assertRaises((frappe.PermissionError, frappe.ValidationError, TypeError)):
				get_announcement(value)

	# --- acknowledgement ---------------------------------------------------

	def test_acknowledging_records_who_and_when(self):
		doc = self._announce(title="Safety policy", category="Policy", acknowledge_required=1)
		frappe.set_user(self.user)
		acknowledge(doc.name)
		row = frappe.db.get_value(
			"HR Announcement Read",
			{"announcement": doc.name, "employee": self.employee},
			["acknowledged", "acknowledged_on"],
			as_dict=True,
		)
		self.assertTrue(row.acknowledged)
		self.assertIsNotNone(row.acknowledged_on)

	def test_you_cannot_acknowledge_something_that_never_asked(self):
		"""Otherwise a report can claim compliance for a notice that had no
		requirement."""
		doc = self._announce(title="Canteen closed")
		frappe.set_user(self.user)
		self.assertRaises(frappe.ValidationError, acknowledge, doc.name)

	def test_you_cannot_acknowledge_somebody_else_s_notice(self):
		doc = self._announce(
			title="Ops policy",
			audience="Department",
			audience_value=self.other_dept,
			acknowledge_required=1,
		)
		frappe.set_user(self.user)
		self.assertRaises(frappe.PermissionError, acknowledge, doc.name)

	def test_an_unacknowledged_notice_stays_at_the_top_of_home(self):
		"""The behaviour acknowledgement exists for: it does not go away by
		being scrolled past."""
		self._announce(title="Old news", publish_from=add_days(nowdate(), -3))
		policy = self._announce(title="Safety policy", category="Policy", acknowledge_required=1)
		frappe.set_user(self.user)
		first = home_announcements()["announcements"][0]
		self.assertEqual(first["title"], "Safety policy")
		self.assertTrue(first["needs_acknowledgement"])
		acknowledge(policy.name)
		self.assertFalse(
			next(row for row in home_announcements()["announcements"] if row["name"] == policy.name)[
				"needs_acknowledgement"
			]
		)

	# --- home block --------------------------------------------------------

	def test_home_shows_three_and_counts_the_rest(self):
		"""Home is not a noticeboard. A block that grows without bound pushes
		the check-in button below the fold. Up to three (alpha.7 §10.2, owner
		25 Sep: a short vertical list, no carousel)."""
		for i in range(5):
			self._announce(title=f"Notice {i}")
		frappe.set_user(self.user)
		home = home_announcements()
		self.assertEqual(len(home["announcements"]), 3)
		self.assertEqual(home["more"], 2)

	def test_unread_leads(self):
		read_one = self._announce(title="Already read")
		self._announce(title="Not yet read")
		frappe.set_user(self.user)
		get_announcement(read_one.name)
		titles = [row["title"] for row in home_announcements()["announcements"]]
		self.assertEqual(titles[0], "Not yet read")

	# --- fail closed -------------------------------------------------------

	def test_a_user_with_no_employee_sees_an_empty_board(self):
		"""Not an unfiltered one. Every fence in this app fails closed and this
		is the shape that would make it fail open."""
		email = "ann_no_employee@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "No Employee",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		self._announce(title="Everyone sees this")
		frappe.set_user(email)
		self.assertEqual(list_announcements()["announcements"], [])
		self.assertEqual(home_announcements()["announcements"], [])


class TestAnnouncementDocument(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		self.company = create_company("_Test Announcements").name

	def _announce(self, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": kwargs.pop("title", "Notice"),
				"category": "Notice",
				"audience": "Everyone",
				**kwargs,
			}
		).insert(ignore_permissions=True)

	def test_dates_default_so_hr_never_has_to_think_about_expiry(self):
		doc = self._announce()
		self.assertEqual(str(doc.publish_from), nowdate())
		self.assertEqual(str(doc.publish_until), add_days(nowdate(), 14))

	def test_an_announcement_cannot_end_before_it_starts(self):
		self.assertRaises(
			frappe.ValidationError,
			self._announce,
			publish_from=nowdate(),
			publish_until=add_days(nowdate(), -1),
		)

	def test_only_one_announcement_is_pinned(self):
		"""Two pinned notices are two things claiming to be the most important,
		which is the same as none."""
		first = self._announce(title="First", pinned=1)
		second = self._announce(title="Second", pinned=1)
		self.assertFalse(frappe.db.get_value("HR Announcement", first.name, "pinned"))
		self.assertTrue(frappe.db.get_value("HR Announcement", second.name, "pinned"))

	def test_a_targeted_announcement_needs_a_target(self):
		self.assertRaises(frappe.ValidationError, self._announce, audience="Company")

	def test_a_target_that_does_not_exist_is_refused(self):
		"""`audience_value` is a typed name rather than a validated Link — a
		Dynamic Link cannot work here, because Frappe resolves its target during
		_validate_links(), before any controller hook runs. So the existence
		check is ours, and without it a typo publishes an announcement addressed
		to nobody, silently, with no way for HR to tell that from "not read
		yet"."""
		self.assertRaises(
			frappe.ValidationError,
			self._announce,
			audience="Department",
			audience_value="No Such Department - XX",
		)

	def test_switching_back_to_everyone_clears_the_target(self):
		"""Otherwise a company-wide notice silently keeps a department filter
		from before the audience was changed."""
		doc = self._announce(audience="Company", audience_value=self.company)
		doc.audience = "Everyone"
		doc.save(ignore_permissions=True)
		self.assertFalse(doc.audience_value)

	def test_deleting_an_announcement_removes_its_read_rows(self):
		doc = self._announce()
		frappe.get_doc(
			{
				"doctype": "HR Announcement Read",
				"announcement": doc.name,
				"employee": make_employee("ann_del@example.com", company=self.company),
			}
		).insert(ignore_permissions=True)
		doc.delete(ignore_permissions=True)
		self.assertEqual(frappe.db.count("HR Announcement Read", {"announcement": doc.name}), 0)


class TestAnnouncementReach(FrappeTestCase):
	"""Did the notice land.

	The plan named exactly one HR report — "read by 31 of 44" — because it is
	the only one anybody asks for, and it shipped without one: HR published
	into silence with no way to tell a notice nobody read from a notice nobody
	needed.
	"""

	def setUp(self):
		frappe.db.delete("HR Announcement Read")
		frappe.db.delete("HR Announcement")
		self.company = create_company("_Test Reach").name
		self.hr_user = "reach_hr@example.com"
		self.staff_user = "reach_staff@example.com"
		self.hr = make_employee(self.hr_user, company=self.company)
		self.staff = make_employee(self.staff_user, company=self.company)
		frappe.get_doc("User", self.hr_user).add_roles("HR Manager")
		self.doc = frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": "Safety policy",
				"category": "Policy",
				"audience": "Everyone",
				"published": 1,
				"acknowledge_required": 1,
				"body": "<p>read me</p>",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _as_hr(self, fn, *args):
		frappe.set_user(self.hr_user)
		try:
			return fn(*args)
		finally:
			frappe.set_user("Administrator")

	def test_hr_gets_the_one_number_that_matters(self):
		reach = self._as_hr(get_reach, self.doc.name)
		self.assertGreater(reach["audience_count"], 0, "there is a denominator")
		self.assertEqual(reach["read_count"], 0, "and nobody has read it yet")

	def test_reading_moves_the_number(self):
		frappe.set_user(self.staff_user)
		get_announcement(self.doc.name)
		frappe.set_user("Administrator")
		self.assertEqual(self._as_hr(get_reach, self.doc.name)["read_count"], 1)

	def test_confirming_is_counted_separately_from_reading(self):
		"""They are different facts. Somebody who opened a policy and did not
		confirm it has read it and not agreed to it, and a report that merges
		the two tells HR the opposite of what it means."""
		frappe.set_user(self.staff_user)
		get_announcement(self.doc.name)
		frappe.set_user("Administrator")
		reach = self._as_hr(get_reach, self.doc.name)
		self.assertEqual(reach["read_count"], 1)
		self.assertEqual(reach["acknowledged_count"], 0)

		frappe.set_user(self.staff_user)
		acknowledge(self.doc.name)
		frappe.set_user("Administrator")
		self.assertEqual(self._as_hr(get_reach, self.doc.name)["acknowledged_count"], 1)

	def test_the_numerator_can_never_exceed_the_denominator(self):
		"""Counted against the CURRENT audience. Somebody who has left, or
		moved department since reading, is no longer part of "31 of 44" — and
		without that the numerator can exceed the denominator, which makes the
		whole line untrustworthy the first time HR sees it."""
		frappe.set_user(self.staff_user)
		get_announcement(self.doc.name)
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.staff, "status", "Left")
		try:
			reach = self._as_hr(get_reach, self.doc.name)
			self.assertLessEqual(reach["read_count"], reach["audience_count"])
		finally:
			frappe.db.set_value("Employee", self.staff, "status", "Active")

	def test_an_employee_cannot_read_the_reach(self):
		"""How many people are in a department, and who has not read something,
		are roster facts. An employee has no business with either."""
		frappe.set_user(self.staff_user)
		self.assertRaises(frappe.PermissionError, get_reach, self.doc.name)
		self.assertRaises(frappe.PermissionError, get_outstanding, self.doc.name)

	def test_who_has_not_confirmed_is_named(self):
		"""HR chases people by name."""
		names = self._as_hr(get_outstanding, self.doc.name)
		self.assertIn(
			frappe.db.get_value("Employee", self.staff, "employee_name"),
			names,
			"somebody who has not confirmed is on the list",
		)

	def test_outstanding_is_refused_for_a_notice_that_never_asked(self):
		"""On an ordinary notice this is a list of everybody who has not
		happened to open the app, which is not a thing anybody should be
		chased about."""
		plain = frappe.get_doc(
			{
				"doctype": "HR Announcement",
				"title": "Canteen closed",
				"category": "Notice",
				"audience": "Everyone",
				"published": 1,
			}
		).insert(ignore_permissions=True)
		frappe.set_user(self.hr_user)
		try:
			self.assertRaises(frappe.ValidationError, get_outstanding, plain.name)
		finally:
			frappe.set_user("Administrator")

	def test_the_audience_rule_is_not_reimplemented(self):
		"""Two implementations of "who does this reach" would give HR a
		denominator that disagrees with who actually gets the card, and the
		number's whole value is that it can be trusted."""
		import inspect

		from hrms.api import announcements

		source = inspect.getsource(announcements._audience_employees)
		for audience in ("Company", "Department", "Branch"):
			self.assertIn(audience, source, f"{audience} is handled")
