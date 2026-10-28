"""Cost Tag/Center from an Excel upload (Data Import → "Cost Tag/Center Upload").

Owner, 28 Oct 2026: "just follow the file upload: if have same existing can
replace, if new then new row; the name and staff id is for you to read where to
put". One Excel row = one upload record; it lands on that employee's Cost
Tag/Center Allocation table (Employee → Overview).

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_cost_tag_center_upload.py
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

from hrms.hr.doctype.cost_tag_center_upload import cost_tag_center_upload as upload

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

	def __init__(self, name, rows=(), fail=None):
		self.name = name
		self.rows = list(rows)
		self.fail = fail
		self.saves = 0

	def get(self, key):
		return self.rows

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


class TestApplyPendingUploads(unittest.TestCase):
	"""Data Import saves one Excel row at a time, so a 60/40 month would be 60%
	after the first row and refused. The rows wait (Pending) until the import
	ends, then each employee's rows go on together, with one save."""

	def _run(self, records, employees):
		db = MagicMock()
		with (
			patch.object(upload.frappe, "get_all", return_value=records),
			patch.object(upload.frappe, "get_doc", side_effect=lambda dt, name: employees[name]),
			patch.object(upload.frappe, "db", db),
		):
			upload.apply_pending_uploads()
		marks = {}
		for c in db.set_value.call_args_list:
			marks[c.args[1]] = c.args[2]
		return marks

	def test_a_split_month_lands_whole_with_one_save(self):
		emp = _Employee("E1")
		marks = self._run([_record("u1", "E1", "CEOF", 60), _record("u2", "E1", "PFME", 40)], {"E1": emp})
		self.assertEqual([(r.cost_center, r.percentage) for r in emp.rows], [("CEOF", 60), ("PFME", 40)])
		self.assertEqual(emp.saves, 1)
		self.assertEqual(marks["u1"]["status"], "Done")
		self.assertEqual(marks["u2"]["status"], "Done")

	def test_an_existing_row_is_replaced_and_a_new_one_added(self):
		emp = _Employee("E1", [_existing(OCT, "CEOF", pct=100)])
		self._run([_record("u1", "E1", "CEOF", 70), _record("u2", "E1", "PFME", 30)], {"E1": emp})
		self.assertEqual([(r.cost_center, r.percentage) for r in emp.rows], [("CEOF", 70), ("PFME", 30)])

	def test_the_same_row_twice_in_one_file_is_one_row(self):
		emp = _Employee("E1")
		self._run([_record("u1", "E1", "CEOF", 50), _record("u2", "E1", "CEOF", 100)], {"E1": emp})
		self.assertEqual([(r.cost_center, r.percentage) for r in emp.rows], [("CEOF", 100)])

	def test_one_employee_failing_does_not_stop_the_others_and_says_why(self):
		bad = _Employee("E1", fail="Cost Tag/Center allocation for Oct 2026 must total 100%, currently 60%.")
		good = _Employee("E2")
		marks = self._run(
			[_record("u1", "E1", "CEOF", 60), _record("u2", "E2", "PFME", 100)], {"E1": bad, "E2": good}
		)
		self.assertEqual(marks["u1"]["status"], "Failed")
		self.assertIn("must total 100%", marks["u1"]["error"])
		self.assertEqual(marks["u2"]["status"], "Done")
		self.assertEqual(good.saves, 1)

	def test_only_pending_rows_are_picked_up_oldest_first(self):
		with patch.object(upload.frappe, "get_all", return_value=[]) as ga:
			upload.apply_pending_uploads()
		self.assertEqual(ga.call_args.kwargs["filters"], {"status": "Pending"})
		self.assertEqual(ga.call_args.kwargs["order_by"], "creation asc")


class TestWhenTheRowsAreApplied(unittest.TestCase):
	def test_after_a_data_import_of_uploads_the_pending_rows_are_applied(self):
		doc = frappe._dict(status="Success", reference_doctype="Cost Tag/Center Upload")
		with patch.object(upload, "apply_pending_uploads") as apply:
			upload.after_data_import(doc)
		apply.assert_called_once()

	def test_other_imports_and_unfinished_ones_are_ignored(self):
		with patch.object(upload, "apply_pending_uploads") as apply:
			upload.after_data_import(frappe._dict(status="Success", reference_doctype="Employee"))
			upload.after_data_import(
				frappe._dict(status="Pending", reference_doctype="Cost Tag/Center Upload")
			)
		apply.assert_not_called()

	def test_the_hook_is_wired_on_data_import_change(self):
		hooks = (ROOT / "hooks.py").read_text()
		block = hooks[hooks.index('"Data Import": {') :]
		block = block[: block.index("},")]
		self.assertIn(
			"hrms.hr.doctype.cost_tag_center_upload.cost_tag_center_upload.after_data_import", block
		)
		self.assertIn("hrms.utils.naming_series_repair.after_data_import", block)


class TestTheUploadDoctype(unittest.TestCase):
	def _meta(self):
		return json.loads(
			(ROOT / "hr/doctype/cost_tag_center_upload/cost_tag_center_upload.json").read_text()
		)

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

	def test_the_tags_link_to_the_same_lists_as_the_profile(self):
		f = {x["fieldname"]: x for x in self._meta()["fields"]}
		self.assertEqual((f["employee"]["fieldtype"], f["employee"]["options"]), ("Link", "Employee"))
		self.assertEqual(
			(f["cost_center"]["fieldtype"], f["cost_center"]["options"]), ("Link", "Cost Center")
		)
		self.assertEqual(f["cost_center"].get("ignore_user_permissions"), 1)
		self.assertEqual((f["territory"]["fieldtype"], f["territory"]["options"]), ("Link", "Territory"))
		for name in ("employee", "allocation_month", "percentage"):
			self.assertEqual(f[name].get("reqd"), 1, name)

	def test_only_hr_and_system_manager_can_upload(self):
		roles = {p["role"]: p for p in self._meta()["permissions"]}
		self.assertEqual(set(roles), {"System Manager", "HR Manager", "HR User"})
		for p in roles.values():
			self.assertEqual(p.get("import"), 1)
			self.assertEqual(p.get("create"), 1)

	def test_a_row_made_by_hand_in_desk_lands_at_once_but_an_imported_one_waits(self):
		src = (ROOT / "hr/doctype/cost_tag_center_upload/cost_tag_center_upload.py").read_text()
		self.assertRegex(
			src,
			r"def after_insert\(self\):\s*\n\s*if not frappe\.flags\.in_import:\s*\n\s*apply_pending_uploads\(\)",
		)


if __name__ == "__main__":
	unittest.main()
