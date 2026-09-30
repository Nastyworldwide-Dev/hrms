// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. For each active employee, the dates in the coming weeks whose rest
// day would change if leave and payroll followed the shift's calendar first
// (REST_DAY_RULE_PLAN.md, step 0). Nothing here writes.
frappe.query_reports["Rest Day Differences"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "weeks",
			label: __("Weeks ahead"),
			fieldtype: "Int",
			default: 4,
			reqd: 1,
		},
		{
			fieldname: "only_changed",
			label: __("Only people whose rest days change"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
