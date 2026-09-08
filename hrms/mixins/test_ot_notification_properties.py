"""Generated OT routing properties executing production function/class bodies.

Native permission/identity evidence is in test_ot_notification_recipients.py;
this suite supplies explicit framework, identity and persistence boundaries.
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

ROOT = Path(__file__).parents[1]


def load_nodes(path, names, namespace):
	tree = ast.parse(path.read_text())
	nodes = [n for n in tree.body if getattr(n, "name", None) in names]
	exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
	return namespace


namespace = {"frappe": frappe, "bold": str, "logger": logging.getLogger(__name__)}
load_nodes(ROOT / "mixins/pwa_notifications.py", {"PWANotificationsMixin"}, namespace)
load_nodes(ROOT / "api/approval.py", {"_is_routed_approver"}, namespace)
namespace["APPROVER_FIELD"] = {}
normalize = load_nodes(ROOT / "utils/identity.py", {"normalize_login"}, {})["normalize_login"]


@settings(max_examples=75, deadline=None)
@given(
	enabled=st.booleans(),
	read=st.booleans(),
	company=st.sampled_from(["A", "B"]),
	routed=st.booleans(),
	self_recipient=st.booleans(),
	upper=st.booleans(),
)
def test_ot_recipient_requires_enabled_company_read_and_actual_routing(
	enabled, read, company, routed, self_recipient, upper
):
	staff, manager = "synthetic-staff@example.invalid", "synthetic-manager@example.invalid"
	target = staff if self_recipient else manager
	login = " " + target.upper() + " " if upper else target
	rows = []
	doc = namespace["PWANotificationsMixin"]()
	doc.__dict__.update(
		doctype="OT Request",
		name="OT-SYNTHETIC",
		employee="STAFF",
		employee_name="Synthetic",
		company="A",
		docstatus=0,
	)
	doc.get = lambda key: getattr(doc, key, None)

	def get_value(dt, name, field, **kw):
		if dt == "User":
			return enabled
		if field == "company":
			return "A"
		if field == "reports_to":
			return "STAFF" if self_recipient else "MANAGER"
		if field == "user_id":
			return staff if name == "STAFF" else login
		# Legacy shift resolver: proves this reports_to-only contract red too.
		if isinstance(field, list):
			return {"shift_request_approver": manager}
		raise AssertionError(field)

	def get_all(dt, filters, **kw):
		if dt == "User Permission":
			return [company]
		return []  # no HR fallback in this property

	def new_doc(dt):
		row = SimpleNamespace()
		row.insert = lambda **kw: rows.append(row)
		return row

	identity = SimpleNamespace(
		normalize_login=normalize,
		own_employees=lambda user: ["STAFF" if self_recipient else "MANAGER"] if routed else [],
	)
	with (
		patch.dict(
			sys.modules,
			{
				"hrms.api.approval": SimpleNamespace(_is_routed_approver=namespace["_is_routed_approver"]),
				"hrms.utils.identity": identity,
				"hrms.overrides.remote_checkin_request_hooks": SimpleNamespace(
					resolve_approver=lambda employee: manager
				),
			},
		),
		patch.object(frappe, "db", MagicMock(get_value=get_value)),
		patch.object(frappe, "session", SimpleNamespace(user=staff)),
		patch.object(frappe, "get_all", side_effect=get_all),
		patch.object(frappe, "get_roles", return_value=["Employee"]),
		patch.object(frappe, "has_permission", return_value=read),
		patch.object(frappe, "new_doc", side_effect=new_doc),
	):
		doc.notify_approver()
		expected = enabled and read and company == "A" and routed and not self_recipient
		assert [row.to_user for row in rows] == ([manager] if expected else [])
