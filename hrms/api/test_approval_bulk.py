"""Approve many requests at once (HR, 4 Oct 2026; owner, 5 Oct).

HR: "allow the list to be expanded, filter by request and bulk approve". 51
requests were waiting, oldest since 17 Aug. The page decides one at a time.

check_many tells the approver, BEFORE anything is written, which of the ticked
requests would go through and which would be refused, with the plain reason.
decide_many approves the ones that can, one by one, each in its own savepoint:
one refusal never stops the rest and never leaves a half write. It adds NO rule
of its own — every item goes through `decide`, so nothing is possible in bulk
that the approver could not do one by one.

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

	def test_rejecting_in_bulk_is_not_offered(self):
		import inspect

		self.assertNotIn("status", inspect.signature(approval.decide_many).parameters)

	def test_both_are_post_only_endpoints(self):
		source = (pathlib.Path(approval.__file__)).read_text()
		for name in ("check_many", "decide_many"):
			head = source.split(f"def {name}(")[0].rstrip().splitlines()[-1]
			self.assertIn('methods=["POST"]', head, name)


if __name__ == "__main__":
	unittest.main()
