"""The filter chips on the Requests panel counted only the rows already
loaded — the newest ten of each type. An employee with 43 requests, 20 of
them rejected, saw "Not approved" empty (audit P0-8). The counts now come
from the server, over every request, with the same rule the chip on each row
reads (frontend/src/utils/requestStatus.js): a draft is waiting; a submitted
request is approved or not by its decision field; a cancelled one is neither.
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import request_counts

ROWS = {
	"Leave Application": [
		{"docstatus": 0, "status": "Open", "n": 3},
		{"docstatus": 1, "status": "Approved", "n": 5},
		{"docstatus": 1, "status": "Rejected", "n": 20},
		{"docstatus": 2, "status": "Approved", "n": 4},
	],
	"Expense Claim": [
		{"docstatus": 0, "approval_status": "Draft", "n": 1},
		{"docstatus": 1, "approval_status": "Approved", "n": 2},
		{"docstatus": 1, "approval_status": "Rejected", "n": 1},
	],
}


def fake_get_all(doctype, filters=None, fields=None, group_by=None, **kw):
	assert filters["employee"] == "HR-EMP-1", "counts are the caller's own requests only"
	return [frappe._dict(r) for r in ROWS.get(doctype, [])]


class TestRequestCounts(unittest.TestCase):
	def _counts(self):
		with (
			patch.object(request_counts, "get_current_employee", return_value="HR-EMP-1"),
			patch.object(frappe, "get_all", side_effect=fake_get_all, create=True),
		):
			return request_counts.get_my_request_counts()

	def test_counts_cover_every_request_not_the_newest_ten(self):
		self.assertEqual(self._counts()["rejected"], 21)

	def test_each_chip_follows_the_row_rule(self):
		self.assertEqual(
			self._counts(),
			{"all": 32, "waiting": 4, "approved": 7, "rejected": 21},
		)

	def test_the_employee_is_the_session_never_a_parameter(self):
		import inspect

		self.assertEqual(list(inspect.signature(request_counts.get_my_request_counts).parameters), [])


if __name__ == "__main__":
	unittest.main()


class TestOneTypeFailing(unittest.TestCase):
	def test_one_missing_type_does_not_blank_the_other_chips(self):
		# A site without one request type (a missing app, an unmigrated table)
		# must not take every chip down with it; the page then showed an error
		# and no counts at all.
		def some_fail(doctype, **kw):
			if doctype == "Replacement Leave Claim":
				raise frappe.DoesNotExistError("DocType Replacement Leave Claim not found")
			return fake_get_all(doctype, **kw)

		with (
			patch.object(request_counts, "get_current_employee", return_value="HR-EMP-1"),
			patch.object(frappe, "get_all", side_effect=some_fail, create=True),
		):
			counts = request_counts.get_my_request_counts()
		self.assertGreater(counts["all"], 0)
