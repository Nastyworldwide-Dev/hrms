// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. The rows come from hrms/utils/attendance_recovery.py's detectors;
// nothing on this page writes. Today is never read (the server clips to yesterday).
frappe.query_reports["Unclaimable Days"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			// attendance_recovery.REPAIR_FLOOR: OT stays claimable four cycles back.
			default: "2026-08-01",
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "family",
			label: __("Family"),
			fieldtype: "Select",
			options: ["", "F1", "F2", "F4", "F6", "F7", "F9", "F13"],
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "fixable", "on purpose", "needs HR"],
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const colour = { fixable: "green", "on purpose": "grey", "needs HR": "orange" }[data.status];
			if (colour) {
				value = `<span class="indicator-pill ${colour}">${frappe.utils.escape_html(
					data.status
				)}</span>`;
			}
		}
		return value;
	},
};
