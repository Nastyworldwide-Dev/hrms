"""Manpower Request: what the Nadi wizard and detail page call.

Reads: `can_request` decides whether Requests offers "Manpower" at all (the controller refuses a
sender with no team regardless); `get_questions` is the list HR keeps in Manpower Request
Settings; `get_progress` is the tracker on the detail page.

`hr_board` is HR's Nadi board: counts and one slim row per request, no pay and no free text.

Writes (POST only): `withdraw` (the sender takes it back) and `set_hiring_status` (HR). Both hand
the work to the document, so its rules and notices run; nothing here decides anything.
"""

import json
import logging

from dateutil.relativedelta import relativedelta

import frappe
from frappe import _
from frappe.utils import getdate

from hrms.api.approval import get_rejection_reason
from hrms.hr.doctype.manpower_request.manpower_request import (
	REPLACEMENT_LEAVER_MONTHS,
	board_group,
	build_progress,
	can_file_manpower_request,
	request_age,
)
from hrms.hr.utils import get_designated_approvers, is_hr_operator, sees_all_employee_data
from hrms.overrides.company_scope import company_visible
from hrms.utils.identity import get_employee, normalize_login

DOCTYPE = "Manpower Request"

#: Which of the board's four lists a request sits in; the Nadi screen draws them in this order.
BOARD_GROUPS = ("waiting_manager", "needs_hr", "recruiting", "done")

#: A request waiting on HR longer than this many days turns the "Needs HR" tile red.
NEEDS_HR_OVER_DAYS = 30

#: The only fields the board reads: who, what, where it stands. Never pay, never free text.
BOARD_FIELDS = [
	"name",
	"position_title",
	"headcount",
	"department",
	"employee_name",
	"status",
	"hiring_status",
	"urgency",
	"creation",
	"modified",
]

#: The two fields whose history the tracker reads; the Version log is the only record of who and when.
TRACKED_FIELDS = ("status", "hiring_status")

logger = logging.getLogger(__name__)


@frappe.whitelist(methods=["GET", "POST"])
def can_request() -> bool:
	"""May the caller send a manpower request? HR, or someone with an Active direct report."""
	allowed = can_file_manpower_request(get_employee())
	logger.debug("[manpower] can_request for %s: %s", frappe.session.user, allowed)
	return allowed


@frappe.whitelist(methods=["GET", "POST"])
def get_questions() -> list[dict]:
	"""The active questions in the order HR set, shaped for the wizard.

	Read with the settings' own permissions bypassed on purpose: the sender holds no right to
	open the Settings, only to answer what it asks. Nothing but the question fields leaves here.
	"""
	settings = frappe.get_cached_doc("Manpower Request Settings")
	rows = sorted((row for row in settings.questions if row.active), key=lambda row: row.idx)
	logger.debug("[manpower] %d active question(s)", len(rows))
	return [
		{
			"step": int(row.step.split(" ", 1)[0]),
			"question": row.question,
			"answer_type": row.answer_type,
			"choices": [line.strip() for line in (row.choices or "").splitlines() if line.strip()],
			"required": 1 if row.required else 0,
			"help": row.help,
		}
		for row in rows
	]


@frappe.whitelist(methods=["GET", "POST"])
def replaceable_staff(department: str) -> list[dict]:
	"""Who can be named as replaced, for the wizard's picker: the department's Active staff first,
	then anyone who left in the last REPLACEMENT_LEAVER_MONTHS months (the request's own rule),
	latest leaver first. The sender is never offered.

	Refused unless the caller may send a request at all. Read past Employee's own permissions on
	purpose (a manager cannot open every colleague), so what leaves is fenced here: five fields
	only, the department asked for, and, unless HR, the caller's own company.
	"""
	me = get_employee()
	if not can_file_manpower_request(me):
		logger.warning("[manpower] replaceable_staff refused for %s: no team", frappe.session.user)
		frappe.throw(_("Only someone with a team can request manpower."), frappe.PermissionError)
	if not department:
		return []
	filters = {"department": department}
	if not sees_all_employee_data(frappe.session.user):
		filters["company"] = frappe.db.get_value("Employee", me, "company")
	earliest = getdate() - relativedelta(months=REPLACEMENT_LEAVER_MONTHS)
	rows = frappe.get_all(
		"Employee",
		filters=filters,
		or_filters=[
			{"status": "Active"},
			{"status": "Left", "relieving_date": [">=", str(earliest)]},
		],
		fields=["name", "employee_name", "designation", "status", "relieving_date"],
	)
	here = sorted(
		(r for r in rows if r.status == "Active" and r.name != me), key=lambda r: r.employee_name or ""
	)
	left = sorted(
		(r for r in rows if r.status != "Active" and r.name != me),
		key=lambda r: str(r.relieving_date or ""),
		reverse=True,
	)
	logger.debug("[manpower] %d staff offered for %s", len(here) + len(left), department)
	return [dict(r) for r in here + left]


def build_board(requests, today) -> dict:
	"""{counts, rows} for the board from plain request rows. Pure: the clock comes in as `today`.

	Ages come from `request_age`. "Filled this month" counts the Filled ones closed in today's month.
	Rows keep the order they came in.
	"""
	rows = []
	counts = dict.fromkeys(("waiting_manager", "needs_hr", "recruiting", "filled_this_month"), 0)
	counts["needs_hr_over_30"] = 0
	for request in requests:
		group = board_group(request.get("status"), request.get("hiring_status"))
		days_open, closed = request_age(request, today)
		if group in counts:
			counts[group] += 1
		if group == "needs_hr" and days_open > NEEDS_HR_OVER_DAYS:
			counts["needs_hr_over_30"] += 1
		if (
			request.get("hiring_status") == "Filled"
			and closed
			and (closed.year, closed.month) == (today.year, today.month)
		):
			counts["filled_this_month"] += 1
		rows.append(
			{
				**{key: request.get(key) for key in BOARD_FIELDS if key != "modified"},
				"days_open": days_open,
				"group": group,
				"closed_on": str(closed) if closed else None,
			}
		)
	return {"counts": counts, "rows": rows}


@frappe.whitelist(methods=["GET", "POST"])
def hr_board(department: str | None = None, search: str | None = None) -> dict:
	"""HR's monitoring board in Nadi: {counts, rows, departments}. HR only.

	Read with frappe.get_list on purpose, so the row scope (the company fence) decides what HR sees;
	nothing is read past permissions. `department` and `search` (position, sender or id) narrow the
	rows and the counts; the department list for the picker is never narrowed by either.
	"""
	if not is_hr_operator():
		logger.warning("[manpower] hr_board refused for %s: not HR", frappe.session.user)
		frappe.throw(_("Only HR can open the manpower board."), frappe.PermissionError)
	filters = [["docstatus", "!=", 2]]
	if department:
		filters.append(["department", "=", department])
	text = (search or "").strip()
	or_filters = (
		[[field, "like", f"%{text}%"] for field in ("position_title", "employee_name", "name")]
		if text
		else None
	)
	# ceiling: every request in the fence is read (a few dozen a year); upgrade: server paging past ~2000 rows
	requests = frappe.get_list(
		DOCTYPE,
		fields=BOARD_FIELDS,
		filters=filters,
		or_filters=or_filters,
		order_by="creation desc",
		limit_page_length=0,
	)
	departments = frappe.get_list(
		DOCTYPE,
		fields=["department"],
		filters=[["docstatus", "!=", 2]],
		group_by="department",
		order_by="department asc",
		limit_page_length=0,
	)
	board = build_board(requests, getdate())
	board["departments"] = [row.department for row in departments if row.department]
	logger.debug("[manpower] hr_board read by %s: %d row(s)", frappe.session.user, len(board["rows"]))
	return board


def _locked_request(name: str):
	"""The request, after taking its row lock, so two taps (or two people) cannot both act on the
	state one of them just changed."""
	if not frappe.db.exists(DOCTYPE, name):
		frappe.throw(_("{0} {1} not found.").format(_(DOCTYPE), name), frappe.DoesNotExistError)
	frappe.db.get_value(DOCTYPE, name, "docstatus", for_update=True)
	return frappe.get_doc(DOCTYPE, name)


@frappe.whitelist(methods=["POST"])
def withdraw(name: str, reason: str | None = None) -> dict:
	"""The sender takes their request back. Only the sender; HR sets Not proceeding instead.

	The request decides whether it can still be withdrawn (Open, or Approved and not yet with
	HR's final word) and keeps the record. Undo lives in the app, which delays this call.
	"""
	doc = _locked_request(name)
	doc.withdraw(reason)
	logger.info("[manpower] %s withdrawn through the API by %s", name, frappe.session.user)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def set_hiring_status(name: str, hiring_status: str, note: str | None = None) -> dict:
	"""HR moves an approved request along: Recruiting, Filled or Not proceeding.

	Saved through the document, so the rules (approved only, final once Filled / Not proceeding,
	Not proceeding needs a note) and the notice to the sender run exactly as in Desk.
	"""
	doc = _locked_request(name)
	if not is_hr_operator():
		logger.warning("[manpower] %s: %s is not HR, hiring status refused", name, frappe.session.user)
		frappe.throw(_("Only HR can set the hiring status."), frappe.PermissionError)
	if not company_visible(doc.company):
		logger.warning("[manpower] %s: %s is fenced out of %s", name, frappe.session.user, doc.company)
		frappe.throw(_("You cannot change a request from another company."), frappe.PermissionError)
	doc.hiring_status = hiring_status
	if note and note.strip():
		doc.hr_note = note.strip()
	doc.save()
	logger.info("[manpower] %s hiring status -> %s by %s", name, hiring_status, frappe.session.user)
	return {"name": doc.name, "hiring_status": doc.hiring_status}


def changes_from_versions(versions, names: dict) -> list[dict]:
	"""The decision and hiring changes in a request's Version log, oldest first, with the name of
	who made each. A Version whose data is not readable is skipped, never fatal."""
	changes = []
	for version in versions:
		try:
			changed = json.loads(version.data or "{}").get("changed", [])
		except ValueError:
			logger.warning("[manpower] a Version of a manpower request holds unreadable data; skipped")
			continue
		for field, old, new in changed:
			if field in TRACKED_FIELDS:
				changes.append(
					{
						"field": field,
						"old": old,
						"new": new,
						"by": names.get(version.owner) or version.owner,
						"at": version.creation,
					}
				)
	return changes


@frappe.whitelist(methods=["GET", "POST"])
def get_progress(name: str) -> list[dict]:
	"""The tracker: [{key, label, who, at, state, note}] for Sent, Manager, HR, Filled.

	Refused unless the caller may read this request (sender, shared approver, HR in their fence).
	"""
	if not frappe.db.exists(DOCTYPE, name):
		frappe.throw(_("{0} {1} not found.").format(_(DOCTYPE), name), frappe.DoesNotExistError)
	doc = frappe.get_doc(DOCTYPE, name)
	if not frappe.has_permission(DOCTYPE, "read", doc=doc):
		frappe.throw(_("You cannot read this request."), frappe.PermissionError)

	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": DOCTYPE, "docname": name},
		fields=["owner", "creation", "data"],
		order_by="creation asc",
	)
	line = (
		get_designated_approvers(doc.employee, "leave_approver", "leave_approvers")
		if doc.status == "Open"
		else []
	)
	logins = {v.owner for v in versions} | {normalize_login(user) for user in line[:1]}
	names = {
		user.name: user.full_name
		for user in frappe.get_all(
			"User", filters={"name": ["in", sorted(logins)]}, fields=["name", "full_name"]
		)
	}
	request = {
		"employee_name": doc.employee_name,
		"creation": doc.creation,
		"status": doc.status,
		"docstatus": doc.docstatus,
		"hiring_status": doc.hiring_status,
		"hr_note": doc.hr_note,
		"approver_name": names.get(normalize_login(line[0])) if line else None,
		"rejection_reason": get_rejection_reason(DOCTYPE, name) if doc.status == "Rejected" else None,
		"withdrawn_reason": doc.withdrawn_reason,
		"withdrawn_at": doc.withdrawn_at,
	}
	logger.debug("[manpower] progress of %s read by %s", name, frappe.session.user)
	return build_progress(request, changes_from_versions(versions, names))
