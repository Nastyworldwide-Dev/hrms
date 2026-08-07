# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""SOP Library read API for the PWA.

Session-scoped by construction: no endpoint accepts an employee or user
argument. The row-scope hooks already restrict the query, but every rule is
re-applied here in code (defense in depth) — new whitelisted endpoints are the
classic way hook enforcement gets bypassed.

Writes are deliberately absent: HR creates and edits SOPs through the standard
document API, gated by the DocType's permission matrix.
"""

import logging
import os

import frappe
from frappe import _

from hrms.hr.utils import HR_ROLES

logger = logging.getLogger(__name__)

LIST_FIELDS = ("name", "title", "scope", "department", "pinned", "published", "modified", "attachment")


def _is_hr(user: str) -> bool:
	return user == "Administrator" or bool(HR_ROLES & set(frappe.get_roles(user)))


def _active_employee(user: str):
	if not user or user == "Guest":
		return None
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "department"],
		as_dict=True,
	)


def _visible(row, is_hr: bool, department: str | None) -> bool:
	"""The one visibility predicate, shared by list and detail."""
	if is_hr:
		return True
	if not row.published:
		return False
	if row.scope == "General":
		return True
	return bool(row.department) and row.department == department


def _card(row) -> dict:
	"""List payload: metadata only — never the content or the file body."""
	return {
		"name": row.name,
		"title": row.title,
		"scope": row.scope,
		"department": row.department,
		"pinned": bool(row.pinned),
		"published": bool(row.published),
		"modified": row.modified,
		"has_attachment": bool(row.attachment),
	}


@frappe.whitelist()
def get_sops() -> dict:
	"""Everything the SOP Library screen needs, scoped to the session user."""
	user = frappe.session.user
	is_hr = _is_hr(user)
	employee = _active_employee(user)
	if not is_hr and not employee:
		logger.warning("[sop] denying get_sops for %s — no active Employee record", user)
		raise frappe.PermissionError(_("No active Employee record is linked to your user."))

	department = employee.department if employee else None
	filters = {} if is_hr else {"published": 1}
	rows = frappe.get_list(
		"SOP Document",
		filters=filters,
		fields=list(LIST_FIELDS),
		order_by="title asc",
		limit_page_length=0,
	)

	pinned, general, by_department = [], [], {}
	for row in rows:
		if not _visible(row, is_hr, department):
			continue
		card = _card(row)
		if card["pinned"]:
			pinned.append(card)
		elif row.scope == "General":
			general.append(card)
		else:
			by_department.setdefault(row.department, []).append(card)

	logger.info(
		"[sop] get_sops user=%s is_hr=%s department=%s pinned=%d general=%d departments=%d",
		user,
		is_hr,
		department,
		len(pinned),
		len(general),
		len(by_department),
	)
	return {
		"is_hr": is_hr,
		"my_department": department,
		"pinned": pinned,
		"general": general,
		"departments": [{"department": dept, "sops": by_department[dept]} for dept in sorted(by_department)],
	}


@frappe.whitelist()
def get_sop(name: str) -> dict:
	"""Full SOP for the reader sheet. Guarded twice: the same predicate the list
	uses, plus the framework's own permission check."""
	user = frappe.session.user
	is_hr = _is_hr(user)
	employee = _active_employee(user)
	if not is_hr and not employee:
		logger.warning("[sop] denying get_sop(%s) for %s — no active Employee record", name, user)
		raise frappe.PermissionError

	doc = frappe.get_doc("SOP Document", name)
	department = employee.department if employee else None
	if not _visible(doc, is_hr, department) or not frappe.has_permission("SOP Document", "read", doc=doc):
		logger.warning("[sop] denying get_sop(%s) for %s — out of scope", name, user)
		raise frappe.PermissionError

	logger.info("[sop] get_sop %s served to %s (is_hr=%s)", name, user, is_hr)
	return {
		"name": doc.name,
		"title": doc.title,
		"scope": doc.scope,
		"department": doc.department,
		"pinned": bool(doc.pinned),
		"published": bool(doc.published),
		"modified": doc.modified,
		"content": doc.content,
		"attachment": _attachment(doc.attachment),
	}


def _attachment(file_url: str | None) -> dict | None:
	if not file_url:
		return None
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "file_name") or os.path.basename(
		file_url.split("?")[0]
	)
	return {"file_name": file_name, "file_url": file_url}
