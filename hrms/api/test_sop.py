"""SOP folders on the SOP page (owner request, 27 Oct 2026).

A folder is a topic. get_sops lists a folder only with the SOPs THIS reader may
see (the same _sees rule as the list, so a Department SOP filed in a folder is
invisible and uncounted for another department), hides a folder that holds
nothing for the reader, and lists a filed SOP under its folder only. HR also
gets the empty folders: the picker and the "Manage folders" sheet need them.

Driven through get_sops with the same harness as test_sop_document.py:

    python3 -m pytest -q hrms/api/test_sop.py
"""

import unittest
from unittest.mock import patch

import frappe

from hrms.hr.doctype.sop_document.test_sop_document import HR, NOBODY, OTHER, STAFF, _Ctx, sop_api


def _sop(name, title, folder=None, scope="General", department=None, pinned=0, published=1):
	return {
		"name": name,
		"title": title,
		"scope": scope,
		"department": department,
		"company": None,
		"pinned": pinned,
		"published": published,
		"modified": "2026-10-01 10:00:00",
		"attachment": None,
		"folder": folder,
	}


# staff (Operations - N) may see 1, 2, 3 and the pinned 6; OTHER (Finance - N) may see 1, 2, 4 and 6
ROWS = [
	_sop("S1", "Fire evacuation plan", folder="Safety"),
	_sop("S2", "Fire extinguisher use", folder="Safety"),
	_sop("S3", "Ops fire exits", folder="Safety", scope="Department", department="Operations - N"),
	_sop("S4", "Finance cash room fire drill", folder="Safety", scope="Department", department="Finance - N"),
	_sop("S5", "Draft safety note", folder="Safety", published=0),
	_sop("S6", "Emergency contacts", folder="Safety", pinned=1),
	_sop("C1", "Till counting", folder="Cash handling", scope="Department", department="Finance - N"),
	_sop("U1", "Dress code"),
	_sop("U2", "Stock delivery checks", scope="Department", department="Operations - N"),
]

# as the database returns them: sort_order asc, then folder_name
FOLDERS = [
	{"name": "Safety", "folder_name": "Safety", "sort_order": 10},
	{"name": "Cash handling", "folder_name": "Cash handling", "sort_order": 20},
	{"name": "Closing", "folder_name": "Closing", "sort_order": 30},
]


def _get(user, rows=ROWS, folders=FOLDERS, **kw):
	with _Ctx(user, sops=rows, folders=folders, **kw) as ctx:
		data = sop_api.get_sops()
	return data, ctx


def _names(cards):
	return [c["name"] for c in cards]


class TestFoldersCountedUnderTheFence(unittest.TestCase):
	def test_staff_count_only_what_they_may_see(self):
		data, _ = _get(STAFF)
		safety = next(f for f in data["folders"] if f["name"] == "Safety")
		# General 1, 2, own department 3, pinned 6; not the Finance one, not the draft
		self.assertEqual(safety["count"], 4)
		self.assertEqual(sorted(_names(safety["sops"])), ["S1", "S2", "S3", "S6"])

	def test_another_department_sees_its_own_not_the_first_departments(self):
		data, _ = _get(OTHER)
		safety = next(f for f in data["folders"] if f["name"] == "Safety")
		self.assertEqual(sorted(_names(safety["sops"])), ["S1", "S2", "S4", "S6"])
		self.assertEqual(safety["count"], 4)

	def test_hr_counts_every_sop_including_the_draft_and_other_departments(self):
		data, _ = _get(HR)
		safety = next(f for f in data["folders"] if f["name"] == "Safety")
		self.assertEqual(safety["count"], 6)

	def test_a_folder_holding_nothing_this_reader_may_see_is_not_listed(self):
		data, _ = _get(STAFF)
		# Cash handling holds only a Finance SOP; Closing holds nothing at all
		self.assertEqual([f["name"] for f in data["folders"]], ["Safety"])

	def test_hr_also_gets_the_empty_folders_for_the_picker_and_manage_sheet(self):
		data, _ = _get(HR)
		by_name = {f["name"]: f["count"] for f in data["folders"]}
		self.assertEqual(by_name["Closing"], 0)
		self.assertEqual(by_name["Cash handling"], 1)

	def test_folders_keep_the_order_the_query_gives_them(self):
		data, _ = _get(HR)
		self.assertEqual([f["name"] for f in data["folders"]], ["Safety", "Cash handling", "Closing"])

	def test_the_query_orders_by_sort_order_then_name(self):
		# the order is the database's; the stub can only pin what was asked for
		_, ctx = _get(HR)
		self.assertEqual(ctx.folder_query["order_by"], "sort_order asc, folder_name asc")


class TestFiledSopsLiveOnlyInTheirFolder(unittest.TestCase):
	def test_a_filed_sop_is_not_repeated_in_general_or_the_department_groups(self):
		data, _ = _get(STAFF)
		listed = _names(data["general"]) + [n for d in data["departments"] for n in _names(d["sops"])]
		for filed in ("S1", "S2", "S3"):
			self.assertNotIn(filed, listed)
		# unfiled SOPs stay exactly where they were
		self.assertEqual(_names(data["general"]), ["U1"])
		self.assertEqual(
			{d["department"]: _names(d["sops"]) for d in data["departments"]}, {"Operations - N": ["U2"]}
		)

	def test_a_pinned_filed_sop_stays_in_essentials(self):
		data, _ = _get(STAFF)
		self.assertEqual(_names(data["pinned"]), ["S6"])

	def test_a_sop_whose_folder_no_longer_exists_is_treated_as_unfiled(self):
		rows = [_sop("G1", "Orphan", folder="Deleted folder")]
		data, _ = _get(STAFF, rows=rows)
		self.assertEqual(_names(data["general"]), ["G1"])
		self.assertEqual(data["folders"], [])

	def test_every_card_carries_its_folder(self):
		data, _ = _get(STAFF)
		safety = next(f for f in data["folders"] if f["name"] == "Safety")
		self.assertEqual({c["name"]: c["folder"] for c in safety["sops"]}["S1"], "Safety")
		self.assertIsNone(data["general"][0]["folder"])

	def test_every_existing_key_is_still_there(self):
		data, _ = _get(STAFF)
		self.assertTrue(
			{"is_hr", "my_department", "pinned", "general", "departments", "folders"} <= set(data)
		)

	def test_the_list_asks_for_the_folder_column(self):
		_, ctx = _get(STAFF)
		self.assertIn("folder", ctx.sop_fields)


class TestDetailCarriesTheFolder(unittest.TestCase):
	def _detail(self, user, folder):
		doc = frappe._dict(_sop("S1", "Fire evacuation plan", folder=folder))
		doc.content = "<p>body</p>"
		with (
			_Ctx(user, sops=ROWS, folders=FOLDERS),
			patch.object(frappe, "get_doc", return_value=doc),
			patch("hrms.api.sop._", lambda msg: msg),
		):
			return sop_api.get_sop("S1")

	def test_the_edit_sheet_can_prefill_the_folder_so_saving_does_not_unfile_the_sop(self):
		self.assertEqual(self._detail(HR, "Safety")["folder"], "Safety")

	def test_an_unfiled_sop_reads_as_no_folder(self):
		self.assertIsNone(self._detail(STAFF, None)["folder"])


class TestBeforeMigrate(unittest.TestCase):
	def test_without_the_folder_column_the_page_still_answers(self):
		# code live a moment before migrate adds the column: asking for it would
		# 500 the whole page for everyone (the calendar's event_date, 27 Oct 2026)
		rows = [{k: v for k, v in r.items() if k != "folder"} for r in ROWS]
		data, ctx = _get(STAFF, rows=rows, folder_field=False)
		self.assertTrue(ctx.sop_fields)
		self.assertNotIn("folder", ctx.sop_fields)
		self.assertEqual(ctx.folder_query, {}, "the folder table is not read before it exists")
		self.assertEqual(data["folders"], [])
		self.assertEqual(sorted(_names(data["general"])), ["S1", "S2", "U1"])

	def test_a_reader_without_an_employee_is_still_refused(self):
		with (
			_Ctx(NOBODY, sops=ROWS, folders=FOLDERS),
			patch("hrms.api.sop._", lambda msg: msg),
			self.assertRaises(frappe.PermissionError),
		):
			sop_api.get_sops()


if __name__ == "__main__":
	unittest.main()


class TestManageFolders(unittest.TestCase):
	"""HR manages folders from the app (owner, 27 Oct 2026): create, rename, reorder, delete when empty.
	HR only — the same rule get_sops uses for is_hr. Inputs are checked at the boundary."""

	def _as(self, hr: bool):
		return patch.object(sop_api, "_unrestricted", return_value=hr)

	def test_staff_are_refused_every_change(self):
		with self._as(False):
			for call in (
				lambda: sop_api.save_folder("Safety"),
				lambda: sop_api.move_folder("Safety", "up"),
				lambda: sop_api.delete_folder("Safety"),
			):
				with self.assertRaises(frappe.PermissionError):
					call()

	def test_a_name_is_required_and_trimmed(self):
		with self._as(True):
			for bad in ("", "   ", None, 7, "x" * 81):
				with self.assertRaises(frappe.ValidationError):
					sop_api.save_folder(bad)

	def test_create_puts_the_folder_last(self):
		docs = []

		class _Doc(frappe._dict):
			def insert(self, **kw):
				docs.append(dict(self))
				self.name = self.folder_name
				return self

		with (
			self._as(True),
			patch.object(
				frappe, "get_all", return_value=[frappe._dict(sort_order=10), frappe._dict(sort_order=20)]
			),
			patch.object(frappe, "get_doc", side_effect=lambda d: _Doc(d)),
		):
			out = sop_api.save_folder("  Safety  ")
		self.assertEqual(docs[0]["folder_name"], "Safety")
		self.assertEqual(docs[0]["sort_order"], 30)
		self.assertEqual(out["name"], "Safety")

	def test_rename_goes_through_rename_doc(self):
		with (
			self._as(True),
			patch.object(frappe, "rename_doc", return_value="Fire safety", create=True) as rename,
			patch.object(frappe.db, "set_value", create=True),
		):
			out = sop_api.save_folder("Fire safety", name="Safety")
		rename.assert_called_once()
		self.assertEqual(rename.call_args.args[:3], ("SOP Folder", "Safety", "Fire safety"))
		self.assertEqual(out["name"], "Fire safety")

	def test_move_swaps_with_the_neighbour_and_renumbers(self):
		rows = [
			frappe._dict(name="A", sort_order=0),
			frappe._dict(name="B", sort_order=0),
			frappe._dict(name="C", sort_order=0),
		]
		writes = {}
		with (
			self._as(True),
			patch.object(frappe, "get_all", return_value=rows),
			patch.object(
				frappe.db,
				"set_value",
				side_effect=lambda dt, n, f, v, **kw: writes.__setitem__(n, v),
				create=True,
			),
		):
			sop_api.move_folder("C", "up")
		self.assertEqual(sorted(writes, key=writes.get), ["A", "C", "B"])
		self.assertEqual(sorted(writes.values()), [10, 20, 30])

	def test_move_rejects_an_unknown_direction(self):
		with self._as(True), self.assertRaises(frappe.ValidationError):
			sop_api.move_folder("A", "sideways")

	def test_delete_goes_through_the_records_own_refusal(self):
		with self._as(True), patch.object(frappe, "delete_doc", create=True) as delete:
			sop_api.delete_folder("Safety")
		delete.assert_called_once_with("SOP Folder", "Safety")

	def test_a_long_desk_made_folder_can_still_be_renamed_and_deleted(self):
		# the field takes 140 characters; only the NEW name the app sends is capped at 80
		long_name = "L" * 120
		with (
			self._as(True),
			patch.object(frappe, "rename_doc", return_value="Short", create=True) as rename,
			patch.object(frappe, "delete_doc", create=True) as delete,
		):
			sop_api.save_folder("Short", name=long_name)
			sop_api.delete_folder(long_name)
		self.assertEqual(rename.call_args.args[1], long_name)
		delete.assert_called_once_with("SOP Folder", long_name)
