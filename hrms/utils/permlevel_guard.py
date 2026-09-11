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
	return needed


def _permission_source(frappe, doctype: str) -> tuple:
	"""(level_zero_roles, existing_rows) from whichever table actually governs.

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
		for dt, role, lvl in writeless:
			if (dt, role, lvl) in gaps:
				continue  # just created above, already granted
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


def after_migrate():
	"""Never let a permission guard break a deploy — but never fail silently either."""
	import frappe

	try:
		ensure_permlevel_rows()
	except Exception:
		logger.error("[permlevel_guard] could not restore permlevel rows", exc_info=True)
		frappe.log_error(title="Permlevel guard failed", message=frappe.get_traceback())
