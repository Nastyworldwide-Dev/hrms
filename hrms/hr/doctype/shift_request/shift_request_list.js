frappe.listview_settings["Shift Request"] = {
	// Waiting / Approved / Rejected / Cancelled, the same words as Nadi (hrms.request_status)
	has_indicator_for_draft: 1,
	get_indicator: (doc) => hrms.request_status.indicator(doc),
	onload: (list_view) =>
		hrms.add_shift_tools_button_to_list(list_view, "Process Shift Requests"),
};
