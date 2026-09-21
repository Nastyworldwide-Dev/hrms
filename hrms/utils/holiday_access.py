"""HR can see the holiday calendar.

THE FAILURE, from Verifica on 21 September 2026 (audit G-holiday-list.md):

HR reported the Holiday List "not available". Their accounts hold HR User.
On v16 the calendar truth is Holiday List (ERPNext, which ships HR User
`select` only — no `read`) plus a submitted Holiday List Assignment (this
fork, System Manager and HR Manager only). Frappe 16 builds the sidebar and
Ctrl+K from `can_read`, so both doctypes vanished from Desk for HR, the direct
URL 403'd, and every "No Holiday List was found ... assign through Holiday
List Assignment" message linked HR to a form they could not open.

THE GRANT: HR User gets `read` + `select` at level 0 on both. Nothing more —
HR Manager keeps create/submit on the assignment (owner ruling).

WHY A HOOK AND NOT ONLY A PATCH

Holiday List is not our JSON, so its grant lives in Custom DocPerm — a row on
the site. Verifica is a clone: it carries a Patch Log saying a patch ran while
the rows the patch wrote did not survive, and a "Restore Original
Permissions" click has the same permanent effect (hrms/utils/permlevel_guard.py
tells the same story for permlevel rows). So this runs on EVERY migrate and is
idempotent: a healthy site finds nothing and writes nothing. A one-shot patch
calls the same function so `bench migrate` applies it once regardless of
after_migrate ordering.

Holiday List Assignment ships the row in its own JSON. This module re-asserts
it ONLY when the site already runs that doctype on Custom DocPerm — copying
the JSON onto custom rows would freeze it, and every later JSON change would
be inert on that site.

This is a level-0 grant — who may see a doctype at all — which is exactly what
permlevel_guard refuses to decide; that is why it is a separate module.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

ROLE = "HR User"

#: doctype -> the level-0 flags HR User must hold. Pinned to
#: holiday_list_assignment.json by test_holiday_access.
HOLIDAY_ACCESS = {
	"Holiday List": ("read", "select"),
	"Holiday List Assignment": ("read", "select"),
}

#: Doctypes whose JSON is ours and already carries the row. Left on their JSON
#: unless the site has moved them onto Custom DocPerm already.
SHIPPED_HERE = ("Holiday List Assignment",)


def missing_flags(row: dict | None, wanted: tuple) -> list:
	"""The flags still to grant; every flag when there is no row at all. Pure."""
	return [flag for flag in wanted if not (row or {}).get(flag)]


def ensure_holiday_access() -> list:
	"""Grant HR User read + select on the holiday doctypes. Idempotent.

	Returns [(doctype, flags_written)] so the deploy log says so; a healthy
	site returns [].
	"""
	import frappe
	from frappe.permissions import add_permission, update_permission_property

	if not frappe.db.exists("Role", ROLE):
		return []

	written = []
	for doctype, wanted in HOLIDAY_ACCESS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		custom = bool(frappe.db.exists("Custom DocPerm", {"parent": doctype}))
		if not custom and doctype in SHIPPED_HERE:
			continue  # our JSON governs and carries the row; do not freeze it
		row = frappe.db.get_value(
			"Custom DocPerm" if custom else "DocPerm",
			{"parent": doctype, "role": ROLE, "permlevel": 0, "if_owner": 0},
			["name", *wanted],
			as_dict=True,
		)
		gaps = missing_flags(row, wanted)
		if not gaps:
			continue
		if row is None:
			add_permission(doctype, ROLE, 0)  # moves the doctype onto Custom DocPerm, grants read
		for flag in gaps:
			update_permission_property(doctype, ROLE, 0, flag, 1, validate=False)
		written.append((doctype, tuple(gaps)))
		logger.warning(
			"[holiday_access] granted %s %s on %s — HR could not open the holiday calendar in Desk",
			ROLE,
			"+".join(gaps),
			doctype,
		)
	if written:
		frappe.clear_cache()
		msg = "HR User can read the holiday calendar again: " + ", ".join(
			f"{d} +{'+'.join(f)}" for d, f in written
		)
		frappe.log_error(title="Holiday access restored", message=msg)
		logger.warning("[holiday_access] %s", msg)
	else:
		logger.info("[holiday_access] HR User already reads the holiday doctypes")
	return written


def after_migrate():
	"""Never let a permission guard break a deploy — but never fail silently either."""
	import frappe

	try:
		ensure_holiday_access()
	except Exception:
		logger.error("[holiday_access] could not grant holiday access", exc_info=True)
		frappe.log_error(title="Holiday access guard failed", message=frappe.get_traceback())
