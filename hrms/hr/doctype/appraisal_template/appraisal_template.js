// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Appraisal Template", {
	setup(frm) {
		frm.get_field("rating_criteria").grid.editable_fields = [
			{ fieldname: "criteria", columns: 6 },
			{ fieldname: "per_weightage", columns: 5 },
		];

		// Filter KPI by KRA in goals table
		frm.set_query("kpi", "goals", (doc, cdt, cdn) => {
			let row = frappe.get_doc(cdt, cdn);
			return { filters: { kra: row.key_result_area } };
		});
	},
});

frappe.ui.form.on("Appraisal Template Goal", {
	kpi(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.kpi) {
			frappe.db.get_value("KPI", row.kpi, ["title", "default_target", "unit_of_measure"], (r) => {
				if (r) {
					frappe.model.set_value(cdt, cdn, "kpi_description", r.title);
					if (flt(r.default_target)) {
						frappe.model.set_value(cdt, cdn, "default_target", r.default_target);
					}
					if (r.unit_of_measure) {
						frappe.model.set_value(cdt, cdn, "unit_of_measure", r.unit_of_measure);
					}
				}
			});
		}
	},
});
