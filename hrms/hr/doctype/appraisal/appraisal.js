// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

const GRADE_SCALE = [
	[91, "Outstanding"],
	[81, "Exceeds Expectations"],
	[71, "Meets Expectations"],
	[60, "Needs Improvement"],
	[0, "Unsatisfactory"],
];

// Lookup table: weighted average score → conversion factor
// Same table used for both A1 (Output KPIs) and A2 (Competency)
const SCORE_CONVERSION_TABLE = [
	[4.5, 0.80, "Exceptional"],
	[3.5, 0.75, "Strong"],
	[2.5, 0.71, "Meets Expectation"],
	[1.5, 0.60, "Needs Improvement"],
	[1.0, 0.50, "Unsatisfactory"],
];

function get_grade(score) {
	for (let [threshold, grade] of GRADE_SCALE) {
		if (score >= threshold) return grade;
	}
	return GRADE_SCALE[GRADE_SCALE.length - 1][1];
}

function get_conversion_factor(weighted_avg) {
	for (let [threshold, factor] of SCORE_CONVERSION_TABLE) {
		if (weighted_avg >= threshold) return factor;
	}
	return 0.5;
}

frappe.ui.form.on("Appraisal", {
	refresh(frm) {
		if (!frm.doc.__islocal) {
			frm.trigger("add_custom_buttons");
			frm.trigger("show_feedback_history");
			frm.trigger("setup_chart");
		}

		frm.trigger("update_section_labels");

		// Filter KPI by KRA in Appraisal KRA table
		frm.set_query("kpi", "appraisal_kra", (doc, cdt, cdn) => {
			let row = frappe.get_doc(cdt, cdn);
			return { filters: { kra: row.kra } };
		});

		// don't allow removing image (fetched from employee)
		frm.sidebar.image_wrapper.find(".sidebar-image-actions").addClass("hide");

		// Render grade scale from shared constant
		if (frm.fields_dict.grade_scale_html) {
			let parts = GRADE_SCALE.map(([threshold, grade], i) => {
				if (i < GRADE_SCALE.length - 1) {
					let upper = i > 0 ? GRADE_SCALE[i - 1][0] : 100;
					return `${threshold}\u2013${upper}: ${grade}`;
				}
				return `&lt;${GRADE_SCALE[i - 1][0]}: ${grade}`;
			});
			frm.fields_dict.grade_scale_html.$wrapper.html(
				`<div style="margin-top:10px; padding:10px; background:#f5f5f5; border-radius:4px; font-size:12px;"><strong>Grade Scale:</strong><br>${parts.join(" | ")}</div>`
			);
		}

		// Filter appraisal_template by employee's department tree (self + ancestors)
		if (frm.doc.department) {
			frappe.call({
				method: "hrms.hr.doctype.appraisal.appraisal.get_department_ancestors",
				args: { department: frm.doc.department },
				callback: (r) => {
					let departments = r.message || [];
					frm.set_query("appraisal_template", () => ({
						filters: {
							department: ["in", departments],
						},
					}));
				},
			});
		}
	},

	appraisal_template(frm) {
		if (frm.doc.appraisal_template) {
			frm.call("set_kras_and_rating_criteria", () => {
				frm.refresh_field("appraisal_kra");
				frm.refresh_field("functional_competencies");
				frm.refresh_field("feedback_ratings");
			});
		}
	},

	appraisal_cycle(frm) {
		if (frm.doc.appraisal_cycle) {
			frappe.run_serially([
				() => {
					if (frm.doc.__islocal && frm.doc.appraisal_cycle) {
						frappe.db.get_value(
							"Appraisal Cycle",
							frm.doc.appraisal_cycle,
							["a1_weight_pct", "a2_weight_pct"],
							(r) => {
								frm.set_value("a1_weight_pct", cint(r.a1_weight_pct) || 70);
								frm.set_value("a2_weight_pct", cint(r.a2_weight_pct) || 10);
								frm.trigger("update_section_labels");
							},
						);
					}
				},
				() => {
					frm.call({
						method: "set_appraisal_template",
						doc: frm.doc,
					});
				},
			]);
		}
	},

	a1_weight_pct(frm) {
		let a1 = cint(frm.doc.a1_weight_pct) || 70;
		frm.set_value("a2_weight_pct", 80 - a1);
		frm.trigger("update_section_labels");
		frm.trigger("calculate_a1");
		frm.trigger("calculate_a2");
	},

	update_section_labels(frm) {
		let a1 = cint(frm.doc.a1_weight_pct) || 70;
		let a2 = cint(frm.doc.a2_weight_pct) || 10;

		if (frm.fields_dict.section_break_kras) {
			frm.fields_dict.section_break_kras.df.label = `A1 \u2014 Output KPIs (${a1}%)`;
			frm.fields_dict.section_break_kras.refresh();
		}
		if (frm.fields_dict.section_a2_heading) {
			frm.fields_dict.section_a2_heading.df.label = `A2 \u2014 Competency (${a2}%)`;
			frm.fields_dict.section_a2_heading.refresh();
		}
	},

	add_custom_buttons(frm) {
		frm.add_custom_button(__("View Goals"), function () {
			frappe.route_options = {
				company: frm.doc.company,
				employee: frm.doc.employee,
				appraisal_cycle: frm.doc.appraisal_cycle,
			};
			frappe.set_route("Tree", "Goal");
		});
	},

	show_feedback_history(frm) {
		frappe.require("performance.bundle.js", () => {
			const feedback_history = new hrms.PerformanceFeedback({
				frm: frm,
				wrapper: $(frm.fields_dict.feedback_html.wrapper),
			});
			feedback_history.refresh();
		});
	},

	setup_chart(frm) {
		let a1 = cint(frm.doc.a1_weight_pct) || 70;
		let a2 = cint(frm.doc.a2_weight_pct) || 10;
		const labels = [
			`A1 \u2014 Output KPIs (${a1}%)`,
			`A2 \u2014 Competency (${a2}%)`,
		];
		const maximum_scores = [a1, a2];
		const scores = [
			flt(frm.doc.a1_score) || 0,
			flt(frm.doc.a2_score) || 0,
		];

		if (scores.some((s) => s > 0)) {
			frm.dashboard.render_graph({
				data: {
					labels: labels,
					datasets: [
						{
							name: "Maximum Score",
							chartType: "bar",
							values: maximum_scores,
						},
						{
							name: "Score Obtained",
							chartType: "bar",
							values: scores,
						},
					],
				},
				title: __("Section A \u2014 Core Performance (max 80%)"),
				height: 250,
				type: "bar",
				barOptions: {
					spaceRatio: 0.7,
				},
				colors: ["blue", "green"],
			});
		}
	},

	calculate_a1(frm) {
		let rows = frm.doc.appraisal_kra || [];
		let total_weightage = 0;
		let weighted_sum = 0;

		rows.forEach((d) => {
			let rating_value = flt(d.manager_rating) * 5;
			weighted_sum += (flt(d.per_weightage) * rating_value) / 5;
			total_weightage += flt(d.per_weightage);
		});

		let weighted_avg = total_weightage
			? flt((weighted_sum / total_weightage) * 5, 2)
			: 0;
		let conversion = get_conversion_factor(weighted_avg);
		let a1_weight = cint(frm.doc.a1_weight_pct) || 70;
		frm.set_value("a1_score", flt(conversion * a1_weight, 2));
		frm.trigger("calculate_pms_total");
	},

	calculate_a2(frm) {
		let rows = frm.doc.functional_competencies || [];
		if (!rows.length) {
			frm.set_value("a2_score", 0);
			frm.trigger("calculate_pms_total");
			return;
		}

		let total_weightage = 0;
		let weighted_sum = 0;

		rows.forEach((d) => {
			let rating_value = flt(d.manager_rating) * 5;
			weighted_sum += (flt(d.per_weightage) * rating_value) / 5;
			total_weightage += flt(d.per_weightage);
		});

		let weighted_avg = total_weightage
			? flt((weighted_sum / total_weightage) * 5, 2)
			: 0;
		let conversion = get_conversion_factor(weighted_avg);
		let a2_weight = cint(frm.doc.a2_weight_pct) || 10;
		frm.set_value("a2_score", flt(conversion * a2_weight, 2));
		frm.trigger("calculate_pms_total");
	},

	calculate_pms_total(frm) {
		let section_a = flt(frm.doc.a1_score) + flt(frm.doc.a2_score);
		frm.set_value("section_a_score", flt(section_a, 2));
		frm.set_value("pms_total_score", flt(section_a, 2));
		frm.set_value("overall_grade", get_grade(section_a));
	},
});

// A1: Appraisal KRA child table handlers
frappe.ui.form.on("Appraisal KRA", {
	kpi(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.kpi) {
			frappe.db.get_value("KPI", row.kpi, ["title"], (r) => {
				if (r) {
					frappe.model.set_value(cdt, cdn, "kpi_description", r.title);
				}
			});
		}
	},
	manager_rating(frm, cdt, cdn) {
		calculate_kra_row(frm, cdt, cdn);
	},
	per_weightage(frm, cdt, cdn) {
		calculate_kra_row(frm, cdt, cdn);
	},
	appraisal_kra_remove(frm) {
		frm.trigger("calculate_a1");
	},
});

function calculate_kra_row(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);

	// Rating field stores 0-1 (fraction), multiply by 5 to get 1-5 scale
	let rating_value = flt(row.manager_rating) * 5;
	let weighted_score = flt((flt(row.per_weightage) * rating_value) / 5, 2);
	frappe.model.set_value(cdt, cdn, "weighted_score", weighted_score);

	frm.trigger("calculate_a1");
}

// A2: Functional Competency child table handlers (repurposed for A2)
frappe.ui.form.on("Appraisal Functional Competency", {
	manager_rating(frm, cdt, cdn) {
		calculate_competency_row(frm, cdt, cdn);
	},
	per_weightage(frm, cdt, cdn) {
		calculate_competency_row(frm, cdt, cdn);
	},
	functional_competencies_remove(frm) {
		frm.trigger("calculate_a2");
	},
});

function calculate_competency_row(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);

	let rating_value = flt(row.manager_rating) * 5;
	let score = flt((flt(row.per_weightage) * rating_value) / 5, 2);
	frappe.model.set_value(cdt, cdn, "score", score);

	frm.trigger("calculate_a2");
}
