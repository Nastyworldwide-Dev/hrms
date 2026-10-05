frappe.listview_settings["Replacement Leave Claim"] = {
	// Waiting / Approved / Rejected / Cancelled, the same words as Nadi (hrms.request_status)
	has_indicator_for_draft: 1,
	get_indicator: (doc) => hrms.request_status.indicator(doc),
};
