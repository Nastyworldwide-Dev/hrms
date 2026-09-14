"""HR in Desk can reach every request type Nadi (the PWA) offers.

THE SYMPTOM (14 Sep 2026): the "Shift & Attendance" workspace showed only
Overtime Type and Overtime Slip under Overtime. OT Request, Replacement Leave
Claim and Remote Checkin Request — all filed by staff from Nadi — had no link
anywhere in Desk, so HR could only reach them by typing the URL.

Both halves are pinned: the shipped JSON (fresh installs) and a patch that
inserts the same links into the live Workspace and Workspace Sidebar records.
The patch must be idempotent and must never duplicate or remove HR's own rows.
Bench-free:

    PYTHONPATH=. python3 hrms/tests/test_nadi_requests_in_shift_attendance_desk.py
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
PATCH_MODULE = "hrms.patches.v16_0.link_nadi_requests_in_shift_attendance"

#: card / sidebar group -> the Nadi request doctypes HR must find there.
EXPECTED = {
	"Attendance": ["Remote Checkin Request"],
	"Overtime": ["OT Request", "Replacement Leave Claim"],
}
HR_READERS = {"HR User", "HR Manager"}


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


def _doctype_json(name):
	folder = name.lower().replace(" ", "_")
	return json.loads((ROOT / "hr/doctype" / folder / f"{folder}.json").read_text())


class TestShippedJson(unittest.TestCase):
	def test_workspace_cards_link_the_nadi_requests(self):
		cards = _cards(json.loads(WORKSPACE_JSON.read_text())["links"])
		for card, doctypes in EXPECTED.items():
			targets = [row["link_to"] for row in cards[card]["links"]]
			for doctype in doctypes:
				with self.subTest(card=card, doctype=doctype):
					self.assertEqual(targets.count(doctype), 1)

	def test_workspace_link_counts_match_the_rows(self):
		# Workspace.build_links_table_from_card deletes link_count + 1 rows, so a
		# stale count eats a neighbouring card when HR edits the page.
		for label, card in _cards(json.loads(WORKSPACE_JSON.read_text())["links"]).items():
			with self.subTest(card=label):
				self.assertEqual(card["break"]["link_count"], len(card["links"]))

	def test_new_workspace_rows_copy_the_neighbour_shape(self):
		links = json.loads(WORKSPACE_JSON.read_text())["links"]
		neighbour = next(r for r in links if r.get("link_to") == "Attendance Request")
		for row in links:
			if row.get("link_to") in {"OT Request", "Replacement Leave Claim", "Remote Checkin Request"}:
				with self.subTest(row=row["link_to"]):
					self.assertEqual(set(row), set(neighbour))
					self.assertEqual((row["type"], row["link_type"]), ("Link", "DocType"))
					self.assertEqual(row["label"], row["link_to"])

	def test_sidebar_places_the_nadi_requests(self):
		items = json.loads(SIDEBAR_JSON.read_text())["items"]
		targets = [i.get("link_to") for i in items]
		for doctypes in EXPECTED.values():
			for doctype in doctypes:
				self.assertEqual(targets.count(doctype), 1, doctype)

		remote = targets.index("Remote Checkin Request")
		self.assertEqual(targets[remote - 1], "Attendance Request")
		self.assertEqual(items[remote]["child"], 0)

		section = next(
			n for n, i in enumerate(items) if i["type"] == "Section Break" and i["label"] == "Overtime"
		)
		group = []
		for item in items[section + 1 :]:
			if not item["child"]:
				break
			group.append(item["link_to"])
		self.assertEqual(group, ["Overtime Type", "Overtime Slip", "OT Request", "Replacement Leave Claim"])

	def test_hr_can_read_every_linked_doctype(self):
		for doctypes in EXPECTED.values():
			for doctype in doctypes:
				meta = _doctype_json(doctype)
				self.assertEqual(meta["name"], doctype)
				readers = {p["role"] for p in meta["permissions"] if p.get("read") and not p.get("permlevel")}
				with self.subTest(doctype=doctype):
					self.assertTrue(HR_READERS.issubset(readers), readers)


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


def _live_workspace():
	"""The Shift & Attendance links as a site has them before the patch, plus an HR-added link."""
	return _Doc(
		"links",
		[
			{"type": "Card Break", "label": "Attendance", "link_count": 3},
			{"type": "Link", "label": "Attendance", "link_to": "Attendance", "link_type": "DocType"},
			{
				"type": "Link",
				"label": "Attendance Request",
				"link_to": "Attendance Request",
				"link_type": "DocType",
			},
			{
				"type": "Link",
				"label": "Employee Checkin",
				"link_to": "Employee Checkin",
				"link_type": "DocType",
			},
			{"type": "Card Break", "label": "Overtime", "link_count": 3},
			{"type": "Link", "label": "Overtime Type", "link_to": "Overtime Type", "link_type": "DocType"},
			{"type": "Link", "label": "Overtime Slip", "link_to": "Overtime Slip", "link_type": "DocType"},
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
				"label": "Attendance Request",
				"link_to": "Attendance Request",
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
			{
				"type": "Link",
				"label": "Overtime Slip",
				"link_to": "Overtime Slip",
				"link_type": "DocType",
				"child": 1,
			},
			{"type": "Section Break", "label": "Reports", "child": 0},
			{
				"type": "Link",
				"label": "Shift Attendance",
				"link_to": "Shift Attendance",
				"link_type": "Report",
				"child": 1,
			},
		],
	)


class TestPatchOnLiveRecords(unittest.TestCase):
	def _run(self, docs):
		module = importlib.import_module(PATCH_MODULE)
		with (
			patch.object(frappe.db, "exists", side_effect=lambda doctype, name: (doctype, name) in docs),
			patch.object(frappe, "get_doc", side_effect=lambda doctype, name: docs[(doctype, name)]),
		):
			module.execute()

	def test_links_land_in_their_card_once_and_hr_rows_survive(self):
		workspace, sidebar = _live_workspace(), _live_sidebar()
		docs = {
			("Workspace", "Shift & Attendance"): workspace,
			("Workspace Sidebar", "Shift & Attendance"): sidebar,
		}

		self._run(docs)
		self._run(docs)  # idempotent

		self.assertEqual(
			[r.link_to or r.label for r in workspace.links],
			[
				"Attendance", "Attendance", "Attendance Request", "Remote Checkin Request", "Employee Checkin",
				"Overtime", "Overtime Type", "Overtime Slip", "OT Request", "Replacement Leave Claim", "Salary Slip",
			],
		)  # fmt: skip
		cards = _cards(workspace.links)
		self.assertEqual(cards["Attendance"]["break"].link_count, 4)
		self.assertEqual(cards["Overtime"]["break"].link_count, 5)
		self.assertEqual([r.idx for r in workspace.links], list(range(1, len(workspace.links) + 1)))
		new = next(r for r in workspace.links if r.link_to == "OT Request")
		self.assertEqual(
			(new.type, new.link_type, new.label, new.onboard), ("Link", "DocType", "OT Request", 0)
		)

		self.assertEqual(
			[(i.link_to or i.label, i.child) for i in sidebar.items],
			[
				("Shift & Attendance", 0), ("Attendance Request", 0), ("Remote Checkin Request", 0),
				("Overtime", 0), ("Overtime Type", 1), ("Overtime Slip", 1), ("OT Request", 1),
				("Replacement Leave Claim", 1), ("Reports", 0), ("Shift Attendance", 1),
			],
		)  # fmt: skip
		self.assertEqual((workspace.saved, sidebar.saved), (1, 1))

	def test_a_link_hr_already_placed_elsewhere_is_not_duplicated(self):
		workspace = _live_workspace()
		workspace.links.append(_row(type="Card Break", label="Mine", link_count=1))
		workspace.links.append(_row(type="Link", label="OT", link_to="OT Request", link_type="DocType"))
		self._run({("Workspace", "Shift & Attendance"): workspace})
		self.assertEqual([r.link_to for r in workspace.links].count("OT Request"), 1)
		# Replacement Leave Claim has no OT Request anchor in the card, so it closes the card.
		overtime = _cards(workspace.links)["Overtime"]
		self.assertEqual(overtime["links"][-1].link_to, "Replacement Leave Claim")
		self.assertEqual(overtime["break"].link_count, 4)

	def test_a_card_hr_removed_is_not_recreated(self):
		workspace = _Doc("links", [{"type": "Card Break", "label": "Time", "link_count": 0}])
		self._run({("Workspace", "Shift & Attendance"): workspace})
		self.assertEqual(len(workspace.links), 1)
		self.assertEqual(workspace.saved, 0)

	def test_a_site_without_the_records_is_skipped(self):
		self._run({})  # no exists -> no get_doc -> no error


if __name__ == "__main__":
	unittest.main(verbosity=2)
