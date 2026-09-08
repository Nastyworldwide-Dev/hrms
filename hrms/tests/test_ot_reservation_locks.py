"""Two approvals for one employee cannot both fit the monthly OT cap.

Astra's native two-connection probe (docs/glass/audit/2026-09-08-ot-
concurrency-probe.py) showed the race on a real MariaDB at REPEATABLE-READ:
two transactions each read no reservations, each admitted 3 h against a 4 h
cap, and both approved — 6 h paid against 4. Nothing serialized the two
approvals, and a plain SELECT inside a transaction answers from its snapshot,
so even a waiter would not have seen the winner's commit.

The fix, per docs/glass/audit/2026-09-08-ot-lock-proposal.md (authorized):
  * lock order EMPLOYEE -> REQUEST on every OT Request write, taken in
    OTRequest.check_if_latest before Frappe locks the request row, and in
    hrms.api.approval.decide before its own request lock;
  * approval (docstatus 1 during validate) reads reservations with a LOCKING
    read — a current read that includes the winner's committed rows;
  * the duplicate-per-day check is a current read under the same lock;
  * a composite (employee, docstatus, ot_date) index so the locking read
    ranges over one employee instead of gap-locking the table.
The real two-thread proof lives in the opt-in native suite
hrms/tests/test_ot_reservation_concurrency.py; this file pins the order and
the read modes bench-free.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_ot_reservation_locks.py
"""

import importlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

ROOT = Path(__file__).resolve().parents[1]
CALLS: list = []


class RecordingDocument:
	"""Frappe's Document, reduced to what the lock order touches."""

	def __init__(self, values):
		self.__dict__.update(values)
		self.flags = frappe._dict()

	def is_new(self):
		return self._new

	def get(self, key, default=None):
		return getattr(self, key, default)

	def check_if_latest(self):
		CALLS.append(("frappe.check_if_latest", self.name))


helpers = types.ModuleType("hrms.hr.utils")
for name in (
	"grant_replacement_leave",
	"reverse_replacement_leave",
	"validate_active_employee",
	"validate_filing_for_self",
	"validate_mandatory_attachment",
	"validate_self_submission",
):
	setattr(helpers, name, lambda *args: None)
model = types.ModuleType("frappe.model.document")
model.Document = RecordingDocument
spec = importlib.util.spec_from_file_location(
	"ot_locks_under_test", ROOT / "hr/doctype/ot_request/ot_request.py"
)
ot_request = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"frappe.model.document": model, "hrms.hr.utils": helpers}):
	spec.loader.exec_module(ot_request)
ot = importlib.import_module("hrms.utils.ot_calculation")
approval = importlib.import_module("hrms.api.approval")
index_patch = importlib.import_module("hrms.patches.v16_0.add_ot_request_reservation_index")


def _request(new, employee="EMP-A", name="OT-1", docstatus=0):
	return ot_request.OTRequest(
		dict(
			name=None if new else name,
			employee=employee,
			ot_date="2026-09-06",
			compensation="Overtime Pay",
			docstatus=docstatus,
			shift="SHIFT-SYNTHETIC",
			_new=new,
		)
	)


def _recording_get_value(saved="EMP-A", after_lock=None):
	"""frappe.db.get_value that records every call and answers the reads."""

	def get_value(doctype, name, fieldname=None, *args, **kwargs):
		CALLS.append((doctype, name, fieldname, bool(kwargs.get("for_update"))))
		if doctype == "OT Request" and fieldname == "employee":
			return (after_lock or saved) if kwargs.get("for_update") else saved
		if doctype == "OT Request" and fieldname == "docstatus":
			return 0
		return name

	return get_value


class TestEmployeeLockComesFirst(unittest.TestCase):
	def setUp(self):
		CALLS.clear()

	def test_insert_locks_the_employee_before_frappe_checks_the_request(self):
		with patch.object(frappe.db, "get_value", side_effect=_recording_get_value()):
			_request(new=True).check_if_latest()
		self.assertEqual(CALLS, [("Employee", "EMP-A", "name", True), ("frappe.check_if_latest", None)])

	def test_save_locks_the_saved_and_the_new_employee_in_sorted_order(self):
		with patch.object(frappe.db, "get_value", side_effect=_recording_get_value(saved="EMP-B")):
			_request(new=False, employee="EMP-A").check_if_latest()
		locks = [c for c in CALLS if c[0] == "Employee"]
		self.assertEqual(locks, [("Employee", "EMP-A", "name", True), ("Employee", "EMP-B", "name", True)])
		self.assertLess(CALLS.index(locks[-1]), CALLS.index(("frappe.check_if_latest", "OT-1")))
		# the re-read that proves nobody moved the request is itself a locking read
		self.assertIn(("OT Request", "OT-1", "employee", True), CALLS)

	def test_a_request_reassigned_while_locking_is_refused(self):
		with (
			patch.object(
				frappe.db, "get_value", side_effect=_recording_get_value(saved="EMP-A", after_lock="EMP-C")
			),
			self.assertRaises(frappe.ValidationError),
		):
			_request(new=False).check_if_latest()
		self.assertNotIn(("frappe.check_if_latest", "OT-1"), CALLS)


class TestApprovalReadsCurrentReservations(unittest.TestCase):
	def _cap_kwargs(self, docstatus):
		seen = {}

		def capacity(employee, day, compensation, **kwargs):
			seen.update(kwargs)
			return {"hours": 1.0, "monthly_remaining": None}

		with (
			patch.object(ot_request, "get_ot_claim_capacity", side_effect=capacity),
			patch.object(frappe.db, "get_value", return_value="SHIFT-SYNTHETIC"),
		):
			_request(new=False, docstatus=docstatus).set_punch_verified_cap()
		return seen

	def test_submission_uses_a_locking_reservation_read(self):
		self.assertTrue(self._cap_kwargs(docstatus=1)["lock_reservations"])

	def test_a_draft_preview_reads_the_snapshot(self):
		self.assertFalse(self._cap_kwargs(docstatus=0)["lock_reservations"])

	def test_the_locking_read_goes_through_get_values_for_update(self):
		with (
			patch.object(
				frappe.db, "get_values", return_value=[frappe._dict(ot_date="2026-09-02", claimed_hours=3)]
			) as locking,
			patch.object(frappe, "get_all") as snapshot,
		):
			rows = ot._approved_reservations("EMP-A", "2026-09-01", "2026-09-30", "OT-1", lock=True)
		self.assertEqual(rows[0].claimed_hours, 3)
		self.assertTrue(locking.call_args.kwargs["for_update"])
		self.assertEqual(locking.call_args.args[1]["name"], ("!=", "OT-1"))
		snapshot.assert_not_called()

	def test_the_snapshot_read_stays_on_get_all(self):
		with (
			patch.object(frappe, "get_all", return_value=[]) as snapshot,
			patch.object(frappe.db, "get_values") as locking,
		):
			ot._approved_reservations("EMP-A", "2026-09-01", "2026-09-30", None, lock=False)
		snapshot.assert_called_once()
		locking.assert_not_called()


class TestDuplicateCheckIsACurrentRead(unittest.TestCase):
	def test_no_duplicate_passes_and_the_read_locks(self):
		with patch.object(frappe.db, "get_values", return_value=[]) as read:
			_request(new=False).validate_duplicate_request()
		self.assertTrue(read.call_args.kwargs["for_update"])
		self.assertEqual(read.call_args.args[1]["ot_date"], "2026-09-06")

	def test_a_committed_sibling_is_refused(self):
		with (
			patch.object(frappe.db, "get_values", return_value=[("OT-0",)]),
			self.assertRaises(frappe.ValidationError),
		):
			_request(new=False).validate_duplicate_request()


class TestDecideTakesTheSameOrder(unittest.TestCase):
	def setUp(self):
		CALLS.clear()

	def _decide(self, doc_employee="EMP-A"):
		field, pending = approval.DECIDE_THEN_SUBMIT["OT Request"]
		doc = SimpleNamespace(
			doctype="OT Request",
			name="OT-1",
			employee=doc_employee,
			docstatus=0,
			flags=frappe._dict(),
			get=lambda key, default=None: pending if key == field else None,
			set=lambda key, value: None,
			submit=lambda: CALLS.append(("submit", "OT-1")),
		)
		with (
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(frappe.db, "get_value", side_effect=_recording_get_value()),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(approval, "_decision_access", return_value="routed"),
			patch.object(approval, "_check_review_revision"),
			patch.object(approval, "_state", return_value={}),
		):
			return approval.decide("OT Request", "OT-1", "Approved")

	def test_the_employee_is_locked_before_the_request(self):
		self._decide()
		employee_lock = CALLS.index(("Employee", "EMP-A", "name", True))
		request_lock = CALLS.index(("OT Request", "OT-1", "docstatus", True))
		self.assertLess(employee_lock, request_lock)
		self.assertIn(("submit", "OT-1"), CALLS)

	def test_a_request_moved_to_another_employee_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self._decide(doc_employee="EMP-Z")
		self.assertNotIn(("submit", "OT-1"), CALLS)


class TestReservationIndexPatch(unittest.TestCase):
	def test_it_adds_the_composite_index_by_name(self):
		with patch.object(frappe.db, "add_index") as add_index:
			index_patch.execute()
		add_index.assert_called_once_with(
			"OT Request", ["employee", "docstatus", "ot_date"], "ot_employee_status_date"
		)


if __name__ == "__main__":
	unittest.main()
