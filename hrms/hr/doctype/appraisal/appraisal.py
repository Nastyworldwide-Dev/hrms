# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Avg
from frappe.utils import flt, get_link_to_form, now

from hrms.hr.doctype.appraisal_cycle.appraisal_cycle import (
	get_department_template,
	validate_active_appraisal_cycle,
)
from hrms.hr.utils import validate_active_employee
from hrms.mixins.appraisal import AppraisalMixin
from hrms.payroll.utils import sanitize_expression


class Appraisal(Document, AppraisalMixin):
	def validate(self):
		self.set_kra_evaluation_method()

		validate_active_employee(self.employee)
		validate_active_appraisal_cycle(self.appraisal_cycle)
		self.validate_duplicate()
		self.set_personal_particulars()

		# New 70/20/10 weightage validation
		self.validate_total_weightage("appraisal_kra", "KRAs (Section A)", 70)
		self.validate_total_weightage("functional_competencies", "Functional Competencies (Section B)", 20)
		self.validate_total_weightage("extra_initiatives", "Extra Initiatives (Section C)", 10)
		self.validate_total_weightage("self_ratings", "Self Ratings")

		# Calculate all section scores
		self.calculate_section_a_score()
		self.calculate_section_b_score()
		self.calculate_section_c_score()
		self.calculate_pms_total()

		self.set_goal_score()
		self.calculate_self_appraisal_score()
		self.calculate_avg_feedback_score()
		self.calculate_final_score()

	def validate_duplicate(self):
		Appraisal = frappe.qb.DocType("Appraisal")
		duplicate = (
			frappe.qb.from_(Appraisal)
			.select(Appraisal.name)
			.where(
				(Appraisal.employee == self.employee)
				& (Appraisal.docstatus != 2)
				& (Appraisal.name != self.name)
				& (
					(Appraisal.appraisal_cycle == self.appraisal_cycle)
					| (
						(Appraisal.start_date.between(self.start_date, self.end_date))
						| (Appraisal.end_date.between(self.start_date, self.end_date))
						| (
							(self.start_date >= Appraisal.start_date)
							& (self.start_date <= Appraisal.end_date)
						)
						| ((self.end_date >= Appraisal.start_date) & (self.end_date <= Appraisal.end_date))
					)
				)
			)
		).run()
		duplicate = duplicate[0][0] if duplicate else 0

		if duplicate:
			frappe.throw(
				_(
					"Appraisal {0} already exists for Employee {1} for this Appraisal Cycle or overlapping period"
				).format(get_link_to_form("Appraisal", duplicate), frappe.bold(self.employee_name)),
				exc=frappe.DuplicateEntryError,
				title=_("Duplicate Entry"),
			)

	def set_kra_evaluation_method(self):
		if (
			self.is_new()
			and self.appraisal_cycle
			and (
				frappe.db.get_value("Appraisal Cycle", self.appraisal_cycle, "kra_evaluation_method")
				== "Manual Rating"
			)
		):
			self.rate_goals_manually = 1

	def set_personal_particulars(self):
		"""Fetch personal particulars from Employee record and appraisal cycle"""
		if not self.employee:
			return

		employee = frappe.get_cached_doc("Employee", self.employee)

		self.date_joined = employee.date_of_joining
		self.staff_no = employee.name
		self.unit = employee.branch
		self.job_grade = employee.grade

		# Set confirmation due from Employee
		self.confirmation_due = (
			employee.get("final_confirmation_date")
			or employee.get("scheduled_confirmation_date")
			or None
		)

		# Auto-fill performance period from cycle dates
		if self.appraisal_cycle and not self.performance_period:
			cycle = frappe.get_cached_doc("Appraisal Cycle", self.appraisal_cycle)
			if cycle.start_date and cycle.end_date:
				self.performance_period = f"{cycle.start_date} to {cycle.end_date}"

	def calculate_section_a_score(self):
		"""Calculate Section A: KRA/KPI score (max 70)

		Note: Frappe Rating field stores values as 0-1 fractions (0, 0.2, 0.4, 0.6, 0.8, 1.0)
		representing a 1-5 star scale. We multiply by 5 to get the 1-5 value.
		"""
		section_a = 0
		for row in self.appraisal_kra:
			if flt(row.target):
				row.achievement = flt(flt(row.actual) / flt(row.target) * 100, 2)
			else:
				row.achievement = 0

			# Rating field stores 0-1 (fraction), multiply by 5 to get 1-5 scale
			rating_value = flt(row.manager_rating) * 5
			row.weighted_score = flt(flt(row.per_weightage) * rating_value / 5, 2)
			section_a += flt(row.weighted_score)

		self.section_a_score = flt(section_a, 2)

	def calculate_section_b_score(self):
		"""Calculate Section B: Functional Competency score (max 20)"""
		section_b = 0
		for row in self.functional_competencies:
			rating_value = flt(row.manager_rating) * 5
			row.score = flt(flt(row.per_weightage) * rating_value / 5, 2)
			section_b += flt(row.score)

		self.section_b_score = flt(section_b, 2)

	def calculate_section_c_score(self):
		"""Calculate Section C: Extra Functions & Initiatives score (max 10)"""
		section_c = 0
		for row in self.extra_initiatives:
			rating_value = flt(row.manager_rating) * 5
			row.score = flt(flt(row.per_weightage) * rating_value / 5, 2)
			section_c += flt(row.score)

		self.section_c_score = flt(section_c, 2)

	def calculate_pms_total(self):
		"""Calculate total PMS score and determine grade"""
		self.pms_total_score = flt(
			flt(self.section_a_score) + flt(self.section_b_score) + flt(self.section_c_score), 2
		)
		self.overall_grade = get_grade(self.pms_total_score)

	@frappe.whitelist()
	def set_appraisal_template(self):
		"""Sets appraisal template from Appraisee table, then department tree, then designation"""
		if not self.employee:
			return

		appraisal_template = None

		# 1. Check Appraisee table in Cycle
		if self.appraisal_cycle:
			appraisal_template = frappe.db.get_value(
				"Appraisee",
				{
					"employee": self.employee,
					"parent": self.appraisal_cycle,
				},
				"appraisal_template",
			)

		# 2. Fall back to department tree
		if not appraisal_template and self.department:
			appraisal_template = get_department_template(self.department)

		# 3. Fall back to designation
		if not appraisal_template and self.designation:
			appraisal_template = frappe.db.get_value(
				"Designation", self.designation, "appraisal_template"
			)

		if appraisal_template:
			self.appraisal_template = appraisal_template
			self.set_kras_and_rating_criteria()

	@frappe.whitelist()
	def set_kras_and_rating_criteria(self):
		if not self.appraisal_template:
			return

		self.set("appraisal_kra", [])
		self.set("self_ratings", [])
		self.set("goals", [])

		template = frappe.get_doc("Appraisal Template", self.appraisal_template)

		# Template goals sum to 100%; scale to 70% for Section A
		template_total = sum(flt(e.per_weightage) for e in template.goals) or 100
		section_a_max = 70
		scale = section_a_max / template_total

		table_name = "goals" if self.rate_goals_manually else "appraisal_kra"

		for entry in template.goals:
			self.append(
				table_name,
				{
					"kra": entry.key_result_area,
					"per_weightage": flt(entry.per_weightage * scale, 2),
					"kra_category": entry.get("kra_category"),
					"kpi_description": entry.get("kpi_description"),
				},
			)

		# Fix rounding so rows sum to exactly section_a_max
		rows = self.get(table_name)
		if rows:
			rounded_total = sum(flt(r.per_weightage) for r in rows)
			diff = flt(section_a_max - rounded_total, 2)
			if diff:
				rows[-1].per_weightage = flt(rows[-1].per_weightage + diff, 2)

		for entry in template.rating_criteria:
			self.append(
				"self_ratings",
				{
					"criteria": entry.criteria,
					"per_weightage": entry.per_weightage,
				},
			)

		return self

	def calculate_total_score(self):
		total_weightage, total, goal_score_percentage = 0, 0, 0
		meta = frappe.get_meta("Appraisal Goal")
		number_of_stars = meta.get_options("score") or 5
		if self.rate_goals_manually:
			table = _("Goals")
			expected_total = 70.0
			for entry in self.goals:
				if flt(entry.score) > flt(number_of_stars):
					frappe.throw(
						_("Row {0}: Goal Score cannot be greater than {1}").format(entry.idx, number_of_stars)
					)

				entry.score_earned = flt(entry.score) * flt(entry.per_weightage) / 100
				total += flt(entry.score_earned)
				total_weightage += flt(entry.per_weightage)

		else:
			table = _("KRAs")
			expected_total = 70.0
			for entry in self.appraisal_kra:
				goal_score_percentage += flt(entry.goal_score)
				total_weightage += flt(entry.per_weightage)

			self.goal_score_percentage = flt(goal_score_percentage, self.precision("goal_score_percentage"))
			# convert goal score percentage to total score out of 5
			total = flt(goal_score_percentage) / 20

		if total_weightage and flt(total_weightage, 2) != flt(expected_total, 2):
			frappe.throw(
				_("Total weightage for all {0} must add up to {1}. Currently, it is {2}%").format(
					table, expected_total, total_weightage
				),
				title=_("Incorrect Weightage Allocation"),
			)

		self.total_score = flt(total, self.precision("total_score"))

	def calculate_self_appraisal_score(self):
		total = 0
		meta = frappe.get_meta("Employee Feedback Rating")
		number_of_stars = meta.get_options("rating") or 5
		for entry in self.self_ratings:
			score = flt(entry.rating) * flt(number_of_stars) * flt(entry.per_weightage / 100)
			total += flt(score)

		self.self_score = flt(total, self.precision("self_score"))

	def calculate_avg_feedback_score(self, update=False):
		avg_feedback_score = frappe.qb.avg(
			"Employee Performance Feedback",
			"total_score",
			{"employee": self.employee, "appraisal": self.name, "docstatus": 1},
		)

		self.avg_feedback_score = flt(avg_feedback_score, self.precision("avg_feedback_score"))

		if update:
			self.calculate_final_score()
			self.db_update()

	def calculate_final_score(self):
		# Use PMS total score as the final score
		if flt(self.pms_total_score):
			self.final_score = flt(self.pms_total_score, self.precision("final_score"))
			return

		# Fallback to legacy formula-based calculation
		final_score = 0
		appraisal_cycle_doc = frappe.get_cached_doc("Appraisal Cycle", self.appraisal_cycle)

		formula = appraisal_cycle_doc.final_score_formula
		based_on_formula = appraisal_cycle_doc.calculate_final_score_based_on_formula

		if based_on_formula:
			data = {
				"goal_score": flt(self.total_score),
				"average_feedback_score": flt(self.avg_feedback_score),
				"self_appraisal_score": flt(self.self_score),
				"section_a_score": flt(self.section_a_score),
				"section_b_score": flt(self.section_b_score),
				"section_c_score": flt(self.section_c_score),
				"pms_total_score": flt(self.pms_total_score),
				"total_score": flt(self.total_score),
				"self_score": flt(self.self_score),
				"avg_feedback_score": flt(self.avg_feedback_score),
			}

			sanitized_formula = sanitize_expression(formula)
			final_score = frappe.safe_eval(sanitized_formula, data)
		else:
			final_score = (flt(self.total_score) + flt(self.avg_feedback_score) + flt(self.self_score)) / 3

		self.final_score = flt(final_score, self.precision("final_score"))

	@frappe.whitelist()
	def add_feedback(self, feedback, feedback_ratings):
		feedback = frappe.get_doc(
			{
				"doctype": "Employee Performance Feedback",
				"appraisal": self.name,
				"employee": self.employee,
				"added_on": now(),
				"feedback": feedback,
				"reviewer": frappe.db.get_value("Employee", {"user_id": frappe.session.user}),
			}
		)

		for entry in feedback_ratings:
			feedback.append(
				"feedback_ratings",
				{
					"criteria": entry.get("criteria"),
					"rating": entry.get("rating"),
					"per_weightage": entry.get("per_weightage"),
				},
			)

		feedback.submit()

		return feedback

	def set_goal_score(self, update=False):
		# Single grouped query instead of N+1 per KRA
		Goal = frappe.qb.DocType("Goal")
		avg_by_kra = {
			row.kra: flt(row.avg_progress)
			for row in (
				frappe.qb.from_(Goal)
				.select(Goal.kra, Avg(Goal.progress).as_("avg_progress"))
				.where(
					(Goal.employee == self.employee)
					& (Goal.appraisal_cycle == self.appraisal_cycle)
					& (Goal.status != "Archived")
					& ((Goal.parent_goal == "") | (Goal.parent_goal.isnull()))
				)
				.groupby(Goal.kra)
			).run(as_dict=True)
		}

		for kra in self.appraisal_kra:
			avg_goal_completion = avg_by_kra.get(kra.kra, 0)
			kra.goal_completion = flt(avg_goal_completion, kra.precision("goal_completion"))
			kra.goal_score = flt(kra.goal_completion * kra.per_weightage / 100, kra.precision("goal_score"))

			if update:
				kra.db_update()

		self.calculate_total_score()

		if update:
			self.calculate_final_score()
			self.db_update()

		return self


GRADE_SCALE = [
	(91, "Outstanding"),
	(81, "Exceeds Expectations"),
	(71, "Meets Expectations"),
	(60, "Needs Improvement"),
	(0, "Unsatisfactory"),
]


def get_grade(score):
	"""Map PMS total score to grade using GRADE_SCALE thresholds"""
	score = flt(score)
	for threshold, grade in GRADE_SCALE:
		if score >= threshold:
			return grade
	return GRADE_SCALE[-1][1]


def get_grade_scale_html():
	"""Generate grade scale HTML from GRADE_SCALE for display on form"""
	parts = []
	for i, (threshold, grade) in enumerate(GRADE_SCALE):
		if i < len(GRADE_SCALE) - 1:
			next_threshold = GRADE_SCALE[i - 1][0] if i > 0 else 100
			parts.append(f"{threshold}\u2013{next_threshold}: {grade}")
		else:
			prev_threshold = GRADE_SCALE[i - 1][0]
			parts.append(f"&lt;{prev_threshold}: {grade}")
	return (
		"<div style='margin-top:10px; padding:10px; background:#f5f5f5; "
		"border-radius:4px; font-size:12px;'><strong>Grade Scale:</strong><br>"
		+ " | ".join(parts)
		+ "</div>"
	)


@frappe.whitelist()
def get_feedback_history(employee, appraisal):
	data = frappe._dict()
	data.feedback_history = frappe.get_list(
		"Employee Performance Feedback",
		filters={"employee": employee, "appraisal": appraisal, "docstatus": 1},
		fields=[
			"feedback",
			"reviewer",
			"user",
			"owner",
			"reviewer_name",
			"reviewer_designation",
			"added_on",
			"employee",
			"total_score",
			"name",
		],
		order_by="added_on desc",
	)

	# get percentage of reviews per rating
	reviews_per_rating = []

	feedback_count = frappe.db.count(
		"Employee Performance Feedback",
		filters={
			"appraisal": appraisal,
			"employee": employee,
			"docstatus": 1,
		},
	)

	for i in range(1, 6):
		count = frappe.db.count(
			"Employee Performance Feedback",
			filters={
				"appraisal": appraisal,
				"employee": employee,
				"total_score": ("between", [i, i + 0.99]),
				"docstatus": 1,
			},
		)

		percent = flt((count / feedback_count) * 100, 0) if feedback_count else 0
		reviews_per_rating.append(percent)

	data.reviews_per_rating = reviews_per_rating
	data.avg_feedback_score = frappe.db.get_value("Appraisal", appraisal, "avg_feedback_score")

	return data


@frappe.whitelist()
def get_department_ancestors(department):
	"""Return list of department and its ancestors (for template filtering)"""
	if not department:
		return []

	dept = frappe.db.get_value("Department", department, ["lft", "rgt"], as_dict=True)
	if not dept:
		return []

	return frappe.get_all(
		"Department",
		filters={
			"lft": ("<=", dept.lft),
			"rgt": (">=", dept.rgt),
			"disabled": 0,
		},
		order_by="lft desc",
		pluck="name",
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_kras_for_employee(doctype, txt, searchfield, start, page_len, filters):
	appraisal = frappe.db.get_value(
		"Appraisal",
		{
			"appraisal_cycle": filters.get("appraisal_cycle"),
			"employee": filters.get("employee"),
		},
		"name",
	)

	return frappe.get_all(
		"Appraisal KRA",
		filters={"parent": appraisal, "kra": ("like", f"{txt}%")},
		fields=["kra"],
		as_list=1,
	)
