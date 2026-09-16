// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. Every row is a verdict from hrms/utils/attendance_ownership.py;
// nothing on this page writes, and the "a rebuild would mark" column is the
// recovery's dry-run preview, computed on copies. Today is never read (the
// server clips the window to yesterday).
frappe.query_reports["Attendance Ownership Check"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			// attendance_ownership_check.START_FLOOR
			default: "2026-08-01",
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			// Today's shifts are still running; the server clamps to yesterday
			// too, this stops the picker offering a date it would only undo.
			max_date: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "owner",
			label: __("Owner"),
			fieldtype: "Select",
			// hrms/utils/attendance_ownership.py OWNERS
			options: ["", "hr", "request", "system", "unsure"],
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "owner_label" && data) {
			const colour = { hr: "orange", request: "blue", system: "green", unsure: "grey" }[data.owner];
			if (colour) {
				value = `<span class="indicator-pill ${colour}">${frappe.utils.escape_html(
					String(data.owner_label)
				)}</span>`;
			}
		}
		return value;
	},
};
