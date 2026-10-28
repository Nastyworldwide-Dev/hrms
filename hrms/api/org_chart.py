# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Org chart node and photo endpoints for the PWA.

Staff see Active employees of their own company; HR sees all companies.
Card shows name, designation, department, branch, photo, away today (bool, NEVER
the leave type), and team size.
"""

import logging
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _
from frappe.utils import getdate

from hrms.api.profile_photo import photo_url
from hrms.hr.utils import sees_all_employee_data
from hrms.utils.identity import get_employee, require_employee
from hrms.utils.leave_day import by_employee, off_session

logger = logging.getLogger(__name__)

FIELDS = ["name", "employee_name", "designation", "department", "branch", "company", "reports_to", "image"]
MAX_CHAIN_STEPS = 12


def _visible(target_company: str, is_hr: bool, my_company: str) -> bool:
	"""Whether the caller may see someone in target_company."""
	return is_hr or target_company == my_company


def _active(**filters) -> list:
	"""Active employees matching filters (fenced by the caller, not by Desk perms)."""
	return frappe.get_all(
		"Employee", filters={"status": "Active", **filters}, fields=FIELDS, limit_page_length=0
	)


def _fence(target_company: str, is_hr: bool, my_employee: str):
	my_row = frappe.get_all("Employee", filters={"name": my_employee}, fields=["company"], limit=1)
	my_company = my_row[0].get("company") if my_row else None
	if not _visible(target_company, is_hr, my_company):
		# Same answer as a missing employee, so staff cannot probe other companies.
		frappe.throw(_("Employee not found."), frappe.DoesNotExistError)


def _team_sizes(ids, scope: dict | None = None) -> dict:
	"""{manager: Active direct reports}, one grouped read, under the caller's company scope."""
	rows = frappe.get_all(
		"Employee",
		filters={"status": "Active", "reports_to": ["in", list(ids)], **(scope or {})},
		fields=["reports_to", {"COUNT": "name", "as": "n"}],
		group_by="reports_to",
		limit_page_length=0,
	)
	return {r["reports_to"]: r["n"] for r in rows}


@frappe.whitelist(methods=["GET"])
def get_node(employee: str | None = None, company: str | None = None) -> dict:
	"""The person, their chain up, reports, peers, and (HR only) gaps."""
	my_employee = require_employee()
	is_hr = sees_all_employee_data()
	target = employee or my_employee

	rows = _active(name=target)
	if not rows:
		frappe.throw(_("Employee not found."), frappe.DoesNotExistError)
	target_row = rows[0]
	target_company = target_row.get("company")
	_fence(target_company, is_hr, my_employee)

	# Staff never see past their own company, whoever the chain points at.
	scope = {} if is_hr else {"company": target_company}
	my_company_only = not is_hr

	chain = []
	seen = {target}
	current = target_row.get("reports_to")
	while current and current not in seen and len(chain) < MAX_CHAIN_STEPS:
		seen.add(current)
		manager = _active(name=current)
		if not manager:
			chain.append({"left": True, "name": current} if is_hr else {"left": True})
			break
		if my_company_only and manager[0].get("company") != target_company:
			break
		chain.append(manager[0])
		current = manager[0].get("reports_to")

	reports = sorted(_active(reports_to=target, **scope), key=lambda e: e.get("employee_name") or "")
	manager_id = target_row.get("reports_to")
	peers = []
	if manager_id:
		peers = sorted(
			(p for p in _active(reports_to=manager_id, **scope) if p["name"] != target),
			key=lambda e: e.get("employee_name") or "",
		)

	gaps_rows = {"no_manager": [], "left_manager": []}
	if is_hr:
		in_company = _active(company=company or target_company)
		sizes = _team_sizes([e["name"] for e in in_company])
		tops = [e for e in in_company if not e.get("reports_to")]
		top = max(tops, key=lambda e: sizes.get(e["name"], 0), default=None)
		gaps_rows["no_manager"] = [e for e in tops if e is not top]
		managers = {e["reports_to"] for e in in_company if e.get("reports_to")}
		live = {e["name"] for e in _active(name=["in", list(managers)])} if managers else set()
		gaps_rows["left_manager"] = [
			e for e in in_company if e.get("reports_to") and e["reports_to"] not in live
		]

	people = [target_row, *[c for c in chain if "left" not in c], *reports, *peers]
	people += gaps_rows["no_manager"] + gaps_rows["left_manager"]
	ids = list({p["name"] for p in people})
	today = getdate()
	leaves = by_employee(ids, today)
	sizes = _team_sizes(ids, scope)

	def card(row: dict) -> dict:
		rid = row["name"]
		rows_off = leaves.get(rid)
		return {
			"id": rid,
			"name": row.get("employee_name"),
			"designation": row.get("designation"),
			"department": row.get("department"),
			"branch": row.get("branch"),
			"company": row.get("company"),
			"image": photo_url(rid, row["image"]) if row.get("image") else "",
			"away": bool(rows_off) and off_session(rows_off, today) is None,
			"team_size": sizes.get(rid, 0),
		}

	result = {
		"person": card(target_row),
		"chain_up": [c if "left" in c else card(c) for c in chain],
		"reports": [card(r) for r in reports],
		"peers": [card(p) for p in peers],
	}
	if is_hr:
		result["gaps"] = {k: [card(r) for r in v] for k, v in gaps_rows.items()}

	logger.info(
		"[org_chart] get_node user=%s target=%s hr=%s chain=%d reports=%d peers=%d",
		frappe.session.user,
		target,
		is_hr,
		len(chain),
		len(reports),
		len(peers),
	)
	return result


@frappe.whitelist(methods=["GET"])
def photo(employee: str, v: str | None = None):
	"""Serve an employee's photo (User.user_image points here).

	HR is served any company, Active or Left. A caller with no Employee row
	(System Manager, Administrator) is served when Desk lets them read it. Staff get
	the company fence and Active targets only; Desk permission is never consulted
	for staff, because Employee is an org-wide directory in Desk.
	"""
	rows = frappe.get_all(
		"Employee",
		filters={"name": employee},
		fields=["name", "company", "status", "image"],
		limit=1,
	)
	if not rows:
		frappe.throw(_("Employee not found."), frappe.DoesNotExistError)
	if sees_all_employee_data():
		pass
	elif get_employee() is None:
		if not frappe.has_permission("Employee", "read", doc=employee):
			frappe.throw(_("Employee not found."), frappe.DoesNotExistError)
	else:
		if rows[0].get("status") != "Active":
			frappe.throw(_("Employee not found."), frappe.DoesNotExistError)
		_fence(rows[0].get("company"), False, require_employee())

	image = rows[0].get("image")
	if not image:
		frappe.throw(_("No photo."), frappe.DoesNotExistError)

	if not frappe.db.exists(
		"File", {"file_url": image, "attached_to_doctype": "Employee", "attached_to_name": employee}
	):
		frappe.throw(_("No photo."), frappe.DoesNotExistError)

	logger.info("[org_chart] photo user=%s employee=%s", frappe.session.user, employee)

	if "frappe_s3_attachment.controller.generate_file" in image:
		# Our fence above is the access check; sign directly, no identity switch.
		query = parse_qs(urlparse(image).query)
		key = query.get("key", [None])[0]
		file_name = query.get("file_name", [""])[0]
		if key:
			client = frappe.get_attr("frappe_s3_attachment.controller.get_s3_client")()
			frappe.local.response.type = "redirect"
			frappe.local.response.location = client.get_url(key, file_name)
			return

	file_doc = frappe.get_doc("File", {"file_url": image})
	frappe.local.response.filename = file_doc.file_name
	frappe.local.response.filecontent = file_doc.get_content()
	frappe.local.response.type = "binary"
