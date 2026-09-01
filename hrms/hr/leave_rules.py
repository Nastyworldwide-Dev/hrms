"""Grade-driven automatic Leave Policy Assignment.

Employee Grade holds `default_leave_policy`. The daily
`auto_assign_leave_policies` job creates and submits a Leave Policy
Assignment for every active employee whose grade has a policy and who has
no assignment covering today. Submitting grants the allocations, and the
existing years-of-service entitlement slabs on each Leave Type compute
the actual leave days (see LeavePolicyAssignment.grant_leave_alloc_for_employee).

Assignments are based on the company's active Leave Period when one
covers today, else on the calendar year.
"""

import logging

import frappe
from frappe.utils import get_year_ending, get_year_start, nowdate

from hrms.hr.utils import get_leave_period

logger = logging.getLogger(__name__)


def auto_assign_leave_policies():
	"""Daily scheduler job."""
	today = nowdate()

	grade_policies = {
		grade.name: grade.default_leave_policy
		for grade in frappe.get_all("Employee Grade", fields=["name", "default_leave_policy"])
		if grade.default_leave_policy
	}
	if not grade_policies:
		logger.info("[leave_rules] no grade has a default leave policy — nothing to do")
		return {}

	employees = frappe.get_all(
		"Employee",
		filters={
			"status": "Active",
			"grade": ["in", list(grade_policies)],
			# Mirrored employees are owned by their source instance
			# (single-writer, hrms/sync/write_block.py). A hub-created,
			# unstamped Leave Policy Assignment for one would grant leave the
			# source also grants — exclude them here.
			"synced_from_instance": ["is", "not set"],
		},
		fields=["name", "company", "grade"],
	)

	counters = {"created": 0, "skipped": 0, "error": 0}
	for index, employee in enumerate(employees, start=1):
		if index % 50 == 0 and not frappe.flags.in_test:
			frappe.db.commit()  # nosemgrep: keep progress on long employee lists
		# savepoint per employee: one bad record must not poison the
		# transaction for everyone after it
		frappe.db.savepoint("leave_rule_employee")
		try:
			if has_assignment_covering(employee.name, today):
				counters["skipped"] += 1
				continue
			create_policy_assignment(employee, grade_policies[employee.grade], today)
			counters["created"] += 1
		except Exception:
			frappe.db.rollback(save_point="leave_rule_employee")
			counters["error"] += 1
			logger.exception("[leave_rules] assignment failed for %s", employee.name)
			frappe.log_error(
				title=f"Auto leave policy assignment failed for {employee.name}",
				message=frappe.get_traceback(),
			)

	logger.info("[leave_rules] sync done — %d employees: %s", len(employees), counters)
	return counters


def has_assignment_covering(employee: str, date) -> bool:
	"""True when any non-cancelled Leave Policy Assignment covers the date
	(drafts count, so the job never races HR mid-assignment)."""
	return bool(
		frappe.db.exists(
			"Leave Policy Assignment",
			{
				"employee": employee,
				"docstatus": ["<", 2],
				"effective_from": ["<=", date],
				"effective_to": [">=", date],
			},
		)
	)


def create_policy_assignment(employee, leave_policy: str, today):
	leave_periods = get_leave_period(today, today, employee.company)

	assignment = {
		"doctype": "Leave Policy Assignment",
		"employee": employee.name,
		"leave_policy": leave_policy,
	}
	if leave_periods:
		assignment.update({"assignment_based_on": "Leave Period", "leave_period": leave_periods[0].name})
	else:
		assignment.update(
			{
				"assignment_based_on": "",
				"effective_from": get_year_start(today),
				"effective_to": get_year_ending(today),
			}
		)

	doc = frappe.get_doc(assignment)
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	logger.info(
		"[leave_rules] assigned %s to %s (%s -> %s)",
		leave_policy,
		employee.name,
		doc.effective_from,
		doc.effective_to,
	)
	return doc
