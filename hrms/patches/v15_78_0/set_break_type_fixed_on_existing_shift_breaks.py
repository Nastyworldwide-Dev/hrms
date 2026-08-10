"""Backfill Shift Break.break_type for rows created before the field existed.

v15.78.0 adds a Break Type (Fixed / Flexible) to the Shift Break child
table. All pre-existing rows are fixed start/end windows, so they are
stamped "Fixed" — the field is mandatory, and leaving it empty would
block re-saving any Shift Type that already has breaks.

Safe to re-run (only touches empty values).
"""

import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabShift Break`
		SET break_type = 'Fixed'
		WHERE IFNULL(break_type, '') = ''
		"""
	)
	frappe.db.commit()
