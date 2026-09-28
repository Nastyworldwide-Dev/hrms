"""New OT rates from the deploy day, old days untouched (HR policy, 28 Sep 2026).

Public Holiday pays 2x for the first 8 hours and 3x after; Off Day pays a
flat 2x; on rest, off and public-holiday days the shift's minimum must be
met first. The owner: "new rates from deploy date so we dont harm old
existing data".

Every shift with overtime on gets the new Public Holiday and Off Day rows
dated today, beside its existing rows (which keep pricing the days before).
HR Settings.ot_nonwork_minimum_from is set to the same day. Both are written
ONCE: the date is the anchor that keeps older days on their old price, so a
second run must never move it. A shift whose rates HR has already dated is
left alone.
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import getdate

logger = logging.getLogger(__name__)

SETTING = "ot_nonwork_minimum_from"

#: (day type, from_hour, to_hour, to_minute, rate)
NEW_ROWS = (
	("Public Holiday", 0, 8, 0, 2.0),
	("Public Holiday", 8, 23, 59, 3.0),
	("Off Day", 0, 23, 59, 2.0),
)


def execute():
	create_custom_fields(
		{
			"HR Settings": [
				{
					"fieldname": SETTING,
					"fieldtype": "Date",
					"label": "Overtime minimum also applies to rest, off and public-holiday days from",
					"description": "From this date a rest, off or public-holiday day must reach the shift's minimum overtime before it counts. Days before it are unchanged.",
					"insert_after": "replacement_leave_hours_per_day",
				}
			]
		},
		update=True,
	)
	# Raw read: get_single_value turns an empty Date into 0001-01-01 (truthy).
	from hrms.utils.ot_calculation import _nonwork_minimum_from

	since = _nonwork_minimum_from()
	if since:
		logger.info("[patch] OT policy already dated %s — nothing to do", since)
		return
	since = getdate()
	dated = sum(
		_date_new_rows(name, since)
		for name in frappe.get_all("Shift Type", {"enable_overtime": 1}, pluck="name")
	)
	frappe.db.set_single_value("HR Settings", SETTING, since)
	logger.info("[patch] OT policy from %s: new rates on %d shift(s)", since, dated)


def _date_new_rows(name, since) -> int:
	shift = frappe.get_doc("Shift Type", name)
	if any(row.get("effective_from") for row in shift.overtime_rates):
		# HR dated this shift's rates by hand; this patch will not guess how to
		# merge. Said in the Error Log so HR can see it and add the rows.
		logger.warning("[patch] %s already has dated OT rates — left alone", name)
		frappe.log_error(
			title=f"OT policy of {since} not applied to {name}",
			message=f"Shift Type {name} already had dated overtime rates, so the new Public Holiday "
			f"(2x first 8h, then 3x) and Off Day (flat 2x) rows were not added. Add them by hand, "
			f"with Effective From {since}.",
		)
		return 0
	for day_type, from_hour, to_hour, to_minute, rate in NEW_ROWS:
		shift.append(
			"overtime_rates",
			{
				"day_type": day_type,
				"from_hour": from_hour,
				"from_minute": 0,
				"to_hour": to_hour,
				"to_minute": to_minute,
				"rate": rate,
				"effective_from": since,
			},
		)
	# Straight to the rows: a full save re-runs every Shift Type check, and one
	# unrelated complaint would leave this shift on the old rates for good.
	for row in shift.overtime_rates:
		if row.get("effective_from"):
			row.db_insert()
	frappe.clear_document_cache("Shift Type", name)
	logger.info("[patch] %s: new OT rates from %s", name, since)
	return 1
