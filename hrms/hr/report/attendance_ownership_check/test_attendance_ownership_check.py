"""The page and the classifier cannot drift apart.

hrms/tests/test_attendance_ownership_report.py pins the report's behaviour —
its columns, its company fence, its filters and that it never writes. This file
pins the seams BETWEEN the report, the classifier and the page's own JavaScript:
a new owner label the Python gains must reach the filter and the colours, and a
window too wide to preview must not quietly preview anyway.

	PYTHONPATH=. python3 hrms/hr/report/attendance_ownership_check/test_attendance_ownership_check.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

HRMS = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HRMS / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.report.attendance_ownership_check import attendance_ownership_check as report
from hrms.utils import attendance_ownership as own

JS = (pathlib.Path(__file__).parent / "attendance_ownership_check.js").read_text()


def _row(name, employee="E1"):
	return {
		"employee": employee,
		"employee_name": "Ria",
		"date": "2026-08-12",
		"attendance": name,
		"status": "Present",
		"working_hours": 9.0,
		"owner": own.OWNER_SYSTEM,
		"reason": "the hourly job marked it",
		"would_relabel": True,
	}


class TestEveryOwnerReachesThePage(unittest.TestCase):
	def test_each_label_the_classifier_can_return_has_words_hr_can_read(self):
		for owner in own.OWNERS:
			self.assertIn(owner, report.OWNER_LABELS, owner)
			self.assertTrue(str(report.OWNER_LABELS[owner]).strip(), owner)

	def test_the_filter_offers_every_owner_the_classifier_can_return(self):
		options = JS[JS.index('fieldname: "owner"') :]
		options = options[options.index("options: [") : options.index("]", options.index("options: ["))]
		for owner in own.OWNERS:
			self.assertIn(f'"{owner}"', options, owner)

	def test_the_colours_cover_every_owner_so_no_row_reads_blank(self):
		colours = JS[JS.index("const colour = {") : JS.index("}[data.owner]")]
		for owner in own.OWNERS:
			self.assertIn(f"{owner}:", colours, owner)

	def test_the_page_starts_where_the_report_module_says_it_does(self):
		self.assertIn(str(report.START_FLOOR), JS)


class TestThePreviewCap(unittest.TestCase):
	"""A month-wide window must not compute a preview per row and time HR out."""

	def _rows(self, count):
		rows = [_row(f"ATT-{i}") for i in range(count)]
		with (
			patch.object(report.own, "classify_window", return_value=rows),
			patch.object(report, "_employee_info", return_value={}),
			patch.object(report, "scoped_companies", return_value=[]),
			patch.object(report, "preview_for", MagicMock(return_value="Present · 9.0h · X")) as preview,
		):
			out = report._rows(frappe._dict(from_date="2026-08-01", to_date="2026-08-31"))
		return out, preview

	def test_a_short_window_previews_every_row(self):
		out, preview = self._rows(3)
		self.assertEqual(preview.call_count, 3)
		self.assertTrue(all(r["preview"] for r in out))

	def test_a_window_past_the_cap_says_so_instead_of_previewing(self):
		out, preview = self._rows(report.PREVIEW_LIMIT + 1)
		preview.assert_not_called()
		self.assertIn("narrow", out[0]["preview"].lower())

	def test_the_employee_filter_is_pushed_down_to_the_classifier(self):
		window = MagicMock(return_value=[])
		with (
			patch.object(report.own, "classify_window", window),
			patch.object(report, "_employee_info", return_value={}),
			patch.object(report, "scoped_companies", return_value=[]),
		):
			report._rows(frappe._dict(from_date="2026-08-01", to_date="2026-08-31", employee="E7"))
		self.assertEqual(window.call_args.kwargs["employees"], ["E7"])


if __name__ == "__main__":
	unittest.main()
