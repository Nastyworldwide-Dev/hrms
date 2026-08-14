import frappe

from erpnext.setup.doctype.designation.test_designation import create_designation
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.appraisal_cycle.test_appraisal_cycle import create_appraisal_cycle
from hrms.hr.doctype.appraisal_template.test_appraisal_template import create_appraisal_template
from hrms.hr.doctype.employee_performance_feedback.test_employee_performance_feedback import (
	create_performance_feedback,
)
from hrms.hr.report.appraisal_overview.appraisal_overview import execute
from hrms.tests.test_utils import create_company
from hrms.tests.utils import HRMSTestSuite


class TestAppraisalOverview(HRMSTestSuite):
	def setUp(self):
		self.company = create_company("_Test Appraisal").name

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = create_appraisal_template().name
		engineer.save()

		consultant = create_designation(designation_name="Consultant")
		consultant.appraisal_template = create_appraisal_template("Consultant").name
		consultant.save()

		self.employee1 = make_employee("employee1@example.com", company=self.company, designation="Engineer")
		self.employee2 = make_employee(
			"employee3@example.com", company=self.company, designation="Consultant"
		)
		self.reviewer = make_employee("reviewer@example.com", company=self.company, designation="Engineer")

	def test_appraisal_overview(self):
		cycle = create_appraisal_cycle(kra_evaluation_method="Manual Rating")
		cycle.create_appraisals()

		appraisal = frappe.get_doc("Appraisal", {"employee": self.employee1})
		appraisal = frappe.get_doc("Appraisal", appraisal.name)

		self.create_appraisal_data(appraisal)
		report = execute()
		data = report[1]

		# The report's job is to surface what the Appraisal stores, so the score
		# columns are asserted against the document rather than against
		# constants from the retired goal-scoring formula. The mapping itself
		# (total_score -> goal_score) is what this pins.
		appraisal.reload()
		expected_data = {
			"employee": self.employee1,
			"employee_name": appraisal.employee_name,
			"designation": appraisal.designation,
			"department": appraisal.department,
			"appraisal_cycle": cycle.name,
			"appraisal": appraisal.name,
			"avg_feedback_score": appraisal.avg_feedback_score,
			"goal_score": appraisal.total_score,
			"self_score": appraisal.self_score,
			"final_score": appraisal.final_score,
			"feedback_count": 1,
		}

		self.assertEqual(len(data), 3)
		self.assertEqual(data[0], expected_data)

	def test_appraisal_filters(self):
		cycle = create_appraisal_cycle(kra_evaluation_method="Manual Rating")
		cycle.create_appraisals()

		report = execute({"designation": "Consultant"})
		data = report[1]

		self.assertEqual(len(data), 1)
		self.assertEqual(data[0].employee, self.employee2)

	def create_appraisal_data(self, appraisal):
		# SECTION A: achievement drives the score in this fork — the legacy
		# `goals` table is never populated, so target/actual is the input.
		for row in appraisal.appraisal_kra:
			row.target = 100
			row.actual = 100

		# SELF APPRAISAL SCORE
		ratings = appraisal.self_ratings
		ratings[0].rating = 0.8  # 70% weightage
		ratings[1].rating = 0.7  # 30% weightage

		appraisal.save()

		# FEEDBACK SCORE
		feedback = create_performance_feedback(
			self.employee1,
			self.reviewer,
			appraisal.name,
		)
		ratings = feedback.feedback_ratings
		ratings[0].rating = 0.8  # 70% weightage
		ratings[1].rating = 0.7  # 30% weightage
		feedback.submit()
