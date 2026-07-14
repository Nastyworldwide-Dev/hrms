// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Intercompany Salary Cost Allocation"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.month_start(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.month_start(), -1),
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Paying Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "territory",
			label: __("Interco (Territory)"),
			fieldtype: "Link",
			options: "Territory",
		},
	],
};
