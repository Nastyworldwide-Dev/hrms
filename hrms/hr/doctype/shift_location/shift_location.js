// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shift Location", {
	refresh: async (frm) => {
		hrms.set_timezone_options(frm, "timezone");

		const allow_geolocation_tracking = await frappe.db.get_single_value(
			"HR Settings",
			"allow_geolocation_tracking",
		);

		toggle_fence_fields(frm, allow_geolocation_tracking);

		if (!frm.doc.__islocal)
			hrms.add_shift_tools_button_to_form(frm, {
				action: "Assign Shift",
				shift_location: frm.doc.name,
			});
	},

	fetch_geolocation: (frm) => {
		hrms.fetch_geolocation(frm);
	},

	is_free_location: async (frm) => {
		const allow_geolocation_tracking = await frappe.db.get_single_value(
			"HR Settings",
			"allow_geolocation_tracking",
		);
		toggle_fence_fields(frm, allow_geolocation_tracking);
	},
});

// A free location has no fence: the coordinate and radius fields are hidden so
// HR is not asked for numbers that would be ignored. They stay hidden when
// geolocation tracking is off site-wide, as before.
function toggle_fence_fields(frm, allow_geolocation_tracking) {
	const show = Boolean(allow_geolocation_tracking) && !frm.doc.is_free_location;
	frm.toggle_display(
		["checkin_radius", "fetch_geolocation", "latitude", "longitude", "geolocation"],
		show,
	);
}
