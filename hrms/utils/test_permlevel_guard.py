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


class TestTheRestoredRowCanWrite(unittest.TestCase):
	"""A permlevel row created by `add_permission` alone grants READ ONLY.

	Found by review of 33d286691, on the bench, with a real user doing a real
	save: the guard restored Employee/HR Manager L1 and HR ticked
	`eligible_for_overtime_pay` — and the value came back 0. Frappe's
	`Document.reset_values_if_no_permlevel_access` reverts a field the user
	cannot WRITE at that level, silently, with no error.

	That is worse than the bug it replaced. Before, the checkbox was absent and
	HR knew something was wrong. After, it renders, HR ticks it, HR believes
	eligibility is granted, and the employee stays on Replacement Leave.

	The patch this guard replaces got it right — `add_permission` there is
	followed by `update_permission_property(..., "write", 1)`
	(staff_perm_lockdown.py:166). The guard dropped that line.

	Source contract, because the defect is in the WIRING: the pure set-difference
	tests above cannot see which flags the created row carries.
	"""

	def setUp(self):
		import pathlib

		self.source = (pathlib.Path(__file__).resolve().parent / "permlevel_guard.py").read_text()

	def test_a_restored_row_is_granted_write_as_well_as_read(self):
		self.assertIn("add_permission", self.source)
		self.assertIn(
			"update_permission_property",
			self.source,
			"add_permission grants read only — the row must also be granted write",
		)
		self.assertRegex(
			self.source,
			r'update_permission_property\(\s*\n?\s*dt,\s*role,\s*lvl,\s*"write",\s*1',
			"the write grant must target the row just created (dt, role, lvl)",
		)

	def test_the_write_grant_follows_the_row_it_grants_on(self):
		# Frappe refuses a property update for a row that does not exist yet.
		self.assertLess(
			self.source.index("add_permission(dt, role, permlevel=lvl)"),
			self.source.index("update_permission_property("),
			"create the row, then grant write on it",
		)


class TestARowThatExistsButCannotWrite(unittest.TestCase):
	"""Existence is not enough — the row has to carry write.

	The first version of this guard keyed only on "does a row exist at this
	level". A row created read-only therefore stayed read-only for ever: the
	guard saw it, called it healthy, and the field kept silently reverting. That
	is exactly the state the guard's own first run left the verify bench in.

	So the guard has two jobs, not one: create the row that is missing, and
	grant write on the row that has none.
	"""

	def test_an_existing_row_without_write_is_reported(self):
		from hrms.utils.permlevel_guard import rows_needing_write

		self.assertEqual(
			rows_needing_write(
				needed={("Employee", 1)},
				rows_without_write={("Employee", "HR Manager", 1), ("Employee", "HR User", 1)},
				roles=HR,
			),
			[("Employee", "HR Manager", 1), ("Employee", "HR User", 1)],
		)

	def test_a_row_that_already_writes_is_left_alone(self):
		from hrms.utils.permlevel_guard import rows_needing_write

		self.assertEqual(rows_needing_write(needed={("Employee", 1)}, rows_without_write=set(), roles=HR), [])

	def test_only_the_levels_we_care_about_are_touched(self):
		from hrms.utils.permlevel_guard import rows_needing_write

		# A level-0 row without write is a deliberate read-only grant, not ours.
		self.assertEqual(
			rows_needing_write(
				needed={("Employee", 1)},
				rows_without_write={("Employee", "HR User", 0), ("Employee", "HR User", 1)},
				roles=HR,
			),
			[("Employee", "HR User", 1)],
		)

	def test_a_role_outside_the_operator_set_is_not_granted_write(self):
		from hrms.utils.permlevel_guard import rows_needing_write

		self.assertEqual(
			rows_needing_write(
				needed={("Employee", 1)}, rows_without_write={("Employee", "Employee", 1)}, roles=HR
			),
			[],
		)


class TestTheGuardStaysInsideItsOwnDoctypes(unittest.TestCase):
	"""The guard may only restore what the lockdown patch created.

	Raised by re-review of 861d9be54. `_needed_permlevels` queried Custom Field
	with no doctype filter, and `rows_needing_write` has no level-0-holder gate
	— so its effect is to grant WRITE on a row somebody deliberately left
	read-only, on any doctype at all.

	Measured on the bench: add one permlevel-1 Custom Field to Appraisal — an
	ordinary HR customisation — and the next migrate would grant HR Manager and
	HR User write at Appraisal level 1. Appraisal's level-1 fields are
	`appraisee_comments`, `appraisee_agreement` and `appraisee_sign_date`: the
	employee's own sign-off, read-only for HR BY DESIGN so HR cannot sign on the
	employee's behalf.

	Not live today, because no such Custom Field exists. Closed anyway: the
	precondition is one form edit away, and nothing would have reported it.

	The right boundary already exists — `staff_perm_lockdown.L1_HR_DOCTYPES`,
	the list the patch maintains. The guard restores that set and nothing else.
	"""

	def test_the_boundary_is_the_lockdown_patchs_own_list(self):
		from hrms.patches.v15_99_0.staff_perm_lockdown import L1_HR_DOCTYPES
		from hrms.utils.permlevel_guard import GUARDED_DOCTYPES

		self.assertEqual(
			set(GUARDED_DOCTYPES),
			set(L1_HR_DOCTYPES),
			"the guard must restore exactly what the lockdown creates — no more, no less",
		)

	def test_a_doctype_outside_the_set_is_dropped(self):
		from hrms.utils.permlevel_guard import guarded_only

		self.assertEqual(
			guarded_only({("Employee", 1), ("Appraisal", 1), ("Sales Invoice", 2)}),
			{("Employee", 1)},
		)

	def test_every_guarded_doctype_survives_the_filter(self):
		from hrms.utils.permlevel_guard import GUARDED_DOCTYPES, guarded_only

		needed = {(doctype, 1) for doctype in GUARDED_DOCTYPES}
		self.assertEqual(guarded_only(needed), needed)
