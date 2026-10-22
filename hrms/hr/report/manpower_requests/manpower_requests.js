// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. One row per request, the questions HR asks pivoted into columns. Pick Columns, Group By and
// the Excel / CSV export are Frappe's own report view; nothing here rebuilds them or writes.
// The options below are the doctype's own Select options, pinned by manpower_requests.test.js.
//: shown as Desk indicator pills (mockup tab 7); the colour follows Desk's own status palette
const PILL_FIELDS = ["status", "hiring_status", "urgency"];
const PILL_COLOUR = {
	Open: "orange",
	Approved: "green",
	Rejected: "red",
	Withdrawn: "gray",
	"Waiting for HR": "orange",
	Recruiting: "blue",
	Filled: "green",
	"Not proceeding": "red",
	High: "red",
	Medium: "orange",
	Low: "gray",
};

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
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
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
		if (!data) return value;
		// the mockup (tab 7) draws these as pills: Desk's own indicator colours, the word always inside
		if (PILL_FIELDS.includes(column.fieldname) && data[column.fieldname]) {
			const colour = PILL_COLOUR[data[column.fieldname]] || "gray";
			return `<span class="indicator-pill ${colour}">${frappe.utils.escape_html(
				__(data[column.fieldname])
			)}</span>`;
		}
		// waiting on HR for over 30 days reads in red AND in words; the Nadi board's rule: approved, and
		// HR has not picked it up (Waiting for HR, or no hiring status yet)
		const waitingOnHr =
			data.status === "Approved" &&
			(!data.hiring_status || data.hiring_status === "Waiting for HR");
		if (column.fieldname === "days_open" && waitingOnHr && data.days_open > 30) {
			value = `<span class="text-danger" title="${__(
				"Over 30 days with HR"
			)}">${value} ▲</span>`;
		}
		return value;
	},
};
