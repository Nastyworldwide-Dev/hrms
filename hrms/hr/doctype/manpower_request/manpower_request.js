// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Manpower Request", {
	onload(frm) {
		// the sender is the person asking; the server fills it too when this is empty
		if (!frm.is_new() || frm.doc.employee) return;
		frappe.db.get_value("Employee", { user_id: frappe.session.user, status: "Active" }, "name").then((r) => {
			if (r.message && r.message.name) frm.set_value("employee", r.message.name);
		});
	},
});
