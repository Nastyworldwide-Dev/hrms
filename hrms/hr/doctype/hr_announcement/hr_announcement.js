// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// HR's side of the announcement board.
//
// The plan promised HR one number — "read by 31 of 44" — and it was the only
// report named, because it is the only one anybody asks for: did the notice
// land. Without it HR publishes into silence and has no way to tell a notice
// nobody read from a notice nobody needed.
//
// Everything here is DISPLAY on a saved document. The publish itself is the
// `published` checkbox the form already has; nothing in this file writes.

frappe.ui.form.on("HR Announcement", {
	refresh(frm) {
		if (frm.is_new()) return;
		render_reach(frm);
		add_acknowledgement_button(frm);
	},
});

function render_reach(frm) {
	frappe.call({
		method: "hrms.api.announcements.get_reach",
		args: { name: frm.doc.name },
		callback(r) {
			const reach = r.message;
			if (!reach) return;

			// One sentence, at the top of the form. A chart of two numbers is a
			// chart nobody reads; the sentence is the whole report.
			const read = reach.read_count;
			const total = reach.audience_count;
			let message = __("Read by {0} of {1}", [read, total]);

			if (reach.acknowledge_required) {
				message += " · " + __("{0} confirmed", [reach.acknowledged_count]);
			}
			if (!frm.doc.published) {
				message = __("Not published yet — nobody can see this.");
			}

			frm.dashboard.clear_headline();
			frm.dashboard.set_headline(message);
		},
	});
}

function add_acknowledgement_button(frm) {
	// Only where it means something. A "who has not confirmed" list on a notice
	// that never asked for confirmation is a list of everybody, which is noise.
	if (!frm.doc.acknowledge_required || !frm.doc.published) return;

	frm.add_custom_button(__("Who has not confirmed"), () => {
		frappe.call({
			method: "hrms.api.announcements.get_outstanding",
			args: { name: frm.doc.name },
			callback(r) {
				const names = r.message || [];
				if (!names.length) {
					frappe.msgprint({
						title: __("Everybody has confirmed"),
						message: __("Every employee this reaches has confirmed they read it."),
						indicator: "green",
					});
					return;
				}
				// Names, plainly. HR chases people by name, and a table with
				// one column is a list wearing a table's clothes.
				frappe.msgprint({
					title: __("{0} have not confirmed", [names.length]),
					message: names.map(frappe.utils.escape_html).join("<br>"),
					indicator: "orange",
				});
			},
		});
	});
}
