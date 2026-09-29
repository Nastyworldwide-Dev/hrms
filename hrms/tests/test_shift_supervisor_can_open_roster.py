"""A Shift Supervisor can open the roster (Fahmie, 29 Sep 2026).

He had the right roles and still hit two walls:
  · Desk "Shift & Attendance" said "No permission for Page": the workspace
    was gated to HR roles only.
  · The roster filter bar showed six "Insufficient Permission for Branch /
    Designation" errors: the role could not read those two name lists.

hrms/patches/v16_0/let_shift_supervisor_open_roster.py grants both. Bench-free:

    PYTHONPATH=. python3 hrms/tests/test_shift_supervisor_can_open_roster.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

from _fake_document import FakeDocument

import frappe

from hrms.patches.v16_0 import let_shift_supervisor_open_roster as role_patch

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]


class _Workspace(FakeDocument):
	def __init__(self, doctype, **fields):
		# A real Document carries `flags` (frappe._dict); the patch sets two.
		super().__init__(doctype, flags=frappe._dict(), **fields)

	def append(self, field, row):
		getattr(self, field).append(FakeDocument("Has Role", **row))

	def save(self):
		self.saves = (self.saves or 0) + 1


def _run(workspace):
	granted = []
	with (
		patch.object(role_patch, "add_permission"),
		patch.object(
			role_patch,
			"update_permission_property",
			side_effect=lambda dt, role, lvl, cap, val: granted.append((dt, cap)),
		),
		patch.object(frappe.db, "exists", return_value=True),
		patch.object(frappe, "get_doc", return_value=workspace),
		patch.object(frappe, "clear_cache"),
	):
		role_patch.execute()
	return granted


def _hr_only_workspace():
	return _Workspace(
		"Workspace",
		name="Shift & Attendance",
		roles=[FakeDocument("Has Role", role=r) for r in ("HR User", "HR Manager", "System Manager")],
	)


class TestShiftSupervisorCanOpenRoster(unittest.TestCase):
	def test_role_can_read_the_roster_filter_lists(self):
		granted = _run(_hr_only_workspace())
		self.assertIn(("Branch", "read"), granted)
		self.assertIn(("Designation", "read"), granted)

	def test_filter_lists_are_read_only(self):
		granted = _run(_hr_only_workspace())
		for doctype in ("Branch", "Designation"):
			self.assertEqual({cap for dt, cap in granted if dt == doctype}, {"read"})

	def test_role_can_open_the_workspace(self):
		workspace = _hr_only_workspace()
		_run(workspace)
		self.assertIn("Shift Supervisor", {row.role for row in workspace.roles})
		self.assertEqual(workspace.saves, 1)

	def test_second_run_adds_nothing(self):
		workspace = _hr_only_workspace()
		_run(workspace)
		_run(workspace)
		roles = [row.role for row in workspace.roles]
		self.assertEqual(roles.count("Shift Supervisor"), 1)
		self.assertEqual(workspace.saves, 1)

	def test_role_can_run_the_attendance_sheet(self):
		inserted = []

		def get_doc(values):
			row = FakeDocument(**values)
			row._on_db_insert = lambda doc: inserted.append((doc.parent, doc.role))
			row.db_insert = lambda: row.run_method("db_insert")
			return row

		with (
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(frappe.db, "exists", side_effect=lambda doctype, *a: doctype == "Report"),
			patch.object(frappe, "clear_document_cache", create=True),
		):
			role_patch._open_report()
		self.assertEqual(inserted, [("Monthly Attendance Sheet", "Shift Supervisor")])

	def test_patch_is_registered(self):
		# An unregistered patch never runs on deploy.
		patches = (HRMS_ROOT / "patches.txt").read_text().splitlines()
		self.assertTrue(
			any(l.startswith("hrms.patches.v16_0.let_shift_supervisor_open_roster") for l in patches)
		)


if __name__ == "__main__":
	unittest.main(verbosity=2)
