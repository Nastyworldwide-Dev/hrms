"""Add columns to users' saved Report views, in place (25 Sep 2026).

Frappe stores each user's own column list for a doctype's Report view in
__UserSettings ("Report" -> "fields"). A field added to the doctype later never
shows in a list saved before it existed, so HR's OT Request report did not get
Day Type and OT Rate. This inserts them after an anchor column, once.
"""

import json
import logging

logger = logging.getLogger(__name__)


def with_columns(raw, doctype: str, fieldnames: list[str], after: str) -> str | None:
	"""The saved settings with the columns added, or None when there is no
	saved Report view (Frappe then builds the default, which already has them)."""
	try:
		settings = json.loads(raw or "{}")
	except ValueError:
		return None
	report = settings.get("Report") if isinstance(settings, dict) else None
	fields = report.get("fields") if isinstance(report, dict) else None
	if not fields:
		return None
	have = {f[0] for f in fields if isinstance(f, list) and f}
	missing = [[name, doctype] for name in fieldnames if name not in have]
	if missing:
		at = next((i + 1 for i, f in enumerate(fields) if f and f[0] == after), len(fields))
		report["fields"] = fields[:at] + missing + fields[at:]
	return json.dumps(settings)


def add_report_columns(doctype: str, fieldnames: list[str], after: str) -> int:
	"""Every user's saved Report view of `doctype` gets the columns. Returns how many."""
	import frappe

	changed = 0
	for row in frappe.db.sql(
		"select user, data from `__UserSettings` where doctype=%s", doctype, as_dict=True
	):
		new = with_columns(row.data, doctype, fieldnames, after)
		if new is None or new == row.data:
			continue
		frappe.db.sql(
			"update `__UserSettings` set data=%s where doctype=%s and user=%s", (new, doctype, row.user)
		)
		frappe.cache.hdel("_user_settings", f"{doctype}::{row.user}")
		changed += 1
	logger.info("[report_columns] %s: %s added to %d saved report view(s)", doctype, fieldnames, changed)
	return changed
