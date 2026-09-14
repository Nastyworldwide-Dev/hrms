frappe.listview_settings["OT Request"] = {
	// Hours are stored to 9 decimals for pay; HR reads them to 2.
	formatters: {
		claimed_hours: (value) => format_number(value, null, 2),
	},
};
