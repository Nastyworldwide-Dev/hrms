"""Turn the sensitive-field lock ON for sites that predate the setting.

`HR Settings.lock_sensitive_employee_fields` ships with `default: "1"`, and a
FRESH site gets that when the Single is first created. An EXISTING site does
not: adding a field to a Single leaves the stored record without it, and
`get_single_value` then returns 0 — indistinguishable from "HR deliberately
unticked it". Measured on the verify bench: the setting read 0 immediately
after the migrate that introduced it, so the lock stayed off.

So the default is written once, here. After this runs the value is HR's to
change: untick it and `permlevel_guard.apply_sensitive_field_lock` puts the
fields back to permlevel 0 on the next deploy.

Only writes when the field has never been stored. A site where someone has
already made a choice keeps it.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	stored = frappe.db.exists(
		"Singles", {"doctype": "HR Settings", "field": "lock_sensitive_employee_fields"}
	)
	if stored:
		logger.info("[sensitive_lock] HR Settings already carries a choice — leaving it alone")
		return
	frappe.db.set_single_value("HR Settings", "lock_sensitive_employee_fields", 1)
	logger.warning(
		"[sensitive_lock] defaulted HR Settings.lock_sensitive_employee_fields to 1 — "
		"bank, IBAN, passport and salary-mode fields on Employee become HR-only on this deploy"
	)
	print("[sensitive_lock] sensitive Employee fields will be restricted (HR Settings, reversible)")
