// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Out of Radius Activity"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -6),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "shift_type",
			label: __("Shift Type"),
			fieldtype: "Link",
			options: "Shift Type",
		},
		{
			fieldname: "shift_location",
			label: __("Shift Location"),
			fieldtype: "Link",
			options: "Shift Location",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["All", "Pending", "Approved", "Rejected", "Blocked", "Misconfig"].join("\n"),
			default: "All",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const palette = {
				Pending: "background:#fef3c7; color:#92400e",
				Approved: "background:#d1fae5; color:#065f46",
				Rejected: "background:#f3f4f6; color:#374151",
				Blocked: "background:#fee2e2; color:#991b1b",
				Misconfig: "background:#fee2e2; color:#991b1b",
			};
			const style = palette[data.status];
			if (style) {
				value = `<span style="padding:2px 8px; border-radius:9999px; font-size:11px; font-weight:600; ${style}">${data.status}</span>`;
			}
		}
		return value;
	},
};
