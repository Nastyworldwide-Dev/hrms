# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import SubQuery
from frappe.utils import flt

logger = logging.getLogger(__name__)


def get_department_template(department):
	"""Find appraisal template by walking up the department tree"""
	if not department:
		return None

	dept = frappe.db.get_value("Department", department, ["lft", "rgt"], as_dict=True)
	if not dept:
		return None

	# Get all ancestor departments (including self), ordered nearest-first
	ancestors = frappe.get_all(
		"Department",
		filters={
			"lft": ("<=", dept.lft),
			"rgt": (">=", dept.rgt),
			"disabled": 0,
		},
		order_by="lft desc",
		pluck="name",
	)

	# Find first ancestor that has an appraisal template
	for ancestor in ancestors:
		template = frappe.db.get_value(
			"Appraisal Template",
			{"department": ancestor},
			"name",
		)
		if template:
			return template

	return None


DEFAULT_SCORE_CONVERSION = [
	(4.5, 0.80, "Exceptional"),
	(3.5, 0.75, "Strong"),
	(2.5, 0.71, "Meets Expectation"),
	(1.5, 0.60, "Needs Improvement"),
	(1.0, 0.50, "Unsatisfactory"),
]


class AppraisalCycle(Document):
	def onload(self):
		self.set_onload("appraisals_created", self.check_if_appraisals_exist())

	def before_insert(self):
		if not self.score_conversion_table:
			for min_score, conversion_pct, label in DEFAULT_SCORE_CONVERSION:
				self.append(
					"score_conversion_table",
					{
						"min_score": min_score,
						"conversion_pct": conversion_pct,
						"label": label,
					},
				)

	def validate(self):
		self.validate_from_to_dates("start_date", "end_date")
		self.validate_a1_a2_weights()
		self.validate_score_conversion_table()

	def validate_score_conversion_table(self):
		if not self.score_conversion_table:
			return

		# Ensure rows sorted descending by min_score
		prev_score = None
		for row in self.score_conversion_table:
			if prev_score is not None and flt(row.min_score) >= flt(prev_score):
				frappe.throw(
					_("Score Conversion rows must be ordered from highest to lowest min_score"),
					title=_("Invalid Score Conversion Table"),
				)
			prev_score = row.min_score

		# Lock the table once appraisals exist — but only on a REAL edit.
		# has_value_changed() reports a child table as changed on every save
		# (row `modified` stamps differ), so relying on it made the guard fire
		# for any save at all: setting status, or completing the cycle, became
		# impossible for every cycle that had appraisals. Compare the row values
		# instead, which is what "the table changed" actually means.
		if not self.is_new() and self._conversion_table_changed():
			if self.check_if_appraisals_exist():
				frappe.throw(
					_("Score Conversion Table cannot be changed as appraisals already exist for this cycle"),
					title=_("Not Allowed"),
				)

	def validate_a1_a2_weights(self):
		from frappe.utils import cint

		a1 = cint(self.a1_weight_pct) or 70
		if a1 < 50 or a1 > 80:
			frappe.throw(
				_("A1 Weight must be between 50 and 80. Currently, it is {0}").format(a1),
				title=_("Invalid A1 Weight"),
			)
		self.a2_weight_pct = 80 - a1

	@staticmethod
	def _conversion_row_signature(rows):
		"""Value-only fingerprint of the score conversion table."""
		from frappe.utils import flt

		return [
			(flt(row.min_score), flt(row.conversion_pct), (row.get("label") or "").strip())
			for row in rows or []
		]

	def _conversion_table_changed(self) -> bool:
		"""True only when the conversion ROWS differ from what is stored."""
		before = self.get_doc_before_save()
		if not before:
			return False
		changed = self._conversion_row_signature(before.get("score_conversion_table")) != (
			self._conversion_row_signature(self.score_conversion_table)
		)
		if changed:
			logger.info("[appraisal_cycle] score conversion table edited on %s", self.name)
		return changed

	def check_if_appraisals_exist(self):
		return frappe.db.exists(
			"Appraisal",
			{"appraisal_cycle": self.name, "docstatus": ["!=", 2]},
		)

	@frappe.whitelist()
	def set_employees(self):
		"""Pull employees in appraisee list based on selected filters"""
		self.check_permission("write")
		employees = self.get_employees_for_appraisal()
		designation_templates = self.get_appraisal_template_map()

		if employees:
			self.set("appraisees", [])
			template_missing = False

			for data in employees:
				# Priority: department tree → designation → None
				template = get_department_template(data.department) or designation_templates.get(
					data.designation
				)

				if not template:
					template_missing = True

				self.append(
					"appraisees",
					{
						"employee": data.name,
						"employee_name": data.employee_name,
						"branch": data.branch,
						"designation": data.designation,
						"department": data.department,
						"appraisal_template": template,
					},
				)

			if template_missing:
				self.show_missing_template_message()
		else:
			self.set("appraisees", [])
			frappe.msgprint(_("No employees found for the selected criteria"))

		return self

	def get_employees_for_appraisal(self):
		filters = {
			"status": "Active",
			"company": self.company,
		}
		if self.department:
			filters["department"] = self.department
		if self.branch:
			filters["branch"] = self.branch
		if self.designation:
			filters["designation"] = self.designation

		employees = frappe.db.get_all(
			"Employee",
			filters=filters,
			fields=[
				"name",
				"employee_name",
				"branch",
				"designation",
				"department",
			],
		)

		return employees

	def get_appraisal_template_map(self):
		designations = frappe.get_all("Designation", fields=["name", "appraisal_template"])
		appraisal_templates = frappe._dict()

		for entry in designations:
			appraisal_templates[entry.name] = entry.appraisal_template

		return appraisal_templates

	@frappe.whitelist()
	def create_appraisals(self):
		self.check_permission("write")
		if not self.appraisees:
			frappe.throw(
				_("Please select employees to create appraisals for"), title=_("No Employees Selected")
			)

		if not all(appraisee.appraisal_template for appraisee in self.appraisees):
			self.show_missing_template_message(raise_exception=True)

		if len(self.appraisees) > 30:
			frappe.enqueue(
				create_appraisals_for_cycle,
				queue="long",
				timeout=600,
				appraisal_cycle=self,
			)
			frappe.msgprint(
				_("Appraisal creation is queued. It may take a few minutes."),
				alert=True,
				indicator="blue",
			)
		else:
			create_appraisals_for_cycle(self, publish_progress=True)
			# since this method is called via frm.call this doc needs to be updated manually
			self.reload()

	def show_missing_template_message(self, raise_exception=False):
		msg = _("Appraisal Template not found for some employees.")
		msg += "<br><br>"
		msg += _(
			"Please set the Appraisal Template for the relevant {0} or {1}, or select the template in the Employees table below."
		).format(
			f"""<a href='{frappe.utils.get_url_to_list("Department")}'>Departments</a>""",
			f"""<a href='{frappe.utils.get_url_to_list("Designation")}'>Designations</a>""",
		)

		frappe.msgprint(
			msg, title=_("Appraisal Template Missing"), indicator="yellow", raise_exception=raise_exception
		)

	@frappe.whitelist()
	def complete_cycle(self):
		self.check_permission("write")

		draft_appraisals = frappe.db.count("Appraisal", {"appraisal_cycle": self.name, "docstatus": 0})

		if draft_appraisals:
			link = frappe.utils.get_url_to_list("Appraisal") + f"?status=Draft&appraisal_cycle={self.name}"
			link = f"""<a href="{link}">documents</a>"""

			msg = _("{0} Appraisal(s) are not submitted yet").format(frappe.bold(draft_appraisals))
			msg += "<br><br>"
			msg += _("Please submit the {0} before marking the cycle as Completed").format(link)
			frappe.throw(msg, title=_("Unsubmitted Appraisals"))

		self.status = "Completed"
		self.save()


def create_appraisals_for_cycle(appraisal_cycle: AppraisalCycle, publish_progress: bool = False):
	"""
	Creates appraisals for employees in the appraisee list of appraisal cycle,
	if not already created
	"""
	count = 0

	for employee in appraisal_cycle.appraisees:
		try:
			appraisal = frappe.get_doc(
				{
					"doctype": "Appraisal",
					"company": appraisal_cycle.company,
					"appraisal_template": employee.appraisal_template,
					"employee": employee.employee,
					"appraisal_cycle": appraisal_cycle.name,
				}
			)

			appraisal.set_kras_and_rating_criteria()
			appraisal.insert()

			if publish_progress:
				count += 1
				frappe.publish_progress(
					count * 100 / len(appraisal_cycle.appraisees), title=_("Creating Appraisals") + "..."
				)
		except frappe.DuplicateEntryError:
			# already exists
			pass


def validate_active_appraisal_cycle(appraisal_cycle: str) -> None:
	if frappe.db.get_value("Appraisal Cycle", appraisal_cycle, "status") == "Completed":
		msg = _("Cannot create or change transactions against an Appraisal Cycle with status {0}.").format(
			frappe.bold(_("Completed"))
		)
		msg += "<br><br>"
		msg += _("Set the status to {0} if required.").format(frappe.bold(_("In Progress")))

		frappe.throw(msg, title=_("Not Allowed"))


@frappe.whitelist()
def get_appraisal_cycle_summary(cycle_name: str) -> dict | None:
	frappe.has_permission("Appraisal Cycle", "read", cycle_name, throw=True)
	# cycle-wide stats are for HR/system roles; scoped users get no summary
	# (deferred import — appraisal.py imports from this module)
	from hrms.hr.doctype.appraisal.appraisal import get_allowed_appraisal_employees

	if get_allowed_appraisal_employees() is not None:
		logger.debug("[appraisal_cycle] summary hidden for scoped user=%s", frappe.session.user)
		return None

	summary = frappe._dict()

	summary["appraisees"] = frappe.db.count(
		"Appraisal", {"appraisal_cycle": cycle_name, "docstatus": ("!=", 2)}
	)
	summary["self_appraisal_pending"] = frappe.db.count(
		"Appraisal", {"appraisal_cycle": cycle_name, "docstatus": 0, "self_score": 0}
	)
	summary["goals_missing"] = get_employees_without_goals(cycle_name)
	summary["feedback_missing"] = get_employees_without_feedback(cycle_name)

	return summary


def get_employees_without_goals(cycle_name: str) -> int:
	Goal = frappe.qb.DocType("Goal")
	Appraisal = frappe.qb.DocType("Appraisal")
	count = Count("*").as_("count")

	filtered_records = SubQuery(
		frappe.qb.from_(Goal)
		.select(Goal.employee)
		.distinct()
		.where((Goal.appraisal_cycle == cycle_name) & (Goal.status != "Archived"))
	)

	goals_missing = (
		frappe.qb.from_(Appraisal)
		.select(count)
		.where(
			(Appraisal.appraisal_cycle == cycle_name)
			& (Appraisal.docstatus != 2)
			& (Appraisal.employee.notin(filtered_records))
		)
	).run(as_dict=True)

	return goals_missing[0].count


@frappe.whitelist()
def get_employees_without_feedback(cycle_name: str | None = None) -> int:
	Feedback = frappe.qb.DocType("Employee Performance Feedback")
	Appraisal = frappe.qb.DocType("Appraisal")
	count = Count("*").as_("count")
	if not cycle_name:
		cycle_name = frappe.get_value(
			"Appraisal Cycle", {"status": "In Progress"}, order_by="start_date desc"
		)

	frappe.has_permission("Appraisal Cycle", "read", cycle_name, throw=True)

	filtered_records = SubQuery(
		frappe.qb.from_(Feedback)
		.select(Feedback.employee)
		.distinct()
		.where((Feedback.appraisal_cycle == cycle_name) & (Feedback.docstatus == 1))
	)

	feedback_missing = (
		frappe.qb.from_(Appraisal)
		.select(count)
		.where(
			(Appraisal.appraisal_cycle == cycle_name)
			& (Appraisal.docstatus != 2)
			& (Appraisal.employee.notin(filtered_records))
		)
	).run(as_dict=True)

	return feedback_missing[0].count
