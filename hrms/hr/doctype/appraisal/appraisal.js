// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Appraisal", {
	refresh(frm) {
		if (!frm.doc.__islocal) {
			frm.trigger("add_custom_buttons");
			frm.trigger("show_feedback_history");
			frm.trigger("setup_chart");
		}

		// don't allow removing image (fetched from employee)
		frm.sidebar.image_wrapper.find(".sidebar-image-actions").addClass("hide");
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
							"kra_evaluation_method",
							(r) => {
								if (r.kra_evaluation_method) {
									frm.set_value(
										"rate_goals_manually",
										cint(r.kra_evaluation_method === "Manual Rating"),
									);
								}
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
		const labels = ["Section A (KRA/KPI)", "Section B (Competency)", "Section C (Initiatives)"];
		const maximum_scores = [70, 20, 10];
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

	calculate_total(frm) {
		let total = 0;

		frm.doc.goals.forEach((d) => {
			total += flt(d.score_earned);
		});

		frm.set_value("total_score", total);
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
		frm.set_value("competency_score", flt(total, 2));
		frm.trigger("calculate_pms_total");
	},

	calculate_section_c(frm) {
		let total = 0;
		(frm.doc.extra_initiatives || []).forEach((d) => {
			total += flt(d.score);
		});
		frm.set_value("section_c_score", flt(total, 2));
		frm.set_value("initiatives_score", flt(total, 2));
		frm.trigger("calculate_pms_total");
	},

	calculate_pms_total(frm) {
		let total =
			flt(frm.doc.section_a_score) +
			flt(frm.doc.section_b_score) +
			flt(frm.doc.section_c_score);
		frm.set_value("pms_total_score", flt(total, 2));

		let grade = "";
		if (total >= 91) grade = "Outstanding";
		else if (total >= 81) grade = "Exceeds Expectations";
		else if (total >= 71) grade = "Meets Expectations";
		else if (total >= 60) grade = "Needs Improvement";
		else grade = "Unsatisfactory";

		frm.set_value("overall_grade", grade);
	},
});

frappe.ui.form.on("Appraisal Goal", {
	score(frm, cdt, cdn) {
		let d = frappe.get_doc(cdt, cdn);

		if (flt(d.score) > 5) {
			frappe.msgprint(__("Score must be less than or equal to 5"));
			d.score = 0;
			refresh_field("score", d.name, "goals");
		} else {
			frm.trigger("set_score_earned", cdt, cdn);
		}
	},

	per_weightage(frm, cdt, cdn) {
		frm.trigger("set_score_earned", cdt, cdn);
	},

	goals_remove(frm, cdt, cdn) {
		frm.trigger("set_score_earned", cdt, cdn);
	},

	set_score_earned(frm, cdt, cdn) {
		let d = frappe.get_doc(cdt, cdn);

		let score_earned = (flt(d.score) * flt(d.per_weightage)) / 100;
		frappe.model.set_value(cdt, cdn, "score_earned", score_earned);

		frm.trigger("calculate_total");
	},
});

// Section A: Appraisal KRA child table handlers
frappe.ui.form.on("Appraisal KRA", {
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

	let achievement = 0;
	if (flt(row.target)) {
		achievement = flt((flt(row.actual) / flt(row.target)) * 100, 2);
	}
	frappe.model.set_value(cdt, cdn, "achievement", achievement);

	// Rating field stores 0-1 (fraction), multiply by 5 to get 1-5 scale
	let rating_value = flt(row.manager_rating) * 5;
	let weighted_score = flt((flt(row.per_weightage) * rating_value) / 5, 2);
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
