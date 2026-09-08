"""Realtime and native push leave only after the row they announce is committed.

N08 (8 Sep 2026 notifications audit): the remote check-in realtime event was
published without after_commit, so an approver's screen could reload before
the SQL was visible — or for a transaction that later rolled back — and the
native web push was sent synchronously inside after_insert, reaching the
relay (and the device) before the notification row existed for anyone else,
while also adding network latency to the originating write.

Now: the realtime event is queued for commit, and the push is a background
job enqueued after commit under one job id per notification (deduplicated),
whose worker re-reads the committed row. Bench-free: the publisher and the
queue are the boundaries.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_notification_delivery_after_commit.py
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.hr.doctype.pwa_notification import pwa_notification as module
from hrms.overrides import remote_checkin_request_hooks as hooks


class TestRealtimeWaitsForCommit(unittest.TestCase):
	def test_the_remote_request_event_is_published_after_commit(self):
		request = types.SimpleNamespace(
			name="RCR-1", status="Pending", log_type="OUT", get=lambda k, d=None: 0
		)
		with patch.object(frappe, "publish_realtime", create=True) as publish:
			hooks._send_push("approver@example.com", "subject", "body", request)
		self.assertEqual(publish.call_count, 1)
		kwargs = publish.call_args.kwargs
		self.assertEqual(kwargs["event"], "hrms:remote_checkin_request")
		self.assertEqual(kwargs["user"], "approver@example.com")
		self.assertTrue(kwargs.get("after_commit"), "the event must wait for the transaction to commit")


def _notification(name="PWAN-1", to_user="approver@example.com"):
	doc = module.PWANotification.__new__(module.PWANotification)
	doc.__dict__.update(
		name=name,
		to_user=to_user,
		reference_document_type="OT Request",
		reference_document_name="OT-1",
		message="m",
	)
	return doc


class TestNativePushIsQueuedAfterCommit(unittest.TestCase):
	def test_after_insert_enqueues_one_deduplicated_job_and_sends_nothing_itself(self):
		doc = _notification()
		with (
			patch.object(frappe, "enqueue", create=True) as enqueue,
			patch.object(module, "flush_email_queue_after_commit"),
			patch.object(module.PWANotification, "send_push_notification") as send_now,
		):
			doc.after_insert()
		send_now.assert_not_called()
		self.assertEqual(enqueue.call_count, 1)
		kwargs = enqueue.call_args.kwargs
		self.assertEqual(
			enqueue.call_args.args[0], "hrms.hr.doctype.pwa_notification.pwa_notification.send_push_for"
		)
		self.assertEqual(kwargs["name"], "PWAN-1")
		self.assertTrue(kwargs["enqueue_after_commit"])
		self.assertTrue(kwargs["deduplicate"])
		self.assertIn("PWAN-1", kwargs["job_id"], "one job per notification, so a retry cannot double-send")

	def test_the_worker_re_reads_the_committed_row_and_sends_from_it(self):
		doc = _notification()
		with (
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(module.PWANotification, "send_push_notification") as send,
		):
			module.send_push_for("PWAN-1")
		send.assert_called_once_with()

	def test_a_row_that_never_committed_sends_nothing(self):
		with (
			patch.object(frappe.db, "exists", return_value=False),
			patch.object(frappe, "get_doc") as get_doc,
			patch.object(module.PWANotification, "send_push_notification") as send,
		):
			module.send_push_for("PWAN-GONE")
		get_doc.assert_not_called()
		send.assert_not_called()

	def test_a_queue_failure_never_breaks_the_insert(self):
		doc = _notification()
		with (
			patch.object(frappe, "enqueue", create=True, side_effect=RuntimeError("redis down")),
			patch.object(module, "flush_email_queue_after_commit"),
			patch.object(doc, "log_error", create=True) as log_error,
		):
			doc.after_insert()  # must not raise
		log_error.assert_called_once()


if __name__ == "__main__":
	unittest.main()
