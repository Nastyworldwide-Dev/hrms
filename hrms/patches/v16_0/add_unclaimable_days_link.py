"""Link the "Unclaimable Days" report next to Shift Attendance for HR.

Nabil, 15 Sep 2026: broken days vanished from Nadi's claim list and HR had no
list of who lost overtime, or why. The Script Report exists (S1); Workspace
and Workspace Sidebar JSON only import when newer and then REPLACE the whole
record, wiping HR's own edits — so this patch inserts the two links into the
live records instead (same reasoning and helpers as add_forgotten_checkouts_link).
Idempotent; never duplicates, deletes or reorders HR's rows.
"""

import logging

import frappe

from hrms.patches.v16_0.add_forgotten_checkouts_link import _after, _insert, _linked

logger = logging.getLogger(__name__)

WORKSPACE_NAME = "Shift & Attendance"
REPORT_NAME = "Unclaimable Days"
REF_DOCTYPE = "Attendance"
CARD = "Reports"
ANCHOR = "Shift Attendance"


def execute():
	if not frappe.db.exists("Report", REPORT_NAME):
		logger.info("[add_unclaimable_days_link] report not installed yet — links skipped")
		return
	_link_workspace()
	_link_sidebar()


def _load(doctype):
	if not frappe.db.exists(doctype, WORKSPACE_NAME):
		logger.info("[add_unclaimable_days_link] %s %s absent — skipped", doctype, WORKSPACE_NAME)
		return None
	return frappe.get_doc(doctype, WORKSPACE_NAME)


def _save(doc, doctype):
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.save()
	logger.info("[add_unclaimable_days_link] %s %s: linked %s", doctype, WORKSPACE_NAME, REPORT_NAME)


def _link_workspace():
	doc = _load("Workspace")
	if not doc or _linked(doc.links, REPORT_NAME):
		return
	links = doc.links
	start = next((n for n, row in enumerate(links) if row.type == "Card Break" and row.label == CARD), None)
	if start is None:
		logger.info("[add_unclaimable_days_link] card %s not on the workspace — not linked", CARD)
		return
	end = next((n for n in range(start + 1, len(links)) if links[n].type == "Card Break"), len(links))
	values = {
		"dependencies": REF_DOCTYPE,
		"hidden": 0,
		"is_query_report": 1,
		"label": REPORT_NAME,
		"link_count": 0,
		"link_to": REPORT_NAME,
		"link_type": "Report",
		"onboard": 0,
		"report_ref_doctype": REF_DOCTYPE,
		"type": "Link",
	}
	_insert(doc, "links", _after(links, start + 1, end, ANCHOR), values)
	links[start].link_count = end - start
	_save(doc, "Workspace")


def _link_sidebar():
	doc = _load("Workspace Sidebar")
	if not doc or _linked(doc.items, REPORT_NAME):
		return
	items = doc.items
	position = next((n + 1 for n, item in enumerate(items) if item.link_to == ANCHOR), None)
	if position is None:
		logger.info("[add_unclaimable_days_link] sidebar has no %s — not linked", ANCHOR)
		return
	values = {
		"child": 0,
		"collapsible": 1,
		"icon": "",
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
