"""Cost Tag/Center from an Excel upload (Data Import → "Employee Cost Tag").

Owner, 28 Oct 2026: "just follow the file upload: if have same existing can
replace, if new then new row; the name and staff id is for you to read where to
put". One Excel row = one upload record; it lands on that employee's Cost
Tag/Center Allocation table (Employee → Overview).

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_employee_cost_tag.py
"""

import datetime
import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.hr.doctype.employee_cost_tag import employee_cost_tag as upload

ROOT = pathlib.Path(__file__).resolve().parents[1]
OCT = datetime.date(2026, 10, 1)


def _existing(month, cost_center=None, territory=None, pct=0):
	return frappe._dict(allocation_month=month, cost_center=cost_center, territory=territory, percentage=pct)


class TestPlaceRow(unittest.TestCase):
	"""place_row(rows, month, cost_center, territory, percentage) → the row it changed or added."""

	def test_the_same_month_and_cost_center_is_replaced_not_duplicated(self):
		rows = [_existing(OCT, "CEOF - NHSB", pct=60), _existing(OCT, "PFME - NHSB", pct=40)]
		row, added = upload.place_row(rows, OCT, "CEOF - NHSB", None, 70)
		self.assertFalse(added)
		self.assertIs(row, rows[0])
		self.assertEqual(rows[0].percentage, 70)
		self.assertEqual(rows[1].percentage, 40)

	def test_a_new_cost_center_in_the_month_is_a_new_row(self):
		rows = [_existing(OCT, "CEOF - NHSB", pct=100)]
		row, added = upload.place_row(rows, OCT, "PFME - NHSB", None, 30)
		self.assertTrue(added)
		self.assertEqual((row["cost_center"], row["percentage"]), ("PFME - NHSB", 30))
		self.assertEqual(rows[0].percentage, 100)

	def test_the_same_cost_center_in_another_month_is_a_new_row(self):
		rows = [_existing(OCT, "CEOF - NHSB", pct=100)]
		_, added = upload.place_row(rows, datetime.date(2026, 11, 1), "CEOF - NHSB", None, 100)
		self.assertTrue(added)

	def test_any_day_counts_as_its_month(self):
		rows = [_existing(OCT, "CEOF - NHSB", pct=100)]
		_, added = upload.place_row(rows, datetime.date(2026, 10, 17), "CEOF - NHSB", None, 100)
		self.assertFalse(added)

	def test_an_old_cost_tag_is_matched_by_its_territory(self):
		rows = [_existing(OCT, territory="All Territories", pct=100)]
		row, added = upload.place_row(rows, OCT, None, "All Territories", 100)
		self.assertFalse(added)
		self.assertIs(row, rows[0])

	def test_a_row_with_neither_tag_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			upload.place_row([], OCT, None, None, 100)


class _Employee:
	"""An Employee with a Cost Tag/Center table, as frappe.get_doc returns it."""

	def __init__(self, name, rows=(), fail=None, may_write=True):
		self.name = name
		self.rows = list(rows)
		self.fail = fail
		self.saves = 0
		self.may_write = may_write

	def get(self, key):
		return self.rows

	def remove(self, row):
		self.rows.remove(row)

	def check_permission(self, ptype):
		if not self.may_write:
			raise frappe.PermissionError(f"No permission to {ptype} Employee {self.name}")

	def append(self, key, row):
		self.rows.append(frappe._dict(row))

	def save(self):
		if self.fail:
			raise frappe.ValidationError(self.fail)
		self.saves += 1


def _record(name, employee, cost_center, pct, month=OCT):
	return frappe._dict(
		name=name,
		employee=employee,
		allocation_month=month,
		cost_center=cost_center,
		territory=None,
		percentage=pct,
	)


class TestApplyUploads(unittest.TestCase):
	"""Data Import saves one Excel row at a time, so a 60/40 month would be 60%
	after the first row and refused. The rows wait (Pending) until the import
	ends, then each employee's rows go on together, with one save."""

	def _run(self, records, employees):
		db = MagicMock()
		with (
			patch.object(upload.frappe, "get_all", return_value=records),
			patch.object(upload.frappe, "get_doc", side_effect=lambda dt, name: employees[name]),
			patch.object(upload.frappe, "db", db),
			patch.object(upload, "find_employee", side_effect=lambda eid, name: eid),
			patch.object(upload, "find_cost_center", side_effect=lambda v, centers=None: v),
		):
			upload.apply_uploads([r.name for r in records])
		marks = {}
		for c in db.set_value.call_args_list:
			marks[c.args[1]] = c.args[2]
		return marks, db

	def test_a_split_month_lands_whole_with_one_save(self):
		emp = _Employee("E1")
		marks, _ = self._run([_record("u1", "E1", "CEOF", 60), _record("u2", "E1", "PFME", 40)], {"E1": emp})
		self.assertEqual([(r.cost_center, r.percentage) for r in emp.rows], [("CEOF", 60), ("PFME", 40)])
		self.assertEqual(emp.saves, 1)
		self.assertEqual(marks["u1"]["status"], "Done")
		self.assertEqual(marks["u2"]["status"], "Done")

	def test_the_files_month_replaces_the_profiles_month(self):
		emp = _Employee("E1", [_existing(OCT, "CEOF", pct=60), _existing(OCT, "PFME", pct=40)])
		self._run([_record("u1", "E1", "CEOF", 70), _record("u2", "E1", "SPLY", 30)], {"E1": emp})
		self.assertEqual([(r.cost_center, r.percentage) for r in emp.rows], [("CEOF", 70), ("SPLY", 30)])

	def test_a_one_row_file_replaces_the_month_like_a_two_row_file(self):
		emp = _Employee("E1", [_existing(OCT, "CEOF", pct=70), _existing(OCT, "PFME", pct=30)])
		marks, _ = self._run([_record("u1", "E1", "CEOF", 100)], {"E1": emp})
		self.assertEqual(marks["u1"]["status"], "Done")
		self.assertEqual([(r.cost_center, r.percentage) for r in emp.rows], [("CEOF", 100)])

	def test_months_not_in_the_file_are_left_as_the_same_rows(self):
		nov = _existing(datetime.date(2026, 11, 1), "NTGY", pct=100)
		emp = _Employee("E1", [_existing(OCT, "CEOF", pct=100), nov])
		self._run([_record("u1", "E1", "PFME", 100)], {"E1": emp})
		self.assertIs(emp.rows[0], nov)  # kept, not deleted and re-made
		self.assertEqual(emp.rows[1].cost_center, "PFME")

	def test_hr_who_may_not_edit_that_employee_fails_that_row(self):
		emp = _Employee("E1", may_write=False)
		marks, _ = self._run([_record("u1", "E1", "CEOF", 100)], {"E1": emp})
		self.assertEqual(marks["u1"]["status"], "Failed")
		self.assertIn("permission", marks["u1"]["error"].lower())
		self.assertEqual(emp.saves, 0)

	def test_a_row_that_can_not_be_read_says_so_on_its_months_other_rows(self):
		emp = _Employee("E1")
		marks, _ = self._run(
			[_record("u1", "E1", "CEOF", 60), _record("u2", "E1", "PFME", "sixty")], {"E1": emp}
		)
		self.assertIn("Percentage", marks["u2"]["error"])
		self.assertEqual(marks["u1"]["status"], "Failed")
		self.assertIn("another row for Oct 2026", marks["u1"]["error"])
		self.assertEqual(emp.saves, 0)

	def test_cost_centers_are_looked_up_once_per_upload(self):
		db = MagicMock()
		centers = [frappe._dict(name="CEOF - NHSB", cost_center_name="CEOF")]
		calls = []

		def get_all(doctype, **kw):
			calls.append(doctype)
			if doctype == "Cost Center":
				return centers
			return [
				_record(f"u{i}", "E1", "CEOF", 50 if i < 2 else 100, month=OCT if i < 2 else "2026-11")
				for i in range(3)
			]

		with (
			patch.object(upload.frappe, "get_all", side_effect=get_all),
			patch.object(upload.frappe, "get_doc", return_value=_Employee("E1")),
			patch.object(upload.frappe, "db", db),
			patch.object(upload, "find_employee", side_effect=lambda eid, name: eid),
		):
			upload.apply_uploads(["u0", "u1", "u2"])
		self.assertEqual(calls.count("Cost Center"), 1)

	def test_the_same_tag_twice_in_one_month_of_the_file_fails_that_person(self):
		emp = _Employee("E1")
		marks, _ = self._run([_record("u1", "E1", "CEOF", 50), _record("u2", "E1", "CEOF", 50)], {"E1": emp})
		self.assertEqual(marks["u1"]["status"], "Failed")
		self.assertIn("more than once", marks["u1"]["error"])
		self.assertEqual(emp.saves, 0)

	def test_an_unreadable_row_fails_alone_with_its_reason(self):
		emp = _Employee("E1")
		marks, _ = self._run(
			[_record("u1", "E1", "CEOF", 100), _record("u2", "E2", "PFME", 100, month="next month")],
			{"E1": emp},
		)
		self.assertEqual(marks["u1"]["status"], "Done")
		self.assertEqual(marks["u2"]["status"], "Failed")
		self.assertIn("2026-10", marks["u2"]["error"])

	def test_done_rows_keep_what_was_understood(self):
		marks, _ = self._run(
			[_record("u1", "E1", "CEOF", "0.6"), _record("u2", "E1", "PFME", "0.4")], {"E1": _Employee("E1")}
		)
		self.assertEqual(marks["u1"]["employee_id"], "E1")
		self.assertEqual(marks["u1"]["month"], OCT)
		self.assertEqual(marks["u1"]["percent"], 60)

	def test_excel_percent_cells_land_as_60_and_40(self):
		emp = _Employee("E1")
		self._run([_record("u1", "E1", "CEOF", 0.6), _record("u2", "E1", "PFME", 0.4)], {"E1": emp})
		self.assertEqual([(r.cost_center, r.percentage) for r in emp.rows], [("CEOF", 60), ("PFME", 40)])

	def test_one_employee_failing_is_rolled_back_alone_and_says_why(self):
		bad = _Employee("E1", fail="Cost Tag/Center allocation for Oct 2026 must total 100%, currently 60%.")
		good = _Employee("E2")
		marks, db = self._run(
			[_record("u1", "E1", "CEOF", 60), _record("u2", "E2", "PFME", 100)], {"E1": bad, "E2": good}
		)
		self.assertEqual(marks["u1"]["status"], "Failed")
		self.assertIn("must total 100%", marks["u1"]["error"])
		self.assertEqual(marks["u2"]["status"], "Done")
		self.assertEqual(good.saves, 1)
		# each employee is its own savepoint; the failing one is rolled back to it
		self.assertEqual(db.savepoint.call_count, 2)  # one per employee
		db.rollback.assert_called_once_with(save_point=db.savepoint.call_args_list[0].args[0])

	def test_only_the_named_pending_rows_are_picked_up_oldest_first(self):
		with patch.object(upload.frappe, "get_all", return_value=[]) as ga:
			upload.apply_uploads(["u1", "u2"])
		first = ga.call_args_list[0]
		self.assertEqual(first.kwargs["filters"], {"status": "Pending", "name": ("in", ["u1", "u2"])})
		self.assertEqual(first.kwargs["order_by"], "creation asc")

	def test_the_employee_is_saved_as_a_desk_save_not_mid_import(self):
		seen = []

		class _Spy(_Employee):
			def save(self):
				seen.append(upload.frappe.flags.in_import)
				super().save()

		flags = frappe._dict(in_import=True)
		with patch.object(upload.frappe, "flags", flags):
			self._run([_record("u1", "E1", "CEOF", 100)], {"E1": _Spy("E1")})
		self.assertEqual(seen, [False])
		self.assertTrue(flags.in_import)


def _log(data_import, docname, rows):
	return frappe._dict(docname=docname, row_indexes=json.dumps(rows), success=1)


class TestWhenTheRowsAreApplied(unittest.TestCase):
	"""Data Import sets "Partial Success" after its FIRST row (importer.py), so
	the status alone does not mean the import has ended. It has ended when the
	log covers every row of the file (payload_count)."""

	def _hook(self, doc, logs):
		with (
			patch.object(upload.frappe, "get_all", return_value=logs),
			patch.object(upload, "apply_uploads") as apply,
		):
			upload.after_data_import(doc)
		return apply

	def _doc(self, status, count=2, doctype="Employee Cost Tag"):
		return frappe._dict(name="DI-1", status=status, reference_doctype=doctype, payload_count=count)

	def test_mid_import_partial_success_does_nothing(self):
		apply = self._hook(self._doc("Partial Success", count=2), [_log("DI-1", "u1", [2])])
		apply.assert_not_called()

	def test_when_every_row_is_logged_this_imports_rows_are_applied(self):
		logs = [_log("DI-1", "u1", [2]), _log("DI-1", "u2", [3])]
		apply = self._hook(self._doc("Success", count=2), logs)
		apply.assert_called_once_with(["u1", "u2"])

	def test_a_finished_import_with_some_failed_rows_still_applies_the_good_ones(self):
		logs = [_log("DI-1", "u1", [2]), frappe._dict(docname=None, row_indexes="[3]", success=0)]
		apply = self._hook(self._doc("Partial Success", count=2), logs)
		apply.assert_called_once_with(["u1"])

	def test_a_failed_import_marks_its_waiting_rows_failed_not_stuck(self):
		logs = [_log("DI-1", "u1", [2])]
		db = MagicMock()
		with (
			patch.object(upload.frappe, "get_all", return_value=logs),
			patch.object(upload.frappe, "db", db),
			patch.object(upload, "apply_uploads") as apply,
		):
			upload.after_data_import(self._doc("Error", count=2))
		apply.assert_not_called()
		args = db.set_value.call_args
		self.assertEqual(args.args[1], {"name": ("in", ["u1"]), "status": "Pending"})
		self.assertEqual(args.args[2]["status"], "Failed")
		self.assertIn("did not finish", args.args[2]["error"])

	def test_other_imports_are_ignored(self):
		apply = self._hook(self._doc("Success", doctype="Employee"), [])
		apply.assert_not_called()

	def test_the_hook_never_breaks_the_import(self):
		with (
			patch.object(upload.frappe, "get_all", side_effect=RuntimeError("db down")),
			patch.object(upload, "logger") as log,
		):
			upload.after_data_import(self._doc("Success"))
		log.exception.assert_called_once()

	def test_the_hook_is_wired_on_data_import_change(self):
		hooks = (ROOT / "hooks.py").read_text()
		block = hooks[hooks.index('"Data Import": {') :]
		block = block[: block.index("},")]
		self.assertIn("hrms.hr.doctype.employee_cost_tag.employee_cost_tag.after_data_import", block)
		self.assertIn("hrms.utils.naming_series_repair.after_data_import", block)


class TestTheUploadDoctype(unittest.TestCase):
	def _meta(self):
		return json.loads((ROOT / "hr/doctype/employee_cost_tag/employee_cost_tag.json").read_text())

	def test_the_template_columns_are_the_ones_hr_asked_for_in_order(self):
		m = self._meta()
		labels = {f["fieldname"]: f["label"] for f in m["fields"]}
		self.assertEqual(
			[labels[f] for f in m["field_order"][:6]],
			[
				"Employee ID",
				"Staff Name",
				"Year/Month",
				"Cost Tag/Center",
				"Old Cost Tag/Center",
				"Percentage",
			],
		)

	def test_status_and_reason_are_shown_but_not_typed(self):
		f = {x["fieldname"]: x for x in self._meta()["fields"]}
		self.assertEqual(f["status"]["options"].split("\n"), ["Pending", "Done", "Failed"])
		self.assertEqual(f["status"]["default"], "Pending")
		for name in ("status", "error"):
			self.assertEqual(f[name].get("read_only"), 1, name)

	def test_the_understood_tag_links_to_the_same_lists_as_the_profile(self):
		f = {x["fieldname"]: x for x in self._meta()["fields"]}
		self.assertEqual(f["cost_center_id"].get("ignore_user_permissions"), 1)
		self.assertEqual((f["territory"]["fieldtype"], f["territory"]["options"]), ("Link", "Territory"))
		for name in ("allocation_month", "percentage"):
			self.assertEqual(f[name].get("reqd"), 1, name)

	def test_it_is_called_employee_cost_tag_and_is_offered_in_data_import(self):
		# owner, 29 Oct 2026: typing "employee" in Data Import's Document Type
		# must offer "Employee Cost Tag"; Data Import lists only allow_import types
		m = json.loads((ROOT / "hr/doctype/employee_cost_tag/employee_cost_tag.json").read_text())
		self.assertEqual(m["name"], "Employee Cost Tag")
		self.assertEqual(m.get("allow_import"), 1)

	def test_only_hr_and_system_manager_can_upload(self):
		roles = {p["role"]: p for p in self._meta()["permissions"]}
		self.assertEqual(set(roles), {"System Manager", "HR Manager", "HR User"})
		for p in roles.values():
			self.assertEqual(p.get("import"), 1)
			self.assertEqual(p.get("create"), 1)

	def test_a_row_made_by_hand_in_desk_lands_at_once_but_an_imported_one_waits(self):
		src = (ROOT / "hr/doctype/employee_cost_tag/employee_cost_tag.py").read_text()
		self.assertRegex(
			src,
			r"def after_insert\(self\):\s*\n\s*if not frappe\.flags\.in_import:\s*\n(?:\s*#[^\n]*\n)?\s*apply_uploads\(\[self\.name\], merge_row=True\)",
		)


def setUpModule():
	# the stub's frappe.bold is a MagicMock; messages must show the real value
	global _bold
	_bold = patch.object(upload.frappe, "bold", side_effect=lambda v: str(v))
	_bold.start()


def tearDownModule():
	_bold.stop()


# ---------- trips, owner 29 Oct 2026: "things that can cause trip can we fix that" ----------


class TestReadMonth(unittest.TestCase):
	"""Whatever HR types or Excel stores, as long as it has a year."""

	def test_every_way_hr_writes_a_month(self):
		for value in (
			datetime.date(2026, 10, 17),
			datetime.datetime(2026, 10, 1, 0, 0),
			"2026-10",
			"2026-10-01",
			"2026/10",
			"Oct 2026",
			"October 2026",
			"oct-2026",
			"10/2026",
			"10-2026",
			"01/10/2026",
			" 2026-10 ",
			"2026-10-01 00:00:00",
			"2026-10-01T00:00:00",
			"Oct-26",
			"oct 26",
		):
			self.assertEqual(upload.read_month(value), OCT, value)

	def test_no_year_or_nonsense_is_refused_with_an_example(self):
		for value in ("Oct", "10", "", None, "next month", "13/2026"):
			with self.assertRaises(frappe.ValidationError, msg=value) as ctx:
				upload.read_month(value)
			self.assertIn("2026-10", str(ctx.exception))


class TestReadPercent(unittest.TestCase):
	def test_number_or_with_a_percent_sign(self):
		self.assertEqual(upload.read_percent("60"), 60)
		self.assertEqual(upload.read_percent("60%"), 60)
		self.assertEqual(upload.read_percent(" 40 % "), 40)
		self.assertEqual(upload.read_percent(33.5), 33.5)

	def test_blank_or_text_is_refused(self):
		for value in ("", None, "sixty", "-5", "0"):
			with self.assertRaises(frappe.ValidationError, msg=value):
				upload.read_percent(value)

	def test_excel_percent_cells_are_scaled_when_the_month_adds_up_to_one(self):
		# Excel stores a 60% cell as 0.6
		self.assertEqual(upload.scale_fractions([0.6, 0.4]), [60, 40])
		self.assertEqual(upload.scale_fractions([1]), [100])
		self.assertEqual(upload.scale_fractions([60, 40]), [60, 40])
		self.assertEqual(upload.scale_fractions([0.5, 50]), [0.5, 50])
		# three rounded thirds from Excel sum to 0.9999
		self.assertEqual(upload.scale_fractions([0.3333, 0.3333, 0.3334]), [33.33, 33.33, 33.34])


class TestFindCostCenter(unittest.TestCase):
	CENTERS = (
		frappe._dict(name="CEOF - NHSB", cost_center_name="CEOF"),
		frappe._dict(name="PFME - NHSB", cost_center_name="PFME"),
		frappe._dict(name="Main - NHSB", cost_center_name="Main"),
		frappe._dict(name="Main - DSDS", cost_center_name="Main"),
	)

	def _find(self, value):
		with patch.object(upload.frappe, "get_all", return_value=self.CENTERS):
			return upload.find_cost_center(value)

	def test_the_short_name_or_the_full_name_any_case(self):
		for value in ("CEOF", "ceof", " CEOF - NHSB ", "ceof - nhsb"):
			self.assertEqual(self._find(value), "CEOF - NHSB", value)

	def test_a_short_name_in_two_companies_asks_for_the_full_name(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._find("Main")
		self.assertIn("Main - NHSB", str(ctx.exception))
		self.assertIn("Main - DSDS", str(ctx.exception))

	def test_an_unknown_tag_says_so(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._find("CEOFF")
		self.assertIn("CEOFF", str(ctx.exception))

	def test_only_enabled_leaf_cost_centers_are_looked_at(self):
		with patch.object(upload.frappe, "get_all", return_value=self.CENTERS) as ga:
			upload.find_cost_center("CEOF")
		self.assertEqual(ga.call_args.kwargs["filters"], {"is_group": 0, "disabled": 0})


class TestFindEmployee(unittest.TestCase):
	def _find(self, employee_id, name, rows):
		def get_all(doctype, filters=None, **kw):
			if "name" in (filters or {}):
				return [r for r in rows if r.name == filters["name"]]
			first = filters["employee_name"][1].strip("%").lower()
			return [r for r in rows if first in r.employee_name.lower()]

		with patch.object(upload.frappe, "get_all", side_effect=get_all):
			return upload.find_employee(employee_id, name)

	PEOPLE = (
		frappe._dict(name="HR-EMP-0001", employee_name="Ahmad bin Ali"),
		frappe._dict(name="HR-EMP-0002", employee_name="Siti Aminah"),
		frappe._dict(name="HR-EMP-0003", employee_name="Siti Aminah"),
	)

	def test_the_id_decides(self):
		self.assertEqual(self._find("HR-EMP-0001", "Ahmad bin Ali", self.PEOPLE), "HR-EMP-0001")

	def test_a_name_that_does_not_match_the_id_is_refused_naming_both(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._find("HR-EMP-0001", "Siti Aminah", self.PEOPLE)
		self.assertIn("Ahmad bin Ali", str(ctx.exception))
		self.assertIn("Siti Aminah", str(ctx.exception))

	def test_name_case_and_spaces_do_not_matter(self):
		self.assertEqual(self._find("HR-EMP-0001", "  ahmad BIN ali ", self.PEOPLE), "HR-EMP-0001")

	def test_a_name_stored_with_stray_spaces_is_still_found(self):
		people = (frappe._dict(name="HR-EMP-0009", employee_name="Nur  Aina "),)

		def get_all(doctype, filters=None, **kw):
			return list(people)

		with patch.object(upload.frappe, "get_all", side_effect=get_all) as ga:
			self.assertEqual(upload.find_employee(None, "Nur Aina"), "HR-EMP-0009")
		self.assertEqual(ga.call_args.kwargs["filters"]["employee_name"], ("like", "%Nur%"))

	def test_no_id_but_one_person_with_that_name_is_found(self):
		self.assertEqual(self._find(None, "Ahmad bin Ali", self.PEOPLE), "HR-EMP-0001")

	def test_no_id_and_two_people_with_that_name_asks_for_the_id(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._find(None, "Siti Aminah", self.PEOPLE)
		self.assertIn("HR-EMP-0002", str(ctx.exception))

	def test_an_unknown_id_says_so(self):
		with self.assertRaises(frappe.ValidationError):
			self._find("HR-EMP-9999", None, self.PEOPLE)


class TestTheFilesMonthReplacesTheMonth(unittest.TestCase):
	"""Owner, 29 Oct 2026: a year+month in the file is the truth for that
	person's year+month; months not in the file stay."""

	def test_a_tag_dropped_from_the_month_drops_off(self):
		oct_ceof = _existing(OCT, "CEOF - NHSB", pct=60)
		oct_pfme = _existing(OCT, "PFME - NHSB", pct=40)
		last_year = _existing(datetime.date(2025, 10, 1), "PFME - NHSB", pct=100)
		drop, add = upload.replace_months(
			[oct_ceof, oct_pfme, last_year],
			[
				frappe._dict(allocation_month=OCT, cost_center="CEOF - NHSB", territory=None, percentage=70),
				frappe._dict(allocation_month=OCT, cost_center="SPLY - NHSB", territory=None, percentage=30),
			],
		)
		self.assertEqual(drop, [oct_ceof, oct_pfme])
		self.assertEqual(
			[(r["cost_center"], r["percentage"]) for r in add], [("CEOF - NHSB", 70), ("SPLY - NHSB", 30)]
		)

	def test_the_same_month_of_another_year_is_left_alone(self):
		drop, _ = upload.replace_months(
			[_existing(datetime.date(2025, 10, 1), "CEOF - NHSB", pct=100)],
			[frappe._dict(allocation_month=OCT, cost_center="PFME - NHSB", territory=None, percentage=100)],
		)
		self.assertEqual(drop, [])

	def test_the_same_tag_twice_in_one_month_of_the_file_is_refused(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			upload.replace_months(
				[],
				[
					frappe._dict(
						allocation_month=OCT, cost_center="CEOF - NHSB", territory=None, percentage=50
					),
					frappe._dict(
						allocation_month=OCT, cost_center="CEOF - NHSB", territory=None, percentage=50
					),
				],
			)
		self.assertIn("CEOF - NHSB", str(ctx.exception))


class TestTheUploadIsTypedLoosely(unittest.TestCase):
	"""Year/Month, Cost Tag/Center and Percentage arrive as typed, so a cell
	Data Import would refuse outright becomes a per-row reason instead."""

	def _meta(self):
		m = json.loads((ROOT / "hr/doctype/employee_cost_tag/employee_cost_tag.json").read_text())
		return {f["fieldname"]: f for f in m["fields"]}

	def test_the_cells_hr_types_are_text(self):
		f = self._meta()
		for name in ("employee", "allocation_month", "cost_center", "percentage"):
			self.assertEqual(f[name]["fieldtype"], "Data", name)
		self.assertFalse(f["employee"].get("reqd"))

	def test_what_was_understood_is_kept_beside_what_was_typed(self):
		f = self._meta()
		self.assertEqual((f["employee_id"]["fieldtype"], f["employee_id"]["options"]), ("Link", "Employee"))
		self.assertEqual((f["month"]["fieldtype"]), "Date")
		self.assertEqual((f["cost_center_id"]["options"]), "Cost Center")
		for name in ("employee_id", "month", "cost_center_id", "percent"):
			self.assertEqual(f[name].get("read_only"), 1, name)

	def test_the_type_says_which_columns_to_tick(self):
		m = json.loads((ROOT / "hr/doctype/employee_cost_tag/employee_cost_tag.json").read_text())
		for label in ("Employee ID", "Staff Name", "Year/Month", "Cost Tag/Center", "Percentage"):
			self.assertIn(label, m["description"])

	def test_status_and_reason_from_the_template_are_ignored_on_upload(self):
		src = (ROOT / "hr/doctype/employee_cost_tag/employee_cost_tag.py").read_text()
		self.assertRegex(
			src, r"self\.employee_id = self\.month = self\.cost_center_id = self\.percent = None"
		)
		self.assertRegex(
			src,
			r"def before_insert\(self\):[\s\S]{0,300}self\.status = \"Pending\"[\s\S]{0,80}self\.error = None",
		)


if __name__ == "__main__":
	unittest.main()
