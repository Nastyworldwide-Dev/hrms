# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Delegates to the bench-free suite in hrms/tests/test_attendance_allowance.py.

That suite stubs `frappe` in sys.modules, so it must run in its own
interpreter — importing it here would clobber a live bench's frappe module.
"""

import pathlib
import subprocess
import sys
import unittest

SUITE = pathlib.Path(__file__).resolve().parents[3] / "tests" / "test_attendance_allowance.py"


class TestAttendanceAllowanceType(unittest.TestCase):
	def test_policy_suite_passes(self):
		result = subprocess.run([sys.executable, str(SUITE)], capture_output=True, text=True, check=False)
		self.assertEqual(result.returncode, 0, result.stderr)
