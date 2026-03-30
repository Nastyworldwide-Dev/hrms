# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_link_to_form, now

from hrms.hr.doctype.appraisal_cycle.appraisal_cycle import (
	get_department_template,
	validate_active_appraisal_cycle,
)
from hrms.hr.utils import validate_active_employee
from hrms.mixins.appraisal import AppraisalMixin


# Lookup table: weighted average score range → conversion factor
# Used for both A1 (Output KPIs) and A2 (Competency)
SCORE_CONVERSION_TABLE = [
	(4.5, 0.80, "Exceptional"),
	(3.5, 0.75, "Strong"),
	(2.5, 0.71, "Meets Expectation"),
	(1.5, 0.60, "Needs Improvement"),
	(1.0, 0.50, "Unsatisfactory"),
]


def get_conversion_factor(weighted_avg):
	"""Convert a 1-5 weighted average score to a percentage factor using the lookup table"""
	weighted_avg = flt(weighted_avg, 2)
	for threshold, factor, _label in SCORE_CONVERSION_TABLE:
		if weighted_avg >= threshold:
			return factor
	return 0.50  # below 1.0 = Unsatisfactory


class Appraisal(Document, AppraisalMixin):
	def validate(self):
		self.set_a1_a2_weights()

		validate_active_employee(self.employee)
		validate_active_appraisal_cycle(self.appraisal_cycle)
		self.validate_duplicate()
		self.set_personal_particulars()
		self.validate_a1_a2_weights()

		# Weightage validation: A1 KRAs must sum to a1_weight_pct, A2 to a2_weight_pct
		a1_weight = cint(self.a1_weight_pct) or 70
		a2_weight = cint(self.a2_weight_pct) or 10
		self.validate_total_weightage("appraisal_kra", "KRAs (A1)", a1_weight)
		if self.functional_competencies:
			self.validate_total_weightage("functional_competencies", "Competencies (A2)", a2_weight)
		self.validate_total_weightage("self_ratings", "Self Ratings")

		# Calculate Section A using lookup table
		self.calculate_a1_score()
		self.calculate_a2_score()
		self.section_a_score = flt(flt(self.a1_score) + flt(self.a2_score), 2)
		self.calculate_pms_total()

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

	def set_a1_a2_weights(self):
		"""Populate A1/A2 weights from cycle on first save"""
		if not self.appraisal_cycle or not self.is_new():
			return

		cycle = frappe.get_cached_doc("Appraisal Cycle", self.appraisal_cycle)
		if not self.a1_weight_pct:
			self.a1_weight_pct = cint(cycle.a1_weight_pct) or 70
		self.a2_weight_pct = 80 - cint(self.a1_weight_pct)

	def validate_a1_a2_weights(self):
		a1 = cint(self.a1_weight_pct) or 70
		if a1 < 50 or a1 > 80:
			frappe.throw(
				_("A1 Weight must be between 50 and 80. Currently, it is {0}").format(a1),
				title=_("Invalid A1 Weight"),
			)
		self.a2_weight_pct = 80 - a1

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

	def calculate_a1_score(self):
		"""Calculate A1: Output KPI score using lookup table conversion.

		Each KRA row has a manager_rating (Frappe Rating: 0-1 fraction = 1-5 stars)
		and a per_weightage. We compute a weighted average score (1-5), then convert
		via the lookup table to get the A1 percentage.

		weighted_score per row = per_weightage × (rating × 5) / 5 (for display)
		"""
		a1_weight = cint(self.a1_weight_pct) or 70
		total_weightage = 0
		weighted_sum = 0

		for row in self.appraisal_kra:
			rating_value = flt(row.manager_rating) * 5  # 0-1 → 1-5
			row.weighted_score = flt(flt(row.per_weightage) * rating_value / 5, 2)
			weighted_sum += flt(row.per_weightage) * rating_value / 5
			total_weightage += flt(row.per_weightage)

		# Weighted average on 1-5 scale
		if total_weightage:
			weighted_avg = flt(weighted_sum / total_weightage * 5, 2)
		else:
			weighted_avg = 0

		conversion = get_conversion_factor(weighted_avg)
		self.a1_score = flt(conversion * a1_weight, 2)

	def calculate_a2_score(self):
		"""Calculate A2: Competency score using the same lookup table conversion."""
		a2_weight = cint(self.a2_weight_pct) or 10
		if not self.functional_competencies:
			self.a2_score = 0
			return

		total_weightage = 0
		weighted_sum = 0

		for row in self.functional_competencies:
			rating_value = flt(row.manager_rating) * 5
			row.score = flt(flt(row.per_weightage) * rating_value / 5, 2)
			weighted_sum += flt(row.per_weightage) * rating_value / 5
			total_weightage += flt(row.per_weightage)

		if total_weightage:
			weighted_avg = flt(weighted_sum / total_weightage * 5, 2)
		else:
			weighted_avg = 0

		conversion = get_conversion_factor(weighted_avg)
		self.a2_score = flt(conversion * a2_weight, 2)

	def calculate_pms_total(self):
		"""Calculate total PMS score and determine grade.
		Phase 1: Section A only. Phase 2 will add Section B and demerits.
		"""
		self.pms_total_score = flt(self.section_a_score, 2)
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

		template = frappe.get_doc("Appraisal Template", self.appraisal_template)

		# Template goals sum to 100%; scale to a1_weight_pct for A1 KPIs
		template_total = sum(flt(e.per_weightage) for e in template.goals) or 100
		a1_max = cint(self.a1_weight_pct) or 70
		scale = a1_max / template_total

		for entry in template.goals:
			self.append(
				"appraisal_kra",
				{
					"kra": entry.key_result_area,
					"per_weightage": flt(entry.per_weightage * scale, 2),
					"kra_category": entry.get("kra_category"),
					"kpi": entry.get("kpi"),
					"kpi_description": entry.get("kpi_description"),
				},
			)

		# Fix rounding so rows sum to exactly a1_max
		rows = self.get("appraisal_kra")
		if rows:
			rounded_total = sum(flt(r.per_weightage) for r in rows)
			diff = flt(a1_max - rounded_total, 2)
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
		"""Legacy method — kept for backward compatibility but no longer used in scoring."""
		pass

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
		"""Final score = PMS total (Phase 2 will add Section B and demerits)"""
		self.final_score = flt(self.pms_total_score, self.precision("final_score"))

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
		"""Legacy method — goal-based scoring no longer used. Kept for API compatibility."""
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
