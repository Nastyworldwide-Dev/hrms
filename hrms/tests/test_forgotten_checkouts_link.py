"""HR can find every forgotten check-out ("Resolve") in Desk without digging.

THE SYMPTOM (14 Sep 2026): a forgotten check-out is stored as a Remote
Checkin Request with `is_late_checkout = 1` — the same doctype that also
holds out-of-area check-in approvals. Neither the "Shift & Attendance"
workspace nor its sidebar separated the two, so HR had to open every Remote
Checkin Request and read the flag row by row.

Both halves are pinned: the shipped JSON (fresh installs) links a
"Forgotten Check-outs" Report Builder report — filtered to
`is_late_checkout = 1` — from the Attendance card and the sidebar, next to
Remote Checkin Request. A patch inserts the same Report and the same two
links into the live Workspace and Workspace Sidebar records. The patch must
be idempotent, must never duplicate or remove HR's own rows, and must never
overwrite a Report HR has already tuned. Bench-free:

    PYTHONPATH=. python3 hrms/tests/test_forgotten_checkouts_link.py
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
WORKSPACE_JSON = ROOT / "hr/workspace/shift_&_attendance/shift_&_attendance.json"
SIDEBAR_JSON = ROOT / "workspace_sidebar/shift_&_attendance.json"
PATCH_MODULE = "hrms.patches.v16_0.add_forgotten_checkouts_link"
REPORT_NAME = "Forgotten Check-outs"
REF_DOCTYPE = "Remote Checkin Request"
ANCHOR = "Remote Checkin Request"


def _cards(links):
	"""Group workspace link rows under their Card Break, as Workspace.get_link_groups does."""
	cards, current = {}, None
	for row in links:
		if row["type"] == "Card Break":
			current = row["label"]
			cards[current] = {"break": row, "links": []}
		elif current is not None:
			cards[current]["links"].append(row)
	return cards


class TestShippedJson(unittest.TestCase):
	def test_attendance_card_links_forgotten_checkouts_once_after_remote_checkin_request(self):
		cards = _cards(json.loads(WORKSPACE_JSON.read_text())["links"])
		targets = [row["link_to"] for row in cards["Attendance"]["links"]]
		self.assertEqual(targets.count(REPORT_NAME), 1)
		self.assertEqual(targets[targets.index(REPORT_NAME) - 1], ANCHOR)

	def test_workspace_link_counts_match_the_rows(self):
		# Workspace.build_links_table_from_card deletes link_count + 1 rows, so a
		# stale count eats a neighbouring card when HR edits the page.
		for label, card in _cards(json.loads(WORKSPACE_JSON.read_text())["links"]).items():
			with self.subTest(card=label):
				self.assertEqual(card["break"]["link_count"], len(card["links"]))

	def test_workspace_row_points_at_the_report_builder_report(self):
		links = json.loads(WORKSPACE_JSON.read_text())["links"]
		row = next(r for r in links if r.get("link_to") == REPORT_NAME)
		self.assertEqual(row["type"], "Link")
		self.assertEqual(row["link_type"], "Report")
		self.assertEqual(row["is_query_report"], 0)
		self.assertEqual(row["report_ref_doctype"], REF_DOCTYPE)
		self.assertEqual(row["dependencies"], REF_DOCTYPE)
		self.assertEqual(row["label"], REPORT_NAME)

	def test_sidebar_places_forgotten_checkouts_next_to_remote_checkin_request(self):
		items = json.loads(SIDEBAR_JSON.read_text())["items"]
		targets = [i.get("link_to") for i in items]
		self.assertEqual(targets.count(REPORT_NAME), 1)
		position = targets.index(REPORT_NAME)
		self.assertEqual(targets[position - 1], ANCHOR)
		self.assertEqual(items[position]["child"], 0)
		self.assertEqual(items[position]["link_type"], "Report")


class TestReportDefinition(unittest.TestCase):
	"""The patch's own Report Builder payload — decoupled from any live-record mocking."""

	def test_report_json_filters_to_late_checkouts_only(self):
		module = importlib.import_module(PATCH_MODULE)
		payload = json.loads(module.REPORT_JSON)
		self.assertEqual(payload["filters"], [[REF_DOCTYPE, "is_late_checkout", "=", 1]])

	def test_report_json_carries_the_requested_columns(self):
		module = importlib.import_module(PATCH_MODULE)
		payload = json.loads(module.REPORT_JSON)
		self.assertEqual(
			[c[0] for c in payload["columns"]],
			["employee", "employee_name", "checkin_time", "status", "approver", "approved_at"],
		)


def _row(**values):
	return frappe._dict(values)


class _Doc:
	def __init__(self, table, rows):
		self.table = table
		setattr(self, table, [_row(**r) for r in rows])
		self.flags = frappe._dict()
		self.saved = 0

	def append(self, table, row):
		child = _row(**row)
		getattr(self, table).append(child)
		return child

	def save(self):
		self.saved += 1


class _NewReport:
	"""Stands in for frappe.get_doc({...new Report...}).insert(...)."""

	def __init__(self, values, registry):
		self.values = dict(values)
		self.registry = registry

	def insert(self, ignore_permissions=False):
		self.values["ignore_permissions"] = ignore_permissions
		self.registry[("Report", self.values["report_name"])] = self.values


def _live_workspace():
	"""The Shift & Attendance Attendance card as a site has it before the patch, plus an HR-added link."""
	return _Doc(
		"links",
		[
			{"type": "Card Break", "label": "Attendance", "link_count": 3},
			{"type": "Link", "label": "Attendance", "link_to": "Attendance", "link_type": "DocType"},
			{
				"type": "Link",
				"label": "Remote Checkin Request",
				"link_to": "Remote Checkin Request",
				"link_type": "DocType",
			},
			{
				"type": "Link",
				"label": "Employee Checkin",
				"link_to": "Employee Checkin",
				"link_type": "DocType",
			},
			{"type": "Card Break", "label": "Overtime", "link_count": 1},
			{"type": "Link", "label": "HR's own", "link_to": "Salary Slip", "link_type": "DocType"},
		],
	)


def _live_sidebar():
	return _Doc(
		"items",
		[
			{
				"type": "Link",
				"label": "Home",
				"link_to": "Shift & Attendance",
				"link_type": "Workspace",
				"child": 0,
			},
			{
				"type": "Link",
				"label": "Remote Checkin Request",
				"link_to": "Remote Checkin Request",
				"link_type": "DocType",
				"child": 0,
			},
			{"type": "Section Break", "label": "Overtime", "child": 0},
			{
				"type": "Link",
				"label": "Overtime Type",
				"link_to": "Overtime Type",
				"link_type": "DocType",
				"child": 1,
			},
		],
	)


class TestPatchOnLiveRecords(unittest.TestCase):
	def _run(self, docs, reports=None):
		reports = reports if reports is not None else {}
		module = importlib.import_module(PATCH_MODULE)

		def _exists(doctype, name):
			return (doctype, name) in docs or (doctype, name) in reports

		def _get_doc(*args):
			if len(args) == 1:
				return _NewReport(args[0], reports)
			doctype, name = args
			return docs[(doctype, name)]

		with (
			patch.object(frappe.db, "exists", side_effect=_exists),
			patch.object(frappe, "get_doc", side_effect=_get_doc),
		):
			module.execute()
		return reports

	def test_creates_the_report_and_links_both_pages_once(self):
		workspace, sidebar = _live_workspace(), _live_sidebar()
		docs = {
			("Workspace", "Shift & Attendance"): workspace,
			("Workspace Sidebar", "Shift & Attendance"): sidebar,
		}

		reports = self._run(docs)
		self._run(docs, reports)  # idempotent

		report = reports[("Report", REPORT_NAME)]
		self.assertEqual(report["report_type"], "Report Builder")
		self.assertEqual(report["is_standard"], "No")
		self.assertEqual(report["ref_doctype"], REF_DOCTYPE)
		self.assertEqual(report["roles"], [{"role": "HR User"}, {"role": "HR Manager"}])
		self.assertTrue(report["ignore_permissions"])
		payload = json.loads(report["json"])
		self.assertEqual(payload["filters"], [[REF_DOCTYPE, "is_late_checkout", "=", 1]])

		self.assertEqual(
			[r.link_to or r.label for r in workspace.links],
			[
				"Attendance", "Attendance", "Remote Checkin Request", REPORT_NAME,
				"Employee Checkin", "Overtime", "Salary Slip",
			],
		)  # fmt: skip
		cards = _cards(workspace.links)
		self.assertEqual(cards["Attendance"]["break"].link_count, 4)
		self.assertEqual([r.idx for r in workspace.links], list(range(1, len(workspace.links) + 1)))
		new = next(r for r in workspace.links if r.link_to == REPORT_NAME)
		self.assertEqual(
			(new.type, new.link_type, new.is_query_report, new.report_ref_doctype, new.dependencies),
			("Link", "Report", 0, REF_DOCTYPE, REF_DOCTYPE),
		)

		self.assertEqual(
			[(i.link_to or i.label, i.child) for i in sidebar.items],
			[
				("Shift & Attendance", 0), ("Remote Checkin Request", 0), (REPORT_NAME, 0),
				("Overtime", 0), ("Overtime Type", 1),
			],
		)  # fmt: skip
		self.assertEqual((workspace.saved, sidebar.saved), (1, 1))

	def test_a_report_hr_already_tuned_is_not_overwritten(self):
		workspace = _live_workspace()
		docs = {("Workspace", "Shift & Attendance"): workspace}
		seeded = {"json": '{"filters": "HR changed this"}'}
		reports = {("Report", REPORT_NAME): seeded}

		self._run(docs, reports)

		self.assertIs(reports[("Report", REPORT_NAME)], seeded)  # untouched object, not replaced
		self.assertIn(REPORT_NAME, [r.link_to for r in workspace.links])

	def test_a_link_hr_already_placed_elsewhere_is_not_duplicated(self):
		workspace = _live_workspace()
		workspace.links.append(_row(type="Card Break", label="Mine", link_count=1))
		workspace.links.append(_row(type="Link", label="Mine", link_to=REPORT_NAME, link_type="Report"))

		reports = self._run({("Workspace", "Shift & Attendance"): workspace})

		self.assertEqual([r.link_to for r in workspace.links].count(REPORT_NAME), 1)
		self.assertIn(("Report", REPORT_NAME), reports)  # still created even though not (re)linked

	def test_a_card_hr_removed_is_not_recreated(self):
		workspace = _Doc("links", [{"type": "Card Break", "label": "Time", "link_count": 0}])
		self._run({("Workspace", "Shift & Attendance"): workspace})
		self.assertEqual(len(workspace.links), 1)
		self.assertEqual(workspace.saved, 0)

	def test_a_site_without_the_records_is_skipped(self):
		self._run({})  # no exists -> no get_doc for Workspace/Sidebar -> no error


if __name__ == "__main__":
	unittest.main(verbosity=2)
