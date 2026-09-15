// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. Every linked user is probed the way Nadi's create form would file
// for them; only the refusals are listed. Nothing on this page writes.
frappe.query_reports["Request Access Health"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "doctype",
			label: __("Request Type"),
			fieldtype: "Select",
			options: [
				"",
				"Leave Application",
				"Attendance Request",
				"Shift Request",
				"Compensatory Leave Request",
				"Expense Claim",
				"OT Request",
				"Replacement Leave Claim",
				"Shift Swap Request",
				"Remote Checkin Request",
				"Employee Issue",
			],
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "refused_by" && data && data.refused_by) {
			const colour = { role: "red", user_permission: "orange", identity: "red" }[data.refused_by] || "blue";
			value = `<span class="indicator-pill ${colour}">${frappe.utils.escape_html(data.refused_by)}</span>`;
		}
		return value;
	},
};
