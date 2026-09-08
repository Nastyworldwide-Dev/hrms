"""Generated access invariants; framework/identity predicates are explicit inputs.

Executes production can_decide and its shared access helper. Native permission
engine and routing are verified separately in test_decision_access.py.
"""

import ast
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

import frappe

SOURCE = Path(__file__).with_name("approval.py")
TYPES = [
	"Leave Application",
	"Expense Claim",
	"Shift Request",
	"OT Request",
	"Attendance Request",
	"Replacement Leave Claim",
]
namespace = {"frappe": frappe, "logger": logging.getLogger(__name__)}
nodes = []
for node in ast.parse(SOURCE.read_text()).body:
	if isinstance(node, ast.Assign) and any(
		getattr(t, "id", "") in {"DECIDE_THEN_SUBMIT", "DECISIONS"} for t in node.targets
	):
		nodes.append(node)
	if isinstance(node, ast.FunctionDef) and node.name in {
		"can_decide",
		"_decision_access",
		"_request_read_allowed",
		"get_decision_actions",
	}:
		node.decorator_list = []
		nodes.append(node)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)


@settings(max_examples=250, deadline=None)
@given(
	doctype=st.sampled_from(TYPES),
	read=st.booleans(),
	write=st.booleans(),
	field=st.booleans(),
	submit=st.booleans(),
	routed=st.booleans(),
	self_employee=st.booleans(),
	prevent_self=st.booleans(),
	company=st.booleans(),
	workflow=st.booleans(),
	state=st.sampled_from(["pending", "Approved", "Rejected", "Invalid"]),
	docstatus=st.sampled_from([0, 1, 2]),
)
def test_capability_is_exactly_the_shared_decision_access(
	doctype,
	read,
	write,
	field,
	submit,
	routed,
	self_employee,
	prevent_self,
	company,
	workflow,
	state,
	docstatus,
):
	user = "synthetic-reviewer@example.invalid"
	decision_field, initial = namespace["DECIDE_THEN_SUBMIT"][doctype]
	doc = SimpleNamespace(
		doctype=doctype,
		name="SYNTHETIC",
		employee="STAFF",
		company="A",
		docstatus=docstatus,
		modified="2026-09-08 12:00:00",
	)
	setattr(doc, decision_field, initial if state == "pending" else state)
	doc.get = lambda key: getattr(doc, key, None)
	namespace["_is_routed_approver"] = lambda doc: routed
	namespace["get_permitted_fields"] = lambda *args, **kwargs: [decision_field] if field else []

	def get_value(doctype, name, fieldname, **kwargs):
		if fieldname == "user_id":
			return user.upper() if self_employee else "synthetic-staff@example.invalid"
		return "A"

	with (
		patch.dict(
			sys.modules,
			{
				"frappe.model.workflow": SimpleNamespace(
					get_workflow_name=lambda dt: "Workflow" if workflow else None
				),
				"hrms.utils.identity": SimpleNamespace(
					normalize_login=lambda value: (value or "").strip().lower()
				),
				"hrms.overrides.company_scope": SimpleNamespace(company_visible=lambda *args: company),
			},
		),
		patch.object(frappe, "session", SimpleNamespace(user=user)),
		patch.object(
			frappe,
			"db",
			MagicMock(
				get_value=get_value, exists=lambda *args: True, get_single_value=lambda *args: prevent_self
			),
		),
		patch.object(frappe, "get_doc", return_value=doc),
		patch.object(
			frappe,
			"has_permission",
			side_effect=lambda dt, ptype, **kw: {"read": read, "write": write, "submit": submit}[ptype],
		),
	):
		actual = namespace["can_decide"](doctype, doc.name)
		capability = namespace["get_decision_actions"](doctype, doc.name)

	def self_allowed(action):
		return not self_employee or (
			doctype in {"Leave Application", "Expense Claim"}
			and (not prevent_self or (doctype == "Leave Application" and action == "Rejected"))
		)

	authority = (submit and write and field) or routed
	baseline = docstatus == 0 and not workflow and company and read and authority
	expected = []
	if baseline:
		if state == "pending":
			expected = [action for action in ["Approved", "Rejected"] if self_allowed(action)]
		elif state in {"Approved", "Rejected"} and self_allowed(state):
			expected = ["Submit"]
	assert actual == ("Approved" in expected)
	assert capability == {"actions": expected, "modified": doc.modified if expected else None}
