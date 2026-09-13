"""Regression tests for hrms.hr.shift_rules (the location/department Shift
Assignment rule layer). Co-located with the module it exercises; reuses the
Shift Location fixtures from the doctype test module so nothing is duplicated.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.shift_location.test_shift_rules import make_department, make_shift_location
from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type
from hrms.hr.shift_rules import reconcile_employee_shift

COMPANY = "_Test Company"


class TestShiftRulesRosterPrecedence(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Shift Assignment")
		self.shift_day = setup_shift_type(shift_type="Rule Shift Day")
		self.shift_night = setup_shift_type(
			shift_type="Rule Shift Night", start_time="19:00:00", end_time="03:30:00"
		)
		self.warehouse = make_department("Rule Warehouse")  # no rule dept -> site default
		# site default rule = night
		self.location = make_shift_location("Rule Loc HQ", [{"shift_type": self.shift_night.name}])
		self.employee = make_employee("shift_rule_roster_emp@example.com", company=COMPANY)
		self._set_employee(department=self.warehouse, shift_location=self.location)

	def _set_employee(self, **values):
		for field, value in values.items():
			frappe.db.set_value("Employee", self.employee, field, value)
		frappe.clear_document_cache("Employee", self.employee)

	def _make_manual(self, start_off, end_off):
		frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": self.employee,
				"company": COMPANY,
				"shift_type": self.shift_day.name,
				"start_date": add_days(nowdate(), start_off),
				"end_date": add_days(nowdate(), end_off),
				"status": "Active",
			}
		).insert().submit()

	def _autos(self):
		return frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"docstatus": 1,
				"status": "Active",
				"created_by_shift_rule": 1,
			},
			pluck="name",
		)

	def test_lapsed_manual_roster_blocks_rule_takeover(self):
		"""The real defect: a variable-shift employee's manual roster segment
		ended yesterday, so the rule layer imposed the open-ended site-default
		(night) shift into the gap — "the system changed her to the night shift
		mid-month, until end of month". A non-rule assignment that ended within
		one roster cycle must keep the rule layer standing down."""
		self._make_manual(-7, -1)  # ended yesterday
		self.assertEqual(reconcile_employee_shift(self.employee), "skipped-manual")
		self.assertEqual(self._autos(), [])

	def test_unmanaged_employee_still_rule_managed(self):
		# No manual history at all: the rule layer must still provide a shift.
		self.assertEqual(reconcile_employee_shift(self.employee), "created")
		self.assertEqual(len(self._autos()), 1)

	def test_stale_manual_beyond_window_hands_off_to_rule(self):
		# A roster segment that ended well beyond one cycle is a genuine lapse;
		# the rule layer legitimately takes over.
		self._make_manual(-50, -40)
		self.assertEqual(reconcile_employee_shift(self.employee), "created")
		self.assertEqual(len(self._autos()), 1)

	def _shift_types_covering_today(self):
		"""Every distinct shift type an Active assignment puts on today.

		This, not "is there an open-ended row", is the thing that matters. A row
		that ENDS today still governs today — every Shift Assignment date read in
		this app is inclusive of `end_date` — so an assertion about open-ended
		rows cannot see the hand-off day at all, and stays green while two shift
		types are both claiming it."""
		today = nowdate()
		rows = frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"docstatus": 1,
				"status": "Active",
				"start_date": ["<=", today],
			},
			or_filters=[["end_date", "is", "not set"], ["end_date", ">=", today]],
			fields=["name", "shift_type", "created_by_shift_rule"],
		)
		return sorted({row.shift_type for row in rows}), rows

	def _open_autos(self):
		"""Rule-created assignments with no end date. A weaker check than
		`_shift_types_covering_today`, kept as a second assertion because an
		open-ended rule row left behind is the durable form of the collision."""
		return frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"docstatus": 1,
				"status": "Active",
				"created_by_shift_rule": 1,
				"end_date": ["is", "not set"],
			},
			pluck="name",
		)

	def test_manual_takeover_closes_the_rules_own_open_rows(self):
		"""Standing down means closing your own rows — in EVERY branch.

		The roster and schedule branches both close their auto rows before
		handing off, because an open-ended rule row left beside a manual one is
		two Active open-ended assignments of different shift types for one
		employee. That is the precondition for the split-day damage: an evening
		punch resolves against the night shift while the morning punch resolves
		against the day shift, the day is split across two Attendance rows, and
		the hours land in the wrong places.

		The manual branch returned without closing anything, so every employee
		who moved from rule-managed to manually rostered kept a live rule row
		underneath the manual one.
		"""
		self.assertEqual(reconcile_employee_shift(self.employee), "created")
		self.assertEqual(len(self._open_autos()), 1)

		# Manual assignment covering today — "manual wins" from here on.
		self._make_manual(0, 30)

		self.assertEqual(reconcile_employee_shift(self.employee), "skipped-manual")

		shift_types, rows = self._shift_types_covering_today()
		self.assertEqual(
			len(shift_types),
			1,
			f"two shift types govern today ({shift_types}) — that is the split-day "
			f"precondition, whether the leftover row is open-ended or merely ends today: "
			f"{[(r.name, r.shift_type, r.created_by_shift_rule) for r in rows]}",
		)
		self.assertEqual(
			self._open_autos(),
			[],
			"the rule layer stood down but left its own open-ended row Active beside the manual one",
		)

	def test_a_lapsed_roster_keeps_the_rules_shift_rather_than_none(self):
		"""Standing down for a LAPSED roster must not strip the person bare.

		The second half of the manual-wins condition fires when a manual segment
		ended recently and has NOT been replaced — so there is no manual row
		covering today to take over. Closing the rule's row there would leave the
		employee with no shift at all: every punch stamped off-shift, no
		attendance auto-marked and no overtime, which is simply a different kind
		of damage in place of the one being removed. Through a roster gap the
		rule's own row is the only coverage they have."""
		self.assertEqual(reconcile_employee_shift(self.employee), "created")
		self._make_manual(-7, -1)  # a segment that ended yesterday, nothing after it

		self.assertEqual(reconcile_employee_shift(self.employee), "skipped-manual")
		shift_types, _rows = self._shift_types_covering_today()
		self.assertEqual(len(shift_types), 1, "a roster gap must leave exactly the rule's own shift standing")

	def test_roster_managed_employee_is_skipped_and_auto_closed(self):
		"""The durable declaration: an employee flagged roster_managed (variable
		shift, e.g. Handa) is owned by the roster. The rule layer must never
		impose a standing shift on them, and must close any auto assignment it
		created before the flag was set."""
		reconcile_employee_shift(self.employee)  # rule creates an auto row first
		self.assertEqual(len(self._autos()), 1)

		self._set_employee(roster_managed=1)
		action = reconcile_employee_shift(self.employee)
		self.assertEqual(action, "skipped-roster")
		open_autos = frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"docstatus": 1,
				"status": "Active",
				"created_by_shift_rule": 1,
				"end_date": ["is", "not set"],
			},
		)
		self.assertEqual(open_autos, [])
