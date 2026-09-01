# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Attendance allowance configuration and monthly processing.

An Attendance Allowance Type is HR-managed configuration: a daily amount
booked against a Salary Component for every eligible attendance day. The
monthly scheduler job reads submitted Attendance rows (the same records the
auto-attendance flow derives from Employee Checkins) and books ONE Additional
Salary per (employee, allowance type, month) — the Additional Salary carries
a reference back to the allowance type, which is also the idempotency key:
re-running the job can never book the same month twice.
"""

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, get_first_day, getdate

logger = logging.getLogger(__name__)

ALLOWANCE_REF_DOCTYPE = "Attendance Allowance Type"


class AttendanceAllowanceType(Document):
	def validate(self):
		if flt(self.allowance_amount) <= 0:
			frappe.throw(_("Allowance Amount Per Day must be greater than zero"))
		if flt(self.minimum_working_hours) < 0:
			frappe.throw(_("Minimum Working Hours cannot be negative"))


def eligible_allowance_days(rows, rule) -> float:
	"""Count eligible allowance days from attendance rows, per one rule.

	Pure function so the policy is testable without a bench. ``rows`` are
	dicts with status / late_entry / early_exit / working_hours; ``rule`` is
	a dict-like with the Attendance Allowance Type flags.
	"""
	days = 0.0
	minimum_hours = flt(rule.get("minimum_working_hours"))
	for row in rows:
		status = row.get("status")
		if status == "Present":
			credit = 1.0
		elif status == "Work From Home" and rule.get("include_work_from_home"):
			credit = 1.0
		elif status == "Half Day" and rule.get("include_half_day"):
			credit = 0.5
		else:
			continue
		if rule.get("exclude_late_entry") and row.get("late_entry"):
			continue
		if rule.get("exclude_early_exit") and row.get("early_exit"):
			continue
		if minimum_hours and flt(row.get("working_hours")) < minimum_hours:
			continue
		days += credit
	return days


def eligible_statuses(rule) -> list[str]:
	statuses = ["Present"]
	if rule.get("include_work_from_home"):
		statuses.append("Work From Home")
	if rule.get("include_half_day"):
		statuses.append("Half Day")
	return statuses


def process_attendance_allowances(start_date=None, end_date=None) -> dict:
	"""Monthly scheduler job — book allowances for the previous calendar month.

	Deterministic and idempotent: one Additional Salary per (employee,
	allowance type, period end), keyed by ref_doctype/ref_docname +
	payroll_date. A failure for one employee never poisons the rest.
	"""
	if not (start_date and end_date):
		end_date = add_days(get_first_day(getdate()), -1)
		start_date = get_first_day(end_date)
	start_date, end_date = getdate(start_date), getdate(end_date)

	rules = frappe.get_all(
		"Attendance Allowance Type",
		filters={"disabled": 0},
		fields=[
			"name",
			"company",
			"salary_component",
			"allowance_amount",
			"include_half_day",
			"include_work_from_home",
			"exclude_late_entry",
			"exclude_early_exit",
			"minimum_working_hours",
		],
	)
	logger.info(
		"[attendance_allowance] processing %s -> %s, %d enabled type(s)", start_date, end_date, len(rules)
	)

	counters = {"created": 0, "skipped": 0, "error": 0}
	for rule in rules:
		filters = {
			"docstatus": 1,
			"attendance_date": ["between", [start_date, end_date]],
			"status": ["in", eligible_statuses(rule)],
		}
		if rule.get("company"):
			filters["company"] = rule["company"]
		attendance_rows = frappe.get_all(
			"Attendance",
			filters=filters,
			fields=["employee", "company", "status", "late_entry", "early_exit", "working_hours"],
		)

		by_employee = {}
		for row in attendance_rows:
			by_employee.setdefault((row["employee"], row["company"]), []).append(row)

		for (employee, company), rows in by_employee.items():
			frappe.db.savepoint("attendance_allowance")
			try:
				if frappe.db.exists(
					"Additional Salary",
					{
						"employee": employee,
						"ref_doctype": ALLOWANCE_REF_DOCTYPE,
						"ref_docname": rule["name"],
						"payroll_date": end_date,
						"docstatus": ["<", 2],
					},
				):
					counters["skipped"] += 1
					continue
				days = eligible_allowance_days(rows, rule)
				amount = flt(days * flt(rule["allowance_amount"]), 2)
				if amount <= 0:
					counters["skipped"] += 1
					continue
				create_additional_salary(employee, company, rule, amount, end_date)
				counters["created"] += 1
				logger.info(
					"[attendance_allowance] booked %s for %s: %s day(s) x %s = %s",
					rule["name"],
					employee,
					days,
					rule["allowance_amount"],
					amount,
				)
			except Exception:
				frappe.db.rollback(save_point="attendance_allowance")
				counters["error"] += 1
				logger.exception(
					"[attendance_allowance] failed for employee=%s type=%s", employee, rule["name"]
				)
				frappe.log_error(
					title=f"Attendance allowance failed for {employee} ({rule['name']})",
					message=frappe.get_traceback(),
				)

	logger.info("[attendance_allowance] done: %s", counters)
	return counters


def create_additional_salary(employee, company, rule, amount, payroll_date):
	# Same booking recipe as Overtime Slip -> Additional Salary, so payroll
	# ingests allowances through the exact pipeline it already knows.
	additional_salary = frappe.get_doc(
		{
			"doctype": "Additional Salary",
			"company": company,
			"employee": employee,
			"salary_component": rule["salary_component"],
			"amount": amount,
			"payroll_date": payroll_date,
			"overwrite_salary_structure_amount": 0,
			"ref_doctype": ALLOWANCE_REF_DOCTYPE,
			"ref_docname": rule["name"],
		}
	)
	additional_salary.flags.ignore_permissions = True
	additional_salary.submit()
