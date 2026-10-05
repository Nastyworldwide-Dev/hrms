frappe.listview_settings["Remote Checkin Request"] = {
	// Not submittable: the status field is the whole truth. Waiting / Approved / Rejected, the same words
	// as Nadi (owner, 5 Oct 2026). The stored word stays Pending, so filters and reports do not move.
	get_indicator: (doc) => {
		if (doc.status === "Approved") return [__("Approved"), "green", "status,=,Approved"];
		if (doc.status === "Rejected") return [__("Rejected"), "red", "status,=,Rejected"];
		return [__("Waiting"), "orange", "status,=,Pending"];
	},
};
