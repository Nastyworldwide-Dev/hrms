"""OT Request: when it was approved, and whether HR has paid it (HR, 28 Sep 2026).

"Approved on" is stamped once, by the system, at the approval. "Payment" is
HR's own Pending/Paid mark: payroll does not link back to the request, so
the owner chose a manual dropdown. Only HR roles may set it; an employee
must not mark their own claim Paid.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_ot_request_approved_on_and_paid.py
"""

import datetime
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.hr.doctype.ot_request.ot_request import approval_time_from_versions, stamp_approved_on

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCTYPE = json.loads((ROOT / "hr/doctype/ot_request/ot_request.json").read_text())
FIELDS = {f["fieldname"]: f for f in DOCTYPE["fields"]}
NOW = datetime.datetime(2026, 9, 28, 10, 25)


class Doc(dict):
	__getattr__ = dict.get

	def __setattr__(self, key, value):
		self[key] = value


class TestApprovedOn(unittest.TestCase):
	def test_an_approval_is_stamped_with_the_moment(self):
		doc = Doc(status="Approved", approved_on=None)
		stamp_approved_on(doc, NOW)
		self.assertEqual(doc.approved_on, NOW)

	def test_a_rejection_is_not_an_approval(self):
		doc = Doc(status="Rejected", approved_on=None)
		stamp_approved_on(doc, NOW)
		self.assertIsNone(doc.approved_on)

	def test_a_value_set_on_the_draft_is_not_trusted(self):
		# read-only is a screen control; an import could have set one
		doc = Doc(status="Approved", approved_on=datetime.datetime(2020, 1, 1))
		stamp_approved_on(doc, NOW)
		self.assertEqual(doc.approved_on, NOW)

	def test_a_rejection_clears_a_planted_value(self):
		doc = Doc(status="Rejected", approved_on=datetime.datetime(2020, 1, 1))
		stamp_approved_on(doc, NOW)
		self.assertIsNone(doc.approved_on)

	def test_the_field_is_read_only_and_kept_on_amend_off(self):
		field = FIELDS["approved_on"]
		self.assertEqual(field["fieldtype"], "Datetime")
		self.assertEqual(field.get("read_only"), 1)
		self.assertEqual(field.get("no_copy"), 1, "an amendment is a new decision")


class TestApprovalTimeFromHistory(unittest.TestCase):
	def test_the_version_that_submitted_it_approved(self):
		versions = [
			("2026-09-24 17:58:21", {"changed": [["status", "Open", "Approved"], ["docstatus", 0, 1]]}),
			("2026-09-24 17:57:00", {"changed": [["claimed_hours", 2, 3]]}),
		]
		self.assertEqual(approval_time_from_versions(versions), "2026-09-24 17:58:21")

	def test_a_submit_without_the_status_change_still_counts(self):
		# Requests submitted before the decision field existed: submitting WAS approving.
		versions = [("2026-09-10 08:00:00", {"changed": [["docstatus", 0, 1]]})]
		self.assertEqual(approval_time_from_versions(versions), "2026-09-10 08:00:00")

	def test_no_submit_in_history_means_unknown(self):
		versions = [("2026-09-10 08:00:00", {"changed": [["docstatus", 1, 2]]})]
		self.assertIsNone(approval_time_from_versions(versions))

	def test_the_earliest_submit_wins(self):
		versions = [
			("2026-09-12 08:00:00", {"changed": [["docstatus", 0, 1]]}),
			("2026-09-11 08:00:00", {"changed": [["docstatus", 0, 1]]}),
		]
		self.assertEqual(approval_time_from_versions(versions), "2026-09-11 08:00:00")


class TestReusedName(unittest.TestCase):
	"""A deleted request's name is handed to the next one (the alpha.13
	re-used-name class). Its history stays under that name, so only the
	history written after THIS request was created is its own."""

	def test_an_earlier_request_under_the_same_name_is_not_this_one(self):
		versions = [
			("2026-09-24 08:57:04", {"changed": [["docstatus", 0, 1]]}),
			("2026-09-24 09:24:41", {"changed": [["docstatus", 1, 2]]}),
			("2026-09-24 17:58:21", {"changed": [["docstatus", 0, 1]]}),
		]
		self.assertEqual(
			approval_time_from_versions(versions, since="2026-09-24 17:58:00"), "2026-09-24 17:58:21"
		)

	def test_no_submit_since_creation_means_unknown(self):
		versions = [("2026-09-24 08:57:04", {"changed": [["docstatus", 0, 1]]})]
		self.assertIsNone(approval_time_from_versions(versions, since="2026-09-24 17:58:00"))


class TestPaymentStatus(unittest.TestCase):
	def test_hr_sets_pending_or_paid_after_approval(self):
		field = FIELDS["payment_status"]
		self.assertEqual(field["fieldtype"], "Select")
		self.assertEqual(field["options"].split("\n"), ["Pending", "Paid"])
		self.assertEqual(field.get("default"), "Pending")
		self.assertEqual(field.get("allow_on_submit"), 1, "set after the approval")
		self.assertEqual(field.get("no_copy"), 1)

	def test_only_hr_roles_may_write_it(self):
		level = FIELDS["payment_status"].get("permlevel")
		self.assertGreater(level or 0, 0, "on its own permission level")
		writers = {
			p["role"] for p in DOCTYPE["permissions"] if p.get("permlevel", 0) == level and p.get("write")
		}
		self.assertEqual(writers, {"HR Manager", "HR User", "System Manager"})
		readers = {p["role"] for p in DOCTYPE["permissions"] if p.get("permlevel", 0) == level}
		self.assertIn("Employee", readers, "the employee can see whether it was paid")

	def test_both_show_in_the_report_view(self):
		for name in ("approved_on", "payment_status"):
			self.assertEqual(
				FIELDS[name].get("in_list_view") or FIELDS[name].get("in_standard_filter"), 1, name
			)


if __name__ == "__main__":
	unittest.main()


class TestCustomDocPermSites(unittest.TestCase):
	"""A site that edited OT Request's Role Permissions carries Custom DocPerm
	rows, and Frappe then ignores the JSON permissions entirely — HR could not
	set Payment. The patch mirrors the level-1 rows there."""

	def _run(self, existing):
		from unittest.mock import MagicMock, patch

		import frappe

		from hrms.patches.v16_0 import ot_request_approved_on_and_payment as patch_mod

		inserted = []
		db = MagicMock()
		db.exists.side_effect = lambda doctype, filters=None: (
			bool(existing)
			if filters == {"parent": "OT Request"}
			else (filters.get("role"), filters.get("permlevel")) in existing
		)
		with (
			patch.object(frappe, "db", db),
			patch.object(
				frappe, "get_doc", side_effect=lambda d: MagicMock(insert=lambda **kw: inserted.append(d))
			),
			patch.object(frappe, "clear_cache", create=True),
		):
			patch_mod.mirror_level_one_permissions()
		return inserted

	def test_a_site_without_custom_rows_is_left_to_the_json(self):
		self.assertEqual(self._run(existing=set()), [])

	def test_a_site_with_custom_rows_gets_hr_write_and_employee_read(self):
		rows = self._run(existing={("HR User", 0)})
		got = {(r["role"], r["permlevel"], r["read"], r["write"]) for r in rows}
		self.assertEqual(
			got,
			{
				("HR User", 1, 1, 1),
				("HR Manager", 1, 1, 1),
				("System Manager", 1, 1, 1),
				("Employee", 1, 1, 0),
			},
		)
		for r in rows:
			self.assertEqual(r["submit"], 0)
			self.assertEqual(r["delete"], 0)

	def test_a_row_already_there_is_not_added_again(self):
		rows = self._run(existing={("HR User", 0), ("HR User", 1)})
		self.assertNotIn("HR User", {r["role"] for r in rows})
