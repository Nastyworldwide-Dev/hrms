"""A test's stand-in for a Frappe document must refuse what a real one refuses.

Three times in one day (28-29 Sep 2026) a stub test passed while the real
code failed on the bench: `doc[field] = x` worked on a dict-based stub and
raised TypeError on a real Document; stand-ins had no `db_set`; a stub
answered one-field reads only, while the approval chain reads several at
once. The real surface was read from the installed Frappe
(frappe/model/base_document.py): BaseDocument has no __getitem__/__setitem__,
and offers get / set / attribute access; Document adds db_set / run_method.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fake_document_is_honest.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fake_document import FakeDocument, fake_employees


class TestTheShapeOfARealDocument(unittest.TestCase):
	def test_fields_read_as_attributes_and_through_get(self):
		doc = FakeDocument("Leave Application", name="LA-1", status="Open")
		self.assertEqual(doc.status, "Open")
		self.assertEqual(doc.get("status"), "Open")
		self.assertIsNone(doc.get("missing"))
		self.assertEqual(doc.get("missing", default=0), 0)

	def test_item_access_is_refused_like_a_real_document(self):
		doc = FakeDocument("Leave Application", name="LA-1")
		with self.assertRaises(TypeError):
			doc["status"] = "Approved"
		with self.assertRaises(TypeError):
			doc["status"]

	def test_set_and_db_set_record_what_was_written(self):
		doc = FakeDocument("OT Request", name="OT-1")
		doc.set("status", "Approved")
		doc.db_set("approved_on", "2026-09-29 10:00:00", update_modified=False)
		self.assertEqual(doc.status, "Approved")
		self.assertEqual(doc.db_writes, [("approved_on", "2026-09-29 10:00:00")])

	def test_new_until_given_a_name(self):
		self.assertTrue(FakeDocument("Expense Claim").is_new())
		self.assertFalse(FakeDocument("Expense Claim", name="EXP-1").is_new())


class TestFakeEmployees(unittest.TestCase):
	"""frappe.db.get_value on Employee, as the approval chain calls it."""

	def setUp(self):
		self.get_value = fake_employees(
			{
				"EMP-YOU": {"user_id": "you@x", "reports_to": "EMP-MGR", "leave_approver": None},
				"EMP-MGR": {"user_id": "mgr@x", "reports_to": None, "status": "Active"},
			}
		)

	def test_one_field(self):
		self.assertEqual(self.get_value("Employee", "EMP-YOU", "reports_to"), "EMP-MGR")

	def test_several_fields_at_once(self):
		row = self.get_value("Employee", "EMP-MGR", ["user_id", "status"], as_dict=True)
		self.assertEqual((row.user_id, row.status), ("mgr@x", "Active"))

	def test_status_defaults_to_active(self):
		self.assertEqual(self.get_value("Employee", "EMP-YOU", "status"), "Active")

	def test_an_unknown_employee_is_none(self):
		self.assertIsNone(self.get_value("Employee", "EMP-NOBODY", "user_id"))
		self.assertIsNone(self.get_value("Employee", "EMP-NOBODY", ["user_id"], as_dict=True))


if __name__ == "__main__":
	unittest.main()
