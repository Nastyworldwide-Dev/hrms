"""The Shift Attendance columns everyone sees stay as they were before HR editing.

95e669114 replaced the visible "Attendance ID" link column with the hidden
hr_owned flag the edit grid reads (Group 2-4 review W5, 14 Sep 2026), so staff
lost the link to the Attendance row. The flag is an extra hidden column; the
link column is back exactly as before.

Bench-free: get_columns is read from the source and run with `_` as identity.
Run it as a FILE:

    python3 hrms/hr/report/shift_attendance/test_shift_attendance_columns.py
"""

import ast
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).with_name("shift_attendance.py")


def get_columns():
	tree = ast.parse(SOURCE.read_text())
	func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_columns")
	namespace = {"_": lambda text: text}
	exec(compile(ast.Module(body=[func], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace["get_columns"]()


class TestColumns(unittest.TestCase):
	def test_the_attendance_id_link_column_is_visible_as_before(self):
		column = next((c for c in get_columns() if c["fieldname"] == "name"), None)
		self.assertEqual(
			column,
			{
				"label": "Attendance ID",
				"fieldname": "name",
				"fieldtype": "Link",
				"options": "Attendance",
				"width": 150,
			},
		)

	def test_hr_owned_is_an_extra_hidden_column_after_it(self):
		columns = get_columns()
		self.assertEqual([c["fieldname"] for c in columns][-2:], ["name", "hr_owned"])
		self.assertEqual(columns[-1]["fieldtype"], "Check")
		self.assertEqual(columns[-1]["hidden"], 1)


if __name__ == "__main__":
	unittest.main()
