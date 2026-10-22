"""Manpower Requests: the Desk report HR monitors hiring with (S4, 22 Oct 2026).

One row per request. The fixed columns are the request's own facts; after them comes ONE COLUMN PER
QUESTION found in the rows' answers (HR keeps the question list in Manpower Request Settings and
changes it over time), pivoted so the question text is the label. Frappe's own report view gives
pick-columns, group-by and the Excel / CSV export; none of that is rebuilt here.

HR User / HR Manager only (System Manager can open the report in Desk but is not HR, so the code
refuses it, the same ruling as the Nadi board). Rows are read with frappe.get_list, never past
permissions, so the Manpower Request row scope applies and an HR user stays inside their company
fence. Nothing here writes.
"""

from __future__ import annotations

import json
import logging
import re
from html import escape

import frappe
from frappe import _
from frappe.utils import getdate, today

from hrms.hr.doctype.manpower_request.manpower_request import request_age
from hrms.hr.utils import is_hr_operator

logger = logging.getLogger(__name__)

DOCTYPE = "Manpower Request"
ANSWER_DOCTYPE = "Manpower Request Answer"

#: A question's column is q_<slug of its words>; a repeat of the same slug gets _2, _3, ...
QUESTION_PREFIX = "q_"


def fixed_columns() -> list[dict]:
	"""The columns every request has, in the owner's order."""

	def col(fieldname, label, fieldtype="Data", width=120, options=None):
		column = {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width}
		if options:
			column["options"] = options
		return column

	return [
		col("name", "Request", "Link", 150, DOCTYPE),
		col("position_title", "Position", width=170),
		col("headcount", "People needed", "Int", 90),
		col("department", "Department", "Link", 160, "Department"),
		col("employee_name", "Requested by", width=160),
		col("status", "Status", width=100),
		col("hiring_status", "Hiring status", width=130),
		col("urgency", "Urgency", width=90),
		col("how_soon", "How soon", width=120),
		col("band", "Pay band", width=80),
		col("budgeted_salary", "Budgeted salary", "Currency", 130),
		col("proposed_salary", "Proposed salary", "Currency", 130),
		col("location", "Location", width=170),
		col("start_date", "Start date", "Date", 100),
		col("sent_on", "Sent on", "Date", 100),
		col("days_open", "Days open", "Int", 90),
		col("days_to_approve", "Days to approve", "Int", 120),
		col("withdrawn_reason", "Withdrawn reason", width=200),
	]


def _slug(text: str) -> str:
	return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def question_columns(answers) -> list[dict]:
	"""One Data column per distinct question text, in the order the questions are first seen.

	The fieldname is a slug of the words behind a fixed prefix, so it can never clash with a fixed
	column; two questions that slug alike are told apart by a number. A blank question is skipped.
	"""
	columns: list[dict] = []
	seen: dict[str, str] = {}
	taken: set[str] = set()
	for row in answers:
		question = (row.get("question") or "").strip()
		if not question or question in seen:
			continue
		base = QUESTION_PREFIX + (_slug(question) or "question")
		fieldname, n = base, 2
		while fieldname in taken:
			fieldname, n = f"{base}_{n}", n + 1
		taken.add(fieldname)
		seen[question] = fieldname
		# the header is HTML in Desk's datatable: escape what was typed in Settings
		columns.append(
			{
				"fieldname": fieldname,
				"label": escape(question, quote=False),
				"fieldtype": "Data",
				"width": 160,
			}
		)
	return columns


def decision_days(versions, created: dict) -> dict:
	"""{request: days from creation to the manager's decision}, from the Version log. A request the
	manager has not decided has no entry. Pure.

	`created` maps a request to its creation time. A Version whose data cannot be read is skipped.
	"""
	decided: dict = {}
	for version in sorted(versions, key=lambda v: str(v.get("creation"))):
		name = version.get("docname")
		if name in decided or name not in created:
			continue
		try:
			changed = json.loads(version.get("data") or "{}").get("changed", [])
		except ValueError:
			logger.warning("[manpower_requests] a Version of %s holds unreadable data; skipped", name)
			continue
		if any(field == "status" and new in ("Approved", "Rejected") for field, _old, new in changed):
			decided[name] = (getdate(version.get("creation")) - getdate(created[name])).days
	return decided


def location_text(request) -> str:
	"""The listed site, or "Other: <the sender's words>"."""
	if request.get("location"):
		return request["location"]
	other = (request.get("location_other") or "").strip()
	return f"{_('Other')}: {other}" if other else ""


def build_rows(requests, answers, decided: dict, columns: list[dict], today_) -> list[dict]:
	"""A row per request: its facts, its ages, and its answers pivoted into the question columns."""
	by_question = {c["label"]: c["fieldname"] for c in columns}
	answered: dict = {}
	for row in sorted(answers, key=lambda a: (a.get("parent"), a.get("idx") or 0)):
		field = by_question.get((row.get("question") or "").strip())
		if field:
			answered.setdefault(row["parent"], {})[field] = (row.get("answer") or "").strip()
	rows = []
	for request in requests:
		days_open, _closed = request_age(request, today_)
		row = {
			"name": request["name"],
			"position_title": request.get("position_title"),
			"headcount": request.get("headcount"),
			"department": request.get("department"),
			"employee_name": request.get("employee_name"),
			"status": request.get("status"),
			"hiring_status": request.get("hiring_status"),
			"urgency": request.get("urgency"),
			"how_soon": request.get("how_soon"),
			"band": request.get("band"),
			"budgeted_salary": request.get("budgeted_salary"),
			"proposed_salary": request.get("proposed_salary"),
			"location": location_text(request),
			"start_date": request.get("start_date"),
			"sent_on": getdate(request.get("creation")),
			"days_open": days_open,
			"days_to_approve": decided.get(request["name"]),
			"withdrawn_reason": request.get("withdrawn_reason"),
		}
		for column in columns:
			row[column["fieldname"]] = answered.get(request["name"], {}).get(column["fieldname"], "")
		rows.append(row)
	return rows


def _conditions(filters) -> list[list]:
	conditions = [["docstatus", "!=", 2]]
	if filters.get("from_date"):
		conditions.append(["creation", ">=", f"{getdate(filters['from_date'])} 00:00:00"])
	if filters.get("to_date"):
		conditions.append(["creation", "<=", f"{getdate(filters['to_date'])} 23:59:59.999999"])
	for field in ("company", "department", "status", "hiring_status", "urgency"):
		if filters.get(field):
			conditions.append([field, "=", filters[field]])
	return conditions


REQUEST_FIELDS = [
	"name",
	"position_title",
	"headcount",
	"department",
	"employee_name",
	"status",
	"hiring_status",
	"urgency",
	"how_soon",
	"band",
	"budgeted_salary",
	"proposed_salary",
	"location",
	"location_other",
	"start_date",
	"creation",
	"modified",
	"withdrawn_reason",
]


def execute(filters=None):
	if not is_hr_operator():
		logger.warning("[manpower_requests] refused for %s: not HR", frappe.session.user)
		frappe.throw(_("Only HR can open the Manpower Requests report."), frappe.PermissionError)
	filters = frappe._dict(filters or {})
	logger.info("[manpower_requests] execute filters=%s", dict(filters))
	# get_list, not get_all: the row scope (and with it HR's company fence) decides what is listed
	requests = frappe.get_list(
		DOCTYPE,
		fields=REQUEST_FIELDS,
		filters=_conditions(filters),
		order_by="creation desc",
		limit_page_length=0,
	)
	if not requests:
		return fixed_columns(), []
	names = [r["name"] for r in requests]
	# the answers and the log are read for the requests above only; the parent was already let through
	answers = frappe.get_all(
		ANSWER_DOCTYPE,
		filters={"parent": ["in", names], "parenttype": DOCTYPE},
		fields=["parent", "idx", "question", "answer"],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)
	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": DOCTYPE, "docname": ["in", names]},
		fields=["docname", "owner", "creation", "data"],
		order_by="creation asc",
		limit_page_length=0,
	)
	columns = question_columns(answers)
	decided = decision_days(versions, {r["name"]: r["creation"] for r in requests})
	rows = build_rows(requests, answers, decided, columns, today())
	logger.info("[manpower_requests] %d row(s), %d question column(s)", len(rows), len(columns))
	return fixed_columns() + columns, rows
