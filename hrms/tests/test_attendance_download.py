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
	fns = [
		n
		for n in tree.body
		if (isinstance(n, ast.FunctionDef) and n.name in names)
		or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in ("FORMULA_START", "SHEET_SHOWS"))
	]
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

	def test_the_sheet_names_each_employee_but_keeps_other_hidden_columns_out(self):
		import datetime

		cols = [
			{"fieldname": "employee", "label": "Employee"},
			{"fieldname": "employee_name", "label": "Employee Name", "hidden": 1},
			{"fieldname": "attendance_date", "label": "Attendance Date"},
			{"fieldname": "working_hours", "label": "Total Working Hours"},
			{"fieldname": "hr_owned", "label": "HR Owned", "hidden": 1},
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
			[
				["Employee", "Employee Name", "Attendance Date", "Total Working Hours"],
				["E1", "Mia", "2026-10-01", 8.5],
			],
		)


class TestNoFormulas(unittest.TestCase):
	"""Security review of 5bff5d377: Frappe 16 writes a "=..." string as a live formula."""

	def setUp(self):
		ns = {}
		tree = ast.parse(SOURCE.read_text())
		nodes = [
			n
			for n in tree.body
			if (isinstance(n, ast.FunctionDef) and n.name == "_cell")
			or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "FORMULA_START")
		]
		exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), ns)
		self.cell = ns["_cell"]

	def test_text_that_would_run_as_a_formula_is_written_as_text(self):
		for bad in ('=HYPERLINK("http://x","y")', "+1", "-2+3", "@SUM(A1)", "\tx"):
			self.assertTrue(self.cell(bad).startswith("'"), bad)

	def test_plain_text_numbers_and_blanks_are_unchanged(self):
		self.assertEqual(self.cell("Shenzhen"), "Shenzhen")
		self.assertEqual(self.cell(8.5), 8.5)
		self.assertIsNone(self.cell(None))

	def test_a_negative_number_stays_a_number_but_text_like_it_does_not(self):
		"""Review of e7119aeaa: pin the number-versus-text split."""
		self.assertEqual(self.cell(-5), -5)
		self.assertEqual(self.cell("-0h 5m"), "'-0h 5m")


class TestMonthShape(unittest.TestCase):
	def test_only_yyyy_mm_reaches_the_report_and_the_file_name(self):
		src = SOURCE.read_text()
		self.assertIn('MONTH = re.compile(r"\\d{4}-\\d{2}", re.ASCII)', src)
		self.assertIn("MONTH.fullmatch(month)", src)
		self.assertIn('f"shift-attendance-{from_date[:7]}"', src)


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
