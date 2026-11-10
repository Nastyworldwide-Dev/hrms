"""Employee Status options (HR, 10 Nov 2026).

The dropdown becomes Active, Resigned, Terminated, Deceased, Suspended. It is
set as a Property Setter — the same record Customize Form writes — so the
change is in the repo and repeatable, not typed into a site by hand.

Everyone Left or Inactive becomes Resigned. Inactive meant the same as Left
on this site. Written with a direct UPDATE: a save would run the leaver checks
(relieving date, active reports) against people who left long ago; HR fills
missing relieving dates in afterwards, and the Employee override lets those
rows save in the meantime. ERPNext's Left already disabled their logins, so
nothing about User.enabled changes here.

Idempotent: a second run finds nobody Left or Inactive and the setter already
holding the same options.
"""

import logging

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from hrms.utils.employee_status import RETIRED_STATUSES, STATUS_OPTIONS

logger = logging.getLogger(__name__)


def execute():
	make_property_setter(
		"Employee",
		"status",
		"options",
		"\n".join(STATUS_OPTIONS),
		"Text",
		validate_fields_for_doctype=False,
	)

	for old, new in RETIRED_STATUSES.items():
		names = frappe.get_all("Employee", filters={"status": old}, pluck="name")
		if not names:
			continue
		undated = frappe.db.count("Employee", {"status": old, "relieving_date": ("is", "not set")})
		frappe.db.sql("UPDATE `tabEmployee` SET `status` = %s WHERE `status` = %s", (new, old))
		logger.info(
			"[patch] employee status: %d %s -> %s (%d without a relieving date, for HR to fill in)",
			len(names),
			old,
			new,
			undated,
		)

	frappe.clear_cache(doctype="Employee")
