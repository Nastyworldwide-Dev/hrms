"""HR Settings switches for the automatic attendance recovery.

Nabil, 15 Sep 2026: one release, and a switch per fix family so HR can pause
one without a redeploy. The code already reads these (absent = on):
attendance_auto_recovery.SWITCH_PREFIX + step, and lone_in_closer.SETTING.
Custom Fields, idempotent; never changes a value HR has set.
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

logger = logging.getLogger(__name__)

SWITCH_STEPS = (
	"release_mirrored",
	"assignments",
	"rostered_shift",
	"overwritten",
	"mirrored_rows",
	"close_lone_ins",
	"heal",
	"skip_stamps",
	"rebuild",
	"leftover_rows",
	"ot_recount",
	"recheck",
)


def fields() -> list:
	rows = [
		{
			"fieldname": "attendance_recovery_section",
			"fieldtype": "Section Break",
			"label": "Attendance Recovery (runs nightly)",
			"collapsible": 1,
			"insert_after": "unlink_payment_on_cancellation_of_employee_advance",
		},
		{
			"fieldname": "attendance_close_lone_ins_from_erp",
			"fieldtype": "Check",
			"label": "Close a pre-cutover lone IN from the old ERP",
			"default": "1",
			"insert_after": "attendance_recovery_section",
		},
	]
	previous = "attendance_close_lone_ins_from_erp"
	for step in SWITCH_STEPS:
		name = f"attendance_recovery_skip_{step}"
		rows.append(
			{
				"fieldname": name,
				"fieldtype": "Check",
				"label": f"Pause: {step.replace('_', ' ')}",
				"default": "0",
				"insert_after": previous,
			}
		)
		previous = name
	return rows


def execute():
	create_custom_fields({"HR Settings": fields()}, ignore_validate=True, update=False)
	logger.info("[attendance_recovery_switches] %d HR Settings switches ensured", len(fields()))
