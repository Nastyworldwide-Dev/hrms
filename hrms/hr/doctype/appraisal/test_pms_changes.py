# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# Tests for PMS 70/20/10 model changes, department-based template binding,
# and related improvements on the as-hr_kpi branch.

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from erpnext.setup.doctype.designation.test_designation import create_designation
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.appraisal.appraisal import GRADE_SCALE, get_grade
from hrms.hr.doctype.appraisal_cycle.appraisal_cycle import get_department_template
from hrms.hr.doctype.appraisal_cycle.test_appraisal_cycle import create_appraisal_cycle
from hrms.hr.doctype.appraisal_template.test_appraisal_template import (
	create_appraisal_template,
	create_kras,
)
from hrms.tests.test_utils import create_company


class TestWeightageScaling(FrappeTestCase):
	"""Tests for template 100% → 70% scaling when copying KRAs to appraisal"""

	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.employee = make_employee("pms_test@example.com", company=self.company, designation="Engineer")

	def test_kras_scaled_to_70(self):
		"""Template KRAs (30+70=100) should become (21+49=70) on appraisal"""
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		total = sum(flt(row.per_weightage) for row in appraisal.appraisal_kra)
		self.assertEqual(total, 70.0)

		# 30% of 100 → 21% of 70
		self.assertEqual(appraisal.appraisal_kra[0].per_weightage, 21.0)
		# 70% of 100 → 49% of 70
		self.assertEqual(appraisal.appraisal_kra[1].per_weightage, 49.0)

	def test_scaling_with_odd_weights(self):
		"""Rounding fix should ensure weights sum to exactly 70"""
		# 33.33 + 33.33 + 33.34 = 100
		template = create_appraisal_template(
			title="Odd Weights",
			kras=[
				{"key_result_area": "Quality", "per_weightage": 33.33},
				{"key_result_area": "Development", "per_weightage": 33.33},
				{"key_result_area": "Innovation", "per_weightage": 33.34},
			],
		)

		appraisal = frappe.get_doc(
			{
				"doctype": "Appraisal",
				"employee": self.employee,
				"company": self.company,
				"appraisal_template": template.name,
				"appraisal_cycle": create_appraisal_cycle(name="Q-Odd", designation="Engineer").name,
			}
		)
		appraisal.set_kras_and_rating_criteria()

		total = sum(flt(row.per_weightage) for row in appraisal.appraisal_kra)
		self.assertEqual(flt(total, 2), 70.0)

	def test_scaling_preserves_ratios(self):
		"""Relative proportions should be maintained after scaling"""
		cycle = create_appraisal_cycle(name="Q-Ratio", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		w0 = appraisal.appraisal_kra[0].per_weightage
		w1 = appraisal.appraisal_kra[1].per_weightage

		# Original ratio: 30:70 = 3:7, scaled should maintain ~3:7
		ratio = w0 / w1
		expected_ratio = 30.0 / 70.0
		self.assertAlmostEqual(ratio, expected_ratio, places=1)

	def test_manual_rating_goals_not_scaled(self):
		"""Manual rating mode uses 'goals' table — weightage should still scale to 70"""
		cycle = create_appraisal_cycle(
			name="Q-Manual", designation="Engineer", kra_evaluation_method="Manual Rating"
		)
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		total = sum(flt(row.per_weightage) for row in appraisal.goals)
		self.assertEqual(flt(total, 2), 70.0)


class TestKRAMetadataCopy(FrappeTestCase):
	"""Tests for kra_category and kpi_description copying from template to appraisal"""

	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name

		create_kras(["Revenue", "Compliance"])

		self.template = create_appraisal_template(
			title="Metadata Test",
			kras=[
				{
					"key_result_area": "Revenue",
					"per_weightage": 60,
					"kra_category": "Financial Goal",
					"kpi_description": "Achieve 15% YoY growth",
				},
				{
					"key_result_area": "Compliance",
					"per_weightage": 40,
					"kra_category": "Stakeholder Goal",
					"kpi_description": "Zero audit findings",
				},
			],
		)

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.employee = make_employee(
			"metadata_test@example.com", company=self.company, designation="Engineer"
		)

	def test_category_and_kpi_copied(self):
		"""kra_category and kpi_description should copy from template to appraisal KRA rows"""
		cycle = create_appraisal_cycle(name="Q-Meta", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		self.assertEqual(appraisal.appraisal_kra[0].kra_category, "Financial Goal")
		self.assertEqual(appraisal.appraisal_kra[0].kpi_description, "Achieve 15% YoY growth")
		self.assertEqual(appraisal.appraisal_kra[1].kra_category, "Stakeholder Goal")
		self.assertEqual(appraisal.appraisal_kra[1].kpi_description, "Zero audit findings")

	def test_empty_metadata_handled(self):
		"""Template goals without metadata should copy as None/empty"""
		template = create_appraisal_template()  # default — no metadata

		appraisal = frappe.get_doc(
			{
				"doctype": "Appraisal",
				"employee": self.employee,
				"company": self.company,
				"appraisal_template": template.name,
				"appraisal_cycle": create_appraisal_cycle(name="Q-NoMeta", designation="Engineer").name,
			}
		)
		appraisal.set_kras_and_rating_criteria()

		for row in appraisal.appraisal_kra:
			self.assertFalse(row.kra_category)
			self.assertFalse(row.kpi_description)


class TestDepartmentTemplateResolution(FrappeTestCase):
	"""Tests for department tree-based template lookup"""

	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name

		# Create department tree: Operations → Logistics, Procurement
		self._create_department_tree()

		create_kras(["Ops KRA", "Procurement KRA"])

		# Template for Operations (parent)
		self.ops_template = create_appraisal_template(
			title="Operations KRAs",
			kras=[
				{"key_result_area": "Ops KRA", "per_weightage": 100},
			],
		)
		self.ops_template.department = self.operations
		self.ops_template.save()

		# Template for Procurement (override)
		self.proc_template = create_appraisal_template(
			title="Procurement KRAs",
			kras=[
				{"key_result_area": "Procurement KRA", "per_weightage": 100},
			],
		)
		self.proc_template.department = self.procurement
		self.proc_template.save()

	def _create_department_tree(self):
		"""Create Operations → Logistics, Procurement department tree"""
		from erpnext.setup.doctype.department.department import get_abbreviated_name

		frappe.get_cached_value("Company", self.company, "abbr")

		# Parent department
		ops_name = get_abbreviated_name("Operations", self.company)
		if not frappe.db.exists("Department", ops_name):
			ops = frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": "Operations",
					"company": self.company,
				}
			).insert()
			self.operations = ops.name
		else:
			self.operations = ops_name

		# Child: Logistics (no template — should inherit from Operations)
		log_name = get_abbreviated_name("Logistics", self.company)
		if not frappe.db.exists("Department", log_name):
			log = frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": "Logistics",
					"company": self.company,
					"parent_department": self.operations,
				}
			).insert()
			self.logistics = log.name
		else:
			self.logistics = log_name

		# Child: Procurement (has own template — overrides parent)
		proc_name = get_abbreviated_name("Procurement", self.company)
		if not frappe.db.exists("Department", proc_name):
			proc = frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": "Procurement",
					"company": self.company,
					"parent_department": self.operations,
				}
			).insert()
			self.procurement = proc.name
		else:
			self.procurement = proc_name

		# Rebuild tree to set lft/rgt
		frappe.get_doc("Department", self.operations).rebuild_tree()

	def test_exact_department_match(self):
		"""Procurement has its own template — should use it directly"""
		result = get_department_template(self.procurement)
		self.assertEqual(result, self.proc_template.name)

	def test_parent_department_inheritance(self):
		"""Logistics has no template — should inherit from parent Operations"""
		result = get_department_template(self.logistics)
		self.assertEqual(result, self.ops_template.name)

	def test_parent_department_direct(self):
		"""Operations has a template — should return it"""
		result = get_department_template(self.operations)
		self.assertEqual(result, self.ops_template.name)

	def test_no_template_returns_none(self):
		"""Department with no template in tree should return None"""
		from erpnext.setup.doctype.department.department import get_abbreviated_name

		dept_name = get_abbreviated_name("Orphan Dept", self.company)
		if not frappe.db.exists("Department", dept_name):
			dept = frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": "Orphan Dept",
					"company": self.company,
				}
			).insert()
			dept_name = dept.name

		result = get_department_template(dept_name)
		self.assertIsNone(result)

	def test_none_department_returns_none(self):
		result = get_department_template(None)
		self.assertIsNone(result)

	def test_cycle_uses_department_over_designation(self):
		"""When both department template and designation template exist, department wins"""
		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.ops_template.name
		engineer.save()

		emp = make_employee(
			"logistics_emp@example.com",
			company=self.company,
			designation="Engineer",
			department=self.procurement,
		)

		cycle = create_appraisal_cycle(name="Q-Dept", company=self.company)
		# Find the appraisee for this employee
		appraisee = [a for a in cycle.appraisees if a.employee == emp]
		self.assertTrue(len(appraisee) > 0)
		# Should use Procurement template, not designation template
		self.assertEqual(appraisee[0].appraisal_template, self.proc_template.name)

	def test_designation_fallback_when_no_dept_template(self):
		"""Employee with no department template should fall back to designation"""
		from erpnext.setup.doctype.department.department import get_abbreviated_name

		# Create a department with no template anywhere in its tree
		dept_name = get_abbreviated_name("NoTemplate Dept", self.company)
		if not frappe.db.exists("Department", dept_name):
			dept = frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": "NoTemplate Dept",
					"company": self.company,
				}
			).insert()
			dept_name = dept.name

		fallback_template = create_appraisal_template()

		designer = create_designation(designation_name="Designer")
		designer.appraisal_template = fallback_template.name
		designer.save()

		emp = make_employee(
			"no_dept_template@example.com",
			company=self.company,
			designation="Designer",
			department=dept_name,
		)

		cycle = create_appraisal_cycle(name="Q-Fallback", company=self.company)
		appraisee = [a for a in cycle.appraisees if a.employee == emp]
		self.assertTrue(len(appraisee) > 0)
		self.assertEqual(appraisee[0].appraisal_template, fallback_template.name)


class TestAppraisalTemplateResolution(FrappeTestCase):
	"""Tests for set_appraisal_template() fallback chain on Appraisal form"""

	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name

		create_kras(["Dept KRA", "Desig KRA"])

		self.dept_template = create_appraisal_template(
			title="Dept Template",
			kras=[{"key_result_area": "Dept KRA", "per_weightage": 100}],
		)

		self.desig_template = create_appraisal_template(
			title="Desig Template",
			kras=[{"key_result_area": "Desig KRA", "per_weightage": 100}],
		)

		from erpnext.setup.doctype.department.department import get_abbreviated_name

		dept_name = get_abbreviated_name("Template Test Dept", self.company)
		if not frappe.db.exists("Department", dept_name):
			dept = frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": "Template Test Dept",
					"company": self.company,
				}
			).insert()
			dept_name = dept.name
		self.department = dept_name

		self.dept_template.department = self.department
		self.dept_template.save()

		analyst = create_designation(designation_name="Analyst")
		analyst.appraisal_template = self.desig_template.name
		analyst.save()

		self.employee = make_employee(
			"template_resolve@example.com",
			company=self.company,
			designation="Analyst",
			department=self.department,
		)

	def test_department_wins_over_designation(self):
		"""When no cycle appraisee entry, department template should be preferred over designation"""
		appraisal = frappe.get_doc(
			{
				"doctype": "Appraisal",
				"employee": self.employee,
				"company": self.company,
				"appraisal_cycle": create_appraisal_cycle(name="Q-Resolve", designation="Analyst").name,
			}
		)
		appraisal.set_appraisal_template()

		# Department template should win since it's checked before designation
		self.assertEqual(appraisal.appraisal_template, self.dept_template.name)


class TestGradeScale(FrappeTestCase):
	"""Tests for centralized grade scale"""

	def test_grade_boundaries(self):
		self.assertEqual(get_grade(100), "Outstanding")
		self.assertEqual(get_grade(91), "Outstanding")
		self.assertEqual(get_grade(90), "Exceeds Expectations")
		self.assertEqual(get_grade(81), "Exceeds Expectations")
		self.assertEqual(get_grade(80), "Meets Expectations")
		self.assertEqual(get_grade(71), "Meets Expectations")
		self.assertEqual(get_grade(70), "Needs Improvement")
		self.assertEqual(get_grade(60), "Needs Improvement")
		self.assertEqual(get_grade(59), "Unsatisfactory")
		self.assertEqual(get_grade(0), "Unsatisfactory")

	def test_grade_scale_constant_sorted_descending(self):
		"""GRADE_SCALE must be sorted descending by threshold for get_grade() to work"""
		thresholds = [t for t, _ in GRADE_SCALE]
		self.assertEqual(thresholds, sorted(thresholds, reverse=True))

	def test_grade_scale_covers_zero(self):
		"""Last threshold must be 0 to catch all scores"""
		self.assertEqual(GRADE_SCALE[-1][0], 0)


class TestSectionScoreCalculation(FrappeTestCase):
	"""Tests for PMS section score calculations"""

	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.employee = make_employee("score_test@example.com", company=self.company, designation="Engineer")

	def test_section_a_score_from_achievement(self):
		"""weighted_score derives from capped achievement, not manager rating.

		weighted_score = per_weightage * min(achievement, 100) / 100
		"""
		cycle = create_appraisal_cycle(name="Q-ScoreA", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		# 100% achievement on 21% weight, 80% achievement on 49% weight
		appraisal.appraisal_kra[0].target = 100
		appraisal.appraisal_kra[0].actual = 100
		appraisal.appraisal_kra[1].target = 100
		appraisal.appraisal_kra[1].actual = 80
		appraisal.save()

		# Row 0: 21 * 100/100 = 21.0
		self.assertEqual(appraisal.appraisal_kra[0].weighted_score, 21.0)
		# Row 1: 49 * 80/100 = 39.2
		self.assertEqual(appraisal.appraisal_kra[1].weighted_score, 39.2)
		# manager_rating no longer influences the score
		self.assertEqual(flt(appraisal.appraisal_kra[0].manager_rating), 0.0)

	def test_a1_full_achievement_is_full_marks(self):
		"""All KRAs at 100% achievement → Section A = full A1 weight (70)."""
		cycle = create_appraisal_cycle(name="Q-FullAch", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		for row in appraisal.appraisal_kra:
			row.target = 100
			row.actual = 100
		appraisal.save()

		self.assertEqual(appraisal.section_a_score, 70.0)

	def test_a1_overachievement_capped_at_100(self):
		"""actual > target is scored as 100%; a single KRA cannot inflate Section A."""
		cycle = create_appraisal_cycle(name="Q-OverAch", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		# Every KRA doubles its target
		for row in appraisal.appraisal_kra:
			row.target = 100
			row.actual = 200
		appraisal.save()

		# Raw achievement is preserved for transparency...
		self.assertEqual(appraisal.appraisal_kra[0].achievement, 200.0)
		# ...but the weighted score is capped as if 100%
		self.assertEqual(
			appraisal.appraisal_kra[0].weighted_score,
			appraisal.appraisal_kra[0].per_weightage,
		)
		# Section A does not exceed the full A1 weight
		self.assertEqual(appraisal.section_a_score, 70.0)

	def test_achievement_calculation(self):
		"""achievement = actual / target * 100"""
		cycle = create_appraisal_cycle(name="Q-Achieve", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		appraisal.appraisal_kra[0].target = 100
		appraisal.appraisal_kra[0].actual = 85
		appraisal.save()

		self.assertEqual(appraisal.appraisal_kra[0].achievement, 85.0)

	def test_zero_target_achievement(self):
		"""Target of 0 should not cause division by zero"""
		cycle = create_appraisal_cycle(name="Q-ZeroTarget", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		appraisal.appraisal_kra[0].target = 0
		appraisal.appraisal_kra[0].actual = 50
		appraisal.save()

		self.assertEqual(appraisal.appraisal_kra[0].achievement, 0)

	def test_pms_total_and_grade(self):
		"""PMS total = section_a + section_b + section_c; grade derived from total"""
		cycle = create_appraisal_cycle(name="Q-PMS", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		# Max out achievement on every KRA (actual == target → 100%)
		for row in appraisal.appraisal_kra:
			row.target = 100
			row.actual = 100

		appraisal.save()

		# Section A should be 70 (all at 100% achievement on total 70% weight)
		self.assertEqual(appraisal.section_a_score, 70.0)
		# No Section B/C rows, so PMS total = 70
		self.assertEqual(appraisal.pms_total_score, 70.0)
		self.assertEqual(appraisal.overall_grade, "Needs Improvement")

	def test_final_score_uses_pms_total(self):
		"""final_score should equal pms_total_score when PMS model is active"""
		cycle = create_appraisal_cycle(name="Q-Final", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		for row in appraisal.appraisal_kra:
			row.target = 100
			row.actual = 100
		appraisal.save()

		self.assertEqual(appraisal.final_score, appraisal.pms_total_score)


class TestCalculateTotalScoreExpects70(FrappeTestCase):
	"""Tests that calculate_total_score validates weightage sums correctly"""

	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.employee = make_employee(
			"total_score_test@example.com", company=self.company, designation="Engineer"
		)

	def test_kra_weightage_70_passes_validation(self):
		"""KRA weights summing to 70 should pass validate_total_weightage"""
		cycle = create_appraisal_cycle(name="Q-Val70", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		# Should not throw — weights sum to 70
		total = sum(flt(row.per_weightage) for row in appraisal.appraisal_kra)
		self.assertEqual(total, 70.0)
		appraisal.save()  # Should succeed without error


class TestGoalScoreGroupedQuery(FrappeTestCase):
	"""Tests that the grouped query in set_goal_score produces same results as N+1"""

	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.employee = make_employee(
			"goal_query_test@example.com", company=self.company, designation="Engineer"
		)

	def test_goal_score_with_no_goals(self):
		"""No goals should result in 0 completion for all KRAs"""
		cycle = create_appraisal_cycle(name="Q-NoGoal", designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		for kra in appraisal.appraisal_kra:
			self.assertEqual(kra.goal_completion, 0)
			self.assertEqual(kra.goal_score, 0)

	def test_goal_score_single_kra(self):
		"""Goal score for a single KRA with one goal"""
		from hrms.hr.doctype.goal.test_goal import create_goal

		cycle = create_appraisal_cycle(name="Q-SingleGoal", designation="Engineer")
		cycle.create_appraisals()

		create_goal(self.employee, "Quality", appraisal_cycle=cycle.name, progress=75)

		appraisal = frappe.get_doc(
			"Appraisal",
			{"appraisal_cycle": cycle.name, "employee": self.employee},
		)

		# Quality KRA, 21% weight, 75% completion → goal_score = 75 * 21 / 100 = 15.75
		self.assertEqual(appraisal.appraisal_kra[0].goal_completion, 75)
		self.assertEqual(appraisal.appraisal_kra[0].goal_score, 15.75)


class TestAppraisalVisibility(FrappeTestCase):
	"""Employees may only see their own Appraisal; HR roles see everything"""

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.user_a = "appraisal_vis_a@example.com"
		self.user_b = "appraisal_vis_b@example.com"
		self.employee_a = make_employee(self.user_a, company=self.company, designation="Engineer")
		self.employee_b = make_employee(self.user_b, company=self.company, designation="Engineer")

		# isolate the code-level restriction from any User Permission rows
		frappe.db.delete("User Permission", {"user": ("in", [self.user_a, self.user_b])})
		frappe.clear_cache(user=self.user_a)
		frappe.clear_cache(user=self.user_b)

		cycle = create_appraisal_cycle(name="Q-Visibility", designation="Engineer")
		cycle.create_appraisals()

		self.appraisal_a = frappe.db.get_value("Appraisal", {"employee": self.employee_a}, "name")
		self.appraisal_b = frappe.db.get_value("Appraisal", {"employee": self.employee_b}, "name")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_employee_sees_only_own_appraisal_in_list(self):
		"""get_list as a plain employee returns only their own appraisal"""
		frappe.set_user(self.user_a)
		visible = frappe.get_list("Appraisal", pluck="name")
		self.assertEqual(visible, [self.appraisal_a])

	def test_employee_cannot_read_others_appraisal(self):
		"""Doc-level read on a colleague's appraisal is denied"""
		self.assertTrue(frappe.has_permission("Appraisal", doc=self.appraisal_a, user=self.user_a))
		self.assertFalse(frappe.has_permission("Appraisal", doc=self.appraisal_b, user=self.user_a))

	def test_hr_user_sees_all_appraisals(self):
		"""HR User role is exempt from the own-employee restriction"""
		hr_email = "appraisal_vis_hr@example.com"
		make_employee(hr_email, company=self.company, designation="Engineer")
		frappe.get_doc("User", hr_email).add_roles("HR User")

		frappe.set_user(hr_email)
		visible = frappe.get_list("Appraisal", pluck="name")
		self.assertIn(self.appraisal_a, visible)
		self.assertIn(self.appraisal_b, visible)

	def test_user_without_employee_sees_nothing(self):
		"""A desk user with no Employee record gets an empty appraisal list"""
		from hrms.hr.doctype.appraisal.appraisal import get_permission_query_conditions

		self.assertEqual(get_permission_query_conditions("no_employee@example.com"), "1=0")

	def test_feedback_history_api_denied_for_others(self):
		"""Whitelisted feedback API cannot leak a colleague's appraisal feedback"""
		from hrms.hr.doctype.appraisal.appraisal import get_feedback_history

		frappe.set_user(self.user_a)
		# own appraisal still works
		self.assertIsNotNone(get_feedback_history(self.employee_a, self.appraisal_a))
		self.assertRaises(frappe.PermissionError, get_feedback_history, self.employee_b, self.appraisal_b)

	def test_kra_search_api_denied_for_others(self):
		"""KRA link search cannot enumerate a colleague's appraisal KRAs"""
		from hrms.hr.doctype.appraisal.appraisal import get_kras_for_employee

		cycle = frappe.db.get_value("Appraisal", self.appraisal_b, "appraisal_cycle")
		frappe.set_user(self.user_a)
		self.assertRaises(
			frappe.PermissionError,
			get_kras_for_employee,
			"Appraisal KRA",
			"",
			"name",
			0,
			20,
			{"appraisal_cycle": cycle, "employee": self.employee_b},
		)

	def test_appraisal_overview_report_scoped(self):
		"""Appraisal Overview report (frappe.qb) applies the own-employee scope"""
		from hrms.hr.report.appraisal_overview.appraisal_overview import get_data

		frappe.set_user(self.user_a)
		rows = get_data(frappe._dict())
		self.assertEqual({row.employee for row in rows}, {self.employee_a})

		frappe.set_user("Administrator")
		rows = get_data(frappe._dict())
		self.assertEqual({row.employee for row in rows}, {self.employee_a, self.employee_b})

	def test_cycle_summary_hidden_from_plain_employee(self):
		"""Cycle-wide completion stats are only returned to unrestricted roles"""
		from hrms.hr.doctype.appraisal_cycle.appraisal_cycle import get_appraisal_cycle_summary

		cycle = frappe.db.get_value("Appraisal", self.appraisal_a, "appraisal_cycle")

		frappe.set_user(self.user_a)
		self.assertIsNone(get_appraisal_cycle_summary(cycle))

		frappe.set_user("Administrator")
		self.assertEqual(get_appraisal_cycle_summary(cycle)["appraisees"], 2)


class TestManagerAppraisalVisibility(FrappeTestCase):
	"""Managers (reports_to) get read-only visibility of the whole reporting chain below them"""

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")

		self.company = create_company("_Test PMS").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		# chain: manager -> report -> grand_report; `other` is outside the chain
		self.manager_user = "appraisal_mgr@example.com"
		self.report_user = "appraisal_mgr_report@example.com"
		self.grand_user = "appraisal_mgr_grand@example.com"
		self.other_user = "appraisal_mgr_other@example.com"
		self.manager = make_employee(self.manager_user, company=self.company, designation="Engineer")
		self.report = make_employee(self.report_user, company=self.company, designation="Engineer")
		self.grand = make_employee(self.grand_user, company=self.company, designation="Engineer")
		self.other = make_employee(self.other_user, company=self.company, designation="Engineer")

		frappe.db.set_value("Employee", self.report, "reports_to", self.manager)
		frappe.db.set_value("Employee", self.grand, "reports_to", self.report)

		# isolate the code-level restriction from any User Permission rows
		users = [self.manager_user, self.report_user, self.grand_user, self.other_user]
		frappe.db.delete("User Permission", {"user": ("in", users)})
		for user in users:
			frappe.clear_cache(user=user)

		cycle = create_appraisal_cycle(name="Q-Mgr", designation="Engineer")
		cycle.create_appraisals()

		self.manager_appraisal = frappe.db.get_value("Appraisal", {"employee": self.manager}, "name")
		self.report_appraisal = frappe.db.get_value("Appraisal", {"employee": self.report}, "name")
		self.grand_appraisal = frappe.db.get_value("Appraisal", {"employee": self.grand}, "name")
		self.other_appraisal = frappe.db.get_value("Appraisal", {"employee": self.other}, "name")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_manager_sees_own_and_whole_chain(self):
		frappe.set_user(self.manager_user)
		visible = set(frappe.get_list("Appraisal", pluck="name"))
		self.assertEqual(visible, {self.manager_appraisal, self.report_appraisal, self.grand_appraisal})

	def test_mid_manager_sees_own_and_subtree_only(self):
		frappe.set_user(self.report_user)
		visible = set(frappe.get_list("Appraisal", pluck="name"))
		self.assertEqual(visible, {self.report_appraisal, self.grand_appraisal})

	def test_manager_read_but_not_write_on_indirect_report(self):
		self.assertTrue(frappe.has_permission("Appraisal", doc=self.grand_appraisal, user=self.manager_user))
		self.assertFalse(
			frappe.has_permission(
				"Appraisal", doc=self.grand_appraisal, ptype="write", user=self.manager_user
			)
		)

	def test_manager_read_but_not_write_on_reports_appraisal(self):
		self.assertTrue(frappe.has_permission("Appraisal", doc=self.report_appraisal, user=self.manager_user))
		self.assertFalse(
			frappe.has_permission(
				"Appraisal", doc=self.report_appraisal, ptype="write", user=self.manager_user
			)
		)

	def test_manager_keeps_write_on_own_appraisal(self):
		self.assertTrue(
			frappe.has_permission(
				"Appraisal", doc=self.manager_appraisal, ptype="write", user=self.manager_user
			)
		)

	def test_manager_cannot_see_non_reports(self):
		self.assertFalse(frappe.has_permission("Appraisal", doc=self.other_appraisal, user=self.manager_user))

	def test_manager_cannot_share_subordinates_appraisal(self):
		"""share is write-equivalent (frappe.share.add grants third-party access)"""
		for appraisal in (self.report_appraisal, self.grand_appraisal):
			self.assertFalse(
				frappe.has_permission("Appraisal", doc=appraisal, ptype="share", user=self.manager_user)
			)

	def test_bottom_of_chain_sees_only_own(self):
		frappe.set_user(self.grand_user)
		visible = frappe.get_list("Appraisal", pluck="name")
		self.assertEqual(visible, [self.grand_appraisal])

	def test_manager_feedback_api_and_report_access(self):
		from hrms.hr.doctype.appraisal.appraisal import get_feedback_history
		from hrms.hr.report.appraisal_overview.appraisal_overview import get_data

		frappe.set_user(self.manager_user)
		self.assertIsNotNone(get_feedback_history(self.report, self.report_appraisal))
		rows = get_data(frappe._dict())
		self.assertEqual({row.employee for row in rows}, {self.manager, self.report, self.grand})


class TestAppraisalShareGrant(FrappeTestCase):
	"""HR can manually grant per-document visibility via the native Share (DocShare)"""

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")
		frappe.db.delete("DocShare", {"share_doctype": "Appraisal"})

		self.company = create_company("_Test PMS").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.user_a = "appraisal_share_a@example.com"
		self.user_b = "appraisal_share_b@example.com"
		self.employee_a = make_employee(self.user_a, company=self.company, designation="Engineer")
		self.employee_b = make_employee(self.user_b, company=self.company, designation="Engineer")

		# isolate the code-level restriction from any User Permission rows
		frappe.db.delete("User Permission", {"user": ("in", [self.user_a, self.user_b])})
		frappe.clear_cache(user=self.user_a)
		frappe.clear_cache(user=self.user_b)

		cycle = create_appraisal_cycle(name="Q-Share", designation="Engineer")
		cycle.create_appraisals()

		self.appraisal_a = frappe.db.get_value("Appraisal", {"employee": self.employee_a}, "name")
		self.appraisal_b = frappe.db.get_value("Appraisal", {"employee": self.employee_b}, "name")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_share_grants_read_only_visibility(self):
		import frappe.share

		frappe.share.add("Appraisal", self.appraisal_b, self.user_a)

		frappe.set_user(self.user_a)
		visible = set(frappe.get_list("Appraisal", pluck="name"))
		self.assertEqual(visible, {self.appraisal_a, self.appraisal_b})
		self.assertTrue(frappe.has_permission("Appraisal", doc=self.appraisal_b, user=self.user_a))
		# read grant does not imply write
		self.assertFalse(
			frappe.has_permission("Appraisal", doc=self.appraisal_b, ptype="write", user=self.user_a)
		)

	def test_share_with_write_grants_write(self):
		import frappe.share

		frappe.share.add("Appraisal", self.appraisal_b, self.user_a, write=1)
		self.assertTrue(
			frappe.has_permission("Appraisal", doc=self.appraisal_b, ptype="write", user=self.user_a)
		)

	def test_revoking_share_removes_access(self):
		import frappe.share

		frappe.share.add("Appraisal", self.appraisal_b, self.user_a)
		frappe.share.remove("Appraisal", self.appraisal_b, self.user_a)

		frappe.set_user(self.user_a)
		self.assertEqual(frappe.get_list("Appraisal", pluck="name"), [self.appraisal_a])
		self.assertFalse(frappe.has_permission("Appraisal", doc=self.appraisal_b, user=self.user_a))

	def test_share_extends_feedback_api_and_report(self):
		import frappe.share

		from hrms.hr.doctype.appraisal.appraisal import get_feedback_history
		from hrms.hr.report.appraisal_overview.appraisal_overview import get_data

		frappe.share.add("Appraisal", self.appraisal_b, self.user_a)

		frappe.set_user(self.user_a)
		self.assertIsNotNone(get_feedback_history(self.employee_b, self.appraisal_b))
		rows = get_data(frappe._dict())
		self.assertEqual({row.employee for row in rows}, {self.employee_a, self.employee_b})

	def test_unshared_colleague_still_hidden(self):
		frappe.set_user(self.user_a)
		self.assertEqual(frappe.get_list("Appraisal", pluck="name"), [self.appraisal_a])

	def test_everyone_share_blocked(self):
		"""Appraisals can never be shared with Everyone, not even by admins"""
		import frappe.share

		self.assertRaises(
			frappe.ValidationError,
			frappe.share.add,
			"Appraisal",
			self.appraisal_b,
			everyone=1,
		)

	def test_can_share_right_blocked(self):
		"""DocShare rows on Appraisal can never carry the Can Share right"""
		import frappe.share

		self.assertRaises(
			frappe.ValidationError,
			frappe.share.add,
			"Appraisal",
			self.appraisal_b,
			self.user_a,
			share=1,
		)

	def test_shared_user_cannot_onward_share(self):
		"""A read grant cannot be re-shared to third parties by the grantee"""
		import frappe.share

		frappe.share.add("Appraisal", self.appraisal_b, self.user_a)

		frappe.set_user(self.user_a)
		self.assertRaises(
			frappe.PermissionError,
			frappe.share.add,
			"Appraisal",
			self.appraisal_b,
			self.user_b,
		)


class TestAppraisalEmployeeQuery(FrappeTestCase):
	"""Employee picker on the Appraisal form follows the appraisal list rule:
	own employee + reports_to chain below, bypassing Employee doctype perms"""

	def setUp(self):
		frappe.set_user("Administrator")
		self.company = create_company("_Test PMS").name

		# chain: manager -> report -> grand_report; `other` is outside the chain
		self.manager_user = "appraisal_query_mgr@example.com"
		self.report_user = "appraisal_query_report@example.com"
		self.grand_user = "appraisal_query_grand@example.com"
		self.other_user = "appraisal_query_other@example.com"
		self.manager = make_employee(self.manager_user, company=self.company)
		self.report = make_employee(self.report_user, company=self.company)
		self.grand = make_employee(self.grand_user, company=self.company)
		self.other = make_employee(self.other_user, company=self.company)

		frappe.db.set_value("Employee", self.report, "reports_to", self.manager)
		frappe.db.set_value("Employee", self.grand, "reports_to", self.report)

		# isolate the code-level restriction from any User Permission rows
		users = [self.manager_user, self.report_user, self.grand_user, self.other_user]
		frappe.db.delete("User Permission", {"user": ("in", users)})
		for user in users:
			frappe.clear_cache(user=user)
		self.addCleanup(frappe.set_user, "Administrator")

	def _query(self, txt="", page_len=20):
		from hrms.hr.doctype.appraisal.appraisal import appraisal_employee_query

		return {row[0] for row in appraisal_employee_query("Employee", txt, "name", 0, page_len, {})}

	def test_manager_gets_own_and_chain(self):
		frappe.set_user(self.manager_user)
		self.assertEqual(self._query(), {self.manager, self.report, self.grand})

	def test_leaf_employee_gets_only_self(self):
		frappe.set_user(self.grand_user)
		self.assertEqual(self._query(), {self.grand})

	def test_search_text_filters_results(self):
		frappe.set_user(self.manager_user)
		emp_name = frappe.db.get_value("Employee", self.report, "employee_name")
		self.assertEqual(self._query(emp_name), {self.report})

	def test_unrestricted_user_sees_beyond_chain(self):
		frappe.set_user("Administrator")
		self.assertEqual(self._query("appraisal_query_"), {self.manager, self.report, self.grand, self.other})

	def test_particulars_denied_outside_chain(self):
		from hrms.hr.doctype.appraisal.appraisal import get_employee_particulars_for_appraisal

		frappe.set_user(self.manager_user)
		self.assertRaises(frappe.PermissionError, get_employee_particulars_for_appraisal, self.other)

	def test_particulars_returned_for_subordinate(self):
		from hrms.hr.doctype.appraisal.appraisal import get_employee_particulars_for_appraisal

		frappe.set_user(self.manager_user)
		particulars = get_employee_particulars_for_appraisal(self.grand)
		self.assertEqual(
			particulars.employee_name, frappe.db.get_value("Employee", self.grand, "employee_name")
		)

	def test_particulars_rejects_non_string_employee(self):
		from hrms.hr.doctype.appraisal.appraisal import get_employee_particulars_for_appraisal

		frappe.set_user("Administrator")
		self.assertRaises(
			frappe.ValidationError, get_employee_particulars_for_appraisal, {"name": ("like", "%")}
		)
