# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from hrms.tests.utils import HRMSTestSuite


class TestPWANotification(HRMSTestSuite):
	def test_notification_link_routes_by_reference_doctype(self):
		"""Push payloads deep-link to the request's PWA detail page.

		Only Leave, Expense, Remote Checkin and Issue used to be mapped, so a tap on
		an OT Request, Shift Request or Replacement Leave Claim push landed on the
		PWA home (runtime crawl, 15 Sep 2026). Doctypes without a PWA detail route
		still fall back to home — Employee Advance deliberately so: it stays hidden
		in the PWA (owner ruling, 15 Sep 2026).
		"""
		base_url = f"{frappe.utils.get_url()}/hrms"
		cases = [
			("Leave Application", "LEAVE-0001", f"{base_url}/leave-applications/LEAVE-0001"),
			("Expense Claim", "EXP-0001", f"{base_url}/expense-claims/EXP-0001"),
			("Attendance Request", "ATT-0001", f"{base_url}/attendance-requests/ATT-0001"),
			("Shift Request", "SR-0001", f"{base_url}/shift-requests/SR-0001"),
			("Shift Assignment", "SA-0001", f"{base_url}/shift-assignments/SA-0001"),
			("OT Request", "OT-0001", f"{base_url}/ot-requests/OT-0001"),
			# No banked overtime (HR policy, 23 Sep 2026): no PWA screen, so Home.
			("Replacement Leave Claim", "RLC-0001", base_url),
			("Employee Issue", "ISS-0001", f"{base_url}/issues/ISS-0001"),
			("Remote Checkin Request", "RCR-0001", f"{base_url}/notifications"),
			("Compensatory Leave Request", "CLR-0001", base_url),
			("Shift Swap Request", "SSR-0001", base_url),
			("Employee Advance", "ADV-0001", base_url),
			(None, None, base_url),
		]
		for reference_doctype, reference_name, expected in cases:
			notification = frappe.new_doc("PWA Notification")
			notification.reference_document_type = reference_doctype
			notification.reference_document_name = reference_name
			self.assertEqual(
				notification.get_notification_link(),
				expected,
				msg=f"wrong link for {reference_doctype}",
			)
