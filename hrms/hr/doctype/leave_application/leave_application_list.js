frappe.listview_settings["Leave Application"] = {
	add_fields: [
		"leave_type",
		"employee",
		"employee_name",
		"total_leave_days",
		"from_date",
		"to_date",
	],
	// Waiting / Approved / Rejected / Cancelled, the same words as Nadi (hrms.request_status)
	has_indicator_for_draft: 1,
	get_indicator: (doc) => hrms.request_status.indicator(doc),
};
