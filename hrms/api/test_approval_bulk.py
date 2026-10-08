"""Approve many requests at once (HR, 4 Oct 2026; owner, 5 Oct).

HR: "allow the list to be expanded, filter by request and bulk approve". 51
requests were waiting, oldest since 17 Aug. The page decides one at a time.

check_many tells the approver, BEFORE anything is written, which of the ticked
requests would go through and which would be refused, with the plain reason.
decide_many approves the ones that can, one by one, each in its own savepoint:
one refusal never stops the rest and never leaves a half write. It adds NO rule
of its own — every item goes through `decide`, so nothing is possible in bulk
that the approver could not do one by one.

Reject in bulk (owner, 8 Oct 2026, reversing the 5 Oct "reject stays one by one"):
reject_many is the same loop with status "Rejected" and a reason per request, and every
bulk decision leaves an "Approved in bulk" / "Rejected in bulk" Info comment in its savepoint.

Bench-free: the shared frappe stub, as the other suites here.

	PYTHONPATH=. python3 hrms/api/test_approval_bulk.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

# The shared stub does not define Frappe's lost-transaction errors; a real bench does.
if not isinstance(getattr(frappe, "QueryDeadlockError", None), type):  # the stub answers with a MagicMock
	frappe.QueryDeadlockError = type("QueryDeadlockError", (Exception,), {})
	frappe.QueryTimeoutError = type("QueryTimeoutError", (Exception,), {})

from hrms.api import approval
from hrms.tests._fake_document import FakeDocument


def item(name, doctype="Leave Application", modified="2026-10-01 09:00:00"):
	return {"doctype": doctype, "name": name, "modified": modified}


class _Refusal(frappe.ValidationError):
	pass


class TestCheckMany(unittest.TestCase):
	def _check(self, items, actions, blocked=None, exists=True):
		def decision_actions(doctype, name):
			if name in (blocked or {}):
				return {"actions": ["Rejected"], "modified": "2026-10-01 09:00:00", "blocked": blocked[name]}
			if name in actions:
				return {"actions": ["Approved", "Rejected"], "modified": "2026-10-01 09:00:00"}
			return {"actions": [], "modified": None}

		with (
			patch.object(approval, "get_decision_actions", side_effect=decision_actions),
			patch.object(approval.frappe.db, "exists", return_value=exists),
		):
			return approval.check_many(items)

	def test_ready_and_refused_are_split_with_the_reason(self):
		items = [item("A"), item("B"), item("C")]
		result = self._check(
			items, actions={"A", "C"}, blocked={"B": {"code": "balance", "message": "No balance left."}}
		)
		self.assertEqual([r["name"] for r in result["ready"]], ["A", "C"])
		self.assertEqual(result["refused"][0]["name"], "B")
		self.assertEqual(result["refused"][0]["reason"], "No balance left.")

	def test_a_request_the_caller_may_not_decide_is_refused_as_not_theirs(self):
		result = self._check([item("X")], actions=set())
		self.assertEqual(result["ready"], [])
		self.assertEqual(result["refused"][0]["code"], "not_yours")

	def test_a_request_edited_after_the_list_was_loaded_is_refused_as_changed(self):
		# the approver saw version "v1"; the employee edited it since, the server now holds "v2".
		# Returning v2 as the revision to approve would let the approval through for dates the
		# approver never saw (reviewer, 5 Oct 2026: the check only covered check -> approve).
		def decision_actions(doctype, name):
			return {"actions": ["Approved", "Rejected"], "modified": "2026-10-02 10:00:00"}

		with (
			patch.object(approval, "get_decision_actions", side_effect=decision_actions),
			patch.object(approval.frappe.db, "exists", return_value=True),
		):
			result = approval.check_many([item("A", modified="2026-10-01 09:00:00")])
		self.assertEqual(result["ready"], [])
		self.assertEqual(result["refused"][0]["code"], "changed")
		self.assertIn("changed", result["refused"][0]["reason"].lower())

	def test_a_request_unchanged_since_the_list_is_ready_with_the_revision_the_approver_saw(self):
		def decision_actions(doctype, name):
			return {"actions": ["Approved", "Rejected"], "modified": "2026-10-01 09:00:00.000000"}

		with (
			patch.object(approval, "get_decision_actions", side_effect=decision_actions),
			patch.object(approval.frappe.db, "exists", return_value=True),
		):
			result = approval.check_many([item("A", modified="2026-10-01 09:00:00")])
		self.assertEqual([r["name"] for r in result["ready"]], ["A"])
		self.assertEqual(result["ready"][0]["modified"], "2026-10-01 09:00:00")

	def test_a_missing_request_is_refused_not_an_error(self):
		result = self._check([item("GONE")], actions={"GONE"}, exists=False)
		self.assertEqual(result["refused"][0]["code"], "gone")

	def test_it_writes_nothing(self):
		with (
			patch.object(
				approval,
				"get_decision_actions",
				return_value={"actions": ["Approved"], "modified": "2026-10-01 09:00:00"},
			),
			patch.object(approval.frappe.db, "exists", return_value=True),
			patch.object(approval, "decide") as decide,
			patch.object(approval.frappe.db, "set_value") as set_value,
			patch.object(approval.frappe.db, "commit") as commit,
		):
			approval.check_many([item("A")])
		decide.assert_not_called()
		set_value.assert_not_called()
		commit.assert_not_called()

	def test_a_batch_over_the_cap_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			approval.check_many([item(f"R{n}") for n in range(approval.BULK_CAP + 1)])

	def test_valid_json_that_is_not_a_list_of_requests_is_a_plain_refusal(self):
		for bad in ("5", "{}", '"x"', "[1, 2]", [None], [{"name": "A"}]):
			with self.assertRaises(frappe.ValidationError, msg=repr(bad)):
				approval.check_many(bad)

	def test_names_and_doctypes_must_be_text_or_the_sort_cannot_crash(self):
		# reviewer 5 Oct: {"doctype": 5} / mixed int and str names made sorted() raise a 500
		for bad in (
			[{"doctype": 5, "name": "x", "modified": "m"}],
			[{"doctype": "Leave Application", "name": 7, "modified": "m"}],
			[
				{"doctype": "Leave Application", "name": "A", "modified": "m"},
				{"doctype": "Leave Application", "name": 9, "modified": "m"},
			],
		):
			with self.assertRaises(frappe.ValidationError, msg=repr(bad)):
				approval.check_many(bad)

	def test_the_attendance_import_tree_is_not_loaded_with_every_approval_request(self):
		# approval.py is imported by every PWA request; the lost-transaction helper lives in
		# attendance code and is imported where it is used, as lone_in_closer does
		import ast

		tree = ast.parse(pathlib.Path(approval.__file__).read_text())
		top = [
			node.module
			for node in tree.body
			if isinstance(node, ast.ImportFrom) and node.module == "hrms.utils.offshift_punch_heal"
		]
		self.assertEqual(top, [])

	def test_a_row_with_no_revision_is_refused_because_decide_skips_the_check_without_one(self):
		# decide() compares `modified` only when it is given: a bulk approve of a request the
		# approver never saw in its current form must not slip through (reviewer, 5 Oct 2026)
		with self.assertRaises(frappe.ValidationError):
			approval.check_many([{"doctype": "Leave Application", "name": "A"}])
		with self.assertRaises(frappe.ValidationError):
			approval.decide_many([{"doctype": "Leave Application", "name": "A", "modified": None}])

		with self.assertRaises(frappe.ValidationError):
			approval.check_many([])


class TestDecideMany(unittest.TestCase):
	def _decide(self, items, outcomes):
		"""outcomes: {name: 'ok' | exception} what the one-at-a-time `decide` does."""

		def decide(doctype, name, status, expected_modified=None, reason=None):
			result = outcomes[name]
			if isinstance(result, Exception):
				raise result
			return {"doctype": doctype, "name": name, "docstatus": 1, "status": status}

		db = MagicMock()
		with (
			patch.object(approval, "decide", side_effect=decide) as call,
			patch.object(approval.frappe, "db", db),
		):
			result = approval.decide_many(items)
		return result, call, db

	def test_one_refusal_does_not_stop_the_rest(self):
		items = [item("A"), item("B"), item("C")]
		result, call, _db = self._decide(items, {"A": "ok", "B": _Refusal("No balance"), "C": "ok"})
		self.assertEqual([r["name"] for r in result["approved"]], ["A", "C"])
		self.assertEqual(result["refused"][0]["name"], "B")
		self.assertEqual(call.call_count, 3)

	def test_a_permission_failure_is_reported_and_the_loop_goes_on(self):
		items = [item("A"), item("B")]
		result, _call, _db = self._decide(items, {"A": frappe.PermissionError("no"), "B": "ok"})
		self.assertEqual([r["name"] for r in result["approved"]], ["B"])
		self.assertEqual(result["refused"][0]["code"], "not_yours")

	def test_every_item_is_decided_as_approved_with_the_revision_the_caller_saw(self):
		_result, call, _db = self._decide([item("A", modified="2026-10-02 10:00:00")], {"A": "ok"})
		args = call.call_args
		self.assertEqual(args.args[:3], ("Leave Application", "A", "Approved"))
		self.assertEqual(args.kwargs["expected_modified"], "2026-10-02 10:00:00")

	def test_each_item_has_its_own_savepoint_and_a_failure_rolls_back_only_that_one(self):
		items = [item("A"), item("B")]
		_result, _call, db = self._decide(items, {"A": _Refusal("x"), "B": "ok"})
		self.assertEqual(db.savepoint.call_count, 2)
		rolled = [c.kwargs.get("save_point") for c in db.rollback.call_args_list]
		self.assertEqual(len(rolled), 1)
		self.assertIsNotNone(rolled[0])

	def test_an_already_decided_request_is_a_no_op_not_an_error(self):
		# decide() answers an identical retry with the settled state
		result, _call, _db = self._decide([item("A")], {"A": "ok"})
		self.assertEqual(result["approved"][0]["status"], "Approved")

	def test_requests_are_decided_in_one_fixed_order_so_two_batches_cannot_deadlock(self):
		items = [item("Z"), item("A"), item("M")]
		_result, call, _db = self._decide(items, {"Z": "ok", "A": "ok", "M": "ok"})
		self.assertEqual([c.args[1] for c in call.call_args_list], ["A", "M", "Z"])

	def test_a_lost_transaction_aborts_the_batch_instead_of_being_swallowed(self):
		# a deadlock rolls back the WHOLE transaction: carrying on would report approvals
		# that no longer exist
		items = [item("A"), item("B")]
		with self.assertRaises(frappe.QueryDeadlockError):
			self._decide(items, {"A": frappe.QueryDeadlockError("1213"), "B": "ok"})

	def test_a_batch_over_the_cap_is_refused_before_anything_is_decided(self):
		with patch.object(approval, "decide") as decide, self.assertRaises(frappe.ValidationError):
			approval.decide_many([item(f"R{n}") for n in range(approval.BULK_CAP + 1)])
		decide.assert_not_called()

	def test_decide_many_has_no_status_argument_rejecting_is_reject_many(self):
		# approve and reject are two endpoints, so a client cannot turn an approve call into a reject
		import inspect

		self.assertNotIn("status", inspect.signature(approval.decide_many).parameters)
		self.assertNotIn("status", inspect.signature(approval.reject_many).parameters)

	def test_all_three_are_post_only_endpoints(self):
		source = (pathlib.Path(approval.__file__)).read_text()
		for name in ("check_many", "decide_many", "reject_many"):
			head = source.split(f"def {name}(")[0].rstrip().splitlines()[-1]
			self.assertIn('methods=["POST"]', head, name)


class _Commentable(FakeDocument):
	"""A request the audit comment is written on; records what was added."""

	def __init__(self, doctype, name, comments, boom=None):
		super().__init__(doctype, name=name)
		object.__setattr__(self, "_comments", comments)
		object.__setattr__(self, "_boom", boom)

	def add_comment(self, comment_type="Comment", text=None, **kwargs):
		if self._boom:
			raise self._boom
		self._comments.append((self.name, comment_type, text))


class _BulkRun:
	"""Runs decide_many / reject_many with the one-at-a-time `decide` stubbed."""

	def __init__(self, outcomes, docstatus=None):
		self.outcomes, self.docstatus = outcomes, docstatus or {}
		self.comments, self.boom = [], {}
		self.db = MagicMock()
		self.db.get_value.side_effect = lambda doctype, name, field, *a, **k: self.docstatus.get(name, 0)
		self.decide = MagicMock(side_effect=self._decide)

	def _decide(self, doctype, name, status, expected_modified=None, reason=None):
		result = self.outcomes.get(name, "ok")
		if isinstance(result, Exception):
			raise result
		return {"doctype": doctype, "name": name, "docstatus": 1, "status": status}

	def _get_doc(self, doctype, name):
		return _Commentable(doctype, name, self.comments, self.boom.get(name))

	def run(self, endpoint, *args, **kwargs):
		with (
			patch.object(approval, "decide", self.decide),
			patch.object(approval.frappe, "db", self.db),
			patch.object(approval.frappe, "get_doc", side_effect=self._get_doc),
		):
			return getattr(approval, endpoint)(*args, **kwargs)


class TestRejectMany(unittest.TestCase):
	def test_every_item_goes_through_decide_as_rejected_with_its_reason_and_revision(self):
		bulk = _BulkRun({})
		result = bulk.run(
			"reject_many", [item("A", modified="2026-10-02 10:00:00")], reason="Short staffed that week"
		)
		args = bulk.decide.call_args
		self.assertEqual(args.args[:3], ("Leave Application", "A", "Rejected"))
		self.assertEqual(args.kwargs["expected_modified"], "2026-10-02 10:00:00")
		self.assertEqual(args.kwargs["reason"], "Short staffed that week")
		self.assertEqual([r["name"] for r in result["rejected"]], ["A"])
		self.assertEqual(result["rejected"][0]["status"], "Rejected")
		self.assertEqual(result["refused"], [])

	def test_an_item_reason_wins_over_the_shared_one_and_the_rest_use_the_shared(self):
		bulk = _BulkRun({})
		items = [{**item("A"), "reason": "  Clashes with audit "}, item("B")]
		bulk.run("reject_many", items, reason="Not this month")
		reasons = {c.args[1]: c.kwargs["reason"] for c in bulk.decide.call_args_list}
		self.assertEqual(reasons, {"A": "Clashes with audit", "B": "Not this month"})

	def test_no_reason_at_all_refuses_the_whole_call_before_anything_is_written(self):
		for shared in (None, "", "   "):
			bulk = _BulkRun({})
			with self.assertRaisesRegex(frappe.ValidationError, "Say why these are not approved."):
				bulk.run("reject_many", [item("A"), item("B")], reason=shared)
			bulk.decide.assert_not_called()
			bulk.db.savepoint.assert_not_called()

	def test_one_item_without_a_reason_refuses_the_whole_call(self):
		# the shared reason is empty and only A carries its own: B has none, so nothing is rejected
		bulk = _BulkRun({})
		items = [{**item("A"), "reason": "Clashes with audit"}, item("B")]
		with self.assertRaisesRegex(frappe.ValidationError, "Say why these are not approved."):
			bulk.run("reject_many", items)
		bulk.decide.assert_not_called()

	def test_a_reason_that_is_not_text_counts_as_none(self):
		bulk = _BulkRun({})
		with self.assertRaises(frappe.ValidationError):
			bulk.run("reject_many", [{**item("A"), "reason": 5}], reason=7)
		bulk.decide.assert_not_called()

	def test_a_request_of_their_own_is_refused_as_not_theirs_and_the_rest_go(self):
		bulk = _BulkRun({"A": frappe.PermissionError("own request"), "B": "ok"})
		result = bulk.run("reject_many", [item("A"), item("B")], reason="No")
		self.assertEqual([r["name"] for r in result["rejected"]], ["B"])
		self.assertEqual(result["refused"][0]["name"], "A")
		self.assertEqual(result["refused"][0]["code"], "not_yours")

	def test_a_failing_row_rolls_back_only_its_savepoint_and_the_next_still_goes(self):
		bulk = _BulkRun({"A": _Refusal("Already cancelled"), "B": "ok"})
		result = bulk.run("reject_many", [item("A"), item("B")], reason="No")
		self.assertEqual(bulk.db.savepoint.call_count, 2)
		rolled = [c.kwargs.get("save_point") for c in bulk.db.rollback.call_args_list]
		self.assertEqual(len(rolled), 1)
		self.assertIsNotNone(rolled[0])
		self.assertEqual([r["name"] for r in result["rejected"]], ["B"])
		self.assertEqual(result["refused"][0]["code"], "refused")
		self.assertEqual(result["refused"][0]["reason"], "Already cancelled")

	def test_a_bug_in_one_row_is_reported_as_a_rejection_that_could_not_be_made(self):
		bulk = _BulkRun({"A": RuntimeError("boom"), "B": "ok"})
		result = bulk.run("reject_many", [item("A"), item("B")], reason="No")
		self.assertEqual(result["refused"][0]["code"], "error")
		self.assertIn("rejected", result["refused"][0]["reason"])
		self.assertEqual([r["name"] for r in result["rejected"]], ["B"])

	def test_a_lost_transaction_aborts_the_batch(self):
		bulk = _BulkRun({"A": frappe.QueryDeadlockError("1213")})
		with self.assertRaises(frappe.QueryDeadlockError):
			bulk.run("reject_many", [item("A"), item("B")], reason="No")

	def test_a_batch_over_the_cap_is_refused_before_anything_is_decided(self):
		bulk = _BulkRun({})
		with self.assertRaises(frappe.ValidationError):
			bulk.run("reject_many", [item(f"R{n}") for n in range(approval.BULK_CAP + 1)], reason="No")
		bulk.decide.assert_not_called()

	def test_requests_are_rejected_in_one_fixed_order_with_their_own_reasons(self):
		bulk = _BulkRun({})
		items = [{**item("Z"), "reason": "z-why"}, {**item("A"), "reason": "a-why"}]
		bulk.run("reject_many", items)
		self.assertEqual(
			[(c.args[1], c.kwargs["reason"]) for c in bulk.decide.call_args_list],
			[("A", "a-why"), ("Z", "z-why")],
		)

	def test_a_json_post_body_is_read_like_decide_many(self):
		import json

		bulk = _BulkRun({})
		result = bulk.run("reject_many", json.dumps([item("A")]), reason="No")
		self.assertEqual([r["name"] for r in result["rejected"]], ["A"])


class TestBulkItemsKeepOnlyWhatTheyShould(unittest.TestCase):
	def test_a_reason_is_kept_stripped_and_nothing_else_is(self):
		rows = approval._bulk_items(
			[
				{
					**item("A"),
					"reason": "  why  ",
					"status": "Approved",
					"docstatus": 1,
					"employee": "E1",
				}
			]
		)
		self.assertEqual(rows, [{**item("A"), "reason": "why"}])

	def test_a_row_without_a_reason_carries_no_reason_key(self):
		self.assertEqual(approval._bulk_items([item("A")]), [item("A")])
		self.assertNotIn("reason", approval._bulk_items([{**item("A"), "reason": 5}])[0])


class TestBulkDecisionsLeaveAnAuditComment(unittest.TestCase):
	def test_an_approval_adds_one_info_comment_per_request_decided_now(self):
		bulk = _BulkRun({})
		bulk.run("decide_many", [item("A"), item("B")])
		self.assertEqual(
			bulk.comments, [("A", "Info", "Approved in bulk"), ("B", "Info", "Approved in bulk")]
		)

	def test_a_rejection_says_rejected_in_bulk(self):
		bulk = _BulkRun({})
		bulk.run("reject_many", [item("A")], reason="No")
		self.assertEqual(bulk.comments, [("A", "Info", "Rejected in bulk")])

	def test_a_request_already_decided_is_the_idempotent_no_op_and_gets_no_second_comment(self):
		# B was submitted before this call: decide answers with the settled state and writes nothing
		bulk = _BulkRun({}, docstatus={"A": 0, "B": 1})
		result = bulk.run("decide_many", [item("A"), item("B")])
		self.assertEqual([r["name"] for r in result["approved"]], ["A", "B"])
		self.assertEqual(bulk.comments, [("A", "Info", "Approved in bulk")])

	def test_a_refused_request_gets_no_comment(self):
		bulk = _BulkRun({"A": _Refusal("No balance"), "B": "ok"})
		bulk.run("decide_many", [item("A"), item("B")])
		self.assertEqual(bulk.comments, [("B", "Info", "Approved in bulk")])

	def test_the_comment_is_written_after_the_decision_and_inside_its_savepoint(self):
		order = []
		bulk = _BulkRun({})
		bulk.db.savepoint.side_effect = lambda name: order.append(("savepoint", name))
		bulk.decide.side_effect = lambda *a, **k: order.append(("decide", a[1])) or {"status": "Approved"}
		real = bulk._get_doc
		bulk._get_doc = lambda dt, n: order.append(("comment", n)) or real(dt, n)
		bulk.run("decide_many", [item("A")])
		self.assertEqual([step[0] for step in order], ["savepoint", "decide", "comment"])

	def test_a_comment_that_cannot_be_written_takes_the_decision_back_with_it(self):
		# the audit line and the decision stand or fall together: no unexplained bulk approval
		bulk = _BulkRun({})
		bulk.boom["A"] = RuntimeError("comment table locked")
		result = bulk.run("decide_many", [item("A"), item("B")])
		self.assertEqual([r["name"] for r in result["approved"]], ["B"])
		self.assertEqual(result["refused"][0]["code"], "error")
		self.assertEqual(len(bulk.db.rollback.call_args_list), 1)


if __name__ == "__main__":
	unittest.main()
