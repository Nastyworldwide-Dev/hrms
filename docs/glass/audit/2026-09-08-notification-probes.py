"""Read-only synthetic inputs exercising real application and local Frappe code.

Run with /home/nabil/verify-bench/env/bin/python. No database connection,
network, mail, notification inserts or other application writes are performed.
The printed observations assert existing defects, not desired behavior.
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
import frappe.permissions as permissions
import frappe.realtime as realtime
from frappe.push_notification import PushNotification

from hrms.hr.doctype.employee_issue.employee_issue import EmployeeIssue
from hrms.hr.doctype.pwa_notification import pwa_notification as notification_scope
from hrms.hr.doctype.pwa_notification.pwa_notification import PWANotification
from hrms.mixins.pwa_notifications import PWANotificationsMixin
from hrms.overrides import company_scope, employee_issue_row_scope, ot_row_scope
from hrms.overrides import remote_checkin_request_hooks as remote

ROOT = Path(__file__).resolve().parents[3]
observations = []

# Real native role permission evaluator against committed DocPerm metadata.
metadata = frappe._dict(json.loads((ROOT / "hrms/hr/doctype/pwa_notification/pwa_notification.json").read_text()))
metadata.permissions = [frappe._dict(row) for row in metadata.permissions]
frappe.local.role_permissions = {}
with patch.object(frappe, "get_roles", return_value=["HR Manager"]), patch.object(
    permissions, "get_rights", return_value=["read", "write", "create", "submit"]
):
    role_perms = permissions.get_role_permissions(metadata, user="synthetic-hr@example.invalid")
assert role_perms["read"] == 0
assert notification_scope.has_permission(SimpleNamespace(to_user="synthetic-hr@example.invalid"), user="synthetic-hr@example.invalid") is True
with patch.object(frappe, "get_meta", return_value=metadata), patch.object(
    permissions, "has_controller_permissions", return_value=True
), patch.object(permissions, "get_role_permissions", return_value=role_perms), patch.object(
    permissions, "has_user_permission", return_value=True
):
    doc_perms = permissions.get_doc_permissions(frappe._dict(doctype="PWA Notification", owner="synthetic-author"), user="synthetic-hr@example.invalid", ptype="read")
assert not doc_perms.get("read")
observations.append("N-FEED-ROLE: real Frappe role/doc evaluators refuse HR Manager-only read despite owned-row hook returning True")

# Actual OT resolver chooses the shift approver; actual OT scope rejects it.
db = MagicMock()
db.get_value.return_value = {"shift_request_approver":"synthetic-shift@example.invalid", "reports_to":"SYNTHETIC-MANAGER"}
ot = SimpleNamespace(doctype="OT Request", employee="SYNTHETIC-EMPLOYEE", name="OT-SYNTHETIC")
with patch.object(frappe, "db", db):
    chosen = PWANotificationsMixin._get_doc_approver(ot)
with patch.object(ot_row_scope, "_unrestricted", return_value=False), patch.object(
    ot_row_scope, "_own_employees", return_value=["SYNTHETIC-SHIFT-EMPLOYEE"]
), patch.object(ot_row_scope, "_reporting_employees", return_value=[]), patch.object(
    ot_row_scope, "get_shared", return_value=[]
):
    visible = ot_row_scope.has_permission(ot, user=chosen)
assert chosen == "synthetic-shift@example.invalid" and visible is False
observations.append("N-OT-RECIPIENT: real OT resolver selects shift approver whom actual OT scope refuses")

# Real issue producer + real company predicate. No actual document inserts.
inserted = []
def fake_new_doc(doctype):
    record = SimpleNamespace(doctype=doctype)
    record.insert = lambda **kwargs: inserted.append(record)
    return record

issue = SimpleNamespace(employee="SYNTHETIC-EMPLOYEE", employee_name="Synthetic Employee", issue_type="Payroll", name="ISSUE-SYNTHETIC", doctype="Employee Issue", company="Synthetic Company A")
issue.get_hr_users = EmployeeIssue.get_hr_users
hr_recipients = ["synthetic-hr-a@example.invalid", "synthetic-hr-b@example.invalid"]
with patch.object(frappe, "db", MagicMock(get_value=MagicMock(return_value="synthetic-employee@example.invalid"))), patch.object(
    frappe, "get_all", return_value=hr_recipients
), patch.object(frappe, "new_doc", side_effect=fake_new_doc), patch.object(
    frappe, "_", side_effect=lambda message, **kw: message
), patch("hrms.hr.doctype.employee_issue.employee_issue._", side_effect=lambda message, **kw: message):
    EmployeeIssue.notify_hr_users(issue)
with patch.object(company_scope, "allowed_companies", return_value=["Synthetic Company B"]):
    allowed = employee_issue_row_scope.has_permission(issue, user=hr_recipients[1])
assert allowed is False
assert inserted[1].to_user == hr_recipients[1]
assert "Synthetic Employee" in inserted[1].message and "Payroll" in inserted[1].message
assert notification_scope.has_permission(inserted[1], user=hr_recipients[1]) is True
observations.append("N-ISSUE-COMPANY: issue read denied by real company fence; producer still addresses name/category notification to other-company HR")

# Native relay transport is replaced, but both application push and framework
# send_notification_to_user execute unchanged. It fires before any commit hook.
sent = []
notification = SimpleNamespace(to_user="synthetic-employee@example.invalid", reference_document_type="OT Request", message="<b>Synthetic approval</b>", get_notification_link=lambda: "https://example.invalid/hrms", name="NOTIF-SYNTHETIC")
with patch.object(PushNotification, "is_enabled", return_value=True), patch.object(
    PushNotification, "_send_post_request", side_effect=lambda *args, **kw: sent.append(args) or {"success":True}
), patch.object(frappe.utils, "get_url", return_value="https://example.invalid"):
    PWANotification.send_push_notification(notification)
assert len(sent) == 1
observations.append("N-PUSH-COMMIT: real application + framework push send reaches transport synchronously without transaction commit")

# Real realtime publisher, replacing Redis transport only.
emitted = []
request = frappe._dict(name="RCR-SYNTHETIC",status="Pending",log_type="IN")
with patch.object(frappe, "publish_realtime", realtime.publish_realtime), patch.object(
    realtime, "emit_via_redis", side_effect=lambda *args: emitted.append(args)
):
    remote._send_push("synthetic-approver@example.invalid", "Synthetic", "Synthetic body", request)
assert len(emitted) == 1
observations.append("N-REALTIME-COMMIT: actual Frappe publisher emits remote event before commit")

with patch.object(frappe.utils, "get_url", return_value="https://example.invalid"):
    for doctype in ("OT Request", "Shift Request"):
        url = PWANotification.get_notification_link(SimpleNamespace(reference_document_type=doctype, reference_document_name="SYNTHETIC"))
        assert url == "https://example.invalid/hrms"
observations.append("N-PUSH-ROUTE: real OT/Shift push deep links fall back to app home despite registered detail routes")

for observation in observations:
    print(observation)
print(f"Confirmed {len(observations)} observations using actual modules; database, transport and identity inputs mocked")
