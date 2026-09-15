"""`Employee.user_id` is stored the way the login is spelled.

A mirror writes the column through `db.set_value`, which does not normalize;
erpnext's `validate_employee_role` compares it to the User name EXACTLY and
strips the Employee role on every User save when it finds no match. The
resolver normalizes, so the person signs in fine and is refused every request
at the role gate. The patch removes the drift; it refuses to write a value
another Employee record already carries (that is a duplicate to reconcile).

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_normalize_employee_user_ids.py
"""

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

from hrms.patches.v16_0 import normalize_employee_user_ids as patch_module


def _rows(*rows):
	return [frappe._dict(name=n, user_id=u, status="Active") for n, u in rows]


class TestNormalizeRows(unittest.TestCase):
	def _run(self, rows):
		with patch.object(frappe.db, "set_value") as set_value:
			written = patch_module.normalize_rows(rows)
		return written, set_value

	def test_case_and_whitespace_drift_is_written_back_normalized(self):
		written, set_value = self._run(_rows(("E1", "  Amran@Example.com "), ("E2", "bob@example.com")))
		self.assertEqual(written, 1)
		set_value.assert_called_once_with(
			"Employee", "E1", "user_id", "amran@example.com", update_modified=False
		)

	def test_a_clean_site_writes_nothing_twice(self):
		written, set_value = self._run(_rows(("E1", "amran@example.com")))
		self.assertEqual(written, 0)
		set_value.assert_not_called()

	def test_a_login_two_records_claim_is_left_for_reconciliation(self):
		"""Writing the normalized value would turn a visible drift into an
		AMBIGUOUS login — the resolver would then deny the person outright."""
		written, set_value = self._run(_rows(("E1", "amran@example.com"), ("E9", "Amran@Example.com")))
		self.assertEqual(written, 0)
		set_value.assert_not_called()

	def test_execute_reads_only_linked_employees(self):
		with (
			patch.object(frappe, "get_all", return_value=[]) as get_all,
			patch.object(frappe.db, "set_value"),
		):
			patch_module.execute()
		self.assertEqual(get_all.call_args.kwargs["filters"], {"user_id": ("is", "set")})


class TestItIsWiredIntoTheNightlyHeal(unittest.TestCase):
	def test_listed_in_heal_known_shapes(self):
		from hrms.utils.request_access import HEALERS

		self.assertIn("hrms.patches.v16_0.normalize_employee_user_ids", HEALERS)


if __name__ == "__main__":
	unittest.main()
