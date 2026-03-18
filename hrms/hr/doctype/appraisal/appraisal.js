// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

const GRADE_SCALE = [
	[91, "Outstanding"],
	[81, "Exceeds Expectations"],
	[71, "Meets Expectations"],
	[60, "Needs Improvement"],
	[0, "Unsatisfactory"],
];

function get_grade(score) {
	for (let [threshold, grade] of GRADE_SCALE) {
		if (score >= threshold) return grade;
	}
	return GRADE_SCALE[GRADE_SCALE.length - 1][1];
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
							[
								"section_a_pct",
								"section_b_pct",
								"section_c_pct",
								"scoring_method",
								"allow_over_achievement",
								"achievement_weight_pct",
								"manager_rating_weight_pct",
							],
							(r) => {
								frm.set_value("section_a_pct", flt(r.section_a_pct) || 70);
								frm.set_value("section_b_pct", flt(r.section_b_pct) || 20);
								frm.set_value("section_c_pct", flt(r.section_c_pct) || 10);
								frm.set_value(
									"scoring_method",
									r.scoring_method || "Manager Rating Only",
								);
								frm.set_value(
									"allow_over_achievement",
									cint(r.allow_over_achievement),
								);
								frm.set_value(
									"achievement_weight_pct",
									flt(r.achievement_weight_pct) || 50,
								);
								frm.set_value(
									"manager_rating_weight_pct",
									flt(r.manager_rating_weight_pct) || 50,
								);
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

	section_a_pct(frm) {
		frm.trigger("update_section_labels");
	},
	section_b_pct(frm) {
		frm.trigger("update_section_labels");
	},
	section_c_pct(frm) {
		frm.trigger("update_section_labels");
	},

	update_section_labels(frm) {
		let a = flt(frm.doc.section_a_pct) || 70;
		let b = flt(frm.doc.section_b_pct) || 20;
		let c = flt(frm.doc.section_c_pct) || 10;

		if (frm.fields_dict.section_break_kras) {
			frm.fields_dict.section_break_kras.df.label = `Section A: KRA/KPI (${a}%)`;
			frm.fields_dict.section_break_kras.refresh();
		}
		if (frm.fields_dict.section_b_heading) {
			frm.fields_dict.section_b_heading.df.label = `Section B: Functional Competency (${b}% Weight)`;
			frm.fields_dict.section_b_heading.refresh();
		}
		if (frm.fields_dict.section_c_heading) {
			frm.fields_dict.section_c_heading.df.label = `Section C: Extra Functions & Initiatives (${c}% Weight)`;
			frm.fields_dict.section_c_heading.refresh();
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
		let a_pct = flt(frm.doc.section_a_pct) || 70;
		let b_pct = flt(frm.doc.section_b_pct) || 20;
		let c_pct = flt(frm.doc.section_c_pct) || 10;
		const labels = [
			`Section A - KRA/KPI (${a_pct}%)`,
			`Section B - Competency (${b_pct}%)`,
			`Section C - Initiatives (${c_pct}%)`,
		];
		const maximum_scores = [a_pct, b_pct, c_pct];
		const scores = [
			flt(frm.doc.section_a_score) || 0,
			flt(frm.doc.section_b_score) || 0,
			flt(frm.doc.section_c_score) || 0,
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
				title: __("PMS Scores"),
				height: 250,
				type: "bar",
				barOptions: {
					spaceRatio: 0.7,
				},
				colors: ["blue", "green"],
			});
		}
	},

	calculate_section_a(frm) {
		let total = 0;
		(frm.doc.appraisal_kra || []).forEach((d) => {
			total += flt(d.weighted_score);
		});
		frm.set_value("section_a_score", flt(total, 2));
		frm.trigger("calculate_pms_total");
	},

	calculate_section_b(frm) {
		let total = 0;
		(frm.doc.functional_competencies || []).forEach((d) => {
			total += flt(d.score);
		});
		frm.set_value("section_b_score", flt(total, 2));
		frm.trigger("calculate_pms_total");
	},

	calculate_section_c(frm) {
		let total = 0;
		(frm.doc.extra_initiatives || []).forEach((d) => {
			total += flt(d.score);
		});
		frm.set_value("section_c_score", flt(total, 2));
		frm.trigger("calculate_pms_total");
	},

	calculate_pms_total(frm) {
		let total =
			flt(frm.doc.section_a_score) +
			flt(frm.doc.section_b_score) +
			flt(frm.doc.section_c_score);
		frm.set_value("pms_total_score", flt(total, 2));
		frm.set_value("overall_grade", get_grade(total));
	},
});

// Section A: Appraisal KRA child table handlers
frappe.ui.form.on("Appraisal KRA", {
	kpi(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.kpi) {
			frappe.db.get_value("KPI", row.kpi, ["title", "default_target", "unit_of_measure"], (r) => {
				if (r) {
					frappe.model.set_value(cdt, cdn, "kpi_description", r.title);
					if (flt(r.default_target)) {
						frappe.model.set_value(cdt, cdn, "target", r.default_target);
					}
					if (r.unit_of_measure) {
						frappe.model.set_value(cdt, cdn, "unit_of_measure", r.unit_of_measure);
					}
				}
			});
		}
	},
	manager_rating(frm, cdt, cdn) {
		calculate_kra_row(frm, cdt, cdn);
	},
	actual(frm, cdt, cdn) {
		calculate_kra_row(frm, cdt, cdn);
	},
	target(frm, cdt, cdn) {
		calculate_kra_row(frm, cdt, cdn);
	},
	per_weightage(frm, cdt, cdn) {
		calculate_kra_row(frm, cdt, cdn);
	},
	appraisal_kra_remove(frm) {
		frm.trigger("calculate_section_a");
	},
});

function calculate_kra_row(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	let scoring_method = frm.doc.scoring_method || "Manager Rating Only";
	let allow_over = cint(frm.doc.allow_over_achievement);

	let achievement = 0;
	if (flt(row.target)) {
		achievement = flt((flt(row.actual) / flt(row.target)) * 100, 2);
	}
	if (!allow_over) {
		achievement = Math.min(achievement, 100);
	}
	frappe.model.set_value(cdt, cdn, "achievement", achievement);

	// Rating field stores 0-1 (fraction), multiply by 5 to get 1-5 scale
	let rating_value = flt(row.manager_rating) * 5;
	let rating_score = flt((flt(row.per_weightage) * rating_value) / 5, 2);
	let achievement_score = flt((flt(row.per_weightage) * achievement) / 100, 2);

	let weighted_score;
	if (scoring_method === "Achievement Based") {
		weighted_score = achievement_score;
	} else if (scoring_method === "Blended") {
		let aw = flt(frm.doc.achievement_weight_pct || 50) / 100;
		let rw = flt(frm.doc.manager_rating_weight_pct || 50) / 100;
		weighted_score = flt(achievement_score * aw + rating_score * rw, 2);
	} else {
		weighted_score = rating_score;
	}
	frappe.model.set_value(cdt, cdn, "weighted_score", weighted_score);

	frm.trigger("calculate_section_a");
}

// Section B: Functional Competency child table handlers
frappe.ui.form.on("Appraisal Functional Competency", {
	manager_rating(frm, cdt, cdn) {
		calculate_competency_row(frm, cdt, cdn);
	},
	per_weightage(frm, cdt, cdn) {
		calculate_competency_row(frm, cdt, cdn);
	},
	functional_competencies_remove(frm) {
		frm.trigger("calculate_section_b");
	},
});

function calculate_competency_row(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);

	let rating_value = flt(row.manager_rating) * 5;
	let score = flt((flt(row.per_weightage) * rating_value) / 5, 2);
	frappe.model.set_value(cdt, cdn, "score", score);

	frm.trigger("calculate_section_b");
}

// Section C: Extra Initiative child table handlers
frappe.ui.form.on("Appraisal Extra Initiative", {
	manager_rating(frm, cdt, cdn) {
		calculate_initiative_row(frm, cdt, cdn);
	},
	per_weightage(frm, cdt, cdn) {
		calculate_initiative_row(frm, cdt, cdn);
	},
	extra_initiatives_remove(frm) {
		frm.trigger("calculate_section_c");
	},
});

function calculate_initiative_row(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);

	let rating_value = flt(row.manager_rating) * 5;
	let score = flt((flt(row.per_weightage) * rating_value) / 5, 2);
	frappe.model.set_value(cdt, cdn, "score", score);

	frm.trigger("calculate_section_c");
}
