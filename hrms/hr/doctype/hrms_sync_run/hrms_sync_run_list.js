// Status at a glance. The list is the operator's first stop after "Sync
// queued", and a plain-text status column made Failed and Completed read
// identically from across the room.
frappe.listview_settings["HRMS Sync Run"] = {
	get_indicator(doc) {
		const colors = {
			Completed: "green",
			Partial: "orange",
			Failed: "red",
			Running: "blue",
		};
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
