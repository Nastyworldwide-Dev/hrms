"""Generated recipient invariants, with explicit framework/IO stand-ins.

Executes the production controller class body with an inert Document base;
native permission-engine evidence lives in test_notification_recipients.py.
"""

import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

import frappe

from hrms.overrides.company_scope import company_visible

SOURCE = Path(__file__).with_name("employee_issue.py")
controller = next(node for node in ast.parse(SOURCE.read_text()).body if isinstance(node, ast.ClassDef))
namespace = {
	"Document": object,
	"frappe": frappe,
	"company_visible": company_visible,
	"logger": logging.getLogger(__name__),
	"_": lambda text: text,
	"bold": str,
}
exec(compile(ast.Module(body=[controller], type_ignores=[]), str(SOURCE), "exec"), namespace)
EmployeeIssue = namespace["EmployeeIssue"]


@settings(max_examples=75, deadline=None)
@given(
	companies=st.sets(st.sampled_from(["Company A", "Company B", "Company C"])),
	company=st.sampled_from([None, "Company A", "Company B", "Company C"]),
	document_read=st.booleans(),
	enabled=st.booleans(),
	role=st.sampled_from(["Employee", "HR User", "HR Manager"]),
	self_recipient=st.booleans(),
)
def test_a_notification_never_broadens_company_or_document_access(
	companies, company, document_read, enabled, role, self_recipient
):
	staff = "synthetic-staff@example.invalid"
	recipient = staff if self_recipient else "synthetic-hr@example.invalid"
	rows = []
	doc = EmployeeIssue()
	doc.__dict__.update(
		doctype="Employee Issue",
		name="ISSUE-SYNTHETIC",
		employee="EMP-SYNTHETIC",
		employee_name="Synthetic Employee",
		company=company,
		issue_type="Payroll",
	)

	def get_all(doctype, filters, **kwargs):
		if doctype == "Has Role":
			return [recipient] if role in {"HR User", "HR Manager"} else []
		if doctype == "User":
			return [recipient] if enabled else []
		if doctype == "User Permission":
			return list(companies)
		raise AssertionError(doctype)

	def new_notification(doctype):
		assert doctype == "PWA Notification"
		row = SimpleNamespace()
		row.insert = lambda **kwargs: rows.append(row)
		return row

	with (
		patch.object(frappe, "db", MagicMock(get_value=MagicMock(return_value=staff))),
		patch.object(frappe, "get_all", side_effect=get_all),
		patch.object(frappe, "new_doc", side_effect=new_notification),
		patch.object(frappe, "has_permission", return_value=document_read),
		patch.object(frappe, "session", SimpleNamespace(user=staff)),
	):
		doc.notify_hr_users()
	company_allowed = not companies or company in companies
	expected = (
		enabled
		and role in {"HR User", "HR Manager"}
		and not self_recipient
		and company_allowed
		and document_read
	)
	assert {row.to_user for row in rows} == ({recipient} if expected else set())
