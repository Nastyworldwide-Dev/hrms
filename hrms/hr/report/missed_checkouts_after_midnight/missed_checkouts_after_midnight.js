// Read-only: the days the 16-hour button bug saved a check-out as a second
// check-in (before alpha.10). HR fixes each with Fix a day, using the real time.
frappe.query_reports["Missed Check-outs After Midnight"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: "2026-08-01", reqd: 1 },
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
	],
};
