"""Half Day Session (AM / PM) on Leave Application (owner, 25 Sep 2026).

Runs itself on deploy:
- a site Property Setter that hides the new field or its list column is
  removed, so the doctype JSON wins (a Property Setter silently overrides it);
- the column is added after Half Day in every user's saved Leave Application
  report view, the way HR's OT columns were.
Existing leave keeps a blank session: nothing is back-filled or guessed.
Idempotent.
"""

import logging

import frappe

from hrms.utils.report_columns import add_report_columns

logger = logging.getLogger(__name__)

SHADOWING = ("hidden", "in_list_view", "depends_on", "options")


def execute():
	removed = frappe.db.delete(
		"Property Setter",
		{
			"doc_type": "Leave Application",
			"field_name": "half_day_session",
			"property": ("in", SHADOWING),
		},
	)
	logger.info("[patch] half_day_session: property setters cleared (%s)", removed)
	frappe.clear_cache(doctype="Leave Application")
	add_report_columns("Leave Application", ["half_day_session"], after="half_day")
