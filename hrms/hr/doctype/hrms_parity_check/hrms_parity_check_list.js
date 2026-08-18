frappe.listview_settings["HRMS Parity Check"] = {
	get_indicator(doc) {
		return doc.in_parity
			? [__("In parity"), "green", "in_parity,=,1"]
			: [__("Variance"), "red", "in_parity,=,0"];
	},
};
