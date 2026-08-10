"""Staff lockdown (v15.99.0).

Sites that carry Custom DocPerm rows for a doctype ignore that doctype's JSON
permissions entirely, so hardening the JSONs alone does nothing on nasty-live
(942 custom rows). This patch aligns existing custom rows with the hardened
JSONs, enforces the Employee (erpnext-owned) matrix unconditionally,
permlevel-locks Employee pay/ID fields, and turns on the self-approval blocks.
Idempotent — safe to re-run.

Phases run GRANTS FIRST (HR permlevel-1 rows), revokes last, so a mid-patch
failure can never strand a site with staff stripped and HR not yet restored.

NOTE: the approver fence and these perms assume staff hold ONLY
Employee + Employee Self Service. Accounts also holding HR roles are exempt
from the fence by design — the rollout's role-hygiene sweep (Staff Role
Profile) is part of the lockdown, not optional.
"""

import logging

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

logger = logging.getLogger(__name__)

from hrms.hr.utils import HR_ROLES

ESS = "Employee Self Service"

# (doctype, role, permlevel, flags to zero) — applied only where custom rows exist
STRIP_FLAGS = [
	("Employee Checkin", "Employee", 0, ("write", "create", "delete")),
	("Employee", ESS, 0, ("write",)),
	("Leave Application", ESS, 0, ("delete",)),
	("Expense Claim", ESS, 0, ("delete",)),
	("Attendance Request", "Employee", 0, ("delete",)),
	("Attendance Request", ESS, 0, ("delete",)),
	("Compensatory Leave Request", "Employee", 0, ("delete",)),
	("Compensatory Leave Request", ESS, 0, ("delete",)),
	("Shift Request", "Employee", 0, ("delete",)),
	("Shift Request", ESS, 0, ("delete",)),
]

# level-0 rows staff must not have at all
DROP_ROWS = [
	("HR Settings", "Employee"),
	("HR Settings", ESS),
	("Salary Slip", "Employee"),
	("Salary Slip", ESS),
	("Salary Component", "Employee"),
	("Salary Component", ESS),
]

# doctypes whose permlevel-1 fields need HR read/write rows in custom perms
L1_HR_DOCTYPES = ("Leave Type", "Shift Type", "Employee", "Employee Checkin")

# staff must keep level-0 read here (names only — config sits at permlevel 1).
# Where custom rows exist the JSON's read row is inert, so restore it.
STAFF_READ_DOCTYPES = ("Leave Type", "Shift Type")

# Employee pay/ID fields hidden from the employee's own permlevel-0 view
EMPLOYEE_SENSITIVE_FIELDS = (
	"salary_mode",
	"salary_currency",
	"bank_name",
	"bank_ac_no",
	"iban",
	"passport_number",
	"valid_upto",
	"place_of_issue",
)

# custom fields on these doctypes follow the JSON rule: only the name-ish
# fields stay at level 0
CUSTOM_FIELD_KEEP_L0 = {
	"Leave Type": {"leave_type_name"},
	"Shift Type": {"start_time", "end_time"},
}


def execute():
	logger.info("[staff_lockdown] patch start")
	phases = (
		# grants first
		ensure_employee_custom_perms,
		ensure_hr_permlevel_rows,
		ensure_staff_read_rows,
		# then revokes/locks
		lock_employee_sensitive_fields,
		lock_custom_fields,
		strip_flags,
		drop_rows,
		set_self_approval_flags,
	)
	done = []
	try:
		for phase in phases:
			phase()
			done.append(phase.__name__)
	except Exception:
		logger.error("[staff_lockdown] FAILED after phases %s", done, exc_info=True)
		raise
	frappe.clear_cache()
	logger.info("[staff_lockdown] patch done: %s", done)


def ensure_employee_custom_perms():
	"""Employee is erpnext-owned — we cannot harden its JSON from this app, so
	materialize custom perms for it on every site before stripping."""
	logger.info("[staff_lockdown] ensure Employee custom perms")
	if not frappe.db.exists("Custom DocPerm", {"parent": "Employee"}):
		setup_custom_perms("Employee")


def strip_flags():
	logger.info("[staff_lockdown] stripping flags on %d perm rows", len(STRIP_FLAGS))
	for doctype, role, level, flags in STRIP_FLAGS:
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": level}):
			continue
		for flag in flags:
			update_permission_property(doctype, role, level, flag, 0, validate=False)
		logger.info("[staff_lockdown] %s/%s L%s -= %s", doctype, role, level, flags)


def drop_rows():
	logger.info("[staff_lockdown] dropping staff rows where present")
	for doctype, role in DROP_ROWS:
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
			frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})
			logger.info("[staff_lockdown] dropped %s/%s L0 row", doctype, role)


def _has_level_zero(doctype: str, role: str) -> bool:
	"""Frappe refuses a permlevel-1 row for a role with no permlevel-0 row
	("Permission at level 0 must be set before higher levels are set"), and the
	grant would be meaningless anyway — restricted fields can't be read on a
	document the role cannot read at all.

	Roles missing at level 0 are left alone rather than granted new level-0
	access: this patch's job is to preserve access for roles that already have
	it, not to widen anyone's reach.
	"""
	if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
		return True
	logger.warning(
		"[staff_lockdown] %s has no level-0 row on %s — skipping its level-1 grant",
		role,
		doctype,
	)
	return False


def ensure_hr_permlevel_rows():
	"""Custom rows override the JSON's permlevel-1 rows, so recreate them as
	custom rows wherever a doctype runs on custom perms."""
	logger.info("[staff_lockdown] ensuring HR permlevel-1 rows")
	for doctype in L1_HR_DOCTYPES:
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue  # no custom perms — hardened JSON governs
		for role in sorted(HR_ROLES):
			if not _has_level_zero(doctype, role):
				continue
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 1}):
				add_permission(doctype, role, permlevel=1)
			update_permission_property(doctype, role, 1, "write", 1, validate=False)
		# staff keep read on their own permlevel-1 checkin fields (selfie etc.)
		if (
			doctype == "Employee Checkin"
			and _has_level_zero(doctype, "Employee")
			and not frappe.db.exists(
				"Custom DocPerm", {"parent": doctype, "role": "Employee", "permlevel": 1}
			)
		):
			add_permission(doctype, "Employee", permlevel=1)


def ensure_staff_read_rows():
	"""Any Custom DocPerm row on a doctype makes its JSON permissions inert, so
	staff would lose Leave Type / Shift Type read entirely (breaking the PWA
	leave flow) unless the level-0 read row is restored as a custom row."""
	logger.info("[staff_lockdown] ensuring staff level-0 read rows")
	for doctype in STAFF_READ_DOCTYPES:
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue  # no custom perms — hardened JSON already grants read
		for role in ("Employee", ESS):
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				add_permission(doctype, role, permlevel=0)
			update_permission_property(doctype, role, 0, "read", 1, validate=False)
			logger.info("[staff_lockdown] %s/%s L0 read ensured", doctype, role)


def lock_employee_sensitive_fields():
	logger.info("[staff_lockdown] permlevel-locking Employee sensitive fields")
	meta = frappe.get_meta("Employee")
	for fieldname in EMPLOYEE_SENSITIVE_FIELDS:
		if not meta.get_field(fieldname):
			continue
		make_property_setter("Employee", fieldname, "permlevel", 1, "Int", validate_fields_for_doctype=False)
		logger.info("[staff_lockdown] Employee.%s -> permlevel 1", fieldname)


def lock_custom_fields():
	logger.info("[staff_lockdown] permlevel-locking custom fields on config masters")
	for doctype, keep in CUSTOM_FIELD_KEEP_L0.items():
		for row in frappe.get_all(
			"Custom Field", filters={"dt": doctype}, fields=["name", "fieldname", "permlevel"]
		):
			if row.fieldname not in keep and not row.permlevel:
				frappe.db.set_value("Custom Field", row.name, "permlevel", 1)
				logger.info("[staff_lockdown] %s.%s (custom) -> permlevel 1", doctype, row.fieldname)


def set_self_approval_flags():
	logger.info("[staff_lockdown] enabling self-approval prevention flags")
	frappe.db.set_single_value("HR Settings", "prevent_self_leave_approval", 1)
	frappe.db.set_single_value("HR Settings", "prevent_self_expense_approval", 1)
