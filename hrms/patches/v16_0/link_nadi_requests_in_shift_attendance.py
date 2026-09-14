"""Link the Nadi request doctypes into the live "Shift & Attendance" Desk pages.

THE SYMPTOM (14 Sep 2026): HR could not find OT Request, Replacement Leave
Claim or Remote Checkin Request anywhere in Desk — staff file all three from
Nadi, but the workspace's Overtime card listed only Overtime Type and Overtime
Slip, and neither the workspace nor its sidebar linked the other two.

WHY A PATCH, NOT JUST THE JSON. The shipped JSONs carry the links for fresh
installs. Workspace and Workspace Sidebar JSON only import when the file's
`modified` is newer than the row's, and that import REPLACES the whole record —
so bumping `modified` would wipe every edit HR made to these pages. This patch
instead inserts the rows into the live records.

Idempotent and non-destructive: a doctype already linked anywhere on the page
(HR may have moved it) is left alone; a card or section HR removed is not
recreated; nothing is ever deleted. Card `link_count` is kept exact, because
Workspace.build_links_table_from_card deletes `link_count + 1` rows when HR
next edits the page.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

NAME = "Shift & Attendance"
#: (card, the link it follows, doctype). Order matters: Replacement Leave Claim
#: follows the OT Request row inserted just before it.
WORKSPACE_LINKS = (
	("Attendance", "Attendance Request", "Remote Checkin Request"),
	("Overtime", "Overtime Slip", "OT Request"),
	("Overtime", "OT Request", "Replacement Leave Claim"),
)
#: (section break or None for top level, the item it follows, doctype, icon).
SIDEBAR_LINKS = (
	(None, "Attendance Request", "Remote Checkin Request", "map-pin-check"),
	("Overtime", "Overtime Slip", "OT Request", ""),
	("Overtime", "OT Request", "Replacement Leave Claim", ""),
)


def execute():
	_link_workspace()
	_link_sidebar()


def _load(doctype):
	if not frappe.db.exists(doctype, NAME):
		logger.info("[link_nadi_requests] %s %s absent on this site — skipped", doctype, NAME)
		return None
	return frappe.get_doc(doctype, NAME)


def _linked(rows, doctype):
	return any(row.type == "Link" and row.link_to == doctype for row in rows)


def _after(rows, start, end, anchor):
	"""Position right after `anchor` within rows[start:end], else the end of that range."""
	for position in range(start, end):
		if rows[position].link_to == anchor:
			return position + 1
	return end


def _sidebar_position(items, section, anchor):
	"""Where a sidebar row goes: after its top-level anchor, or inside its section. None = skip."""
	if section is None:
		return next(
			(n + 1 for n, item in enumerate(items) if item.link_to == anchor and not item.child), None
		)
	start = next(
		(n for n, item in enumerate(items) if item.type == "Section Break" and item.label == section), None
	)
	if start is None:
		logger.info("[link_nadi_requests] sidebar section %s not found", section)
		return None
	end = next((n for n in range(start + 1, len(items)) if not items[n].child), len(items))
	return _after(items, start + 1, end, anchor)


def _insert(doc, table, position, values):
	rows = getattr(doc, table)
	row = doc.append(table, values)
	rows.pop()  # append() placed the row last; move it into its card
	rows.insert(position, row)
	for idx, each in enumerate(rows, start=1):
		each.idx = idx


def _save(doc, doctype, added):
	if not added:
		return
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.save()
	logger.info("[link_nadi_requests] %s %s: linked %s", doctype, NAME, added)


def _link_workspace():
	doc = _load("Workspace")
	if not doc:
		return
	added = []
	for card, anchor, doctype in WORKSPACE_LINKS:
		links = doc.links
		if _linked(links, doctype):
			continue
		start = next(
			(n for n, row in enumerate(links) if row.type == "Card Break" and row.label == card), None
		)
		if start is None:
			logger.info("[link_nadi_requests] card %s not on the workspace — %s not linked", card, doctype)
			continue
		end = next((n for n in range(start + 1, len(links)) if links[n].type == "Card Break"), len(links))
		values = {
			"hidden": 0,
			"is_query_report": 0,
			"label": doctype,
			"link_count": 0,
			"link_to": doctype,
			"link_type": "DocType",
			"onboard": 0,
			"type": "Link",
		}
		_insert(doc, "links", _after(links, start + 1, end, anchor), values)
		links[start].link_count = end - start  # the card's rows, now one more
		added.append(doctype)
	_save(doc, "Workspace", added)


def _link_sidebar():
	doc = _load("Workspace Sidebar")
	if not doc:
		return
	added = []
	for section, anchor, doctype, icon in SIDEBAR_LINKS:
		items = doc.items
		if _linked(items, doctype):
			continue
		position = _sidebar_position(items, section, anchor)
		if position is None:
			logger.info("[link_nadi_requests] sidebar has no %s — %s not linked", section or anchor, doctype)
			continue
		values = {
			"child": 0 if section is None else 1,
			"collapsible": 1,
			"icon": icon,
			"indent": 0,
			"keep_closed": 0,
			"label": doctype,
			"link_to": doctype,
			"link_type": "DocType",
			"show_arrow": 0,
			"type": "Link",
		}
		_insert(doc, "items", position, values)
		added.append(doctype)
	_save(doc, "Workspace Sidebar", added)
