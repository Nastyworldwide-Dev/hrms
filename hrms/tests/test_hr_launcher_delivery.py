"""The HR launcher and the two payroll deduction reports reach staff sites as HR-only.

Two open Criticals from the 7 Sep 2026 Nadi audit (docs/glass/nadi-audit-2026-09-07.md
D1, D2):

  * every employee's Desk launcher showed all nine HR children of the Nadi
    icon, Payroll included. The workspace PAGES were role-gated on 1 Sep, but
    v16 filters "Workspace Sidebar" desktop icons by their own roles table,
    which shipped empty — and an empty roles table means everyone;
  * the Professional Tax and Provident Fund deduction reports carry HR roles in
    their JSON but their `modified` still reads 2022, so the timestamp-gated
    import never delivered those roles to a site that already had the report.
    Zero `Has Role` rows on a report means visible to every Desk user.

Both are delivery problems, so both halves are pinned: the shipped JSON says
HR-only AND carries a `modified` that will actually import, and a patch sets
the same roles on live rows for sites where the timestamp gate already ran.
Pure static checks plus a bench-free patch run.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_hr_launcher_delivery.py
"""

import importlib
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

ROOT = pathlib.Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "desktop_icon"
APP_LABEL = "Nadi"
#: The operator set; hrms/tests/test_is_hr_single_source.py pins it to hrms.hr.utils.HR_ROLES.
HR_ROLES = {"HR User", "HR Manager", "System Manager"}
#: The day the roles landed in the fixtures — anything older will not import.
DELIVERY_DATE = "2026-09-08"
REPORTS = {
	"Professional Tax Deductions": ROOT
	/ "payroll/report/professional_tax_deductions/professional_tax_deductions.json",
	"Provident Fund Deductions": ROOT
	/ "payroll/report/provident_fund_deductions/provident_fund_deductions.json",
}


def _icons():
	return {p.name: json.loads(p.read_text()) for p in sorted(ICON_DIR.glob("*.json"))}


class TestShippedFixturesAreHrOnlyAndWillImport(unittest.TestCase):
	def test_every_child_icon_carries_the_hr_roles(self):
		for name, icon in _icons().items():
			if icon.get("parent_icon") != APP_LABEL:
				continue
			with self.subTest(icon=name):
				self.assertEqual({row["role"] for row in icon.get("roles", [])}, HR_ROLES)
				self.assertGreaterEqual(
					icon["modified"][:10], DELIVERY_DATE, "roles edit needs a newer modified"
				)

	def test_the_app_icon_itself_stays_open(self):
		app = next(i for i in _icons().values() if i["label"] == APP_LABEL)
		self.assertEqual(
			app.get("roles", []), [], "the launcher tile is for everyone; its children are gated"
		)

	def test_payroll_deduction_reports_carry_hr_roles_with_an_importable_timestamp(self):
		for name, path in REPORTS.items():
			with self.subTest(report=name):
				report = json.loads(path.read_text())
				self.assertEqual({row["role"] for row in report["roles"]}, HR_ROLES)
				self.assertGreaterEqual(
					report["modified"][:10], DELIVERY_DATE, "2022 timestamps never import"
				)


class _Doc:
	def __init__(self, roles):
		self.roles = [frappe._dict(role=r) for r in roles]
		self.flags = frappe._dict()
		self.saved = 0

	def append(self, table, row):
		getattr(self, table).append(frappe._dict(row))

	def save(self):
		self.saved += 1


class TestPatchSetsRolesOnLiveRows(unittest.TestCase):
	def _run(self, docs):
		module = importlib.import_module("hrms.patches.v16_0.gate_hr_desktop_icons_and_payroll_reports")
		with (
			patch.object(frappe.db, "exists", side_effect=lambda doctype, name: (doctype, name) in docs),
			patch.object(frappe, "get_doc", side_effect=lambda doctype, name: docs[(doctype, name)]),
		):
			module.execute()
		return module

	def test_missing_roles_are_added_once_and_existing_scoping_is_kept(self):
		payroll = _Doc([])
		leaves = _Doc(["HR Manager"])  # an operator already scoped it further
		report = _Doc([])
		docs = {
			("Desktop Icon", "Payroll"): payroll,
			("Desktop Icon", "Leaves"): leaves,
			("Report", "Professional Tax Deductions"): report,
		}
		self._run(docs)
		self.assertEqual({r.role for r in payroll.roles}, HR_ROLES)
		self.assertEqual({r.role for r in leaves.roles}, HR_ROLES)
		self.assertEqual({r.role for r in report.roles}, HR_ROLES)
		self.assertEqual((payroll.saved, leaves.saved, report.saved), (1, 1, 1))
		self._run(docs)  # idempotent: nothing missing, nothing saved again
		self.assertEqual((payroll.saved, leaves.saved, report.saved), (1, 1, 1))

	def test_a_site_without_the_row_is_skipped(self):
		self._run({})  # no exists -> no get_doc -> no error


if __name__ == "__main__":
	unittest.main()
