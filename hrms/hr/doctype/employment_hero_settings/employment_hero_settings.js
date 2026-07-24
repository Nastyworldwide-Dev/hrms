// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Employment Hero Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Connect to Employment Hero"), () => {
			frappe
				.call({
					method: "hrms.hr.doctype.employment_hero_settings.employment_hero_settings.get_authorize_url",
				})
				.then((r) => {
					if (r.message) {
						window.open(r.message, "_blank");
					}
				});
		});

		frm.add_custom_button(__("Test Connection"), () => {
			frappe
				.call({
					method: "hrms.hr.doctype.employment_hero_settings.employment_hero_settings.test_connection",
					freeze: true,
					freeze_message: __("Contacting Employment Hero…"),
				})
				.then((r) => {
					if (r.message && r.message.ok) {
						frappe.msgprint({
							title: __("Connected"),
							message: __("Employment Hero organisation: {0}", [
								r.message.organisation || __("OK"),
							]),
							indicator: "green",
						});
					}
				});
		});
	},
});
