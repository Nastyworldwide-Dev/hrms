# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.utils.email_flush import FLUSH_JOB_ID, flush_email_queue_after_commit


class TestEmailFlush(FrappeTestCase):
	def test_enqueues_background_flush_after_commit(self):
		with patch("hrms.utils.email_flush.frappe.enqueue") as enqueue:
			flush_email_queue_after_commit()

		enqueue.assert_called_once()
		args, kwargs = enqueue.call_args
		self.assertEqual(args[0], "frappe.email.queue.flush")
		self.assertEqual(kwargs["queue"], "short")
		self.assertTrue(kwargs["enqueue_after_commit"])
		self.assertTrue(kwargs["deduplicate"])
		self.assertEqual(kwargs["job_id"], FLUSH_JOB_ID)

	def test_enqueue_failure_does_not_raise(self):
		with patch("hrms.utils.email_flush.frappe.enqueue", side_effect=Exception("redis down")):
			flush_email_queue_after_commit()  # must not raise

	def test_pwa_notification_insert_schedules_flush(self):
		with patch(
			"hrms.hr.doctype.pwa_notification.pwa_notification.flush_email_queue_after_commit"
		) as flush:
			notification = frappe.new_doc("PWA Notification")
			notification.from_user = "Administrator"
			notification.to_user = "Administrator"
			notification.message = "test instant email flush"
			notification.insert(ignore_permissions=True)

		flush.assert_called_once()
