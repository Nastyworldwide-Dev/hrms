"""Re-assert the permission rows that make restricted fields visible.

THE FAILURE, from the live hub on 10 September 2026:

`eligible_for_overtime_pay` — the switch that decides whether an employee's
approved overtime is PAID or converted to Replacement Leave — did not render
on Employee at all. Not for HR, not for Administrator. The field existed, the
value was correct, and the PWA read it fine; only the Desk could not show it.

It is the one Employee custom field at permlevel 1, and ERPNext's Employee
ships permission rows at level 0 only. `frappe.model.meta.get_permlevel_access`
collects the levels that have a row and has no Administrator bypass, so one
missing row hides the field from every human on the site. HR could neither
grant nor revoke eligibility, and a new employee — unticked by default — was
stuck on Replacement Leave with no way to change it.

WHY A HOOK AND NOT A PATCH

The rows are created by `v15_99_0.staff_perm_lockdown`, and a patch runs once.
Verifica is a clone: it carries a Patch Log saying that patch is done while the
rows themselves did not survive, so nothing would ever recreate them. Anything
that resets permissions later — a restore, a "Restore Original Permissions" in
the Role Permission Manager — has the same permanent effect.

So this runs on EVERY migrate. It is idempotent: on a healthy site it finds
nothing and writes nothing.

WHAT IT WILL NOT DO

It never creates a permlevel-0 row. Level 0 is access to the whole document,
which is a decision about who may see a doctype at all; this guard only
restores access to restricted FIELDS for roles that already hold the document.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


#: The only doctypes this guard may touch — the same set the lockdown patch
#: creates rows for (`staff_perm_lockdown.L1_HR_DOCTYPES`). Imported lazily in
#: `guarded_only` so the pure half stays frappe-free; restated here so a reader
#: sees the boundary without chasing a patch, and pinned equal by test.
#:
#: Why a boundary at all: `rows_needing_write` grants WRITE on a row that
#: exists, and an unfiltered scan would apply that to any doctype with a
#: restricted field — including Appraisal L1, where `appraisee_comments` and
#: `appraisee_sign_date` are read-only for HR BY DESIGN so HR cannot sign on
#: the employee's behalf.
GUARDED_DOCTYPES = ("Employee", "Employee Checkin", "Leave Type", "Shift Type")


def guarded_only(needed) -> set:
	"""Drop anything outside GUARDED_DOCTYPES. Pure."""
	return {(doctype, level) for doctype, level in needed if doctype in GUARDED_DOCTYPES}


#: Employee fields that must not be readable by everyone who can open the
#: record. Restated from `staff_perm_lockdown.EMPLOYEE_SENSITIVE_FIELDS` and
#: pinned equal by test — two lists would drift and a field would quietly stay
#: readable.
SENSITIVE_EMPLOYEE_FIELDS = (
	"salary_mode",
	"salary_currency",
	"bank_name",
	"bank_ac_no",
	"iban",
	"passport_number",
	"valid_upto",
	"place_of_issue",
)

#: The HR Settings checkbox that governs the lock. On by default; unticking it
#: UNLOCKS on the next migrate, so the decision is reversible from Desk without
#: a code change.
SENSITIVE_LOCK_SETTING = "lock_sensitive_employee_fields"


def sensitive_field_changes(current: dict, locked: bool) -> dict:
	"""fieldname -> the permlevel it should have, for fields not already there.

	Pure, and deliberately two-way. A one-way lock would make the checkbox a
	switch wearing a two-way label: ticking it would restrict the fields and
	unticking it would do nothing at all.
	"""
	target = 1 if locked else 0
	return {field: target for field, level in current.items() if int(level or 0) != target}


def missing_permlevel_rows(needed, level_zero_roles, existing_rows, roles) -> list:
	"""Which (doctype, role, permlevel) rows have to be created. Pure.

	`needed` is {(doctype, permlevel)} for every restricted field this app
	relies on; `level_zero_roles` maps doctype -> the roles that already hold a
	level-0 row there; `existing_rows` is {(doctype, role, permlevel)} already
	present; `roles` is the operator set to grant.

	Sorted, so the log line a migrate prints is stable and diffable.
	"""
	out = []
	for doctype, level in needed:
		if level <= 0:
			continue  # level 0 is who may see the doctype at all — not ours to decide
		holders = level_zero_roles.get(doctype) or set()
		for role in roles:
			if role not in holders:
				logger.debug("[permlevel_guard] %s has no level-0 row on %s — skipping", role, doctype)
				continue
			if (doctype, role, level) in existing_rows:
				continue
			out.append((doctype, role, level))
	return sorted(out)


def rows_needing_write(needed, rows_without_write, roles) -> list:
	"""Existing rows at a needed level that carry no write flag. Pure.

	Creating the row is only half the job: `add_permission` grants READ, and a
	restricted field the user cannot write is silently reverted on save. A row
	left read-only therefore stays read-only for ever, because the create path
	sees it and calls the doctype healthy.

	Level 0 is excluded — a read-only level-0 row is a deliberate grant and
	nothing to do with restricted fields.
	"""
	levels = {(doctype, level) for doctype, level in needed if level > 0}
	out = [
		(doctype, role, level)
		for doctype, role, level in rows_without_write
		if (doctype, level) in levels and role in roles
	]
	return sorted(out)


#: The operator set granted access to restricted fields. Mirrors
#: hrms.hr.utils.HR_ROLES, imported lazily so the pure half stays frappe-free.
def _hr_roles() -> tuple:
	from hrms.hr.utils import HR_ROLES

	return tuple(sorted(HR_ROLES))


def _needed_permlevels(frappe) -> set:
	"""Every (doctype, permlevel) this site has a restricted field at.

	Three sources, because a field reaches permlevel three ways: shipped in a
	doctype's own JSON, added as a Custom Field (the OT eligibility case), or
	moved there later by a Property Setter (how the Employee pay fields were
	locked down).
	"""
	needed = set()
	for row in frappe.get_all("Custom Field", filters={"permlevel": (">", 0)}, fields=["dt", "permlevel"]):
		needed.add((row.dt, int(row.permlevel or 0)))
	for row in frappe.get_all(
		"Property Setter",
		filters={"property": "permlevel", "doctype_or_field": "DocField"},
		fields=["doc_type", "value"],
	):
		try:
			level = int(row.value or 0)
		except (TypeError, ValueError):
			continue
		if level > 0:
			needed.add((row.doc_type, level))
	# Third source: the doctype's own JSON. Without it only Employee was covered
	# (its restricted field is a Custom Field); Leave Type, Shift Type and
	# Employee Checkin declare theirs in their own fields and were invisible.
	for doctype in GUARDED_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		for field in frappe.get_meta(doctype).fields:
			level = int(field.permlevel or 0)
			if level > 0:
				needed.add((doctype, level))
	return guarded_only(needed)


def _permission_source(frappe, doctype: str) -> tuple:
	"""(level_zero_roles, existing_rows, rows_without_write, table) from whichever
	table actually governs.

	A doctype with any Custom DocPerm row runs entirely on custom perms — the
	JSON's rows are inert — so the two must never be mixed.
	"""
	table = "Custom DocPerm" if frappe.db.exists("Custom DocPerm", {"parent": doctype}) else "DocPerm"
	rows = frappe.get_all(table, filters={"parent": doctype}, fields=["role", "permlevel", "read", "write"])
	zero = {r.role for r in rows if not int(r.permlevel or 0) and r.read}
	existing = {(doctype, r.role, int(r.permlevel or 0)) for r in rows}
	no_write = {(doctype, r.role, int(r.permlevel or 0)) for r in rows if not r.write}
	return zero, existing, no_write, table


def ensure_permlevel_rows() -> list:
	"""Create any missing permission row for a restricted field. Idempotent.

	Runs on every migrate (hooks.after_migrate). Returns what it created so the
	deploy log says so; a healthy site returns [].
	"""
	import frappe
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	roles = _hr_roles()
	needed = _needed_permlevels(frappe)
	if not needed:
		return []

	created = []
	for doctype, level in sorted(needed):
		if not frappe.db.exists("DocType", doctype):
			continue
		zero, existing, no_write, table = _permission_source(frappe, doctype)
		gaps = missing_permlevel_rows({(doctype, level)}, {doctype: zero}, existing, roles)
		# A row that exists but cannot write is the same failure wearing a
		# different face: the field renders and the edit is reverted.
		writeless = rows_needing_write({(doctype, level)}, no_write, roles)
		if not gaps and not writeless:
			continue
		# Only now does the doctype have to move onto custom perms: the rows we
		# are about to add cannot live beside an inert JSON set.
		if table == "DocPerm":
			logger.info("[permlevel_guard] materialising custom perms for %s", doctype)
			setup_custom_perms(doctype)
		for dt, role, lvl in gaps:
			add_permission(dt, role, permlevel=lvl)
			# add_permission grants READ only. Without this the field renders and
			# every edit to it is silently reverted by Frappe's
			# reset_values_if_no_permlevel_access — worse than the missing row,
			# because HR then believes the change landed. The patch this guard
			# replaces did the same thing (staff_perm_lockdown.py:166).
			update_permission_property(dt, role, lvl, "write", 1, validate=False)
			created.append((dt, role, lvl))
			logger.warning(
				"[permlevel_guard] restored %s level-%s access on %s — a restricted field there "
				"was invisible to every user, Administrator included",
				role,
				lvl,
				dt,
			)
		for dt, role, lvl in writeless:
			if (dt, role, lvl) in gaps:
				continue  # disjoint by construction — belt and braces
			update_permission_property(dt, role, lvl, "write", 1, validate=False)
			created.append((dt, role, lvl))
			logger.warning(
				"[permlevel_guard] granted %s write at level %s on %s — the field rendered but "
				"every edit to it was being silently reverted",
				role,
				lvl,
				dt,
			)
			logger.warning(
				"[permlevel_guard] restored %s level-%s read for %s — a restricted field on %s was "
				"invisible to every user, Administrator included",
				role,
				lvl,
				dt,
				dt,
			)
	if created:
		frappe.clear_cache()
		msg = "Restored permission rows for restricted fields: " + ", ".join(
			f"{d}/{r} L{l}" for d, r, l in created
		)
		frappe.log_error(title="Permlevel rows restored", message=msg)
		print(f"[permlevel_guard] {msg}")
	else:
		logger.info("[permlevel_guard] every restricted field already has its permission row")
	return created


def apply_sensitive_field_lock() -> dict:
	"""Bring the sensitive Employee fields into line with the HR Setting.

	The lock already existed in `v15_99_0.staff_perm_lockdown`, but
	`install_app` stamps every patch complete without running it, so a fresh
	site never locked them and nothing ever would. Confirmed on the verify
	bench: bank_ac_no, iban, passport_number and salary_mode all at permlevel 0.

	Idempotent, and reversible from Desk: untick the setting and the next
	migrate puts every field back to permlevel 0.
	"""
	import frappe
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	locked = frappe.db.get_single_value("HR Settings", SENSITIVE_LOCK_SETTING)
	# A site that predates the field reads None. Default to LOCKED: the safe
	# reading of "not configured" for a field holding bank and passport data.
	locked = True if locked is None else bool(locked)

	meta = frappe.get_meta("Employee")
	current = {}
	for field in SENSITIVE_EMPLOYEE_FIELDS:
		df = meta.get_field(field)
		if df:
			current[field] = int(df.permlevel or 0)

	changes = sensitive_field_changes(current, locked)
	for field, level in changes.items():
		make_property_setter("Employee", field, "permlevel", level, "Int", validate_fields_for_doctype=False)
		logger.warning(
			"[permlevel_guard] Employee.%s -> permlevel %s (%s)",
			field,
			level,
			"restricted" if level else "readable at level 0, per HR Settings",
		)
	if changes:
		frappe.clear_cache(doctype="Employee")
		verb = "Restricted" if locked else "Unrestricted"
		msg = f"{verb} Employee fields: {', '.join(sorted(changes))}"
		frappe.log_error(title="Sensitive employee fields", message=msg)
		print(f"[permlevel_guard] {msg}")
	return changes


def after_migrate():
	"""Never let a permission guard break a deploy — but never fail silently either."""
	import frappe

	try:
		ensure_permlevel_rows()
		apply_sensitive_field_lock()
	except Exception:
		logger.error("[permlevel_guard] could not restore permlevel rows", exc_info=True)
		frappe.log_error(title="Permlevel guard failed", message=frappe.get_traceback())
