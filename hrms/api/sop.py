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
from urllib.parse import parse_qs, quote, urlparse

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


def _get_visible_doc(name: str, caller: str) -> tuple:
	"""Shared guard for the detail endpoints: same predicate as the list, plus
	the framework's own permission check. Returns (doc, is_hr)."""
	user = frappe.session.user
	is_hr = _unrestricted(user)
	employee = _active_employee(user)
	if not is_hr and not employee:
		logger.warning("[sop] denying %s(%s) for %s — no active Employee record", caller, name, user)
		raise frappe.PermissionError(_(NO_EMPLOYEE_MSG))

	doc = frappe.get_doc("SOP Document", name)
	department = employee.department if employee else None
	visible = is_hr or record_visible(doc.published, doc.scope, doc.department, department)
	if not visible or not frappe.has_permission("SOP Document", "read", doc=doc):
		logger.warning("[sop] denying %s(%s) for %s — out of scope", caller, name, user)
		raise frappe.PermissionError(_(OUT_OF_SCOPE_MSG))
	return doc, is_hr


@frappe.whitelist()
def get_sop(name: str) -> dict:
	"""Full SOP for the reader sheet."""
	doc, is_hr = _get_visible_doc(name, "get_sop")

	logger.info("[sop] get_sop %s served to %s (is_hr=%s)", name, frappe.session.user, is_hr)
	return {
		"is_hr": is_hr,
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
	# same-origin proxy for in-page rendering: external storage (S3 presigned
	# redirects) has no CORS headers, so pdf.js must fetch through our server
	content_url = "/api/method/hrms.api.sop.attachment_content?name=" + quote(doc.name)
	if doc.attachment:
		file_name = frappe.db.get_value(
			"File", {"file_url": doc.attachment}, "file_name"
		) or os.path.basename(doc.attachment.split("?")[0])
		return {"file_name": file_name, "file_url": doc.attachment, "content_url": content_url}

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
	return {"file_name": rows[0].file_name, "file_url": rows[0].file_url, "content_url": content_url}


def _s3_presigned_location(file_url: str) -> str | None:
	"""If the URL is a frappe_s3_attachment redirect link, resolve the presigned
	S3 location in-process (server side has no CORS constraint)."""
	parsed = urlparse(file_url)
	if not parsed.path.endswith("frappe_s3_attachment.controller.generate_file"):
		return None
	query = parse_qs(parsed.query)
	saved_response = frappe.local.response
	frappe.local.response = frappe._dict()
	try:
		frappe.get_attr("frappe_s3_attachment.controller.generate_file")(
			key=query.get("key", [None])[0], file_name=query.get("file_name", [""])[0]
		)
		location = frappe.local.response.get("location")
	finally:
		frappe.local.response = saved_response
	logger.info("[sop] resolved S3 presigned location for %s", parsed.path)
	return location


@frappe.whitelist()
def attachment_content(name: str):
	"""Stream the SOP's attachment bytes same-origin so the inline viewer can
	fetch them (S3-backed files redirect to presigned URLs without CORS
	headers, which pdf.js cannot follow cross-origin)."""
	logger.debug("[sop] attachment_content requested for %s by %s", name, frappe.session.user)
	doc, _is_hr = _get_visible_doc(name, "attachment_content")
	attachment = _attachment(doc)
	if not attachment:
		raise frappe.DoesNotExistError(_("This SOP has no attachment."))

	file_url = attachment["file_url"]
	location = _s3_presigned_location(file_url)
	if location:
		import requests

		response = requests.get(location, timeout=30)
		response.raise_for_status()
		content = response.content
	else:
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		content = file_doc.get_content()

	logger.info(
		"[sop] streaming attachment for %s to %s (%d bytes, s3=%s)",
		name,
		frappe.session.user,
		len(content),
		bool(location),
	)
	frappe.local.response.filename = attachment["file_name"]
	frappe.local.response.filecontent = content
	frappe.local.response.type = "binary"


@frappe.whitelist()
def remove_attachment(name: str):
	"""Explicit removal of the SOP's attachment. The controller's on_update
	cleanup only sees field transitions — legacy rows (and Desk sidebar
	attaches) carry their file purely as a File row with an empty field, so
	'clear the field' is a no-op there and the File-row fallback resurrects
	the file. This deletes every attached File row, whatever the field says."""
	logger.debug("[sop] remove_attachment requested for %s by %s", name, frappe.session.user)
	doc, _is_hr = _get_visible_doc(name, "remove_attachment")
	if not frappe.has_permission("SOP Document", "write", doc=doc):
		logger.warning("[sop] denying remove_attachment(%s) for %s — no write", name, frappe.session.user)
		raise frappe.PermissionError(_("You cannot edit this SOP."))

	file_names = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "SOP Document", "attached_to_name": name},
		pluck="name",
	)
	for file_name in file_names:
		# write on the SOP was just proven; File cleanup is a cascade of it
		frappe.delete_doc("File", file_name, ignore_permissions=True)
	if doc.attachment:
		doc.db_set("attachment", "")

	logger.info(
		"[sop] remove_attachment %s by %s — deleted %d file row(s)",
		name,
		frappe.session.user,
		len(file_names),
	)
	return {"removed": len(file_names)}
