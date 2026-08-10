"""HRMS-only User Permission scope helpers.

Used by `hrms.overrides.employee_hrms_scope.sync_hrms_only_user_permission` to decide
whether a User Permission row should be scoped and which doctypes it
applies to.

Source-of-truth precedence for the doctype list:
    1. HR Settings -> Scoped HRMS Doctypes (child table) if non-empty.
    2. Live HRMS Employee Self Service list (hrms.setup.get_user_types_data)
       if HRMS is importable.
    3. The static DEFAULT_HRMS_DOCTYPES list below — last-ditch fallback.

The pure helpers (`should_scope_to_hrms`, `merge_doctype_list`) are
unit-tested without Frappe; `get_scoped_doctypes` is the Frappe-bound
wrapper.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Always present in the scope — the Employee record itself is the anchor.
ANCHOR_DOCTYPE = "Employee"

# Last-ditch fallback when neither HR Settings nor HRMS module is available.
# Mirrors what hrms.setup.get_user_types_data() returns for the "Employee
# Self Service" user type as of HRMS v15, plus a few obvious additions.
DEFAULT_HRMS_DOCTYPES: list[str] = [
	"Employee",
	"Leave Application",
	"Leave Allocation",
	"Compensatory Leave Request",
	"Attendance",
	"Attendance Request",
	"Employee Checkin",
	"Shift Request",
	"Salary Slip",
	"Expense Claim",
	"Travel Request",
	"Employee Advance",
	"Loan",
	"Loan Application",
	"Goal",
	"Appraisal",
	"Training Result",
	"Performance Feedback",
	"Employee Grievance",
]


def should_scope_to_hrms(restrict_user_permission_to_hrms) -> bool:
	"""Return True when the Employee has 'Restrict User Permission to HRMS
	Module Only' ticked.

	The scope applies to every User Permission for the employee's user_id
	regardless of which mechanism originally created it (the Employee
	create_user_permission flow, the User Permissions Manager, default
	company hooks, etc.).
	"""
	return bool(restrict_user_permission_to_hrms)


# Approver-routed request doctypes take their row scope from
# hrms.overrides.approval_row_scope hooks, never from per-employee User
# Permissions: a UP (allow=Employee, for_value=<own employee>) scopes the
# APPROVER to their own records too, which 403s every approval for their
# team. Maps doctype -> approver field.
APPROVER_ROUTED_DOCTYPES: dict[str, str] = {
	"Leave Application": "leave_approver",
	"Expense Claim": "expense_approver",
	"Shift Request": "approver",
}

ACTION_SCOPED = "scoped"
ACTION_REVERT = "revert"
ACTION_NOOP = "noop"


def plan_user_permission_sync_action(
	restrict_flag,
	has_existing_perms: bool,
) -> str:
	"""Decide what the Employee.after_save handler should do.

	Inputs:
	    restrict_flag         — value of Employee.restrict_user_permission_to_hrms
	    has_existing_perms    — True if at least one User Permission row
	                            currently exists for this employee's user_id

	Returns one of:
	    "scoped"  — flag is on → upsert the Employee anchor UP for this
	                employee AND reshape every UP for the user to
	                apply_to_all_doctypes=0 + HRMS doctype scope. The
	                anchor is what actually restricts which Employee
	                records are visible — without it, the user can still
	                see siblings via other UPs (Company, Department,
	                etc.) that don't narrow by employee.
	    "revert"  — flag is off AND UPs exist → broaden each row back
	                to apply_to_all_doctypes=1
	    "noop"    — flag is off AND no UPs exist → nothing to do

	Extracted as a pure function so the branching can be unit-tested
	without touching Frappe.
	"""
	scope = should_scope_to_hrms(restrict_flag)
	if scope:
		return ACTION_SCOPED
	if has_existing_perms:
		return ACTION_REVERT
	return ACTION_NOOP


def merge_doctype_list(custom_rows, fallback) -> list[str]:
	"""Resolve which doctypes go into for_value_doctypes.

	Rules:
	  - If `custom_rows` is non-empty, use them as the base.
	  - Else use `fallback`.
	  - Always include ANCHOR_DOCTYPE (Employee).
	  - Return de-duplicated and alphabetically sorted.
	"""
	base = list(custom_rows) if custom_rows else list(fallback or [])
	if ANCHOR_DOCTYPE not in base:
		base.append(ANCHOR_DOCTYPE)
	# approver-routed doctypes are excluded regardless of source (HR Settings
	# rows included) — their row scope lives in approval_row_scope hooks
	return sorted({d for d in base if d and d not in APPROVER_ROUTED_DOCTYPES})


def _live_hrms_employee_self_service_doctypes() -> list[str]:
	"""Pull the live HRMS Employee Self Service doctype list.

	Returns the static DEFAULT_HRMS_DOCTYPES if hrms.setup isn't
	importable (defensive — should never happen now that we live inside
	hrms, but kept as a belt-and-braces fallback).
	"""
	try:
		from hrms.setup import get_user_types_data
	except ImportError:
		logger.warning("[user_permission_scope] hrms.setup not importable — using DEFAULT_HRMS_DOCTYPES")
		return list(DEFAULT_HRMS_DOCTYPES)

	try:
		data = get_user_types_data() or {}
		ess = data.get("Employee Self Service") or {}
		doctypes = list((ess.get("doctypes") or {}).keys())
		if not doctypes:
			return list(DEFAULT_HRMS_DOCTYPES)
		return doctypes
	except Exception as exc:
		logger.warning(
			"[user_permission_scope] hrms.setup.get_user_types_data() failed: %s",
			exc,
		)
		return list(DEFAULT_HRMS_DOCTYPES)


def get_scoped_doctypes() -> list[str]:
	"""Frappe-bound: resolve the final doctype list for the User Permission scope.

	Checks HR Settings first; falls back to the live HRMS list, then to the
	hardcoded DEFAULT_HRMS_DOCTYPES.
	"""
	import frappe

	rows = frappe.get_all(
		"Scoped HRMS Doctype",
		filters={"parent": "HR Settings", "parenttype": "HR Settings"},
		pluck="doctype_name",
	)
	if rows:
		merged = merge_doctype_list(rows, [])
		logger.info("[user_permission_scope] using %d doctype(s) from HR Settings", len(merged))
		return merged

	fallback = _live_hrms_employee_self_service_doctypes()
	merged = merge_doctype_list(None, fallback)
	logger.info(
		"[user_permission_scope] HR Settings empty — using %d doctype(s) from fallback",
		len(merged),
	)
	return merged
