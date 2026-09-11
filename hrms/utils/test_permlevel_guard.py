"""A permlevel-1 field with no permlevel-1 permission row is invisible to EVERYONE.

Found 10 Sep 2026 on the live hub. `eligible_for_overtime_pay` is a custom
field on Employee at permlevel 1 — the switch that decides whether an
employee's approved overtime is PAID or converted to Replacement Leave. On
Verifica the checkbox does not render at all, not even for Administrator,
while the PWA reads the value fine.

That is not a bug in the field. `frappe/model/meta.py:728 get_permlevel_access`
collects only the permlevels that have an actual permission row, and has no
Administrator special case; ERPNext's Employee ships rows at level 0 only. So
one missing row hides the field from every human on the site, and HR can
neither grant nor revoke OT-pay eligibility.

The rows are created by a PATCH (v15_99_0.staff_perm_lockdown), and a patch
runs once. Verifica is a clone: it carries the Patch Log saying "done" while
the rows themselves did not survive. Nothing will ever recreate them.

So the rule cannot live in a patch. This module is the pure half of a guard
that re-asserts the rows on EVERY migrate.

Pure — no site, so the commit gate runs it on the system interpreter.
"""

import unittest

from hrms.utils.permlevel_guard import missing_permlevel_rows

HR = ("HR Manager", "HR User", "System Manager")


class TestMissingPermlevelRows(unittest.TestCase):
	def test_a_level_one_field_with_no_level_one_row_is_reported(self):
		# The Employee case exactly: level-0 rows exist, level-1 does not.
		missing = missing_permlevel_rows(
			needed={("Employee", 1)},
			level_zero_roles={"Employee": set(HR)},
			existing_rows=set(),
			roles=HR,
		)
		self.assertEqual(
			missing,
			[("Employee", "HR Manager", 1), ("Employee", "HR User", 1), ("Employee", "System Manager", 1)],
		)

	def test_rows_that_already_exist_are_not_recreated(self):
		missing = missing_permlevel_rows(
			needed={("Employee", 1)},
			level_zero_roles={"Employee": set(HR)},
			existing_rows={("Employee", r, 1) for r in HR},
			roles=HR,
		)
		self.assertEqual(missing, [], "idempotent: a healthy site needs nothing")

	def test_a_role_without_a_level_zero_row_is_skipped(self):
		# Frappe refuses a level-1 row for a role with no level-0 row, and the
		# grant would be meaningless anyway — you cannot read a restricted field
		# on a document you cannot read at all. Never widen level-0 reach here.
		missing = missing_permlevel_rows(
			needed={("Employee", 1)},
			level_zero_roles={"Employee": {"HR Manager"}},
			existing_rows=set(),
			roles=HR,
		)
		self.assertEqual(missing, [("Employee", "HR Manager", 1)])

	def test_a_doctype_with_no_level_zero_rows_at_all_yields_nothing(self):
		missing = missing_permlevel_rows(
			needed={("Some Doctype", 1)}, level_zero_roles={}, existing_rows=set(), roles=HR
		)
		self.assertEqual(missing, [])

	def test_several_doctypes_and_levels_are_all_covered(self):
		missing = missing_permlevel_rows(
			needed={("Employee", 1), ("Leave Type", 1), ("Shift Type", 2)},
			level_zero_roles={
				"Employee": {"HR Manager"},
				"Leave Type": {"HR User"},
				"Shift Type": {"HR Manager"},
			},
			existing_rows={("Leave Type", "HR User", 1)},
			roles=HR,
		)
		self.assertEqual(missing, [("Employee", "HR Manager", 1), ("Shift Type", "HR Manager", 2)])

	def test_level_zero_is_never_created_by_this_guard(self):
		# The guard restores ACCESS TO RESTRICTED FIELDS. Creating a level-0 row
		# would hand a role the whole doctype, which is a different decision.
		missing = missing_permlevel_rows(
			needed={("Employee", 0)},
			level_zero_roles={"Employee": set(HR)},
			existing_rows=set(),
			roles=HR,
		)
		self.assertEqual(missing, [])

	def test_the_result_is_ordered_so_a_log_line_is_stable(self):
		missing = missing_permlevel_rows(
			needed={("Shift Type", 1), ("Employee", 1)},
			level_zero_roles={"Employee": {"HR User"}, "Shift Type": {"HR User"}},
			existing_rows=set(),
			roles=HR,
		)
		self.assertEqual(missing, [("Employee", "HR User", 1), ("Shift Type", "HR User", 1)])
