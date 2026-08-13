"""Take the Employee / Employee Self Service roles off org-wide Script Reports.

A Script Report runs its own SQL. Frappe gates it on the report's roles plus a
doctype-level `has_permission(ref_doctype, "report")` — neither of which is a
ROW check, and `permission_query_conditions` never runs. So a report shipping
the Employee role let any member of staff read the whole organisation's data:
`Shift Attendance` returned every employee's punches, `Employee Analytics` and
`Employee Birthday` every employee's record (dates of birth included),
`Employee Advance Summary` every advance.

This is the same finding, and the same fix, the leave-balance reports already
got: "the report reads the ledger directly, bypassing row scope".

Report roles live in `Has Role` rows created when the report is first
installed, so editing the shipped JSON only helps a fresh site. This patch
removes the rows on existing sites. Idempotent — safe to re-run.

Three reports are deliberately NOT in the list, because they scope their own
rows in code and therefore keep staff access:

  * `Appraisal Overview`  — own employee + manual shares (appraisal_overview)
  * `Shift Attendance`    — own attendance      (hrms.utils.report_scope)
  * `Employee Advance Summary` — own advances   (hrms.utils.report_scope)

Every other entry is an organisation-wide HR operational report with no
self-service reading, so HR-only is its final classification, not a holding
position. The four Salary Slip reports stay HR-only for a second reason:
`patches/v15_99_0/staff_perm_lockdown` removed the staff role from Salary Slip
itself, so a self-scoped variant could not read its own ref doctype without
undoing that lockdown.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

STAFF_ROLES = ("Employee", "Employee Self Service")

#: Reports whose SQL has no row scope of its own. Kept in sync with the shipped
#: JSONs by hrms/tests/test_report_role_integrity.py.
ORG_WIDE_REPORTS = (
	"Daily Work Summary Replies",
	"Employee Analytics",
	"Employee Birthday",
	"Employee CTC Break-up",
	"Income Tax Computation",
	"Income Tax Deductions",
	"Leave Ledger",
	"Project Profitability",
	"Salary Payments Based On Payment Mode",
)


def execute():
	logger.info("[restrict_staff_script_reports] start")
	stripped = 0

	for report in ORG_WIDE_REPORTS:
		if not frappe.db.exists("Report", report):
			logger.info("[restrict_staff_script_reports] %s not installed — skipped", report)
			continue

		filters = {"parent": report, "parenttype": "Report", "role": ("in", STAFF_ROLES)}
		roles = frappe.get_all("Has Role", filters=filters, pluck="role")
		if not roles:
			continue

		frappe.db.delete("Has Role", filters)
		frappe.clear_document_cache("Report", report)
		stripped += len(roles)
		logger.info("[restrict_staff_script_reports] %s: removed %s", report, sorted(roles))

	logger.info("[restrict_staff_script_reports] done, %d role row(s) removed", stripped)
