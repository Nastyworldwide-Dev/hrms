"""Give HR a Desk link to every forgotten check-out, next to Remote Checkin Request.

THE SYMPTOM (14 Sep 2026): a forgotten check-out is stored as a Remote Checkin
Request with `is_late_checkout = 1` — the same doctype that also holds
out-of-area check-in approvals. HR had no way to see only the forgotten ones:
the "Shift & Attendance" workspace and its sidebar link the doctype
unfiltered, so resolving a forgotten check-out meant opening every Remote
Checkin Request and reading `is_late_checkout` row by row.

WHY A REPORT, NOT A FILTERED DOCTYPE LINK. A Workspace Link row (the card
tiles on the workspace page) has no field for a filter, a route or a URL —
`link_type` is only "DocType" / "Page" / "Report", and the widget that
renders the card ignores anything else it might carry. A Workspace Sidebar
Item CAN carry a `filters` JSON (proven on the sidebar's own DocType links),
but the card cannot, and both entry points need to land on the same view.
A "Report Builder" Report bakes the filter — and here, the sort — into the
report definition itself, and both Workspace Link and Workspace Sidebar Item
can point straight at a Report by name (exactly how the shipped
"Employee Information" report is linked from the HR Setup card and the
Tenure sidebar). So: one Report Builder report, `is_late_checkout = 1`,
linked from both places.

WHY A PATCH, NOT JUST THE JSON. Same reasoning as
link_nadi_requests_in_shift_attendance: Workspace and Workspace Sidebar JSON
only import when the file's `modified` is newer than the row's, and that
import REPLACES the whole record — bumping `modified` would wipe every edit
HR made to these pages. This patch inserts the report and the two links into
the live records instead.

Idempotent and non-destructive: a Report already named "Forgotten
Check-outs" is left alone (HR may have tuned its filters); a link already on
either page (HR may have moved it) is not duplicated; a card or section HR
removed is not recreated; nothing is ever deleted.
"""

import json
import logging

import frappe

logger = logging.getLogger(__name__)

WORKSPACE_NAME = "Shift & Attendance"
REPORT_NAME = "Forgotten Check-outs"
REF_DOCTYPE = "Remote Checkin Request"
CARD = "Attendance"
ANCHOR = "Remote Checkin Request"

REPORT_JSON = json.dumps(
	{
		"filters": [[REF_DOCTYPE, "is_late_checkout", "=", 1]],
		"columns": [
			["employee", REF_DOCTYPE],
			["employee_name", REF_DOCTYPE],
			["checkin_time", REF_DOCTYPE],
			["status", REF_DOCTYPE],
			["approver", REF_DOCTYPE],
			["approved_at", REF_DOCTYPE],
		],
		# Frappe's report view only honours the first field of `order_by` for
		# the query itself (frappe.ui.SortSelector keeps one sort_by/sort_order
		# pair); "status" is kept first so it drives the initial sort, with
		# checkin_time recorded as the intended tiebreak HR can pick from the
		# in-page sort control.
		"order_by": "status asc, checkin_time desc",
		"add_totals_row": 0,
		"page_length": 20,
	}
)


def execute():
	_ensure_report()
	_link_workspace()
	_link_sidebar()


def _ensure_report():
	if frappe.db.exists("Report", REPORT_NAME):
		logger.info("[add_forgotten_checkouts_link] Report %s already exists — left alone", REPORT_NAME)
		return
	frappe.get_doc(
		{
			"doctype": "Report",
			"report_name": REPORT_NAME,
			"ref_doctype": REF_DOCTYPE,
			"report_type": "Report Builder",
			"is_standard": "No",
			"module": "HR",
			"disabled": 0,
			"add_total_row": 0,
			"json": REPORT_JSON,
			"roles": [{"role": "HR User"}, {"role": "HR Manager"}],
		}
	).insert(ignore_permissions=True)
	logger.info("[add_forgotten_checkouts_link] created Report %s", REPORT_NAME)


def _load(doctype):
	if not frappe.db.exists(doctype, WORKSPACE_NAME):
		logger.info(
			"[add_forgotten_checkouts_link] %s %s absent on this site — skipped", doctype, WORKSPACE_NAME
		)
		return None
	return frappe.get_doc(doctype, WORKSPACE_NAME)


def _linked(rows, target):
	return any(row.type == "Link" and row.link_to == target for row in rows)


def _after(rows, start, end, anchor):
	"""Position right after `anchor` within rows[start:end], else the end of that range."""
	for position in range(start, end):
		if rows[position].link_to == anchor:
			return position + 1
	return end


def _insert(doc, table, position, values):
	rows = getattr(doc, table)
	row = doc.append(table, values)
	rows.pop()  # append() placed the row last; move it into its card
	rows.insert(position, row)
	for idx, each in enumerate(rows, start=1):
		each.idx = idx


def _save(doc, doctype):
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.save()
	logger.info("[add_forgotten_checkouts_link] %s %s: linked %s", doctype, WORKSPACE_NAME, REPORT_NAME)


def _link_workspace():
	doc = _load("Workspace")
	if not doc:
		return
	links = doc.links
	if _linked(links, REPORT_NAME):
		return
	start = next((n for n, row in enumerate(links) if row.type == "Card Break" and row.label == CARD), None)
	if start is None:
		logger.info("[add_forgotten_checkouts_link] card %s not on the workspace — not linked", CARD)
		return
	end = next((n for n in range(start + 1, len(links)) if links[n].type == "Card Break"), len(links))
	values = {
		"dependencies": REF_DOCTYPE,
		"hidden": 0,
		"is_query_report": 0,
		"label": REPORT_NAME,
		"link_count": 0,
		"link_to": REPORT_NAME,
		"link_type": "Report",
		"onboard": 0,
		"report_ref_doctype": REF_DOCTYPE,
		"type": "Link",
	}
	_insert(doc, "links", _after(links, start + 1, end, ANCHOR), values)
	links[start].link_count = end - start  # the card's rows, now one more
	_save(doc, "Workspace")


def _link_sidebar():
	doc = _load("Workspace Sidebar")
	if not doc:
		return
	items = doc.items
	if _linked(items, REPORT_NAME):
		return
	position = next(
		(n + 1 for n, item in enumerate(items) if item.link_to == ANCHOR and not item.child), None
	)
	if position is None:
		logger.info("[add_forgotten_checkouts_link] sidebar has no %s — not linked", ANCHOR)
		return
	values = {
		"child": 0,
		"collapsible": 1,
		"icon": "clock-alert",
		"indent": 0,
		"keep_closed": 0,
		"label": REPORT_NAME,
		"link_to": REPORT_NAME,
		"link_type": "Report",
		"show_arrow": 0,
		"type": "Link",
	}
	_insert(doc, "items", position, values)
	_save(doc, "Workspace Sidebar")
