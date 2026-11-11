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
		render_audience_picker(frm);
		if (frm.is_new()) return;
		render_reach(frm);
		add_acknowledgement_button(frm);
		add_alpha7_buttons(frm);
	},
	audience(frm) {
		// a new audience is a new list: names of another kind never carry over
		frm.set_value("audience_value", "");
		render_audience_picker(frm);
	},
});

// Which ones (owner, 11 Nov 2026): a list HR picks from, as many as needed,
// instead of a box to type one exact name into. The pills write the field
// one name per line; the server checks each name exists.
const AUDIENCE_DOCTYPE = { Company: "Company", Department: "Department", Branch: "Branch" };

function render_audience_picker(frm) {
	const field = frm.fields_dict.audience_value;
	if (!field) return;
	const doctype = AUDIENCE_DOCTYPE[frm.doc.audience];
	field.$wrapper.find(".hr-audience-picker").remove();
	if (!doctype) {
		field.$wrapper.find(".control-input-wrapper").show();
		return;
	}
	console.info(
		"[HR Announcement] audience picker:",
		doctype,
		names_of(frm.doc.audience_value).length
	);
	field.$wrapper.find(".control-input-wrapper").hide();
	const holder = $('<div class="hr-audience-picker"></div>').insertAfter(
		field.$wrapper.find(".control-label")
	);
	const picker = frappe.ui.form.make_control({
		parent: holder,
		df: {
			fieldtype: "MultiSelectPills",
			fieldname: "audience_value_picker",
			placeholder: __("Search {0}", [__(doctype)]),
			get_data(txt) {
				return frappe.db.get_link_options(doctype, txt);
			},
		},
		render_input: true,
	});
	picker.set_value(names_of(frm.doc.audience_value));
	picker.$input.on("awesomplete-selectcomplete", () => sync_audience(frm, picker));
	picker.$wrapper.on("click", ".btn-remove", () => setTimeout(() => sync_audience(frm, picker)));
	picker.$input.on("keydown", (e) => {
		if (e.keyCode === frappe.ui.keyCode.BACKSPACE)
			setTimeout(() => sync_audience(frm, picker));
	});
	if (frm.doc.docstatus > 0 || !frm.perm?.[0]?.write) picker.$input.prop("disabled", true);
}

//: The names stored one per line, as a list.
const names_of = (value) =>
	String(value || "")
		.split("\n")
		.map((name) => name.trim())
		.filter(Boolean);

function sync_audience(frm, picker) {
	const names = [...new Set(picker.get_value() || [])];
	const joined = names.join("\n");
	if (joined !== (frm.doc.audience_value || "")) frm.set_value("audience_value", joined);
}

// alpha.7 4.2 / 4.6 / Q6: see it as staff do, chase who has not confirmed,
// and the per-person confirmation report.
function add_alpha7_buttons(frm) {
	frm.add_custom_button(__("Preview as staff"), () => {
		window.open(`/hrms/announcements/${encodeURIComponent(frm.doc.name)}?preview=1`, "_blank");
	});
	frm.add_custom_button(__("Confirmation report"), () => {
		frappe.set_route("query-report", "Announcement Confirmations", {
			announcement: frm.doc.name,
		});
	});
	if (!frm.doc.acknowledge_required || !frm.doc.published) return;
	frm.add_custom_button(__("Remind who has not confirmed"), () => {
		frappe.confirm(
			__("Send a reminder to everyone who has not confirmed this notice yet?"),
			() => {
				frappe.call({
					method: "hrms.api.announcements.remind_outstanding",
					args: { name: frm.doc.name },
					callback(r) {
						const n = r.message?.reminded || 0;
						frappe.show_alert({
							message: n
								? __("Reminder sent to {0} people.", [n])
								: __("Everybody has confirmed; nobody to remind."),
							indicator: n ? "green" : "blue",
						});
					},
				});
			}
		);
	});
}

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
