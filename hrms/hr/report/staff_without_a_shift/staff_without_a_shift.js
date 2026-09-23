// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. Active staff with no shift assignment for today and no default
// shift: their rest-day and holiday overtime cannot be counted until HR sets one.
frappe.query_reports["Staff Without A Shift"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],
};
