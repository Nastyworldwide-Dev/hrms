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

from hrms.api.approval import DECIDE_THEN_SUBMIT

logger = logging.getLogger(__name__)

#: The request types the Requests panel LISTS (frontend/src/data/requestLists.js REQUEST_LISTS). The chips
#: count what the rows under them show, so a type the app has no list or screen for is not counted:
#: Compensatory Leave Request has neither, and counting it made "All" read higher than the rows a person
#: could open (review of 55b190300, 6 Oct 2026). Add a type here only together with its list.
LISTED_TYPES = (
	"Leave Application",
	"Expense Claim",
	"Shift Request",
	"Attendance Request",
	"OT Request",
	"Replacement Leave Claim",
)

#: Each listed type's decision field, read from approval.DECIDE_THEN_SUBMIT (the one table of decision
#: fields): only the LIST of types is kept here, never a second copy of the fields.
DECISION_FIELD = {doctype: DECIDE_THEN_SUBMIT[doctype][0] for doctype in LISTED_TYPES}


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
		try:
			rows = frappe.get_all(
				doctype,
				filters={"employee": employee},
				# Frappe 16 refuses SQL functions written as strings in fields.
				fields=["docstatus", field, {"COUNT": "*", "as": "n"}],
				group_by=f"docstatus, {field}",
			)
		except Exception:
			# One type a site lacks (missing app, unmigrated table) must not
			# blank every chip (review of the P0-8 counts). Logged by name so a
			# short count is never mistaken for a true one.
			logger.exception("[request_counts] %s failed; skipped", doctype)
			continue
		for row in rows:
			bucket = _bucket(int(row.get("docstatus") or 0), row.get(field))
			if not bucket:
				continue
			counts[bucket] += int(row.get("n") or 0)
			counts["all"] += int(row.get("n") or 0)
	logger.info("[request_counts] employee=%s counts=%s", employee, counts)
	return counts
