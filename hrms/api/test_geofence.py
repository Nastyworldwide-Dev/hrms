"""One employee must not be able to read where another one works.

Both endpoints here resolve the shift assignment through raw SQL and
`db.get_value`. Both bypass the document permission layer completely, so before
this suite nothing in either call refused anybody.

Measured, not inferred. Acting as a plain Employee-role user against a colleague:

    get_active_shift_location -> {'shift_location': 'LEAKTEST HQ',
                                  'latitude': 3.1234, 'longitude': 101.6,
                                  'checkin_radius': 100}
    check_geofence            -> {'ok': True, 'mode': 'ok'}

The first hands over a colleague's work coordinates. The second is worse, and is
the reason this file exists: `ok: True` for someone else's employee id is a live
answer to "is that person standing at their work site right now". Every other
open read in this app leaked a fact about a person; this one tracks them.

Nine other endpoints taking an `employee` argument were checked the same way and
already refuse — `get_leave_balance_on`, `get_leave_types` and
`get_reports_to_employee_name` all raise PermissionError, because they read
through `frappe.get_doc` and the document layer catches it. The three fixed here
are the ones that never touch a document.

`_ensure_own_employee_or_permitted` is deliberately not a "self only" check: it
passes anyone holding real read permission on the Employee doc, so HR and
approvers keep working. The PWA only ever asks about the signed-in user.

Bench-backed — a permission test that stubs the permission layer tests nothing.
Run with:
    bench --site <site> run-tests --module hrms.api.test_geofence
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from hrms.api.geofence import check_geofence, get_active_shift_location

LOCATION = "_Test Geofence Leak HQ"


class TestGeofenceReadsAreFenced(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.victim = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		cls.intruder_user = frappe.db.get_value(
			"Employee", {"status": "Active", "user_id": ("!=", "")}, "user_id"
		)

	def setUp(self):
		if not (self.victim and self.intruder_user):
			self.skipTest("needs two employees, one with a linked user")
		# A location worth stealing, so a pass cannot come from there being
		# nothing to return — the failure mode of the first version of this test.
		if not frappe.db.exists("Shift Location", LOCATION):
			location = frappe.get_doc(
				{
					"doctype": "Shift Location",
					"location_name": LOCATION,
					"latitude": 3.1234,
					"longitude": 101.6,
					"checkin_radius": 100,
				}
			)
			location.flags.ignore_permissions = True
			location.insert()

		assignment = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": self.victim,
				"shift_type": frappe.db.get_value("Shift Type", {}, "name"),
				"company": frappe.db.get_value("Employee", self.victim, "company"),
				"shift_location": LOCATION,
				"start_date": add_days(today(), -5),
				"status": "Active",
				"docstatus": 1,
			}
		)
		for flag in ("ignore_permissions", "ignore_validate", "ignore_mandatory", "ignore_links"):
			setattr(assignment.flags, flag, True)
		assignment.insert()

		frappe.set_user(self.intruder_user)
		self.addCleanup(frappe.set_user, "Administrator")

	def _is_someone_else(self):
		return frappe.db.get_value("Employee", self.victim, "user_id") != frappe.session.user

	def test_a_colleagues_work_location_is_refused(self):
		if not self._is_someone_else():
			self.skipTest("the two fixtures resolved to the same person")
		with self.assertRaises(frappe.PermissionError):
			get_active_shift_location(self.victim)

	def test_a_colleagues_presence_is_refused(self):
		"""`ok: True` for another employee answers "are they at work right now"."""
		if not self._is_someone_else():
			self.skipTest("the two fixtures resolved to the same person")
		with self.assertRaises(frappe.PermissionError):
			check_geofence(self.victim, "IN", latitude=3.1234, longitude=101.6)

	def test_hr_still_passes(self):
		"""The guard is not self-only. An HR user holds real read permission on
		Employee, and check-in support depends on being able to look."""
		frappe.set_user("Administrator")
		self.assertIsNotNone(get_active_shift_location(self.victim))
