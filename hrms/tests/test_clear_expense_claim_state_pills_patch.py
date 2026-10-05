"""Frappe's own state pills on Expense Claim outrank the list script, so the site's DocType State rows are cleared.

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_clear_expense_claim_state_pills_patch.py
(The patch was also run on the real database on fresh.local with a savepoint: 6 standard rows removed, a
custom row kept, a second run a no-op, no claim touched.)
"""

import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.patches.v16_0 import clear_expense_claim_state_pills as patch_module

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _rows(*titles):
	return [frappe._dict(name=f"S-{i}", title=t, color="Gray") for i, t in enumerate(titles)]


class TestClearStatePills(unittest.TestCase):
	def _run(self, rows):
		with (
			patch.object(patch_module.frappe, "get_all", return_value=rows) as get_all,
			patch.object(patch_module.frappe, "delete_doc") as delete_doc,
			patch.object(patch_module.frappe, "clear_cache") as clear_cache,
		):
			patch_module.execute()
		return get_all, delete_doc, clear_cache

	def test_only_the_shipped_expense_claim_states_are_asked_for(self):
		get_all, _, _ = self._run([])
		filters = get_all.call_args.kwargs["filters"]
		self.assertEqual(filters, {"parent": "Expense Claim", "parenttype": "DocType", "custom": 0})

	def test_each_row_is_removed_and_the_cache_is_cleared(self):
		_, delete_doc, clear_cache = self._run(_rows("Draft", "Unpaid"))
		self.assertEqual([c.args for c in delete_doc.call_args_list], [("DocType State", "S-0"), ("DocType State", "S-1")])
		clear_cache.assert_called_once_with(doctype="Expense Claim")

	def test_nothing_to_remove_touches_nothing(self):
		_, delete_doc, clear_cache = self._run([])
		delete_doc.assert_not_called()
		clear_cache.assert_not_called()

	def test_the_doctype_json_ships_no_states_and_the_patch_is_listed(self):
		doctype = json.loads((HRMS_ROOT / "hr/doctype/expense_claim/expense_claim.json").read_text())
		self.assertEqual(doctype["states"], [])
		self.assertIn(
			"hrms.patches.v16_0.clear_expense_claim_state_pills",
			(HRMS_ROOT / "patches.txt").read_text().split("[post_model_sync]")[1],
		)


if __name__ == "__main__":
	unittest.main()
