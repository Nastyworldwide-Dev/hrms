"""Request validation reserves monthly capacity from approved claims, not unclaimed work."""

import ast
import importlib
import sys
import unittest
from datetime import date, timedelta
from itertools import product
from pathlib import Path
from unittest.mock import Mock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
ot = importlib.import_module("hrms.utils.ot_calculation")
filing = importlib.import_module("test_ot_filing_edits")

approval_spec = importlib.util.spec_from_file_location(
	"ot_approval_under_test", Path(__file__).resolve().parents[1] / "api/approval.py"
)
approval = importlib.util.module_from_spec(approval_spec)
approval_spec.loader.exec_module(approval)

frappe = filing.frappe
DAY = date(2026, 9, 18)
CONFIG = {
	"min_minutes": 0,
	"days_per_month": 26,
	"hours_per_day": 8,
	"bands": {"normal": [(0, 24, 1.5)]},
	"daily_cap": 0,
	"monthly_cap": 4,
}


# Execute the actual whitelisted API bodies with authorization/time boundaries
# supplied explicitly; their calculator imports still resolve production code.
api_source = Path(__file__).resolve().parents[1] / "api/__init__.py"
api_tree = ast.parse(api_source.read_text())
api_nodes = [
	node
	for node in api_tree.body
	if isinstance(node, ast.FunctionDef) and node.name in {"get_ot_claim_summary", "get_claimable_ot_summary"}
]
for node in api_nodes:
	node.decorator_list = []
API = {
	"frappe": frappe,
	"getdate": lambda value=None: date(2026, 9, 30) if value is None else date.fromisoformat(str(value)),
	"add_days": lambda value, days: value + timedelta(days=days),
	"cint": int,
	"flt": float,
	"_ensure_own_employee_or_permitted": lambda employee: None,
	"logger": __import__("logging").getLogger(__name__),
}
exec(compile(ast.Module(body=api_nodes, type_ignores=[]), str(api_source), "exec"), API)


class DecisionDocument(filing.ot_request.OTRequest):
	"""In-memory persistence boundary; validation and submit consequences stay real."""

	def get(self, field):
		return getattr(self, field, None)

	def set(self, field, value):
		setattr(self, field, value)

	def check_permission(self, permission):
		assert permission == "read"

	def submit(self):
		self.validate()
		self.on_submit()
		self.docstatus = 1


class TestClaimCapacity(unittest.TestCase):
	def validate_claim(
		self,
		*,
		other_day=date(2026, 9, 3),
		other_status=None,
		other_hours=4,
		claim_hours=3,
		existing=False,
		target_work=3,
		cap=4,
		consumer="validate",
		discovery_dates=(DAY,),
		worked_hours=None,
		pay_eligible=1,
		other_docstatus=None,
		min_minutes=0,
		decision="Approved",
		allowed=True,
		submission_guard=None,
		saved_status="Open",
		shift_caps=None,
		payroll_day=DAY,
	):

		rows = []
		if other_status:
			rows.append(
				frappe._dict(
					name="OT-OTHER",
					employee="EMP-SYNTHETIC",
					ot_date=other_day,
					compensation="Overtime Pay",
					status=other_status,
					claimed_hours=other_hours,
					docstatus=other_docstatus
					if other_docstatus is not None
					else (0 if other_status == "Open" else (2 if other_status == "Cancelled" else 1)),
				)
			)
		if existing:
			rows.append(
				frappe._dict(
					name="OT-CURRENT",
					employee="EMP-SYNTHETIC",
					ot_date=DAY,
					compensation="Overtime Pay",
					status="Approved",
					claimed_hours=claim_hours,
					docstatus=1,
				)
			)

		def worked(employee, start, end):
			hours = worked_hours or {other_day: other_hours, DAY: target_work}
			selected = {day: value for day, value in hours.items() if start <= day <= end}
			return selected, {day: str(day) if shift_caps else "SHIFT-SYNTHETIC" for day in selected}

		def matches(row, field, condition):
			value = row.get(field)
			if not isinstance(condition, (list, tuple)):
				return value == condition
			op, operand = condition
			if op == "between":
				return operand[0] <= value <= operand[1]
			if op == "!=":
				return value != operand
			if op == "<":
				return value < operand
			raise AssertionError(f"Unmodelled filter {op}")

		def get_all(doctype, filters=None, fields=None, **kwargs):
			if doctype == "User Permission":
				return ["Company A"]
			if doctype == "Attendance":
				return [frappe._dict(attendance_date=day, ot_hours=99) for day in discovery_dates]
			self.assertEqual(doctype, "OT Request")
			if kwargs.get("pluck"):
				return []
			return [
				row for row in rows if all(matches(row, key, value) for key, value in (filters or {}).items())
			]

		def get_value(doctype, name, fieldname, **kwargs):
			# Permission reads use synthetic identity/company data; calculator
			# eligibility remains an independent financial input.
			if doctype == "OT Request" and fieldname == "employee":
				return "EMP-SYNTHETIC"  # lock-order reads (decide / check_if_latest)
			if doctype == "Employee" and fieldname == "company":
				return "Company A"
			if doctype == "Employee" and fieldname == "user_id":
				return "synthetic-staff@example.invalid"
			return pay_eligible

		doc = DecisionDocument(
			dict(
				name="OT-CURRENT",
				doctype="OT Request",
				status=saved_status,
				docstatus=0,
				punch_ot_hours=claim_hours,
				employee="EMP-SYNTHETIC",
				ot_date=DAY,
				amended_from=None,
				_new=False if consumer == "decide" else not existing,
				_previous=None,
				shift="SHIFT-SYNTHETIC",
				claimed_hours=claim_hours,
			)
		)
		with (
			patch.object(
				filing.ot_request,
				"getdate",
				side_effect=lambda value=None: (
					date(2026, 9, 30) if value is None else date.fromisoformat(str(value))
				),
			),
			patch.object(frappe.db, "get_value", side_effect=get_value),
			patch.object(frappe.db, "exists", side_effect=lambda doctype, value: isinstance(value, str)),
			# Locking reads (approval reservations, duplicate check) answer from the
			# same synthetic rows as the snapshot reads above.
			patch.object(
				frappe.db,
				"get_values",
				side_effect=lambda doctype, filters=None, fields=None, **kwargs: (
					[] if fields == "name" else get_all(doctype, filters=filters, fields=fields)
				),
			),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(
				ot,
				"_get_shift_ot_config",
				side_effect=lambda shift: {
					**CONFIG,
					"monthly_cap": (shift_caps or {}).get(shift, cap),
					"min_minutes": min_minutes,
				},
			),
			patch.object(ot, "_classify_day", return_value="normal"),
			patch.object(ot, "_per_day_ot_hours", side_effect=worked),
			patch.object(
				ot, "_per_day_contributions", side_effect=lambda *a: ot._contributions_from_maps(*worked(*a))
			),
		):
			if consumer == "decide":
				with (
					patch.object(frappe, "get_doc", return_value=doc),
					patch.object(frappe, "has_permission", return_value=allowed),
					patch.object(approval, "_is_routed_approver", return_value=False),
					patch.object(approval, "get_permitted_fields", return_value=["status"]),
					patch("frappe.model.workflow.get_workflow_name", return_value=None),
					patch.object(frappe, "session", frappe._dict(user="synthetic-reviewer@example.invalid")),
					patch.object(
						filing.ot_request, "validate_self_submission", side_effect=submission_guard
					) as self_guard,
					patch.object(filing.ot_request, "validate_mandatory_attachment") as attachment_guard,
					patch.object(filing.ot_request, "grant_replacement_leave") as grant,
				):
					state = approval.decide("OT Request", doc.name, decision)
					self_guard.assert_called_once_with(doc)
					attachment_guard.assert_called_once_with(doc)
					if decision == "Rejected":
						grant.assert_not_called()
					return state
			if consumer == "payroll":
				return ot.get_ot_pay("EMP-SYNTHETIC", payroll_day, payroll_day, 2080)
			if consumer == "validate":
				doc.validate()
				return doc.punch_ot_hours
			return API[consumer](
				employee="EMP-SYNTHETIC", **({"date": str(DAY)} if consumer == "get_ot_claim_summary" else {})
			)

	def test_rejection_can_finalize_when_later_approval_consumed_capacity(self):
		state = self.validate_claim(
			consumer="decide",
			decision="Rejected",
			other_day=date(2026, 9, 25),
			other_status="Approved",
			other_hours=3,
			claim_hours=3,
		)
		self.assertEqual((state["status"], state["docstatus"]), ("Rejected", 1))

	def test_rejection_can_finalize_without_current_punch_evidence(self):
		for eligible in (0, 1):
			with self.subTest(pay_eligible=eligible):
				state = self.validate_claim(
					consumer="decide", decision="Rejected", target_work=0, pay_eligible=eligible
				)
				self.assertEqual((state["status"], state["docstatus"]), ("Rejected", 1))

	def test_approval_still_refuses_invalid_financial_capacity(self):
		for values in (
			{"target_work": 0},
			{"other_status": "Approved", "other_hours": 3, "other_day": date(2026, 9, 25)},
		):
			with self.subTest(values=values), self.assertRaises(frappe.ValidationError):
				self.validate_claim(consumer="decide", **values)

	def test_new_rejected_document_does_not_bypass_filing_capacity(self):
		with self.assertRaises(frappe.ValidationError):
			self.validate_claim(saved_status="Rejected", target_work=0)

	def test_rejected_existing_document_preserves_verified_cap(self):
		self.assertEqual(self.validate_claim(existing=True, saved_status="Rejected", target_work=0), 3)

	def test_rejection_keeps_authorization_and_submit_guards(self):
		with self.assertRaises(frappe.PermissionError):
			self.validate_claim(consumer="decide", decision="Rejected", target_work=0, allowed=False)
		guard = Mock(side_effect=frappe.ValidationError("synthetic self-submission refusal"))
		with self.assertRaisesRegex(frappe.ValidationError, "synthetic self-submission refusal"):
			self.validate_claim(consumer="decide", decision="Rejected", target_work=0, submission_guard=guard)
		guard.assert_called_once()

	def test_unclaimed_draft_and_rejected_work_do_not_reserve_capacity(self):
		for status in (None, "Open", "Rejected", "Cancelled"):
			with self.subTest(status=status):
				self.assertEqual(self.validate_claim(other_status=status), 3)

	def test_approved_earlier_or_later_dates_reserve_capacity(self):
		for other_day in (date(2026, 9, 3), date(2026, 9, 25)):
			with self.subTest(other_day=other_day):
				with self.assertRaises(frappe.ValidationError):
					self.validate_claim(
						other_day=other_day, other_status="Approved", other_hours=3, claim_hours=2
					)
				self.assertEqual(
					self.validate_claim(
						other_day=other_day, other_status="Approved", other_hours=3, claim_hours=1
					),
					1,
				)

	def test_current_approved_request_does_not_consume_its_own_capacity_twice(self):
		self.assertEqual(self.validate_claim(other_status="Approved", other_hours=1, existing=True), 3)

	def test_form_preview_and_discovery_use_the_same_remaining_capacity(self):
		params = dict(other_day=date(2026, 9, 25), other_status="Approved", other_hours=3, claim_hours=1)
		self.assertEqual(self.validate_claim(**params), 1)
		self.assertEqual(self.validate_claim(**params, consumer="get_ot_claim_summary")["punch_ot_hours"], 1)
		self.assertEqual(
			self.validate_claim(**params, consumer="get_claimable_ot_summary")["days"],
			[{"date": str(DAY), "hours": 1}],
		)

	def test_remaining_allowance_below_rounding_band_is_never_rounded_up(self):
		for reserved, remainder in ((3.8, 0.2), (3.7, 0.3)):
			self.assertAlmostEqual(
				self.validate_claim(
					other_day=date(2026, 9, 25),
					other_status="Approved",
					other_hours=reserved,
					claim_hours=remainder,
				),
				remainder,
			)
		with self.assertRaises(frappe.ValidationError):
			self.validate_claim(
				other_day=date(2026, 9, 25), other_status="Approved", other_hours=3.8, claim_hours=0.5
			)

	def test_discovery_total_is_capped_by_shared_budget_without_changing_each_date(self):
		earlier = date(2026, 9, 3)
		for reserved, expected_day, expected_total in ((0, 3, 4), (1, 3, 3), (2, 2, 2)):
			with self.subTest(reserved=reserved):
				result = self.validate_claim(
					consumer="get_claimable_ot_summary",
					other_day=date(2026, 9, 25),
					other_status="Approved",
					other_hours=reserved,
					worked_hours={earlier: 3, DAY: 3},
					discovery_dates=(earlier, DAY),
				)
				self.assertEqual(result["claimable_hours"], expected_total)
				self.assertEqual(
					result["days"],
					[
						{"date": str(DAY), "hours": expected_day},
						{"date": str(earlier), "hours": expected_day},
					],
				)

	def test_legacy_submitted_non_rejected_claims_still_reserve_like_payroll(self):
		with self.assertRaises(frappe.ValidationError):
			self.validate_claim(
				other_day=date(2026, 9, 25),
				other_status="Open",
				other_docstatus=1,
				other_hours=3,
				claim_hours=2,
			)

	def test_replacement_leave_discovery_keeps_its_existing_attendance_source(self):
		result = self.validate_claim(consumer="get_claimable_ot_summary", pay_eligible=0)
		self.assertEqual(result["claimable_hours"], 99)

	def test_payroll_prices_an_approved_partial_budget_after_work_qualifies(self):
		self.assertEqual(
			self.validate_claim(
				other_status="Approved",
				other_hours=3.8,
				claim_hours=0.2,
				existing=True,
				min_minutes=60,
				consumer="payroll",
			),
			3,
		)

	def test_backdated_mixed_shift_claim_preserves_later_approved_payroll(self):
		later = date(2026, 9, 25)
		params = dict(
			other_day=later, other_status="Approved", other_hours=3, shift_caps={str(DAY): 6, str(later): 4}
		)
		self.assertEqual(self.validate_claim(**params, consumer="payroll", payroll_day=later), 45)
		capacity = self.validate_claim(**params, consumer="get_ot_claim_summary")["punch_ot_hours"]
		self.assertEqual(capacity, 1)
		self.assertEqual(self.validate_claim(**params, claim_hours=1), 1)
		with self.assertRaises(frappe.ValidationError):
			self.validate_claim(**params, claim_hours=3)
		self.assertEqual(
			self.validate_claim(
				**params, claim_hours=capacity, existing=True, consumer="payroll", payroll_day=later
			),
			45,
		)

	def test_unlimited_earlier_shift_still_preserves_later_finite_cap(self):
		later = date(2026, 9, 25)
		self.assertEqual(
			self.validate_claim(
				other_day=later,
				other_status="Approved",
				other_hours=3,
				claim_hours=1,
				shift_caps={str(DAY): 0, str(later): 4},
			),
			1,
		)

	def test_earlier_small_shift_cap_does_not_limit_later_high_cap_work(self):
		earlier = date(2026, 9, 3)
		self.assertEqual(
			self.validate_claim(
				other_day=earlier,
				other_status="Approved",
				other_hours=3,
				claim_hours=3,
				shift_caps={str(earlier): 4, str(DAY): 6},
			),
			3,
		)

	def test_mixed_shift_discovery_total_has_a_feasible_claim_allocation(self):
		earlier = date(2026, 9, 3)
		result = self.validate_claim(
			consumer="get_claimable_ot_summary",
			discovery_dates=(earlier, DAY),
			worked_hours={earlier: 5, DAY: 2},
			shift_caps={str(earlier): 6, str(DAY): 2},
		)
		self.assertEqual(result["days"], [{"date": str(DAY), "hours": 2}, {"date": str(earlier), "hours": 5}])
		self.assertEqual(result["claimable_hours"], 5)

	@settings(max_examples=45, deadline=None)
	@given(
		earned=st.lists(st.integers(0, 4), min_size=3, max_size=3),
		caps=st.lists(st.integers(0, 7), min_size=3, max_size=3),
	)
	def test_discovery_maximum_matches_exhaustive_feasible_allocations(self, earned, caps):
		dates = [date(2026, 9, 3), date(2026, 9, 10), DAY]
		feasible = [
			sum(claims)
			for claims in product(*(range(hours + 1) for hours in earned))
			if all(
				not hours or not caps[index] or sum(claims[: index + 1]) <= caps[index]
				for index, hours in enumerate(claims)
			)
		]
		result = self.validate_claim(
			consumer="get_claimable_ot_summary",
			discovery_dates=dates,
			worked_hours=dict(zip(dates, earned, strict=True)),
			shift_caps={str(day): cap for day, cap in zip(dates, caps, strict=True)},
		)
		self.assertEqual(result["claimable_hours"], max(feasible))

	def test_later_cap_reservation_keeps_unrounded_fractional_consumption(self):
		later = date(2026, 9, 25)
		params = dict(
			other_day=later,
			other_status="Approved",
			other_hours=3.733,
			shift_caps={str(DAY): 6, str(later): 4},
		)
		self.assertAlmostEqual(self.validate_claim(**params, claim_hours=0.267), 0.267)
		with self.assertRaises(frappe.ValidationError):
			self.validate_claim(**params, claim_hours=0.27)

	@settings(max_examples=45, deadline=None)
	@given(earlier_cap=st.integers(0, 8), later_cap=st.integers(0, 8), approved=st.integers(1, 7))
	def test_admitted_backdated_capacity_never_reduces_existing_later_pay(
		self, earlier_cap, later_cap, approved
	):
		later = date(2026, 9, 25)
		params = dict(
			other_day=later,
			other_status="Approved",
			other_hours=approved,
			shift_caps={str(DAY): earlier_cap, str(later): later_cap},
		)
		before = self.validate_claim(**params, consumer="payroll", payroll_day=later)
		capacity = self.validate_claim(**params, consumer="get_ot_claim_summary")["punch_ot_hours"]
		after = self.validate_claim(
			**params, consumer="payroll", payroll_day=later, existing=True, claim_hours=capacity
		)
		self.assertEqual(after, before)

	@settings(max_examples=45, deadline=None)
	@given(
		earned=st.lists(st.integers(0, 4), min_size=2, max_size=2),
		caps=st.lists(st.integers(0, 7), min_size=2, max_size=2),
		reserved=st.integers(1, 3),
		later_headroom=st.integers(0, 3),
	)
	def test_discovery_with_existing_approval_matches_feasible_allocations(
		self, earned, caps, reserved, later_headroom
	):
		earlier, approved_day = date(2026, 9, 3), date(2026, 9, 10)
		feasible = [
			sum(claims)
			for claims in product(*(range(hours + 1) for hours in earned))
			if claims[0] <= later_headroom
			and all(
				not hours or not caps[index] or reserved + sum(claims[: index + 1]) <= caps[index]
				for index, hours in enumerate(claims)
			)
		]
		result = self.validate_claim(
			consumer="get_claimable_ot_summary",
			discovery_dates=(earlier, DAY),
			other_day=approved_day,
			other_status="Approved",
			other_hours=reserved,
			worked_hours={earlier: earned[0], approved_day: reserved, DAY: earned[1]},
			shift_caps={
				str(earlier): caps[0],
				str(approved_day): reserved + later_headroom,
				str(DAY): caps[1],
			},
		)
		self.assertEqual(result["claimable_hours"], max(feasible))

	@settings(max_examples=60, deadline=None)
	@given(approved=st.integers(min_value=0, max_value=7), remaining=st.integers(min_value=1, max_value=7))
	def test_admitted_claim_plus_existing_approvals_never_exceeds_monthly_limit(self, approved, remaining):
		cap = approved + remaining
		self.assertEqual(
			self.validate_claim(
				other_day=date(2026, 9, 25),
				other_status="Approved",
				other_hours=approved,
				target_work=remaining + 1,
				claim_hours=remaining,
				cap=cap,
			),
			remaining,
		)
		with self.assertRaises(frappe.ValidationError):
			self.validate_claim(
				other_day=date(2026, 9, 25),
				other_status="Approved",
				other_hours=approved,
				target_work=remaining + 1,
				claim_hours=remaining + 1,
				cap=cap,
			)


if __name__ == "__main__":
	unittest.main()
