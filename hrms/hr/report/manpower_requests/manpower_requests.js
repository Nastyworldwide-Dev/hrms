// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. One row per request, the questions HR asks pivoted into columns. Pick Columns, Group By and
// the Excel / CSV export are Frappe's own report view; nothing here rebuilds them or writes.
// The options below are the doctype's own Select options, pinned by manpower_requests.test.js.
frappe.query_reports["Manpower Requests"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Open", "Approved", "Rejected", "Withdrawn"],
		},
		{
			fieldname: "hiring_status",
			label: __("Hiring Status"),
			fieldtype: "Select",
			options: ["", "Waiting for HR", "Recruiting", "Filled", "Not proceeding"],
		},
		{
			fieldname: "urgency",
			label: __("Urgency"),
			fieldtype: "Select",
			options: ["", "High", "Medium", "Low"],
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		// a request waiting on HR for over 30 days reads in red AND in words ("42 d")
		if (column.fieldname === "days_open" && data && data.days_open > 30 && data.hiring_status === "Waiting for HR") {
			value = `<span class="text-danger" title="${__("Over 30 days with HR")}">${value} ▲</span>`;
		}
		return value;
	},
};
