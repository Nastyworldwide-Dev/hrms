"""Drop the saved list sort on the attendance lists so HR sees the new default.

The Desk list reads `view_user_settings.sort_by || <doctype default>`
(frappe/public/js/frappe/list/list_view.js), so a sort a user once set — or
that their browser saved for them — outranks the doctype forever. HR reported
the check-in list as "haywire": it was sorted by creation ascending, and
changing the doctype default alone would have left every existing user exactly
where they were.

Clears only `sort_by` / `sort_order` from `__UserSettings` for the three
attendance lists. Filters, columns and group-by that people chose themselves
are left untouched.
"""

import json

import frappe

DOCTYPES = ("Employee Checkin", "Attendance", "Remote Checkin Request")


def execute():
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
		if not isinstance(data, dict):
			continue
		changed = False
		for view in [*data.values(), data]:
			if isinstance(view, dict):
				for key in ("sort_by", "sort_order"):
					if view.pop(key, None) is not None:
						changed = True
		if not changed:
			continue
		frappe.db.sql(
			"""update `__UserSettings` set `data` = %(data)s where `user` = %(user)s and `doctype` = %(doctype)s""",
			{"data": json.dumps(data), "user": row.user, "doctype": row.doctype},
		)
		cleared += 1

	frappe.db.commit()
	print(f"[reset_attendance_list_sort_preferences] cleared a saved sort for {cleared} user/list pair(s)")
