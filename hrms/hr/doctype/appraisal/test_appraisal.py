# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from erpnext.setup.doctype.designation.test_designation import create_designation
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.appraisal_cycle.appraisal_cycle import get_appraisal_cycle_summary
from hrms.hr.doctype.appraisal_cycle.test_appraisal_cycle import create_appraisal_cycle
from hrms.hr.doctype.appraisal_template.test_appraisal_template import create_appraisal_template
from hrms.hr.doctype.employee_performance_feedback.test_employee_performance_feedback import (
	create_performance_feedback,
)
from hrms.hr.doctype.goal.test_goal import create_goal
from hrms.tests.test_utils import create_company
from hrms.tests.utils import HRMSTestSuite


class TestAppraisal(HRMSTestSuite):
	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")
		frappe.db.delete("Employee Performance Feedback")

		self.company = create_company("_Test Appraisal").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()
		self.employee1 = make_employee(
			"test_appraisal1@example.com", company=self.company, designation="Engineer"
		)

	def test_validate_duplicate(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.get_doc(
			{
				"doctype": "Appraisal",
				"employee": self.employee1,
				"appraisal_cycle": cycle.name,
			}
		)
		appraisal.set_appraisal_template()

		self.assertRaises(frappe.DuplicateEntryError, appraisal.insert)

	# ------------------------------------------------------------------
	# Achievement scoring (this fork's model).
	#
	# Goal-based scoring is retired: `Appraisal.set_goal_score` is an explicit
	# legacy no-op in this branch AND in the as-hr_kpi donor, so nothing writes
	# `goal_completion` / `goal_score` any more. Those columns survive only so
	# historical rows keep rendering, and `hrms/api/kpi.py` reads them as a
	# fallback behind `achievement`. The live contract is:
	#
	#     achievement    = actual / target * 100      (0 when target is 0)
	#     capped         = clamp(achievement, 0, 100) (no reward for overshoot)
	#     weighted_score = per_weightage * capped / 100
	#     weighted_avg   = weighted_sum / total_weightage * 5
	#     a1_score       = min(conversion / 0.80 * a1_weight, a1_weight)
	#     final_score    = pms_total_score
	#
	# Template goals are copied verbatim and still sum to 100 (Quality 30,
	# Development 70); the Section-A weight is applied at scoring time.
	# ------------------------------------------------------------------

	def make_appraisal(self, cycle):
		name = frappe.db.exists("Appraisal", {"appraisal_cycle": cycle.name, "employee": self.employee1})
		return frappe.get_doc("Appraisal", name)

	def score(self, cycle, pairs):
		"""Set (target, actual) on the KRA rows in order and save."""
		appraisal = self.make_appraisal(cycle)
		for row, (target, actual) in zip(appraisal.appraisal_kra, pairs, strict=False):
			row.target = target
			row.actual = actual
		appraisal.save()
		return appraisal

	def test_achievement_at_target_earns_full_weight(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(100, 100), (100, 100)])

		self.assertEqual(appraisal.appraisal_kra[0].achievement, 100)
		self.assertEqual(appraisal.appraisal_kra[1].achievement, 100)
		# weighted_score == per_weightage when achievement is 100%
		self.assertEqual(appraisal.appraisal_kra[0].weighted_score, 30.0)
		self.assertEqual(appraisal.appraisal_kra[1].weighted_score, 70.0)
		# the docstring's own worked example: full achievement -> full A1 weight
		self.assertEqual(appraisal.a1_score, 70.0)

	def test_achievement_below_target_scales_down(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(100, 100), (100, 80)])

		self.assertEqual(appraisal.appraisal_kra[1].achievement, 80)
		self.assertEqual(appraisal.appraisal_kra[0].weighted_score, 30.0)
		self.assertEqual(appraisal.appraisal_kra[1].weighted_score, 56.0)

	def test_overachievement_is_capped_at_target(self):
		"""Beating the target earns no bonus — the cap is what makes A1 bounded."""
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(100, 200), (100, 100)])

		self.assertEqual(appraisal.appraisal_kra[0].achievement, 200)
		# ...but the SCORE is capped at the 100% equivalent
		self.assertEqual(appraisal.appraisal_kra[0].weighted_score, 30.0)
		self.assertEqual(appraisal.a1_score, 70.0)

	def test_zero_target_scores_zero(self):
		"""A KRA with no target cannot be achieved — never a divide-by-zero."""
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(0, 50), (100, 100)])

		self.assertEqual(appraisal.appraisal_kra[0].achievement, 0)
		self.assertEqual(appraisal.appraisal_kra[0].weighted_score, 0.0)

	def test_missing_target_and_actual_score_zero(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(None, None), (None, None)])

		for row in appraisal.appraisal_kra:
			self.assertEqual(row.achievement, 0)
			self.assertEqual(row.weighted_score, 0.0)
		# a1 is NOT zero: a weighted average of 0 still lands on the lowest
		# configured band (0.50), so a1 = 0.50 / 0.80 * 70 = 43.75. The band
		# floor is deliberate — the table has no 0% row.
		self.assertEqual(appraisal.a1_score, 43.75)

	def test_negative_actual_floors_at_zero(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(100, -50), (100, 100)])

		# the ratio itself is reported honestly, the score floors at 0
		self.assertEqual(appraisal.appraisal_kra[0].weighted_score, 0.0)

	def test_decimal_achievement_rounds_to_two_places(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(3, 1), (100, 100)])

		# 1/3 -> 33.33%, and 30 * 33.33 / 100 = 10.0 (2dp)
		self.assertEqual(appraisal.appraisal_kra[0].achievement, 33.33)
		self.assertEqual(appraisal.appraisal_kra[0].weighted_score, 10.0)

	def test_final_score_is_the_pms_total(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(100, 100), (100, 100)])

		self.assertEqual(appraisal.final_score, appraisal.pms_total_score)
		self.assertEqual(appraisal.section_a_score, flt(appraisal.a1_score) + flt(appraisal.a2_score))

	def test_recalculates_when_inputs_change(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(100, 100), (100, 100)])
		self.assertEqual(appraisal.a1_score, 70.0)

		appraisal.appraisal_kra[1].actual = 0
		appraisal.save()
		self.assertLess(appraisal.a1_score, 70.0)

	def test_goal_scoring_is_retired(self):
		"""set_goal_score is an API-compatibility no-op, not a scorer.

		It must not write goal_completion / goal_score — those columns exist so
		historical rows keep rendering. It still recalculates the final score so
		callers such as Goal.on_update stay correct.
		"""
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		appraisal = self.score(cycle, [(100, 100), (100, 100)])

		appraisal.set_goal_score(update=True)
		appraisal.reload()

		for row in appraisal.appraisal_kra:
			self.assertEqual(flt(row.goal_completion), 0.0)
			self.assertEqual(flt(row.goal_score), 0.0)
		self.assertEqual(appraisal.final_score, appraisal.pms_total_score)

	def test_calculate_self_appraisal_score(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.db.exists("Appraisal", {"appraisal_cycle": cycle.name, "employee": self.employee1})
		appraisal = frappe.get_doc("Appraisal", appraisal)

		ratings = appraisal.self_ratings
		# 70% weightage
		ratings[0].rating = 0.8
		# 30% weightage
		ratings[1].rating = 0.7

		appraisal.save()
		self.assertEqual(appraisal.self_score, 3.85)

	def test_cycle_completion(self):
		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()
		# create_appraisals leaves this doc stale: the score conversion table was
		# populated on insert, so saving the in-memory copy looks like an edit to
		# it and trips the "cannot be changed as appraisals already exist" guard.
		# Reload rather than relax the guard — it is protecting real appraisals.
		cycle.reload()

		# unsubmitted appraisals
		self.assertRaises(frappe.ValidationError, cycle.complete_cycle)

		appraisal = frappe.db.exists("Appraisal", {"appraisal_cycle": cycle.name, "employee": self.employee1})
		appraisal = frappe.get_doc("Appraisal", appraisal)
		appraisal.submit()

		cycle.complete_cycle()
		appraisal = frappe.get_doc(
			{
				"doctype": "Appraisal",
				"employee": self.employee1,
				"appraisal_cycle": cycle.name,
				"appraisal_template": self.template.name,
			}
		)

		# transaction against a Completed cycle
		self.assertRaises(frappe.ValidationError, appraisal.insert)

	def test_cycle_summary(self):
		employee2 = make_employee("test_appraisal2@example.com", company=self.company, designation="Engineer")

		cycle = create_appraisal_cycle(designation="Engineer")
		cycle.create_appraisals()

		appraisal = frappe.db.exists("Appraisal", {"appraisal_cycle": cycle.name, "employee": self.employee1})
		appraisal = frappe.get_doc("Appraisal", appraisal)

		create_goal(self.employee1, "Quality", appraisal_cycle=cycle.name)
		feedback = create_performance_feedback(
			self.employee1,
			employee2,
			appraisal.name,
		)
		ratings = feedback.feedback_ratings
		ratings[0].rating = 0.8  # 70% weightage
		ratings[1].rating = 0.7  # 30% weightage
		feedback.submit()

		summary = get_appraisal_cycle_summary(cycle.name)

		expected_data = {
			"appraisees": 2,
			"self_appraisal_pending": 2,
			"goals_missing": 1,
			"feedback_missing": 1,
		}
		self.assertEqual(summary, expected_data)


class TestScoreConversionBands(FrappeTestCase):
	"""The band table converts a 1-5 weighted average into a Section-A factor.

	Boundaries are inclusive lower bounds, so a value sitting exactly on a
	threshold takes that band, and anything below the lowest takes the floor.
	"""

	def test_exact_band_boundaries(self):
		from hrms.hr.doctype.appraisal.appraisal import get_conversion_factor

		self.assertEqual(get_conversion_factor(4.5), 0.80)
		self.assertEqual(get_conversion_factor(3.5), 0.75)
		self.assertEqual(get_conversion_factor(2.5), 0.71)
		self.assertEqual(get_conversion_factor(1.5), 0.60)
		self.assertEqual(get_conversion_factor(1.0), 0.50)

	def test_values_between_bands_take_the_lower_band(self):
		from hrms.hr.doctype.appraisal.appraisal import get_conversion_factor

		self.assertEqual(get_conversion_factor(4.49), 0.75)
		self.assertEqual(get_conversion_factor(3.49), 0.71)
		self.assertEqual(get_conversion_factor(2.49), 0.60)

	def test_below_the_lowest_band_takes_the_floor(self):
		from hrms.hr.doctype.appraisal.appraisal import get_conversion_factor

		self.assertEqual(get_conversion_factor(0.9), 0.50)
		self.assertEqual(get_conversion_factor(0), 0.50)

	def test_configured_table_overrides_the_default(self):
		from hrms.hr.doctype.appraisal.appraisal import get_conversion_factor

		table = [
			frappe._dict(min_score=4.0, conversion_pct=0.90),
			frappe._dict(min_score=2.0, conversion_pct=0.55),
		]
		self.assertEqual(get_conversion_factor(4.0, table), 0.90)
		self.assertEqual(get_conversion_factor(3.9, table), 0.55)
		# below every configured row -> the lowest configured factor, not the default
		self.assertEqual(get_conversion_factor(0.5, table), 0.55)
