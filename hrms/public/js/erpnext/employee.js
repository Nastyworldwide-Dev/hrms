// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee", {
	refresh: function (frm) {
		// IC number (3 Nov 2026): HR sees the real field; a person opening their OWN
		// profile gets it from the server's onload, read-only, and nobody else gets it.
		const ownIc = frm.doc.__onload && frm.doc.__onload.own_ic_number;
		if (ownIc && !frm.get_perm(2, "read")) {
			frm.set_intro("");
			frm.dashboard.set_headline(__("Your IC number: {0}", [frappe.utils.escape_html(ownIc)]));
		}
		frm.set_query("payroll_cost_center", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		// filter advance account based on salary currency
		if (frm.doc.salary_currency) {
			frm.set_query("employee_advance_account", function () {
				return {
					filters: {
						root_type: "Asset",
						is_group: 0,
						company: frm.doc.company,
						account_currency: frm.doc.salary_currency,
						account_type: "Receivable",
					},
				};
			});
		}
		// Cost Tag/Center: the ERP's cost tags, which NASTY keeps as Territory
		// (owner, 11 Nov 2026; mirrored by the sync). Leaves only: a group such as
		// "All Territories" cannot carry a split.
		frm.set_query("territory", "interco_cost_allocation", () => {
			return { filters: { is_group: 0 } };
		});
		frm.set_df_property("holiday_list", "hidden", 1);

		// The naming-series mode hides Employee Number on the create form. On an
		// existing profile it is useful to see the saved value, but it must not
		// become an editable alternative to the generated employee ID.
		frappe.db.get_single_value("HR Settings", "emp_created_by").then((value) => {
			frm.toggle_display("naming_series", value === "Naming Series");
			if (!frm.fields_dict.employee_number) return;
			if (value === "Employee Number") {
				frm.set_df_property("employee_number", "read_only", frm.is_new() ? 0 : 1);
				frm.set_df_property("employee_number", "hidden", 0);
			} else if (frm.is_new()) {
				frm.set_df_property("employee_number", "read_only", 0);
				frm.set_df_property("employee_number", "hidden", 1);
			} else {
				frm.set_df_property("employee_number", "read_only", 1);
				frm.set_df_property("employee_number", "hidden", 0);
			}
			console.info("[employee] Employee Number display mode:", value, "existing:", !frm.is_new());
		});
	},

	date_of_birth(frm) {
		frm.call({
			method: "hrms.overrides.employee_master.get_retirement_date",
			args: {
				date_of_birth: frm.doc.date_of_birth,
			},
		}).then((r) => {
			if (r && r.message) frm.set_value("date_of_retirement", r.message);
		});
	},
});
