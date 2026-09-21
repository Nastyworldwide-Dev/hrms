"""HR can see the holiday calendar.

21 Sep 2026 (docs/glass/audit/2026-09-21/G-holiday-list.md, F1/F7): on
Verifica the holiday calendar was "not available". The HR staff hold HR User,
and on v16 the truth is Holiday List (ERPNext ships HR User `select` only, no
`read`) plus a submitted Holiday List Assignment (this fork's JSON: System
Manager and HR Manager only). Frappe 16 builds the sidebar and Ctrl+K from
`can_read`, so both doctypes vanished from Desk for HR and the direct URL
403'd — while every throw message sent HR to a form they could not open.

Rule pinned here: HR User holds `read` + `select` at level 0 on both.

  (a) Holiday List is not our JSON, so the grant is a Custom DocPerm row,
      re-asserted on EVERY migrate: Verifica is a clone that drops rows a
      one-shot patch wrote (hrms/utils/permlevel_guard.py). Idempotent — a
      healthy site writes nothing.
  (b) Holiday List Assignment is ours, so its JSON carries the row.

HR User does NOT get create/submit on the assignment (owner ruling; HR
Manager keeps that). Bench-free: the frappe boundary is a dict store.

    PYTHONPATH=. python3 hrms/tests/test_holiday_access.py
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

from hrms.utils import holiday_access as module

REPO = Path(__file__).resolve().parents[2]
HLA_JSON = REPO / "hrms/hr/doctype/holiday_list_assignment/holiday_list_assignment.json"


class _Store:
	"""Custom DocPerm / DocPerm rows as the permission functions see them."""

	def __init__(self, custom: list, shipped: list):
		self.tables = {"Custom DocPerm": custom, "DocPerm": shipped}
		self.writes = []

	def exists(self, doctype, filters=None):
		if doctype in ("Role", "DocType"):
			return filters
		return any(r["parent"] == filters["parent"] for r in self.tables[doctype])

	def get_value(self, doctype, filters, fields, as_dict=False):
		for row in self.tables[doctype]:
			if all(row.get(k) == v for k, v in filters.items()):
				return frappe._dict({f: row.get(f, 0) for f in fields})
		return None

	def setup_custom_perms(self, doctype):
		"""What both frappe.permissions writers do first: a doctype with no
		custom rows gets its shipped rows copied over, and runs on them from
		then on."""
		custom = self.tables["Custom DocPerm"]
		if not any(r["parent"] == doctype for r in custom):
			custom.extend(dict(r) for r in self.tables["DocPerm"] if r["parent"] == doctype)

	def add_permission(self, doctype, role, permlevel=0, ptype=None):
		self.writes.append(("add", doctype, role))
		self.setup_custom_perms(doctype)
		self.tables["Custom DocPerm"].append(
			{"parent": doctype, "role": role, "permlevel": permlevel, "if_owner": 0, "read": 1}
		)

	def update_permission_property(self, doctype, role, permlevel, ptype, value=None, validate=True):
		self.writes.append(("set", doctype, role, ptype, value))
		self.setup_custom_perms(doctype)
		for row in self.tables["Custom DocPerm"]:
			if row["parent"] == doctype and row["role"] == role and row["permlevel"] == permlevel:
				row[ptype] = value


def _run(store):
	import frappe.permissions as perms

	with (
		patch.object(frappe.db, "exists", side_effect=store.exists),
		patch.object(frappe.db, "get_value", side_effect=store.get_value),
		patch.object(perms, "add_permission", store.add_permission, create=True),
		patch.object(perms, "update_permission_property", store.update_permission_property, create=True),
	):
		return module.ensure_holiday_access()


def _hr_user_rows(store, doctype):
	return [
		r
		for r in store.tables["Custom DocPerm"]
		if r["parent"] == doctype and r["role"] == "HR User" and r["permlevel"] == 0
	]


def _row(parent, role, **flags):
	return {"parent": parent, "role": role, "permlevel": 0, "if_owner": 0, **flags}


class TestHrUserReadsHolidayList(unittest.TestCase):
	def setUp(self):
		# What ERPNext ships and what test.local confirmed: HR User select only.
		self.store = _Store(
			custom=[],
			shipped=[
				_row("Holiday List", "HR Manager", read=1),
				_row("Holiday List", "HR User", select=1),
			],
		)

	def test_the_grant_lands_as_a_custom_docperm_row(self):
		written = _run(self.store)
		rows = _hr_user_rows(self.store, "Holiday List")
		self.assertEqual(len(rows), 1)
		self.assertEqual((rows[0]["read"], rows[0]["select"]), (1, 1))
		self.assertIn("Holiday List", [d for d, _ in written])

	def test_a_second_run_writes_nothing(self):
		"""Runs on every migrate; a healthy site must be left alone."""
		_run(self.store)
		self.store.writes.clear()
		self.assertEqual(_run(self.store), [])
		self.assertEqual(self.store.writes, [])

	def test_a_row_dropped_by_the_clone_comes_back(self):
		"""The permlevel_guard lesson: the row existed once, the clone lost it."""
		self.store.tables["Custom DocPerm"] = [_row("Holiday List", "HR Manager", read=1)]
		_run(self.store)
		(row,) = _hr_user_rows(self.store, "Holiday List")
		self.assertEqual((row["read"], row["select"]), (1, 1))

	def test_hr_user_never_gains_create_or_submit_on_the_assignment(self):
		"""Owner ruling: HR Manager assigns calendars, HR User reads them."""
		self.store.tables["Custom DocPerm"] = [_row("Holiday List Assignment", "HR Manager", read=1)]
		_run(self.store)
		(row,) = _hr_user_rows(self.store, "Holiday List Assignment")
		self.assertEqual((row["read"], row["select"]), (1, 1))
		self.assertFalse(row.get("create") or row.get("submit") or row.get("write"))

	def test_our_own_json_is_not_frozen_when_the_site_runs_on_it(self):
		"""Holiday List Assignment ships the row in its JSON (below). Copying
		it onto Custom DocPerm would make every later JSON change inert."""
		self.store.tables["DocPerm"].append(_row("Holiday List Assignment", "HR User", read=1, select=1))
		_run(self.store)
		self.assertEqual(_hr_user_rows(self.store, "Holiday List Assignment"), [])


class TestTheAssignmentJsonGrantsHrUserRead(unittest.TestCase):
	def test_hr_user_holds_read_and_select_but_not_create(self):
		perms = json.loads(HLA_JSON.read_text())["permissions"]
		rows = [p for p in perms if p["role"] == "HR User" and not p.get("permlevel")]
		self.assertEqual(len(rows), 1, "HR User has no level-0 row on Holiday List Assignment")
		self.assertEqual(rows[0].get("read"), 1)
		self.assertEqual(rows[0].get("select"), 1)
		for flag in ("create", "write", "submit", "cancel", "delete"):
			self.assertFalse(rows[0].get(flag), f"HR User must not hold {flag}")

	def test_the_module_pins_the_same_flags_the_json_ships(self):
		self.assertEqual(module.HOLIDAY_ACCESS["Holiday List Assignment"], ("read", "select"))


if __name__ == "__main__":
	unittest.main()
