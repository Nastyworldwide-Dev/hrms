"""An Attendance Report Viewer can download Shift Attendance, nothing more
(owner, 15 Oct 2026: the Shenzhen staff count the month in Excel).

    python3 hrms/tests/test_attendance_viewer_export.py
"""

import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATCH = ROOT / "patches" / "v16_0" / "let_attendance_report_viewer_export.py"


class TestExportOnly(unittest.TestCase):
	def setUp(self):
		self.src = PATCH.read_text()
		self.tree = ast.parse(self.src)

	def test_read_report_and_export_on_attendance_only(self):
		loop = next(n for n in ast.walk(self.tree) if isinstance(n, ast.For))
		self.assertEqual(ast.literal_eval(loop.iter), ("read", "report", "export"))
		self.assertIn('add_permission("Attendance", ATTENDANCE_VIEWER_ROLE, 0)', self.src)

	def test_never_write_create_or_submit(self):
		for ptype in ('"write"', '"create"', '"submit"', '"delete"'):
			self.assertNotIn(ptype, self.src)

	def test_registered(self):
		self.assertIn(
			"hrms.patches.v16_0.let_attendance_report_viewer_export", (ROOT / "patches.txt").read_text()
		)


if __name__ == "__main__":
	unittest.main()
