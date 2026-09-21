"""Indexes for the attendance domain's hot filters, re-asserted on every migrate.

Audit 21 Sep 2026 (D-H3, D-M11): the per-day Attendance read (`employee,
attendance_date, docstatus`), the Employee Checkin `attendance` link counted
per Fix Day action, and the OT / Attendance Request duplicate and overlap
checks all ran on unindexed columns.

Why a migrate hook and not only a patch: Frappe's schema sync drops any
non-unique index whose first column is a field without `search_index` when
the doctype's JSON reloads (frappe/database/schema.py, mariadb/schema.py). A
one-shot patch never re-runs, so three of the four indexes would vanish on
the next doctype change. `after_migrate` runs after the schema sync, and
`frappe.db.add_index` checks first, so a site that already carries an index
keeps it and the hook writes nothing.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

#: (doctype, columns) — composite where the hot filter is by employee.
INDEXES = (
	("Attendance", ["employee", "attendance_date", "docstatus"]),
	("Employee Checkin", ["attendance"]),
	("OT Request", ["employee", "ot_date"]),
	("Attendance Request", ["employee", "from_date", "to_date"]),
)


def ensure_hot_indexes() -> None:
	"""Idempotent: add_index is a no-op for an index that already exists."""
	for doctype, fields in INDEXES:
		frappe.db.add_index(doctype, fields)
	logger.info("[hot_indexes] %d attendance hot-filter indexes ensured", len(INDEXES))


def after_migrate():
	"""Never let an index guard break a deploy — but never fail silently either."""
	try:
		ensure_hot_indexes()
	except Exception:
		logger.error("[hot_indexes] could not ensure the attendance indexes", exc_info=True)
		frappe.log_error(title="Attendance index guard failed", message=frappe.get_traceback())
