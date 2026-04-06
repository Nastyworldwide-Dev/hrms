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


# Default lookup table — used as fallback when cycle has no conversion table
DEFAULT_SCORE_CONVERSION = [
	(4.5, 0.80, "Exceptional"),
	(3.5, 0.75, "Strong"),
	(2.5, 0.71, "Meets Expectation"),
	(1.5, 0.60, "Needs Improvement"),
	(1.0, 0.50, "Unsatisfactory"),
]


def get_conversion_factor(weighted_avg, conversion_table=None):
	"""Convert a 1-5 weighted average score to a percentage factor.

	Args:
		weighted_avg: The weighted average score on a 1-5 scale
		conversion_table: Optional list of Score Conversion Row docs from Appraisal Cycle.
			Falls back to DEFAULT_SCORE_CONVERSION if not provided.
	"""
	weighted_avg = flt(weighted_avg, 2)

	if conversion_table:
		for row in conversion_table:
			if weighted_avg >= flt(row.min_score):
				return flt(row.conversion_pct)
		# Below lowest threshold
		return flt(conversion_table[-1].conversion_pct) if conversion_table else 0.50

	for threshold, factor, _label in DEFAULT_SCORE_CONVERSION:
		if weighted_avg >= threshold:
			return factor
	return 0.50


class Appraisal(Document, AppraisalMixin):
	def validate(self):
		self.set_a1_a2_weights()

		validate_active_employee(self.employee)
		validate_active_appraisal_cycle(self.appraisal_cycle)
		self.validate_duplicate()
		self.set_personal_particulars()
		self.validate_a1_a2_weights()
		self.detect_new_joiner()
		self.set_leadership_gate_applicability()

		# Weightage validation: all tables always sum to 100%
		self.validate_total_weightage("appraisal_kra", "KRAs (A1)", 100)
		if self.functional_competencies:
			self.validate_total_weightage("functional_competencies", "Competencies (A2)", 100)
		self.validate_total_weightage("self_ratings", "Self Ratings")

		# Calculate Section A using lookup table
		self.calculate_a1_score()
		self.calculate_a2_score()
		self.section_a_score = flt(flt(self.a1_score) + flt(self.a2_score), 2)

		# Calculate Section B (evidence-based), demerits, and leadership gate
		self.calculate_demerits()
		self.calculate_section_b_score()
		self.calculate_leadership_gate()
		self.calculate_pms_total()
		self.set_second_validator_flag()

		self.calculate_self_appraisal_score()
		self.calculate_avg_feedback_score()
		self.calculate_final_score()

	def before_submit(self):
		if cint(self.requires_second_validator) and not cint(self.second_validator_approved):
			frappe.throw(
				_("Score is above 90%. Second validator approval is required before submission."),
				title=_("Second Validator Required"),
			)

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

	def _get_conversion_table(self):
		"""Get score conversion table from the linked Appraisal Cycle, or None for default."""
		if not self.appraisal_cycle:
			return None
		cycle = frappe.get_cached_doc("Appraisal Cycle", self.appraisal_cycle)
		return cycle.score_conversion_table or None

	def calculate_a1_score(self):
		"""Calculate A1: Output KPI score using lookup table.

		The conversion factor represents the absolute Section A score out of 80%.
		Per sub-section: score = (factor / 0.80) × sub_weight.
		Example: factor 0.80 (Exceptional), A1=70% → (0.80/0.80) × 70 = 70 (full marks).
		"""
		a1_weight = cint(self.a1_weight_pct) or 70
		total_weightage = 0
		weighted_sum = 0

		for row in self.appraisal_kra:
			# Calculate achievement (informational — supports the rating)
			if flt(row.target):
				row.achievement = flt(flt(row.actual) / flt(row.target) * 100, 2)
			else:
				row.achievement = 0

			rating_value = flt(row.manager_rating) * 5  # 0-1 → 1-5
			row.weighted_score = flt(flt(row.per_weightage) * rating_value / 5, 2)
			weighted_sum += flt(row.per_weightage) * rating_value / 5
			total_weightage += flt(row.per_weightage)

		# Weighted average on 1-5 scale
		if total_weightage:
			weighted_avg = flt(weighted_sum / total_weightage * 5, 2)
		else:
			weighted_avg = 0

		conversion = get_conversion_factor(weighted_avg, self._get_conversion_table())
		# Factor is out of 0.80 (Section A max). Scale to sub-section weight.
		self.a1_score = flt(conversion / 0.80 * a1_weight, 2)

	def calculate_a2_score(self):
		"""Calculate A2: Competency score. Same lookup table logic as A1."""
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

		conversion = get_conversion_factor(weighted_avg, self._get_conversion_table())
		self.a2_score = flt(conversion / 0.80 * a2_weight, 2)

	def detect_new_joiner(self):
		"""Auto-set is_new_joiner if employee joined after month 6 of the cycle"""
		if not self.appraisal_cycle or not self.employee:
			return

		cycle = frappe.get_cached_doc("Appraisal Cycle", self.appraisal_cycle)
		if not cycle.start_date or not cycle.end_date:
			return

		from frappe.utils import add_months, getdate

		midpoint = add_months(cycle.start_date, 6)
		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

		if date_of_joining and getdate(date_of_joining) > getdate(midpoint):
			self.is_new_joiner = 1
		else:
			self.is_new_joiner = 0

	def calculate_demerits(self):
		"""Calculate demerit penalties with rolling expiry and set flags"""
		from frappe.utils import add_months, getdate

		total_penalty = 0
		has_written = 0
		has_serious = 0
		has_false_evidence = 0

		# Get cycle end date for active check
		cycle_end = None
		if self.appraisal_cycle:
			cycle_end = frappe.db.get_value("Appraisal Cycle", self.appraisal_cycle, "end_date")

		for row in self.demerits:
			# Calculate expiry date based on type
			if row.demerit_type == "Verbal Warning":
				row.expiry_date = add_months(row.date_issued, 12) if row.date_issued else None
				row.penalty_pct = 5
			elif row.demerit_type == "Written Warning":
				row.expiry_date = add_months(row.date_issued, 24) if row.date_issued else None
				row.penalty_pct = 10
				has_written = 1
			elif row.demerit_type == "Repeated Tardiness":
				row.expiry_date = add_months(row.date_issued, 12) if row.date_issued else None
				row.penalty_pct = 3
			elif row.demerit_type == "Serious Misconduct":
				row.expiry_date = None  # permanent
				row.penalty_pct = 20
				has_serious = 1
			elif row.demerit_type == "False Evidence":
				row.expiry_date = None  # cycle-scoped
				row.penalty_pct = 0  # disqualifies Section B entirely
				has_false_evidence = 1

			# Determine if active (not expired relative to cycle end)
			if row.demerit_type == "Serious Misconduct":
				row.active = 1  # permanent
			elif row.expiry_date and cycle_end:
				row.active = 1 if getdate(row.expiry_date) >= getdate(cycle_end) else 0
			else:
				row.active = 1

			if row.active:
				total_penalty += flt(row.penalty_pct)

		self.total_demerit_pct = flt(total_penalty, 2)
		self.has_written_warning = has_written
		self.has_serious_misconduct = has_serious
		# Store false evidence flag for Section B calculation
		self._has_false_evidence = has_false_evidence

	def calculate_section_b_score(self):
		"""Calculate Section B: evidence-based B4/B5 with progression gates.

		Gates:
		- New joiner: Section B = 0
		- Section A < 71%: Section B locked
		- B5 requires full B4 (15+ pts) AND no written warning AND no serious misconduct
		- B5 replaces B4 (not additive)
		- False Evidence demerit: Section B disqualified
		"""
		# Gate: new joiner
		if cint(self.is_new_joiner):
			self.section_b_score = 0
			self.section_b_gate_status = "New Joiner Rule: Section B not assessed this cycle. Rating based on Section A only."
			return

		# Gate: false evidence
		if getattr(self, "_has_false_evidence", 0):
			self.section_b_score = 0
			self.section_b_gate_status = "False Evidence: Section B disqualified for this cycle."
			return

		# Gate: Section A < 71%
		section_a = flt(self.section_a_score)
		if section_a < 71:
			self.section_b_score = 0
			self.section_b_gate_status = (
				"Section B locked: Section A must reach \u2265 71% first. "
				"A weak foundation cannot be compensated by Section B evidence."
			)
			return

		# Calculate B4 points
		b4_pts = sum(self._evidence_points(row) for row in self.b4_evidence)
		self.b4_total_points = b4_pts

		b4_score = 0
		if 8 <= b4_pts <= 14:
			b4_score = 5
		elif b4_pts >= 15:
			b4_score = 10

		# Calculate B5 (requires full B4 15+ pts, no written warning, no serious misconduct)
		b5_score = 0
		self.b5_total_points = 0

		if b4_pts >= 15 and not cint(self.has_written_warning) and not cint(self.has_serious_misconduct):
			b5_pts = sum(self._evidence_points(row) for row in self.b5_evidence)
			self.b5_total_points = b5_pts

			if 8 <= b5_pts <= 13:
				b5_score = 15
			elif b5_pts >= 14:
				b5_score = 20
		elif b4_pts < 15 and self.b5_evidence:
			self.section_b_gate_status = (
				"B5 locked: Full B4 score (15+ pts) required before B5 can be claimed."
			)
		elif (cint(self.has_written_warning) or cint(self.has_serious_misconduct)) and self.b5_evidence:
			self.section_b_gate_status = (
				"B5 locked: Active written warning or serious misconduct blocks B5 access."
			)

		# B5 replaces B4 (not additive)
		if b5_score > 0:
			self.section_b_score = flt(b5_score)
			self.section_b_gate_status = ""
		else:
			self.section_b_score = flt(b4_score)
			if b4_score > 0 and not self.section_b_gate_status:
				self.section_b_gate_status = ""

	def _evidence_points(self, row):
		"""Convert evidence quality to points and set on row"""
		if row.evidence_quality == "Strong":
			row.points = 3
		elif row.evidence_quality == "Partial":
			row.points = 2
		else:
			row.points = 0
		return row.points

	def set_leadership_gate_applicability(self):
		"""Set is_leader based on employee band (B, C, D are leaders)"""
		band = (self.employee_band or "").strip()
		self.is_leader = 1 if band in ("B", "C", "D") else 0

	def calculate_leadership_gate(self):
		"""Calculate leadership scorecard average and gate pass/fail.
		Leaders must score >= 60% on the scorecard to pass the gate.
		"""
		if not cint(self.is_leader):
			self.leadership_score_pct = 0
			self.leadership_gate_passed = 0
			return

		if not self.leadership_scorecard:
			self.leadership_score_pct = 0
			self.leadership_gate_passed = 0
			return

		total_score = sum(flt(row.score_pct) for row in self.leadership_scorecard)
		count = len(self.leadership_scorecard)
		avg_score = flt(total_score / count, 2) if count else 0

		self.leadership_score_pct = avg_score
		self.leadership_gate_passed = 1 if avg_score >= 60 else 0

	def set_second_validator_flag(self):
		"""Auto-set requires_second_validator when PMS score > 90%"""
		self.requires_second_validator = 1 if flt(self.pms_total_score) > 90 else 0

	def calculate_pms_total(self):
		"""Calculate total PMS score: Section A + Section B bonus - demerits, with hard caps"""
		raw_score = flt(self.section_a_score) + flt(self.section_b_score) - flt(self.total_demerit_pct)
		raw_score = max(0, min(100, raw_score))

		# Hard cap: serious misconduct caps at 59%
		if cint(self.has_serious_misconduct):
			raw_score = min(raw_score, 59)

		# Hard cap: leadership gate failed caps at 80% (Rating C)
		if cint(self.is_leader) and not cint(self.leadership_gate_passed):
			raw_score = min(raw_score, 80)

		self.pms_total_score = flt(raw_score, 2)
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

		# Template goals already sum to 100% — copy directly
		for entry in template.goals:
			self.append(
				"appraisal_kra",
				{
					"kra": entry.key_result_area,
					"per_weightage": flt(entry.per_weightage, 2),
					"kpi": entry.get("kpi"),
					"kpi_description": entry.get("kpi_description"),
					"target": flt(entry.get("default_target")),
					"unit_of_measure": entry.get("unit_of_measure"),
				},
			)

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
			upper = (GRADE_SCALE[i - 1][0] - 1) if i > 0 else 100
			parts.append(f"{threshold}\u2013{upper}: {grade}")
		else:
			prev_threshold = GRADE_SCALE[i - 1][0] - 1
			parts.append(f"&lt;{prev_threshold + 1}: {grade}")
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
def get_templates_for_department(doctype, txt, searchfield, start, page_len, filters):
	"""Return appraisal templates matching the department tree (self + ancestors).
	Used as a server-side query so the filter is always applied when dropdown opens.
	"""
	department = filters.get("department")
	departments = get_department_ancestors(department) if department else []

	conditions = ""
	if departments:
		dept_list = ", ".join(frappe.db.escape(d) for d in departments)
		conditions = f"AND `department` IN ({dept_list})"

	return frappe.db.sql(
		f"""
		SELECT `name`, `template_title`
		FROM `tabAppraisal Template`
		WHERE (`template_title` LIKE %(txt)s OR `name` LIKE %(txt)s)
		{conditions}
		ORDER BY `template_title` ASC
		LIMIT %(page_len)s OFFSET %(start)s
		""",
		{"txt": f"%{txt}%", "page_len": page_len, "start": start},
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
