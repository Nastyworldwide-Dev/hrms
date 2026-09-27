"""A request's story, read from the history Frappe already keeps (alpha.13 slice 1).

Every request doctype has track_changes on, so each save writes a Version row
whose JSON records what changed. The timeline reads only the decision lines —
status and docstatus — and says them in the employee's words: "Sent",
"Approved by W0 approver", "Not approved by W0 approver — <reason>".

Evidence, 26 Sep 2026, test site: Version for HR-LAP-2026-00045 holds
{"changed": [["status", "Open", "Rejected"], ["docstatus", 0, 1]]}, owner
nadi.w0.approver, 24 Sep 17:58.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/api/test_request_history.py
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _frappe_stub

_frappe_stub.install()

from hrms.api.request_history import history_steps

SENT = "2026-09-24 09:12:00"
DECIDED = "2026-09-24 17:58:25"


def version(changed, owner, when):
	return {
		"data": json.dumps({"changed": changed, "added": [], "removed": []}),
		"owner": owner,
		"creation": when,
	}


class TestSteps(unittest.TestCase):
	def test_a_rejected_leave_reads_sent_then_not_approved_with_the_reason(self):
		steps = history_steps(
			created=SENT,
			created_by="emp@x",
			versions=[version([["status", "Open", "Rejected"], ["docstatus", 0, 1]], "boss@x", DECIDED)],
			decision_field="status",
			names={"emp@x": "W0 employee", "boss@x": "W0 approver"},
			reason="Team is short that week",
		)
		self.assertEqual(
			[(s["what"], s["who"], s["when"], s.get("note")) for s in steps],
			[
				("sent", "W0 employee", SENT, None),
				("rejected", "W0 approver", DECIDED, "Team is short that week"),
			],
		)

	def test_an_approval_then_a_cancel_are_two_steps(self):
		steps = history_steps(
			created=SENT,
			created_by="emp@x",
			versions=[
				version([["status", "Open", "Approved"], ["docstatus", 0, 1]], "boss@x", DECIDED),
				version([["docstatus", 1, 2]], "emp@x", "2026-09-25 08:00:00"),
			],
			decision_field="status",
			names={"emp@x": "W0 employee", "boss@x": "W0 approver"},
		)
		self.assertEqual([s["what"] for s in steps], ["sent", "approved", "cancelled"])

	def test_expense_claims_decide_on_approval_status(self):
		steps = history_steps(
			created=SENT,
			created_by="emp@x",
			versions=[version([["approval_status", "Draft", "Approved"]], "boss@x", DECIDED)],
			decision_field="approval_status",
			names={},
		)
		self.assertEqual(steps[-1]["what"], "approved")

	def test_other_edits_are_not_steps(self):
		steps = history_steps(
			created=SENT,
			created_by="emp@x",
			versions=[version([["description", "a", "b"]], "emp@x", DECIDED)],
			decision_field="status",
			names={},
		)
		self.assertEqual([s["what"] for s in steps], ["sent"])

	def test_a_login_is_never_shown(self):
		steps = history_steps(
			created=SENT,
			created_by="emp@x",
			versions=[version([["status", "Open", "Approved"]], "boss@x", DECIDED)],
			decision_field="status",
			names={},
		)
		self.assertTrue(all("@" not in (s["who"] or "") for s in steps))

	def test_steps_are_oldest_first_whatever_order_they_arrive_in(self):
		steps = history_steps(
			created=SENT,
			created_by="emp@x",
			versions=[
				version([["docstatus", 1, 2]], "emp@x", "2026-09-25 08:00:00"),
				version([["status", "Open", "Approved"]], "boss@x", DECIDED),
			],
			decision_field="status",
			names={},
		)
		self.assertEqual([s["what"] for s in steps], ["sent", "approved", "cancelled"])


class TestHistoryBelongsToThisDocument(unittest.TestCase):
	"""Measured on the test site, 27 Sep 2026: HR-LAP-2026-00045 was created at
	17:58:04, but Version rows under that name went back to 09:09 — earlier
	documents deleted and re-made under the same name. Version rows are keyed by
	name, so they outlive the document they described. History older than the
	document cannot be its own."""

	def test_a_version_older_than_the_document_is_not_its_history(self):
		steps = history_steps(
			created=SENT,
			created_by="emp@x",
			versions=[
				version([["status", "Open", "Approved"]], "boss@x", "2026-09-24 08:00:00"),
				version([["status", "Open", "Rejected"]], "boss@x", DECIDED),
			],
			decision_field="status",
			names={},
		)
		self.assertEqual([s["what"] for s in steps], ["sent", "rejected"])


class TestTheEndpointIsFenced(unittest.TestCase):
	def test_it_reads_through_the_same_fence_as_the_request(self):
		src = (pathlib.Path(__file__).resolve().parent / "request_history.py").read_text()
		self.assertIn('@frappe.whitelist(methods=["GET", "POST"])', src)
		self.assertIn("_request_read_allowed(", src)
		self.assertIn("frappe.PermissionError", src)
		self.assertIn("get_rejection_reason(", src)


if __name__ == "__main__":
	unittest.main()


class TestTheReasonBelongsToThisDocument(unittest.TestCase):
	"""Same re-used-name class as the history: a rejection reason is a Comment
	keyed by name, so a new request re-using a deleted one's name would show the
	old reason. Only a comment made on or after this document counts."""

	def test_the_reason_query_is_bounded_by_the_document_s_creation(self):
		src = (pathlib.Path(__file__).resolve().parent / "approval.py").read_text()
		body = src[src.index("def get_rejection_reason") : src.index("def _check_review_revision")]
		self.assertIn('"creation": (">=", doc.creation)', body)
