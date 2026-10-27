"""Event announcements get the day they happen (owner, 27 Oct 2026).

HR Announcement gains `event_date`, required when the category is Event. The calendar used to put
an Event's dot on `publish_from`, so an Event notice already on the board keeps a dot on that same
day: its event_date becomes its show-from day. HR can move it afterwards.

Also removes any Property Setter that hides or un-requires the new field, so the JSON is not
shadowed on a live site (the JSON alone can be; see the Property Setter memory). Idempotent: only
Events with no event_date are touched, and `modified` is left alone (a backfill is not an HR edit).
"""

import logging

import frappe

logger = logging.getLogger(__name__)

#: What a Property Setter could set on the field that makes the JSON's rule moot.
SHADOWING_PROPERTIES = ("hidden", "reqd", "depends_on", "mandatory_depends_on")


def execute():
	rows = frappe.get_all(
		"HR Announcement",
		filters={"category": "Event", "event_date": ("is", "not set")},
		fields=["name", "publish_from"],
	)
	filled = 0
	for row in rows:
		if not row.publish_from:
			continue
		frappe.db.set_value(
			"HR Announcement", row.name, "event_date", row.publish_from, update_modified=False
		)
		filled += 1

	# Counted first: frappe.db.delete returns the query result, not a row count.
	shadows = frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": "HR Announcement",
			"field_name": "event_date",
			"property": ("in", SHADOWING_PROPERTIES),
		},
		pluck="name",
	)
	if shadows:
		frappe.db.delete("Property Setter", {"name": ("in", shadows)})
		frappe.clear_cache(doctype="HR Announcement")
	logger.info(
		"[patch] %d of %d event notice(s) given their show-from day as event_date; %d shadowing property setter(s) removed",
		filled,
		len(rows),
		len(shadows),
	)
