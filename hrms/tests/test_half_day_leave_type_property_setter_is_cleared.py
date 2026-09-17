"""A site's own override must not keep demanding a Leave Type on a half day.

2ed460509 narrowed `Attendance.leave_type.mandatory_depends_on` to On Leave in
the doctype JSON, so HR can save an hours-based Half Day again. A Property
Setter outranks the reloaded JSON, so a site where someone once opened
Customize Form on Attendance would still refuse the save after the release —
and the release would look like it had worked everywhere.

Nobody is asked to check. The patch clears that one override if it is there,
and does nothing if it is not.

    PYTHONPATH=. python3 -m pytest -q \
        hrms/tests/test_half_day_leave_type_property_setter_is_cleared.py
"""

from __future__ import annotations

import pathlib
import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.patches.v16_0 import half_day_leave_type_not_mandatory as patch_module

OVERRIDE = {
	"doc_type": "Attendance",
	"field_name": "leave_type",
	"property": "mandatory_depends_on",
}


class PatchCase(unittest.TestCase):
	def _run(self, existing: list[str]):
		db = MagicMock()
		db.get_all.return_value = list(existing)
		deleted: list[tuple] = []
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "delete_doc", side_effect=lambda *a, **k: deleted.append(a)),
			patch.object(frappe, "clear_cache", MagicMock()),
		):
			patch_module.execute()
		return db, deleted

	def test_it_looks_for_exactly_that_one_override(self):
		db, _ = self._run([])
		doctype, kwargs = db.get_all.call_args[0][0], db.get_all.call_args[1]
		self.assertEqual(doctype, "Property Setter")
		self.assertEqual(kwargs["filters"], OVERRIDE)

	def test_an_override_is_removed(self):
		_, deleted = self._run(["Attendance-leave_type-mandatory_depends_on"])
		self.assertEqual(deleted, [("Property Setter", "Attendance-leave_type-mandatory_depends_on")])

	def test_a_site_without_one_is_left_alone(self):
		"""Idempotent: the second run, and every clean site, must be a no-op."""
		_, deleted = self._run([])
		self.assertEqual(deleted, [])

	def test_it_is_registered_to_run_on_release(self):
		listed = (pathlib.Path(patch_module.__file__).resolve().parents[2] / "patches.txt").read_text()
		self.assertIn("hrms.patches.v16_0.half_day_leave_type_not_mandatory", listed)


if __name__ == "__main__":
	unittest.main()
