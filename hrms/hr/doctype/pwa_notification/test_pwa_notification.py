# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPWANotification(FrappeTestCase):
	def test_notification_link_routes_by_reference_doctype(self):
		"""Push payloads deep-link per reference doctype; unmapped doctypes fall back to the PWA home."""
		base_url = f"{frappe.utils.get_url()}/hrms"
		cases = [
			("Leave Application", "LEAVE-0001", f"{base_url}/leave-applications/LEAVE-0001"),
			("Expense Claim", "EXP-0001", f"{base_url}/expense-claims/EXP-0001"),
			("Remote Checkin Request", "RCR-0001", f"{base_url}/notifications"),
			("Attendance Request", "ATT-0001", base_url),
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
