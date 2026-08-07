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

# single source of truth for "who is unrestricted", "who is asking" and "what
# may they see" — the row-scope hook module owns all three (see FIX B rationale
# in sop_document_row_scope.record_visible)
from hrms.overrides.sop_document_row_scope import _active_employee, _unrestricted, record_visible

logger = logging.getLogger(__name__)

LIST_FIELDS = ("name", "title", "scope", "department", "pinned", "published", "modified", "attachment")

NO_EMPLOYEE_MSG = "No active Employee record is linked to your user."
OUT_OF_SCOPE_MSG = "This SOP is not available to you."


def _card(row, attached_names=()) -> dict:
	"""List payload: metadata only — never the content or the file body."""
	logger.debug("[sop] card %s attachment_field=%s", row.name, bool(row.attachment))
	return {
		"name": row.name,
		"title": row.title,
		"scope": row.scope,
		"department": row.department,
		"pinned": bool(row.pinned),
		"published": bool(row.published),
		"modified": row.modified,
		"has_attachment": bool(row.attachment) or row.name in attached_names,
	}


def _names_with_file_rows(names: list[str]) -> set[str]:
	"""SOPs whose file arrived as a File row without the attachment field being
	set (Desk sidebar attach, or older PWA uploads) — fall back to the File
	table so those attachments still surface."""
	if not names:
		return set()
	attached = set(
		frappe.get_all(
			"File",
			filters={"attached_to_doctype": "SOP Document", "attached_to_name": ("in", names)},
			pluck="attached_to_name",
		)
	)
	logger.info("[sop] File-row attachment fallback matched %d of %d SOPs", len(attached), len(names))
	return attached


@frappe.whitelist()
def get_sops() -> dict:
	"""Everything the SOP Library screen needs, scoped to the session user."""
	user = frappe.session.user
	is_hr = _unrestricted(user)
	employee = _active_employee(user)
	if not is_hr and not employee:
		logger.warning("[sop] denying get_sops for %s — no active Employee record", user)
		raise frappe.PermissionError(_(NO_EMPLOYEE_MSG))

	department = employee.department if employee else None
	filters = {} if is_hr else {"published": 1}
	rows = frappe.get_list(
		"SOP Document",
		filters=filters,
		fields=list(LIST_FIELDS),
		order_by="title asc",
		limit_page_length=0,
	)

	visible_rows = [
		row for row in rows if is_hr or record_visible(row.published, row.scope, row.department, department)
	]
	attached_names = _names_with_file_rows([row.name for row in visible_rows if not row.attachment])

	pinned, general, by_department = [], [], {}
	for row in visible_rows:
		card = _card(row, attached_names)
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
	is_hr = _unrestricted(user)
	employee = _active_employee(user)
	if not is_hr and not employee:
		logger.warning("[sop] denying get_sop(%s) for %s — no active Employee record", name, user)
		raise frappe.PermissionError(_(NO_EMPLOYEE_MSG))

	doc = frappe.get_doc("SOP Document", name)
	department = employee.department if employee else None
	visible = is_hr or record_visible(doc.published, doc.scope, doc.department, department)
	if not visible or not frappe.has_permission("SOP Document", "read", doc=doc):
		logger.warning("[sop] denying get_sop(%s) for %s — out of scope", name, user)
		raise frappe.PermissionError(_(OUT_OF_SCOPE_MSG))

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
		"attachment": _attachment(doc),
	}


def _attachment(doc) -> dict | None:
	logger.debug("[sop] resolving attachment for %s (field set=%s)", doc.name, bool(doc.attachment))
	if doc.attachment:
		file_name = frappe.db.get_value(
			"File", {"file_url": doc.attachment}, "file_name"
		) or os.path.basename(doc.attachment.split("?")[0])
		return {"file_name": file_name, "file_url": doc.attachment}

	# attachment field empty — fall back to the newest File row attached to the
	# SOP (Desk sidebar attach, or older PWA uploads that never set the field)
	rows = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "SOP Document", "attached_to_name": doc.name},
		fields=["file_name", "file_url"],
		order_by="creation desc",
		limit=1,
	)
	if not rows:
		return None
	logger.info("[sop] %s attachment served via File-row fallback", doc.name)
	return {"file_name": rows[0].file_name, "file_url": rows[0].file_url}
