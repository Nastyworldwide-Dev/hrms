"""Attachments load through the parent's permission, not the File list filter.

Live, 15 Sep 2026: every attachment panel in Nadi failed with
`(1267, "Illegal mix of collations (utf8mb4_general_ci,IMPLICIT) and
(utf8mb4_unicode_ci,IMPLICIT)")`. `get_attachments` read File through
`frappe.get_list`, which appends every installed app's permission condition —
the Helpdesk app's identity-graph filter builds its CTE with CAST(... AS CHAR),
which takes the connection collation and then clashes with the table columns.

The endpoint already proves the caller may read the parent document; Frappe's
own rule is that a readable document's attachments are readable. So the rows
are read by parent with no second permission filter, and no other app's list
condition can break the panel again.

    PYTHONPATH=. python3 hrms/tests/test_get_attachments_reads_by_parent.py
"""

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

ROWS = [{"name": "F1", "file_name": "mc.pdf", "file_url": "/private/files/mc.pdf", "is_private": 1}]


class TestGetAttachments(unittest.TestCase):
	def _call(self, has_permission):
		import hrms.api as api

		list_filter = MagicMock(side_effect=Exception("(1267, 'Illegal mix of collations')"))
		get_all = MagicMock(return_value=ROWS)
		with (
			patch.object(frappe, "has_permission", has_permission, create=True),
			patch.object(frappe, "get_list", list_filter),
			patch.object(frappe, "get_all", get_all),
		):
			result = api.get_attachments("Leave Application", "HR-LAP-2026-02667")
		return result, get_all, list_filter

	def test_a_readable_parent_lists_its_attachments_without_the_file_list_filter(self):
		result, get_all, list_filter = self._call(MagicMock(return_value=True))
		self.assertEqual(result, ROWS)
		list_filter.assert_not_called()
		kwargs = get_all.call_args.kwargs
		self.assertEqual(get_all.call_args.args[0], "File")
		self.assertEqual(
			kwargs["filters"],
			{"attached_to_doctype": "Leave Application", "attached_to_name": "HR-LAP-2026-02667"},
		)

	def test_the_parent_permission_is_still_checked_first(self):
		refused = MagicMock(side_effect=frappe.PermissionError("no"))
		with self.assertRaises(frappe.PermissionError):
			self._call(refused)
		refused.assert_called_once_with("Leave Application", doc="HR-LAP-2026-02667", throw=True)


if __name__ == "__main__":
	unittest.main()
