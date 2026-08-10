"""Drop the legacy scalar overtime multiplier columns from Shift Type.

v15.82 introduced six scalar overtime multiplier fields on Shift Type; v15.83
replaced them with the Shift Overtime Rate child table (hour-range tiers).
Removing fields from the doctype JSON does not drop their DB columns, so this
patch drops the orphaned columns when present.
"""

from __future__ import annotations

import logging

import frappe

logger = logging.getLogger(__name__)

LEGACY_COLUMNS = (
	"overtime_normal_day_multiplier",
	"overtime_rest_day_multiplier",
	"overtime_public_holiday_multiplier",
	"overtime_off_day_multiplier",
	"overtime_off_day_band_hours",
	"overtime_off_day_excess_multiplier",
)


def execute() -> None:
	for column in LEGACY_COLUMNS:
		if not frappe.db.has_column("Shift Type", column):
			continue
		frappe.db.sql_ddl(f"alter table `tabShift Type` drop column `{column}`")
		logger.info("[patch.v15_83_0] dropped legacy Shift Type column %s", column)
	frappe.db.commit()
