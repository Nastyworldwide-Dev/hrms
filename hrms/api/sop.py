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
from hrms.overrides.company_scope import company_visible
from hrms.overrides.sop_document_row_scope import _active_employee, _unrestricted, record_visible

logger = logging.getLogger(__name__)

LIST_FIELDS = (
	"name",
	"title",
	"folder",
	"scope",
	"department",
	"company",
	"pinned",
	"published",
	"modified",
	"attachment",
)

NO_EMPLOYEE_MSG = "No active Employee record is linked to your user."
OUT_OF_SCOPE_MSG = "This SOP is not available to you."


def _card(row, attached_names=()) -> dict:
	"""List payload: metadata only — never the content or the file body."""
	logger.debug("[sop] card %s attachment_field=%s", row.name, bool(row.attachment))
	return {
		"name": row.name,
		"title": row.title,
		"folder": row.get("folder") or None,
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


def _folder_rows(has_folder: bool) -> list:
	"""Every SOP Folder in the order staff see them. Empty until migrate has added
	the table and the SOP's folder column: code goes live a moment before migrate,
	and a missing folder must not take the whole SOP page down (as the calendar's
	event_date did, 27 Oct 2026)."""
	if not has_folder:
		return []
	return frappe.get_all(
		"SOP Folder",
		fields=["name", "folder_name", "sort_order"],
		order_by="sort_order asc, folder_name asc",
		limit_page_length=0,
	)


@frappe.whitelist(methods=["GET", "POST"])
def get_sops() -> dict:
	"""Everything the SOP Library screen needs, scoped to the session user."""
	user = frappe.session.user
	is_hr = _unrestricted(user)
	employee = _active_employee(user)
	if not is_hr and not employee:
		logger.warning("[sop] denying get_sops for %s — no active Employee record", user)
		raise frappe.PermissionError(_(NO_EMPLOYEE_MSG))

	department = employee.department if employee else None
	company = employee.company if employee else None
	filters = {} if is_hr else {"published": 1}
	# Read with our own rule, not get_list: with "Apply Strict User Permissions"
	# on, a reader holding a Company User Permission was refused every SOP whose
	# company is blank, i.e. every SOP saved from Nadi ("for the whole group"),
	# and staff saw an empty list (owner, 15 Oct 2026). The role gate stays.
	frappe.has_permission("SOP Document", "read", throw=True)
	has_folder = frappe.get_meta("SOP Document").has_field("folder")
	rows = frappe.get_all(
		"SOP Document",
		filters=filters,
		fields=[field for field in LIST_FIELDS if has_folder or field != "folder"],
		order_by="title asc",
		limit_page_length=0,
	)

	visible_rows = [row for row in rows if _sees(row, is_hr, user, department, company)]
	if rows and not visible_rows:
		_record_why_empty(user, rows, department, company)
	attached_names = _names_with_file_rows([row.name for row in visible_rows if not row.attachment])

	folder_rows = _folder_rows(has_folder)
	known_folders = {folder.name for folder in folder_rows}

	pinned, general, by_department, by_folder = [], [], {}, {}
	for row in visible_rows:
		card = _card(row, attached_names)
		# a folder counts and lists every SOP the reader may see in it, pinned or not
		filed = card["folder"] in known_folders
		if filed:
			by_folder.setdefault(card["folder"], []).append(card)
		# pinned stays in Essentials; any other filed SOP is listed under its folder only
		if card["pinned"]:
			pinned.append(card)
		elif filed:
			continue
		elif row.scope == "General":
			general.append(card)
		else:
			by_department.setdefault(row.department, []).append(card)

	# counted from what THIS reader may see; a folder with none of it is not listed,
	# except to HR, whose picker and Manage folders sheet need the empty ones
	folders = [
		{
			"name": folder.name,
			"folder_name": folder.folder_name,
			"sort_order": folder.sort_order or 0,
			"count": len(by_folder.get(folder.name, [])),
			"sops": by_folder.get(folder.name, []),
		}
		for folder in folder_rows
		if is_hr or by_folder.get(folder.name)
	]

	logger.info(
		"[sop] get_sops user=%s is_hr=%s department=%s pinned=%d general=%d departments=%d folders=%d",
		user,
		is_hr,
		department,
		len(pinned),
		len(general),
		len(by_department),
		len(folders),
	)
	return {
		"is_hr": is_hr,
		"my_department": department,
		"pinned": pinned,
		"general": general,
		"departments": [{"department": dept, "sops": by_department[dept]} for dept in sorted(by_department)],
		"folders": folders,
	}


def _record_why_empty(user: str, rows, department, company) -> None:
	"""Published SOPs exist but this reader sees none: say why, once a day per
	reader, as an Error Log HR can read. The SOP list was empty twice before
	anyone could tell why (15 Oct 2026); nobody should have to guess again."""
	key = f"hrms:sop_empty:{user}"
	if frappe.cache.get_value(key):
		return
	frappe.cache.set_value(key, 1, expires_in_sec=86400)
	other_company = sum(1 for row in rows if row.get("company") and row.get("company") != company)
	other_department = sum(1 for row in rows if row.scope == "Department" and row.department != department)
	frappe.log_error(
		title=f"SOP list empty for {user}",
		message=(
			f"{len(rows)} published SOP(s), none visible to {user} "
			f"(company {company}, department {department}). "
			f"For another company: {other_company}. For another department: {other_department}."
		),
	)


def _sees(row, is_hr: bool, user: str, department, company) -> bool:
	"""Whether this reader may see this SOP: the one rule for the list and the
	reader. HR sees their companies' SOPs and the group-wide ones; everyone else
	a published SOP for their company (or the whole group) that is General or
	for their own department (sop_document_row_scope.record_visible)."""
	if is_hr:
		return company_visible(row.get("company"), user, allow_blank=True)
	return record_visible(row.published, row.scope, row.department, department, row.get("company"), company)


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
	company = employee.company if employee else None
	# the same rule as the list; the role gate without the per-document user
	# permission check that hid group-wide SOPs (see get_sops)
	if not _sees(doc, is_hr, user, department, company) or not frappe.has_permission("SOP Document", "read"):
		logger.warning("[sop] denying %s(%s) for %s — out of scope", caller, name, user)
		raise frappe.PermissionError(_(OUT_OF_SCOPE_MSG))
	return doc, is_hr


@frappe.whitelist(methods=["GET", "POST"])
def get_sop(name: str) -> dict:
	"""Full SOP for the reader sheet."""
	doc, is_hr = _get_visible_doc(name, "get_sop")

	logger.info("[sop] get_sop %s served to %s (is_hr=%s)", name, frappe.session.user, is_hr)
	return {
		"is_hr": is_hr,
		"name": doc.name,
		"title": doc.title,
		"folder": doc.get("folder") or None,
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


@frappe.whitelist(methods=["GET", "POST"])
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


@frappe.whitelist(methods=["POST"])
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


# ---------------------------------------------------------------------------
# SOP folders, managed by HR from the app (owner, 27 Oct 2026). HR only: the same
# rule get_sops uses for is_hr. Deleting a folder that holds SOPs is refused by
# the record itself (SOPFolder.on_trash), so Desk and the app agree.

FOLDER_NAME_MAX = 80


def _require_sop_hr():
	if not _unrestricted(frappe.session.user):
		logger.warning("[sop] %s refused a folder change", frappe.session.user)
		frappe.throw(_("Only HR can change SOP folders."), frappe.PermissionError)


def _clean_name(value) -> str:
	"""A NEW folder name, as typed in the app: trimmed, at most FOLDER_NAME_MAX."""
	name = value.strip() if isinstance(value, str) else ""
	if not name or len(name) > FOLDER_NAME_MAX:
		frappe.throw(_("Name the folder in up to {0} characters.").format(FOLDER_NAME_MAX))
	return name


def _folder_ref(value) -> str:
	"""An EXISTING folder, by its name: any length the field allows (Desk takes 140)."""
	if not isinstance(value, str) or not value.strip():
		frappe.throw(_("Pick a folder."))
	return value


@frappe.whitelist(methods=["POST"])
def save_folder(folder_name, name=None, description=None) -> dict:
	"""Create a folder (placed last), or rename one when `name` is given."""
	_require_sop_hr()
	folder_name = _clean_name(folder_name)
	if name:
		new = frappe.rename_doc("SOP Folder", _folder_ref(name), folder_name, force=False)
		if description is not None:
			frappe.db.set_value("SOP Folder", new, "description", str(description)[:500])
		logger.info("[sop] folder %s renamed to %s by %s", name, new, frappe.session.user)
		return {"name": new}
	orders = [row.sort_order or 0 for row in frappe.get_all("SOP Folder", fields=["sort_order"])]
	doc = frappe.get_doc(
		{
			"doctype": "SOP Folder",
			"folder_name": folder_name,
			"sort_order": max(orders, default=0) + 10,
			"description": str(description)[:500] if description else None,
		}
	).insert()
	logger.info("[sop] folder %s created by %s", doc.name, frappe.session.user)
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def move_folder(name, direction) -> dict:
	"""Move a folder one place up or down; the order is renumbered 10, 20, 30..."""
	_require_sop_hr()
	if direction not in ("up", "down"):
		frappe.throw(_("Move a folder up or down."))
	rows = frappe.get_all(
		"SOP Folder", fields=["name", "sort_order"], order_by="sort_order asc, folder_name asc"
	)
	names = [row.name for row in rows]
	if name not in names:
		frappe.throw(_("That folder is not there."), frappe.DoesNotExistError)
	i = names.index(name)
	j = i - 1 if direction == "up" else i + 1
	if 0 <= j < len(names):
		names[i], names[j] = names[j], names[i]
	for position, folder in enumerate(names, start=1):
		frappe.db.set_value("SOP Folder", folder, "sort_order", position * 10, update_modified=False)
	logger.info("[sop] folder %s moved %s by %s", name, direction, frappe.session.user)
	return {"order": names}


@frappe.whitelist(methods=["POST"])
def delete_folder(name) -> dict:
	"""Delete an empty folder; one that holds SOPs is refused by SOPFolder.on_trash."""
	_require_sop_hr()
	name = _folder_ref(name)
	frappe.delete_doc("SOP Folder", name)
	logger.info("[sop] folder %s deleted by %s", name, frappe.session.user)
	return {"deleted": name}
