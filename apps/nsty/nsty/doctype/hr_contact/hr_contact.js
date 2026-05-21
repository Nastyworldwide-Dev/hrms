// Copyright (c) 2026, Nsty and contributors
// For license information, please see license.txt

frappe.ui.form.on("HR Contact", {
	refresh(frm) {
		frm.set_query("employee", () => ({
			query: "nsty.api.hr_contacts.employee_with_hr_role_query",
		}))
	},
})
