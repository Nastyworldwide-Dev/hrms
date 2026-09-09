"""Drop the saved list sort and columns on the attendance lists so HR sees the new defaults.

Two saved layers outrank a doctype's own list settings:

* per user, `__UserSettings` — the Desk reads
  `view_user_settings.sort_by || <doctype default>`
  (frappe/public/js/frappe/list/list_view.js), so a sort someone once set
  wins forever;
* site-wide, `List View Settings.fields` — one person's use of the column
  picker replaces `in_list_view` for everybody
  (list_view.js `reorder_listview_fields`).

HR reported the check-in list as "haywire": it was sorted by creation
ascending and showed no shift. Changing the doctype JSON alone would have
left every existing user exactly where they were.

`__UserSettings` is a WRITE-BACK cache: `update_user_settings` writes only to
the `_user_settings` Redis hash, and `sync_user_settings` (hourly_maintenance)
is what writes the table. So this syncs first, then edits the table, then
invalidates the one `doctype::user` key it touched. It never drops the whole
hash — that would throw away every preference every user changed in the last
hour, on every doctype.

Only `sort_by` / `sort_order` are removed. Filters, columns and group-by that
people chose themselves stay.
"""

import json

import frappe

DOCTYPES = ("Employee Checkin", "Attendance", "Remote Checkin Request")


def strip_sort(data: dict) -> bool:
	"""Remove sort_by/sort_order wherever a view keeps them. True if anything went."""
	if not isinstance(data, dict):
		return False
	changed = False
	for view in [*data.values(), data]:
		if isinstance(view, dict):
			for key in ("sort_by", "sort_order"):
				if view.pop(key, None) is not None:
					changed = True
	return changed


def execute():
	from frappe.model.utils.user_settings import sync_user_settings

	# A sort set in the last hour lives only in Redis; flush it to the table
	# first or the patch cannot see it (and it would sync back afterwards).
	sync_user_settings()

	rows = frappe.db.sql(
		"""select `user`, `doctype`, `data` from `__UserSettings` where `doctype` in %(doctypes)s""",
		{"doctypes": DOCTYPES},
		as_dict=True,
	)
	cleared = 0
	for row in rows:
		try:
			data = json.loads(row.data) if row.data else {}
		except ValueError:
			continue
		if not strip_sort(data):
			continue
		frappe.db.sql(
			"""update `__UserSettings` set `data` = %(data)s where `user` = %(user)s and `doctype` = %(doctype)s""",
			{"data": json.dumps(data), "user": row.user, "doctype": row.doctype},
		)
		# Only this user's entry for this doctype — frappe's own pattern.
		frappe.cache.hset("_user_settings", f"{row.doctype}::{row.user}", None)
		cleared += 1

	# The site-wide column choice, if anyone ever used the column picker.
	columns_cleared = []
	for doctype in DOCTYPES:
		if frappe.db.get_value("List View Settings", doctype, "fields"):
			frappe.db.set_value("List View Settings", doctype, "fields", None)
			columns_cleared.append(doctype)

	print(
		f"[reset_attendance_list_sort_preferences] cleared a saved sort for {cleared} user/list pair(s); "
		f"cleared saved columns on {columns_cleared or 'none'}"
	)
