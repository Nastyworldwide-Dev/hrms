"""You may look up your own manager, not everybody's.

This module is a contact directory and that is not in question: `list_hr_contacts`
publishes HR's cards to all staff on purpose, because unreachable HR is worse than
a published mobile number.

`get_reporting_manager` is different only in that it takes an employee id. It
reads through `db.get_value`, which never consults the permission layer, so any
signed-in employee could pass any colleague's id and receive that colleague's
manager — including `personal_email` and `cell_number` from `_CONTACT_FIELDS`.
Employee ids are sequential, so "who reports to whom, with personal phone
numbers" was enumerable by anyone with a login.

The fence deliberately keeps the feature whole. Your own manager still resolves,
because the guard passes the caller's own employee; HR and approvers still resolve
anyone's, because it passes real read permission on the Employee doc. Only the
third case — an ordinary employee asking about somebody else — is refused, and
nothing in the PWA does that.

Bench-backed: a permission test that stubs the permission layer tests nothing.
Run with:
    bench --site <site> run-tests --module hrms.api.test_hr_contacts
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.api.hr_contacts import get_reporting_manager


class TestReportingManagerLookupIsFenced(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.intruder_user = frappe.db.get_value(
			"Employee", {"status": "Active", "user_id": ("!=", "")}, "user_id"
		)
		cls.victim = frappe.db.get_value(
			"Employee", {"status": "Active", "user_id": ("in", ("", None))}, "name"
		)

	def setUp(self):
		if not (self.intruder_user and self.victim):
			self.skipTest("needs one employee with a user and one without")
		frappe.set_user(self.intruder_user)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_another_employees_manager_is_refused(self):
		"""Refused BEFORE the reports_to lookup, so a null answer cannot be mistaken
		for a fence — the first version of this test passed for that reason."""
		with self.assertRaises(frappe.PermissionError):
			get_reporting_manager(self.victim)

	def test_your_own_manager_still_resolves(self):
		"""The whole feature. A fence that breaks this is worse than the leak."""
		own = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if not own:
			self.skipTest("the session user has no employee")
		# No exception is the assertion; None is a valid answer (no reports_to).
		get_reporting_manager(own)

	def test_no_argument_still_means_me(self):
		"""The PWA calls this with no argument at all, and that path must not have
		acquired a fence it cannot satisfy."""
		get_reporting_manager()

	def test_hr_may_still_look_anyone_up(self):
		frappe.set_user("Administrator")
		get_reporting_manager(self.victim)
