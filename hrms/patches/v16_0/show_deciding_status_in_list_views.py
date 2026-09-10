"""Show the status that decides something, to people who already picked columns.

Nabil, 10 September, on the Shift Assignment list: "the status shown submitted.
but for how long? isnt it suppose not show these? if they are approve then
approved?"

Every submittable doctype has a DOCUMENT state — Draft / Submitted / Cancelled
— which frappe renders as the list's status indicator. Three of these doctypes
also have a `status` FIELD that means something else entirely and is the one the
code branches on: Shift Assignment is Active/Inactive, and the two requests are
Approved/Rejected. None of the three was a list column, so the page answered
"is this filed?" while looking like it answered "is this in force?".

The doctype JSON now sets `in_list_view`, but that is only the default. Once
anyone uses the column picker, `List View Settings.fields` is written and
replaces the doctype's columns SITE-WIDE for everybody (frappe's list_view.js,
`reorder_listview_fields`). So on a site where HR has ever arranged these
lists — this one — the new column would never appear.

Clearing their saved columns would also work, and would throw away a choice
that is theirs. This appends instead: their columns, plus the one the code
reads.
"""

import json

import frappe

# doctype -> (fieldname, label). The label is only a first draft; the picker
# shows the field's own label once the user opens it.
DECIDING_STATUS = {
	"Shift Assignment": ("status", "Status"),
	"Shift Request": ("status", "Status"),
	"Leave Application": ("status", "Status"),
}


def add_status_column(saved: str | None, fieldname: str, label: str) -> str | None:
	"""The saved column set with `fieldname` appended, or None to leave it alone.

	None means "nothing to do": nothing saved (the doctype default already
	applies), the column is already there, or the value cannot be read. A
	value we cannot parse is left for a human — rewriting it would discard
	columns we cannot see.
	"""
	if not saved or not saved.strip():
		return None
	try:
		columns = json.loads(saved)
	except (ValueError, TypeError):
		return None
	if not isinstance(columns, list) or not columns:
		return None
	if not all(isinstance(column, dict) for column in columns):
		return None
	# "status_field" is list_view.js's name for the DOCUMENT-state indicator,
	# not this field. Counting it would re-make the exact confusion.
	if any(column.get("fieldname") == fieldname for column in columns):
		return None
	return json.dumps([*columns, {"fieldname": fieldname, "label": label}])


def execute():
	touched = []
	for doctype, (fieldname, label) in DECIDING_STATUS.items():
		if not frappe.db.exists("List View Settings", doctype):
			continue
		saved = frappe.db.get_value("List View Settings", doctype, "fields")
		updated = add_status_column(saved, fieldname, label)
		if updated is None:
			continue
		frappe.db.set_value("List View Settings", doctype, "fields", updated)
		touched.append(doctype)

	print(
		"[show_deciding_status_in_list_views] appended the deciding status column on "
		f"{touched or 'none'} (the rest already show it, or have no saved columns "
		"and so follow the doctype)"
	)
