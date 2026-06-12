# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.hr.doctype.leave_type.leave_type import get_service_based_leave_days

test_records = frappe.get_test_records("Leave Type")


class TestLeaveType(FrappeTestCase):
	def test_service_entitlements_mandatory_when_enabled(self):
		leave_type = new_service_based_leave_type(service_entitlements=[])
		self.assertRaises(frappe.ValidationError, leave_type.insert)

	def test_invalid_service_entitlement_range(self):
		leave_type = new_service_based_leave_type(
			service_entitlements=[{"from_years": 5, "to_years": 2, "leave_days": 10}]
		)
		self.assertRaises(frappe.ValidationError, leave_type.insert)

	def test_overlapping_service_entitlement_ranges(self):
		leave_type = new_service_based_leave_type(
			service_entitlements=[
				{"from_years": 0, "to_years": 5, "leave_days": 10},
				{"from_years": 5, "to_years": 10, "leave_days": 15},
			]
		)
		self.assertRaises(frappe.ValidationError, leave_type.insert)

	def test_get_service_based_leave_days(self):
		leave_type = new_service_based_leave_type(
			service_entitlements=[
				{"from_years": 0, "to_years": 1, "leave_days": 8},
				{"from_years": 2, "to_years": 5, "leave_days": 12},
				{"from_years": 6, "to_years": 99, "leave_days": 16},
			]
		)
		leave_type.insert()

		# completed years of service on 2026-01-01 for someone who joined on 2023-01-15 = 2
		self.assertEqual(get_service_based_leave_days(leave_type.name, "2023-01-15", "2026-01-01"), 12)
		# exactly on the slab boundaries
		self.assertEqual(get_service_based_leave_days(leave_type.name, "2025-06-01", "2026-01-01"), 8)
		self.assertEqual(get_service_based_leave_days(leave_type.name, "2019-01-01", "2026-01-01"), 16)
		# service years not covered by any slab
		leave_type.service_entitlements = leave_type.service_entitlements[1:]
		leave_type.save()
		self.assertIsNone(get_service_based_leave_days(leave_type.name, "2025-06-01", "2026-01-01"))


def new_service_based_leave_type(service_entitlements):
	leave_type_name = "_Test Service Based Leave"
	if frappe.db.exists("Leave Type", leave_type_name):
		frappe.delete_doc("Leave Type", leave_type_name, force=True)

	return frappe.get_doc(
		{
			"doctype": "Leave Type",
			"leave_type_name": leave_type_name,
			"based_on_years_of_service": 1,
			"service_entitlements": service_entitlements,
		}
	)


def create_leave_type(**args):
	args = frappe._dict(args)
	leave_type_name = args.leave_type_name or "_Test Leave Type"
	if frappe.db.exists("Leave Type", leave_type_name):
		frappe.delete_doc("Leave Type", leave_type_name, force=True)

	leave_type = frappe.get_doc(
		{
			"doctype": "Leave Type",
			"leave_type_name": leave_type_name,
			"include_holiday": args.include_holidays or 1,
			"allow_encashment": args.allow_encashment or 0,
			"is_earned_leave": args.is_earned_leave or 0,
			"is_lwp": args.is_lwp or 0,
			"is_ppl": args.is_ppl or 0,
			"is_carry_forward": args.is_carry_forward or 0,
			"expire_carry_forwarded_leaves_after_days": args.expire_carry_forwarded_leaves_after_days or 0,
			"non_encashable_leaves": args.non_encashable_leaves or 5,
			"earning_component": "Leave Encashment",
			"max_leaves_allowed": args.max_leaves_allowed,
			"maximum_carry_forwarded_leaves": args.maximum_carry_forwarded_leaves,
			"allocate_on_day": args.allocate_on_day or "Last Day",
		}
	)

	if leave_type.is_ppl:
		leave_type.fraction_of_daily_salary_per_leave = args.fraction_of_daily_salary_per_leave or 0.5

	leave_type.insert()

	return leave_type
