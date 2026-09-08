"""Generated permission-boundary checks over the actual controller with a Frappe stub.

Run with system Python (Hypothesis installed). Framework insert semantics are
covered separately by test_inherited_checkout_lifecycle using real Frappe.
"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parent)]
import _frappe_stub

_frappe_stub.install()
from hypothesis import given, settings
from hypothesis import strategies as st

import frappe
import frappe.model.document


class DocumentSeam:
	def __init__(self, **values):
		self.__dict__.update(values)
		self.flags = frappe._dict()

	def get(self, field, default=None):
		return getattr(self, field, default)

	def is_new(self):
		return True

	def has_value_changed(self, field):
		return True


frappe.model.document.Document = DocumentSeam
from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import (
	_INHERITED_CHECKOUT,
	RemoteCheckinRequest,
)

JSON_VALUES = st.recursive(
	st.none() | st.booleans() | st.integers() | st.text(max_size=20),
	lambda children: (
		st.lists(children, max_size=3) | st.dictionaries(st.text(max_size=10), children, max_size=3)
	),
	max_leaves=10,
)


class TestInheritedCheckoutProperties(unittest.TestCase):
	def setUp(self):
		logger = patch("hrms.hr.doctype.remote_checkin_request.remote_checkin_request.logger")
		logger.start()
		self.addCleanup(logger.stop)

	@settings(max_examples=80, deadline=None, derandomize=True)
	@given(marker=JSON_VALUES, decision=st.sampled_from(["Approved", "Rejected"]))
	def test_serializable_flags_never_authorize_employee_decisions(self, marker, decision):
		request = RemoteCheckinRequest(
			name="GENERATED",
			status=decision,
			approver="approver@example.invalid",
			parent_request="PARENT",
			employee="EMP",
			log_type="OUT",
		)
		request.flags.inherited_checkout = marker
		with (
			patch.object(frappe.session, "user", "employee@example.invalid"),
			patch.object(frappe, "get_roles", return_value=["Employee"]),
		):
			with self.assertRaises(frappe.ValidationError):
				request.before_save()

	@settings(max_examples=60, deadline=None, derandomize=True)
	@given(
		parent_status=st.sampled_from(["Pending", "Rejected", "Approved"]),
		parent_employee=st.sampled_from(["EMP", "OTHER"]),
		last_in=st.sampled_from(["IN", "OTHER-IN"]),
		late=st.booleans(),
	)
	def test_only_same_employee_approved_session_can_be_derived(
		self, parent_status, parent_employee, last_in, late
	):
		request = RemoteCheckinRequest(
			name="GENERATED",
			status="Approved",
			approver="approver@example.invalid",
			parent_request="PARENT",
			employee="EMP",
			log_type="OUT",
			checkin="OUT",
			checkin_time=datetime(2026, 9, 3, 20),
			is_late_checkout=int(late),
		)
		request.flags.inherited_checkout = _INHERITED_CHECKOUT

		def get_value(dt, name, *args, **kwargs):
			if dt == "Employee":
				return "employee@example.invalid"
			if dt == "Remote Checkin Request":
				return frappe._dict(
					employee=parent_employee,
					checkin="IN",
					status=parent_status,
					log_type="IN",
					approver="approver@example.invalid",
				)
			if name == "OUT":
				return frappe._dict(name="OUT", employee="EMP", log_type="OUT", time=datetime(2026, 9, 3, 20))
			return frappe._dict(
				name=last_in, employee="EMP", log_type="IN", remote_approval_status="Approved"
			)

		with (
			patch.object(frappe.session, "user", "employee@example.invalid"),
			patch.object(frappe, "get_roles", return_value=["Employee"]),
			patch.object(frappe.db, "get_value", side_effect=get_value),
			patch.object(
				frappe,
				"get_all",
				return_value=[
					frappe._dict(
						name=last_in, employee="EMP", log_type="IN", remote_approval_status="Approved"
					)
				],
			),
		):
			if parent_status == "Approved" and parent_employee == "EMP" and last_in == "IN" and not late:
				request.before_save()
			else:
				with self.assertRaises(frappe.ValidationError):
					request.before_save()

	@settings(max_examples=100, deadline=None, derandomize=True)
	@given(
		intervening=st.lists(
			st.tuples(
				st.sampled_from(["IN", "OUT"]), st.sampled_from(["Rejected", "Pending", "Approved", None, ""])
			),
			max_size=6,
		)
	)
	def test_rejected_noise_never_closes_or_replaces_the_approved_session(self, intervening):
		request = RemoteCheckinRequest(
			name="GENERATED",
			status="Approved",
			approver="approver@example.invalid",
			parent_request="PARENT",
			employee="EMP",
			log_type="OUT",
			checkin="OUT",
			checkin_time=datetime(2026, 9, 3, 20),
			is_late_checkout=0,
		)
		request.flags.inherited_checkout = _INHERITED_CHECKOUT
		rows = [
			frappe._dict(
				name="IN",
				employee="EMP",
				log_type="IN",
				time=datetime(2026, 9, 3, 9),
				remote_approval_status="Approved",
			)
		]
		rows.extend(
			frappe._dict(
				name=f"NOISE-{i}",
				employee="EMP",
				log_type=kind,
				time=datetime(2026, 9, 3, 10) + timedelta(minutes=i),
				remote_approval_status=status,
			)
			for i, (kind, status) in enumerate(intervening)
		)

		def get_all(dt, filters, or_filters, **kwargs):
			# Model SQL NULL comparison explicitly: NULL != Rejected is not true.
			def satisfies(row, condition):
				field, op, value = condition
				actual = row.get(field)
				if op == "!=":
					return actual is not None and actual != value
				if op == "is" and value == "not set":
					return actual is None
				raise AssertionError(f"Unsupported DB comparison: {condition}")

			eligible = [
				r
				for r in rows
				if r.employee == filters["employee"]
				and r.time < filters["time"][1]
				and any(satisfies(r, condition) for condition in or_filters)
			]
			return sorted(eligible, key=lambda r: (r.time, r.name), reverse=True)[
				: kwargs["limit_page_length"]
			]

		def get_value(dt, name, *args, **kwargs):
			if dt == "Employee":
				return "employee@example.invalid"
			if dt == "Remote Checkin Request":
				return frappe._dict(
					employee="EMP",
					checkin="IN",
					status="Approved",
					log_type="IN",
					approver="approver@example.invalid",
				)
			return frappe._dict(name="OUT", employee="EMP", log_type="OUT", time=datetime(2026, 9, 3, 20))

		with (
			patch.object(frappe.session, "user", "employee@example.invalid"),
			patch.object(frappe, "get_roles", return_value=["Employee"]),
			patch.object(frappe.db, "get_value", side_effect=get_value),
			patch.object(frappe, "get_all", side_effect=get_all),
		):
			if all(status == "Rejected" for _, status in intervening):
				request.before_save()
			else:
				with self.assertRaises(frappe.ValidationError):
					request.before_save()


if __name__ == "__main__":
	unittest.main()
