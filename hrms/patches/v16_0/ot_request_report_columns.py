"""Show Day Type and OT Rate in every user's existing OT Request report view.

HR (25 Sep 2026): "I asked for the column inside this existing report". Frappe
keeps each user's own column list for the Report view; the two fields added on
25 Sep never appeared in a list saved before they existed. They are inserted
right after Compensation in each saved view; nothing else in the view moves.
Idempotent.
"""

from hrms.utils.report_columns import add_report_columns


def execute():
	add_report_columns("OT Request", ["day_type", "ot_rate"], after="compensation")
