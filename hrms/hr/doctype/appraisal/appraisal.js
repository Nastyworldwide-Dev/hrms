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

		// Filter KRA by employee's department
		frm.set_query("kra", "appraisal_kra", () => {
			return {
				filters: { department: ["in", [frm.doc.department, ""]] },
			};
		});

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

	auto_recalc_weightage(frm) {
		if (cint(frm.doc.auto_recalc_weightage)) {
			if ((frm.doc.appraisal_kra || []).length) {
				normalize_weightage(frm, "appraisal_kra");
				frm.trigger("calculate_a1");
			}
			if ((frm.doc.functional_competencies || []).length) {
				normalize_weightage(frm, "functional_competencies");
				frm.trigger("calculate_a2");
			}
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
			`A1 \u2014 KPIs (${a1}%)`,
			`A2 \u2014 Competency (${a2}%)`,
			"B \u2014 Differentiator",
			"Demerits",
		];
		const maximum_scores = [a1, a2, 20, 0];
		const scores = [
			flt(frm.doc.a1_score) || 0,
			flt(frm.doc.a2_score) || 0,
			flt(frm.doc.section_b_score) || 0,
			-(flt(frm.doc.total_demerit_pct) || 0),
		];

		if (scores.some((s) => s !== 0)) {
			frm.dashboard.render_graph({
				data: {
					labels: labels,
					datasets: [
						{
							name: "Maximum",
							chartType: "bar",
							values: maximum_scores,
						},
						{
							name: "Actual",
							chartType: "bar",
							values: scores,
						},
					],
				},
				title: __("PMS Score Breakdown"),
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

		let section_b = flt(frm.doc.section_b_score);
		let demerits = flt(frm.doc.total_demerit_pct);
		let raw = Math.max(0, Math.min(100, section_a + section_b - demerits));

		// Hard cap: serious misconduct
		if (cint(frm.doc.has_serious_misconduct)) {
			raw = Math.min(raw, 59);
		}

		// Hard cap: leadership gate failed
		if (cint(frm.doc.is_leader) && !cint(frm.doc.leadership_gate_passed)) {
			raw = Math.min(raw, 80);
		}

		frm.set_value("pms_total_score", flt(raw, 2));
		frm.set_value("overall_grade", get_grade(raw));

		// Second validator flag
		frm.set_value("requires_second_validator", raw > 90 ? 1 : 0);
	},

	calculate_leadership_gate(frm) {
		if (!cint(frm.doc.is_leader)) {
			frm.set_value("leadership_score_pct", 0);
			frm.set_value("leadership_gate_passed", 0);
			return;
		}

		let rows = frm.doc.leadership_scorecard || [];
		if (!rows.length) {
			frm.set_value("leadership_score_pct", 0);
			frm.set_value("leadership_gate_passed", 0);
			frm.trigger("calculate_pms_total");
			return;
		}

		let total = 0;
		rows.forEach((d) => {
			total += flt(d.score_pct);
		});
		let avg = flt(total / rows.length, 2);

		frm.set_value("leadership_score_pct", avg);
		frm.set_value("leadership_gate_passed", avg >= 60 ? 1 : 0);
		frm.trigger("calculate_pms_total");
	},

	calculate_section_b(frm) {
		// New joiner gate
		if (cint(frm.doc.is_new_joiner)) {
			frm.set_value("section_b_score", 0);
			frm.set_value("section_b_gate_status",
				"New Joiner Rule: Section B not assessed this cycle.");
			frm.trigger("calculate_pms_total");
			return;
		}

		// False evidence gate
		let has_false = (frm.doc.demerits || []).some(
			(d) => d.demerit_type === "False Evidence"
		);
		if (has_false) {
			frm.set_value("section_b_score", 0);
			frm.set_value("section_b_gate_status",
				"False Evidence: Section B disqualified for this cycle.");
			frm.trigger("calculate_pms_total");
			return;
		}

		// Section A gate
		let section_a = flt(frm.doc.a1_score) + flt(frm.doc.a2_score);
		if (section_a < 71) {
			frm.set_value("section_b_score", 0);
			frm.set_value("section_b_gate_status",
				"Section B locked: Section A must reach \u2265 71% first.");
			frm.trigger("calculate_pms_total");
			return;
		}

		// B4 points
		let b4_pts = 0;
		(frm.doc.b4_evidence || []).forEach((d) => {
			b4_pts += cint(d.points);
		});
		frm.set_value("b4_total_points", b4_pts);

		let b4_score = 0;
		if (b4_pts >= 15) b4_score = 10;
		else if (b4_pts >= 8) b4_score = 5;

		// B5 points (requires full B4 15+, no written warning, no serious misconduct)
		let b5_score = 0;
		let b5_pts = 0;
		if (
			b4_pts >= 15 &&
			!cint(frm.doc.has_written_warning) &&
			!cint(frm.doc.has_serious_misconduct)
		) {
			(frm.doc.b5_evidence || []).forEach((d) => {
				b5_pts += cint(d.points);
			});
			if (b5_pts >= 14) b5_score = 20;
			else if (b5_pts >= 8) b5_score = 15;
		}
		frm.set_value("b5_total_points", b5_pts);

		// B5 replaces B4
		frm.set_value("section_b_score", b5_score > 0 ? b5_score : b4_score);
		frm.set_value("section_b_gate_status", "");
		frm.trigger("calculate_pms_total");
	},

	calculate_demerits(frm) {
		let total = 0;
		let has_written = 0;
		let has_serious = 0;

		(frm.doc.demerits || []).forEach((d) => {
			if (cint(d.active)) {
				total += flt(d.penalty_pct);
			}
			if (d.demerit_type === "Written Warning") has_written = 1;
			if (d.demerit_type === "Serious Misconduct") has_serious = 1;
		});

		frm.set_value("total_demerit_pct", flt(total, 2));
		frm.set_value("has_written_warning", has_written);
		frm.set_value("has_serious_misconduct", has_serious);
		frm.trigger("calculate_section_b");
	},
});

// A1: Appraisal KRA child table handlers
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
	target(frm, cdt, cdn) {
		calculate_achievement(cdt, cdn);
	},
	actual(frm, cdt, cdn) {
		calculate_achievement(cdt, cdn);
	},
	manager_rating(frm, cdt, cdn) {
		calculate_kra_row(frm, cdt, cdn);
	},
	per_weightage(frm, cdt, cdn) {
		if (cint(frm.doc.auto_recalc_weightage)) {
			adjust_other_rows(frm, "appraisal_kra", cdn);
		}
		calculate_kra_row(frm, cdt, cdn);
	},
	appraisal_kra_add(frm) {
		if (cint(frm.doc.auto_recalc_weightage)) {
			setTimeout(() => {
				add_row_weightage(frm, "appraisal_kra");
				frm.trigger("calculate_a1");
			}, 200);
		}
	},
	appraisal_kra_remove(frm) {
		if (cint(frm.doc.auto_recalc_weightage)) {
			normalize_weightage(frm, "appraisal_kra");
		}
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

function calculate_achievement(cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	let achievement = 0;
	if (flt(row.target)) {
		achievement = flt((flt(row.actual) / flt(row.target)) * 100, 2);
	}
	frappe.model.set_value(cdt, cdn, "achievement", achievement);
}

// A2: Functional Competency child table handlers (repurposed for A2)
frappe.ui.form.on("Appraisal Functional Competency", {
	manager_rating(frm, cdt, cdn) {
		calculate_competency_row(frm, cdt, cdn);
	},
	per_weightage(frm, cdt, cdn) {
		if (cint(frm.doc.auto_recalc_weightage)) {
			adjust_other_rows(frm, "functional_competencies", cdn);
		}
		calculate_competency_row(frm, cdt, cdn);
	},
	functional_competencies_add(frm) {
		if (cint(frm.doc.auto_recalc_weightage)) {
			setTimeout(() => {
				add_row_weightage(frm, "functional_competencies");
				frm.trigger("calculate_a2");
			}, 200);
		}
	},
	functional_competencies_remove(frm) {
		if (cint(frm.doc.auto_recalc_weightage)) {
			normalize_weightage(frm, "functional_competencies");
		}
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

/**
 * Called when a NEW row is added.
 * Reduces each existing row proportionally to carve out space for the new row.
 * Example: 3 rows at 40/35/25, add 4th → new row gets ~25%, existing scale down.
 */
function add_row_weightage(frm, table_name) {
	let rows = frm.doc[table_name] || [];
	if (rows.length <= 1) {
		// First row — just set to 100
		if (rows.length === 1) {
			frappe.model.set_value(rows[0].doctype, rows[0].name, "per_weightage", 100);
		}
		frm.refresh_field(table_name);
		return;
	}

	// The new row is the last one (just added), with per_weightage = 0
	let new_row = rows[rows.length - 1];
	let others = rows.slice(0, -1);
	let others_total = others.reduce((sum, r) => sum + flt(r.per_weightage), 0);

	// New row gets equal share: 100 / total_rows
	let new_share = flt(100 / rows.length, 2);

	if (others_total > 0) {
		// Scale existing rows down proportionally
		let scale = (100 - new_share) / others_total;
		let running = 0;

		others.forEach((row, i) => {
			let value;
			if (i < others.length - 1) {
				value = flt(flt(row.per_weightage) * scale, 2);
			} else {
				value = flt(100 - new_share - running, 2);
			}
			running += value;
			frappe.model.set_value(row.doctype, row.name, "per_weightage", value);
		});
	}

	frappe.model.set_value(new_row.doctype, new_row.name, "per_weightage", new_share);
	frm.refresh_field(table_name);
}

/**
 * Called when a row is REMOVED or checkbox toggled on.
 * Scales all remaining rows proportionally so they sum to exactly 100%.
 */
function normalize_weightage(frm, table_name) {
	let rows = frm.doc[table_name] || [];
	if (!rows.length) return;

	let total = rows.reduce((sum, r) => sum + flt(r.per_weightage), 0);

	if (total === 0) {
		// All zero — equal split
		let each = flt(100 / rows.length, 2);
		let running = 0;
		rows.forEach((row, i) => {
			let value = i < rows.length - 1 ? each : flt(100 - running, 2);
			running += each;
			frappe.model.set_value(row.doctype, row.name, "per_weightage", value);
		});
	} else if (flt(total, 2) !== 100) {
		// Scale proportionally to 100
		let scale = 100 / total;
		let running = 0;
		rows.forEach((row, i) => {
			let value;
			if (i < rows.length - 1) {
				value = flt(flt(row.per_weightage) * scale, 2);
				running += value;
			} else {
				value = flt(100 - running, 2);
			}
			frappe.model.set_value(row.doctype, row.name, "per_weightage", value);
		});
	}

	frm.refresh_field(table_name);
}

/**
 * Called when user manually CHANGES a row's weightage.
 * Adjusts all OTHER rows proportionally so total stays at 100%.
 * The changed row keeps its new value; others scale to fill the remainder.
 */
function adjust_other_rows(frm, table_name, changed_cdn) {
	let rows = frm.doc[table_name] || [];
	if (rows.length <= 1) return;

	let changed_row = rows.find((r) => r.name === changed_cdn);
	if (!changed_row) return;

	let changed_value = flt(changed_row.per_weightage);
	let remainder = flt(100 - changed_value, 2);
	if (remainder < 0) remainder = 0;

	let others = rows.filter((r) => r.name !== changed_cdn);
	let others_total = others.reduce((sum, r) => sum + flt(r.per_weightage), 0);

	if (others_total > 0) {
		let scale = remainder / others_total;
		let running = 0;
		others.forEach((row, i) => {
			let value;
			if (i < others.length - 1) {
				value = flt(flt(row.per_weightage) * scale, 2);
				running += value;
			} else {
				value = flt(remainder - running, 2);
			}
			frappe.model.set_value(row.doctype, row.name, "per_weightage", value);
		});
	} else {
		// Others are all zero — split remainder equally
		let each = flt(remainder / others.length, 2);
		let running = 0;
		others.forEach((row, i) => {
			let value = i < others.length - 1 ? each : flt(remainder - running, 2);
			running += each;
			frappe.model.set_value(row.doctype, row.name, "per_weightage", value);
		});
	}

	frm.refresh_field(table_name);
}

// B4 Evidence child table handlers
frappe.ui.form.on("Appraisal B4 Evidence", {
	evidence_quality(frm, cdt, cdn) {
		set_evidence_points(cdt, cdn);
		frm.trigger("calculate_section_b");
	},
	b4_evidence_remove(frm) {
		frm.trigger("calculate_section_b");
	},
});

// B5 Evidence child table handlers
frappe.ui.form.on("Appraisal B5 Evidence", {
	evidence_quality(frm, cdt, cdn) {
		set_evidence_points(cdt, cdn);
		frm.trigger("calculate_section_b");
	},
	b5_evidence_remove(frm) {
		frm.trigger("calculate_section_b");
	},
});

function set_evidence_points(cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	let points = 0;
	if (row.evidence_quality === "Strong") points = 3;
	else if (row.evidence_quality === "Partial") points = 2;
	frappe.model.set_value(cdt, cdn, "points", points);
}

// Demerit child table handlers
frappe.ui.form.on("Appraisal Demerit", {
	demerit_type(frm, cdt, cdn) {
		set_demerit_penalty(cdt, cdn);
		frm.trigger("calculate_demerits");
	},
	date_issued(frm, cdt, cdn) {
		set_demerit_expiry(cdt, cdn);
		frm.trigger("calculate_demerits");
	},
	demerits_remove(frm) {
		frm.trigger("calculate_demerits");
	},
});

function set_demerit_penalty(cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	let penalty = 0;
	if (row.demerit_type === "Verbal Warning") penalty = 5;
	else if (row.demerit_type === "Written Warning") penalty = 10;
	else if (row.demerit_type === "Repeated Tardiness") penalty = 3;
	else if (row.demerit_type === "Serious Misconduct") penalty = 20;
	frappe.model.set_value(cdt, cdn, "penalty_pct", penalty);
	frappe.model.set_value(cdt, cdn, "active", 1);
	set_demerit_expiry(cdt, cdn);
}

function set_demerit_expiry(cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	if (!row.date_issued || !row.demerit_type) return;

	let expiry = null;
	if (row.demerit_type === "Verbal Warning" || row.demerit_type === "Repeated Tardiness") {
		expiry = frappe.datetime.add_months(row.date_issued, 12);
	} else if (row.demerit_type === "Written Warning") {
		expiry = frappe.datetime.add_months(row.date_issued, 24);
	}
	// Serious Misconduct and False Evidence: no expiry
	frappe.model.set_value(cdt, cdn, "expiry_date", expiry);
}

// Leadership Scorecard child table handlers
frappe.ui.form.on("Leadership Scorecard", {
	score_pct(frm) {
		frm.trigger("calculate_leadership_gate");
	},
	leadership_scorecard_remove(frm) {
		frm.trigger("calculate_leadership_gate");
	},
});
