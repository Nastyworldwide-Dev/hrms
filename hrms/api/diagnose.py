"""Why can't I create this? — a self-service permission diagnostic.

"You need the 'create' permission on Attendance Request" is one sentence for
at least three different gates in `frappe.has_permission(doctype, "create",
doc)`:

1. **role** — no role of the caller carries `create` at level 0 (Custom
   DocPerm rows on the site override the DocType JSON, and have lost the flag
   before: `patches.v16_0.restore_staff_create_on_pwa_requests`);
2. **a `has_permission` hook** — this fork's row scopes
   (`employee_owned_row_scope`, `approval_row_scope`, ...) can only deny, and
   deny with no message of their own;
3. **User Permissions on link fields** — an `allow=Employee` row naming a
   different Employee than the one the form sends drops the caller to
   owner-only rights, which never include create
   (`patches.v16_0.realign_self_employee_permission`).

Telling them apart has meant reproducing on a bench each time. This endpoint
runs the same gates, in Frappe's order, for the CALLER and the same shape of
document Nadi's create form sends (their own employee, no `company` — that
field is fetched from the employee only after the create check), and names
the first gate that said no.

It reports only about the session user — there is no `user` argument — and
writes nothing. Open in the browser:

    /api/method/hrms.api.diagnose_create_permission?doctype=Attendance%20Request
"""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.permissions import (
	get_doctypes_with_custom_docperms,
	get_role_permissions,
	get_valid_perms,
	has_user_permission,
)
from frappe.permissions import has_permission as check_permission
from frappe.utils import cint

from hrms.utils.identity import own_employees

logger = logging.getLogger(__name__)

GATE_ROLE = "role"
GATE_USER_PERMISSION = "user_permission"
GATE_FRAMEWORK = "frappe.has_permission"


@frappe.whitelist()
def diagnose_create_permission(doctype: str) -> dict:
	"""Every gate of `frappe.has_permission(doctype, "create", <new doc>)` for the caller, with verdicts."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Sign in to run this diagnostic."), frappe.PermissionError)
	meta = frappe.get_meta(doctype)  # an unknown doctype raises DoesNotExistError
	logger.info("[diagnose] %s asks why they cannot create %s", user, doctype)

	roles = sorted(frappe.get_roles(user))
	own = own_employees(user)
	user_permissions = [
		{
			"allow": row.allow,
			"for_value": row.for_value,
			"applicable_for": row.applicable_for,
			"is_default": cint(row.is_default),
		}
		for row in frappe.get_all(
			"User Permission",
			filters={"user": user},
			fields=["allow", "for_value", "applicable_for", "is_default"],
			order_by="allow asc, for_value asc",
		)
	]
	docperms = [
		{
			"role": perm.role,
			"permlevel": cint(perm.permlevel),
			"create": cint(perm.create),
			"if_owner": cint(perm.if_owner),
		}
		for perm in get_valid_perms(doctype, user)
	]
	docperm_source = "Custom DocPerm" if doctype in get_doctypes_with_custom_docperms() else "DocType JSON"
	role_create = bool(get_role_permissions(meta, user=user).get("create"))

	# The document Nadi's create form produces: the caller's own employee and
	# no company (fetch_from writes it AFTER the create check), user defaults
	# applied by new_doc the way insert() applies them.
	doc = frappe.new_doc(doctype)
	if own and meta.has_field("employee"):
		doc.employee = own[0]

	hooks = frappe.get_hooks("has_permission")
	hook_verdicts = [
		{"hook": method, "allows": bool(frappe.call(method, doc=doc, ptype="create", user=user))}
		for method in list(hooks.get(doctype, [])) + list(hooks.get("*", []))
	]
	user_permission_ok = bool(has_user_permission(doc, user, ptype="create"))
	# the permissions-module entry point: no msgprint side effects for the caller
	allowed = bool(check_permission(doctype, "create", doc, user=user, print_logs=False))

	doc_at_check_time = {
		"employee": doc.get("employee"),
		"company": doc.get("company"),
	}
	refused_by = _refusing_gate(allowed, role_create, hook_verdicts, user_permission_ok)
	why = _explain(
		doctype,
		refused_by,
		roles=roles,
		own=own,
		user_permissions=user_permissions,
		doc=doc_at_check_time,
	)
	logger.info("[diagnose] %s create %s: allowed=%s refused_by=%s", user, doctype, allowed, refused_by)
	return {
		"doctype": doctype,
		"user": user,
		"allowed": allowed,
		"refused_by": refused_by,
		"why": why,
		"roles": roles,
		"own_employees": own,
		"user_permissions": user_permissions,
		"docperm_source": docperm_source,
		"docperms": docperms,
		"role_create": role_create,
		"hooks": hook_verdicts,
		"user_permission_ok": user_permission_ok,
		"doc_at_check_time": doc_at_check_time,
		"apply_strict_user_permissions": cint(frappe.get_system_settings("apply_strict_user_permissions")),
	}


def _refusing_gate(allowed, role_create, hook_verdicts, user_permission_ok) -> str | None:
	"""The first gate that said no, in the order Frappe consults them."""
	if allowed:
		return None
	if not role_create:
		return GATE_ROLE
	for verdict in hook_verdicts:
		if not verdict["allows"]:
			return verdict["hook"]
	if not user_permission_ok:
		return GATE_USER_PERMISSION
	return GATE_FRAMEWORK


def _explain(doctype, refused_by, *, roles, own, user_permissions, doc) -> str:
	"""One plain-English sentence a non-developer can act on."""
	sentence = _gate_sentence(
		doctype, refused_by, roles=roles, own=own, user_permissions=user_permissions, doc=doc
	)
	if not own:
		sentence += " Your login resolves to no active Employee record, so the probe carried no employee."
	return sentence


def _gate_sentence(doctype, refused_by, *, roles, own, user_permissions, doc) -> str:
	if refused_by is None:
		return f"You can create {doctype}: every gate passed."
	if refused_by == GATE_ROLE:
		return (
			f"None of your roles ({', '.join(roles)}) has 'create' on {doctype} on this site "
			"(the site's Custom DocPerm rows override the app's JSON)."
		)
	if refused_by == GATE_USER_PERMISSION:
		employee_rows = [up["for_value"] for up in user_permissions if up["allow"] == "Employee"]
		own_text = ", ".join(own) if own else "no active Employee record"
		return (
			f"A User Permission on a link field of {doctype} refused you: your allow=Employee rows name "
			f"{', '.join(employee_rows) or 'nothing'}, but your login resolves to {own_text}. "
			"A stale self permission drops you to owner-only rights, which never include create."
		)
	if refused_by == GATE_FRAMEWORK:
		return f"Frappe refused create on {doctype} but no role, hook or User Permission gate explains it."
	employee_text = doc["employee"] or "no active Employee record for your login"
	return (
		f"The app's row-scope hook {refused_by} refused a new {doctype} for employee "
		f"{employee_text} with company {doc['company']!r} at check time. "
		"That hook fences HR to their companies and staff to their own employee."
	)
