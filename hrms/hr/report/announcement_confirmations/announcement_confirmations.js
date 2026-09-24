// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. Who a notice reached, who read it and who confirmed the current
// wording (alpha.7 4.6, owner Q6). Export with the report's own menu.
frappe.query_reports["Announcement Confirmations"] = {
	filters: [
		{
			fieldname: "announcement",
			label: __("Announcement"),
			fieldtype: "Link",
			options: "HR Announcement",
			reqd: 1,
		},
		{
			fieldname: "show",
			label: __("Show"),
			fieldtype: "Select",
			options: ["Everyone", "Not confirmed", "Confirmed"].join("\n"),
			default: "Everyone",
		},
	],
};
