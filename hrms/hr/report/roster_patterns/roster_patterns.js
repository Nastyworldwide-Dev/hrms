// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. Sorts each active employee by how their last full weeks were
// rostered (Fixed / Weekly / Rotating / Day by day). Nothing here writes.
frappe.query_reports["Roster Patterns"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "weeks",
			label: __("Weeks"),
			fieldtype: "Int",
			default: 8,
			reqd: 1,
		},
	],
};
