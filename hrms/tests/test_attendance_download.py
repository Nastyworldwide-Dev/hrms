"""Shift Attendance as an Excel file from Nadi (owner, 15 Oct 2026).

python3 hrms/tests/test_attendance_download.py
"""

import ast
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent.parent / "api" / "attendance_download.py"


def _lift(*names):
	tree = ast.parse(SOURCE.read_text())
	ns = {"calendar": __import__("calendar")}
	fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
	exec(compile(ast.Module(body=fns, type_ignores=[]), str(SOURCE), "exec"), ns)
	return ns


class TestMonth(unittest.TestCase):
	def setUp(self):
		self.range = _lift("month_range")["month_range"]

	def test_a_month_is_its_first_to_its_last_day(self):
		self.assertEqual(self.range("2026-10"), ("2026-10-01", "2026-10-31"))
		self.assertEqual(self.range("2026-09"), ("2026-09-01", "2026-09-30"))
		self.assertEqual(self.range("2028-02"), ("2028-02-01", "2028-02-29"))

	def test_anything_else_is_refused(self):
		for bad in ("2026-13", "2026-00", "1999-01", "abc", "2026"):
			with self.assertRaises(ValueError):
				self.range(bad)


class TestSheet(unittest.TestCase):
	def setUp(self):
		self.rows = _lift("sheet_rows", "_cell")["sheet_rows"]

	def test_header_then_one_row_per_day_without_hidden_columns(self):
		import datetime

		cols = [
			{"fieldname": "employee", "label": "Employee"},
			{"fieldname": "employee_name", "label": "Employee Name", "hidden": 1},
			{"fieldname": "attendance_date", "label": "Attendance Date"},
			{"fieldname": "working_hours", "label": "Total Working Hours"},
		]
		data = [
			{
				"employee": "E1",
				"employee_name": "Mia",
				"attendance_date": datetime.date(2026, 10, 1),
				"working_hours": 8.5,
			}
		]
		self.assertEqual(
			self.rows(cols, data),
			[["Employee", "Attendance Date", "Total Working Hours"], ["E1", "2026-10-01", 8.5]],
		)


class TestOnlyTheViewer(unittest.TestCase):
	def test_both_endpoints_require_the_role_first(self):
		tree = ast.parse(SOURCE.read_text())
		for name in ("download", "my_company"):
			fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
			first = fn.body[1] if isinstance(fn.body[0], ast.Expr) else fn.body[0]
			self.assertIn("_require_viewer()", ast.unparse(first), name)

	def test_rows_come_from_the_report_itself(self):
		self.assertIn(
			"from hrms.hr.report.shift_attendance.shift_attendance import execute", SOURCE.read_text()
		)


if __name__ == "__main__":
	unittest.main()
