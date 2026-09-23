"""How many of MY requests sit under each filter chip on the Requests panel.

The chips used to count only the rows already loaded — the newest ten of
each type — so an employee with 20 rejected requests could see "Not
approved" empty (audit P0-8). These counts cover every request, and apply
the same rule the chip on each row reads (frontend/src/utils/requestStatus.js):

  * cancelled (docstatus 2) is under no decision chip;
  * a draft (docstatus 0) is waiting;
  * a submitted request is approved or not approved by its decision field.

Session-scoped: the employee is the caller, never a parameter.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

#: The decision field of each request type the panel lists. Same pairs as
#: approval.DECIDE_THEN_SUBMIT, minus the pending value the chips don't need.
DECISION_FIELD = {
	"Leave Application": "status",
	"Expense Claim": "approval_status",
	"Shift Request": "status",
	"Attendance Request": "status",
	"OT Request": "status",
	"Replacement Leave Claim": "status",
}


def get_current_employee():
	from hrms.api import get_current_employee as current

	return current()


def _bucket(docstatus: int, decision: str | None) -> str | None:
	if docstatus == 2:
		return None
	if docstatus == 0:
		return "waiting"
	if decision == "Rejected":
		return "rejected"
	return "approved"


@frappe.whitelist(methods=["GET", "POST"])
def get_my_request_counts() -> dict:
	employee = get_current_employee()
	counts = {"all": 0, "waiting": 0, "approved": 0, "rejected": 0}
	for doctype, field in DECISION_FIELD.items():
		rows = frappe.get_all(
			doctype,
			filters={"employee": employee},
			# Frappe 16 refuses SQL functions written as strings in fields.
			fields=["docstatus", field, {"COUNT": "*", "as": "n"}],
			group_by=f"docstatus, {field}",
		)
		for row in rows:
			bucket = _bucket(int(row.get("docstatus") or 0), row.get(field))
			if not bucket:
				continue
			counts[bucket] += int(row.get("n") or 0)
			counts["all"] += int(row.get("n") or 0)
	logger.info("[request_counts] employee=%s counts=%s", employee, counts)
	return counts
