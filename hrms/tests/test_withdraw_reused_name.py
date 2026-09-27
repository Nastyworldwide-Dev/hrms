"""Withdrawing your own draft is not blocked by a deleted request's leftovers.

Found 27 Sep 2026 (alpha.13 gate, WebKit): withdraw_request answered 417
LinkExistsError for a fresh DRAFT leave — "linked with Attendance
HR-ATT-2026-00067". That Attendance (cancelled) belonged to an EARLIER leave
with the same name: Frappe hands a deleted document's name back when it was
the newest in its series (delete_doc -> revert_series_if_last), so the next
request re-uses it and inherits every cancelled row still pointing at it.

A draft was never submitted, so nothing can legitimately depend on it: no
submitted row can reference a draft. What stands in the way is only cancelled
history (docstatus 2) keyed by the re-used name. Withdraw now ignores that and
still refuses when a LIVE row (draft or submitted) links to the request.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_withdraw_reused_name.py
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.api import withdraw_blockers


class TestWhatMayBlockAWithdraw(unittest.TestCase):
	def test_cancelled_rows_of_a_reused_name_do_not_block(self):
		links = [
			{"reference_doctype": "Attendance", "reference_docname": "HR-ATT-67", "docstatus": 2},
			{"reference_doctype": "Attendance", "reference_docname": "HR-ATT-68", "docstatus": 2},
		]
		self.assertEqual(withdraw_blockers(links), [])

	def test_a_live_row_still_blocks(self):
		links = [
			{"reference_doctype": "Attendance", "reference_docname": "HR-ATT-67", "docstatus": 2},
			{"reference_doctype": "Expense Claim", "reference_docname": "EXP-1", "docstatus": 0},
		]
		self.assertEqual([b["reference_docname"] for b in withdraw_blockers(links)], ["EXP-1"])


class TestTheWithdrawUsesIt(unittest.TestCase):
	def test_the_live_links_are_checked_here_then_the_delete_skips_its_own_check(self):
		src = (pathlib.Path(__file__).resolve().parents[1] / "api" / "__init__.py").read_text()
		body = src[src.index("def withdraw_request") : src.index("# staff lockdown")]
		self.assertIn("get_linked_docs(doc)", body)
		self.assertIn("check_if_doc_is_dynamically_linked(doc)", body)
		self.assertIn("withdraw_blockers(", body)
		self.assertIn("frappe.LinkExistsError", body)
		# the framework check would refuse on the cancelled rows; it runs only
		# after this one has refused every live link
		self.assertLess(body.index("withdraw_blockers("), body.index("force=True"))


if __name__ == "__main__":
	unittest.main()
