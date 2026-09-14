"""HR User may cancel a Shift Request (v16_0 patch) + the matching JSON row.

HR User held `cancel` on every other request doctype but not Shift Request.
Live sites carry Custom DocPerm rows, which make the doctype JSON permissions
inert, so the JSON edit alone does nothing there — the patch grants the flag on
the live row. Only an EXISTING HR User level-0 row is widened; no row is
created. Approved requests stay uncancellable regardless (see
test_approved_request_guard.py) — this grant only reaches rejected ones.

    PYTHONPATH=. python3 hrms/tests/test_hr_user_can_cancel_shift_request.py
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

HRMS_ROOT = Path(__file__).resolve().parents[1]
PATCH = "hrms.patches.v16_0.hr_user_can_cancel_shift_request"


class _PermTables:
	"""rows: {(table, parent, role): cancel_flag}"""

	def __init__(self, rows):
		self.rows = dict(rows)

	def exists(self, doctype, filters):
		return doctype == "Custom DocPerm" and any(
			k[0] == "Custom DocPerm" and k[1] == filters.get("parent") for k in self.rows
		)

	def get_value(self, doctype, filters, fieldname=None, **kwargs):
		key = (doctype, filters.get("parent"), filters.get("role"))
		if key not in self.rows:
			return None
		return frappe._dict(name="row", cancel=self.rows[key])


def _run(rows):
	from hrms.patches.v16_0 import hr_user_can_cancel_shift_request as patch_module

	tables = _PermTables(rows)
	db = MagicMock()
	db.exists.side_effect = tables.exists
	db.get_value.side_effect = tables.get_value
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "clear_cache", create=True),
		patch.object(patch_module, "update_permission_property") as update,
	):
		patch_module.execute()
	return [c.args[:5] for c in update.call_args_list]


class TestPatch(unittest.TestCase):
	def test_grants_on_a_custom_docperm_site(self):
		self.assertEqual(
			_run({("Custom DocPerm", "Shift Request", "HR User"): 0}),
			[("Shift Request", "HR User", 0, "cancel", 1)],
		)

	def test_grants_on_a_site_without_custom_perms(self):
		self.assertEqual(
			_run({("DocPerm", "Shift Request", "HR User"): 0}),
			[("Shift Request", "HR User", 0, "cancel", 1)],
		)

	def test_never_creates_a_row_for_hr_user(self):
		self.assertEqual(_run({("Custom DocPerm", "Shift Request", "HR Manager"): 1}), [])

	def test_is_idempotent(self):
		self.assertEqual(_run({("Custom DocPerm", "Shift Request", "HR User"): 1}), [])

	def test_registered_once_after_model_sync(self):
		lines = [
			line.split("#")[0].strip()
			for line in (HRMS_ROOT / "patches.txt").read_text(encoding="utf-8").splitlines()
		]
		self.assertEqual(lines.count(PATCH), 1)
		self.assertGreater(lines.index(PATCH), lines.index("[post_model_sync]"))


class TestShiftRequestJson(unittest.TestCase):
	def test_hr_user_row_grants_cancel_alongside_submit(self):
		perms = json.loads(
			(HRMS_ROOT / "hr/doctype/shift_request/shift_request.json").read_text(encoding="utf-8")
		)["permissions"]
		rows = [p for p in perms if p.get("role") == "HR User" and not p.get("permlevel")]
		self.assertEqual(len(rows), 1)
		# Frappe refuses cancel without submit on the same row (fresh-install abort).
		self.assertEqual((rows[0].get("cancel"), rows[0].get("submit")), (1, 1))


if __name__ == "__main__":
	unittest.main()
