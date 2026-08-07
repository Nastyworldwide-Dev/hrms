# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""SOP Library row scope + API tests.

Pure unit tests: `frappe` is mocked, so these run without a bench or site
(same runnable pattern as hrms/tests/test_checkin_timezone.py).

What they pin down: an SOP is visible to an employee only when it is published
AND (General OR their own department). Everything else — no Employee record,
inactive employee, another department, unpublished — fails closed.
"""

import types
import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import sop as sop_api
from hrms.hr.doctype.sop_document.sop_document import SOPDocument
from hrms.overrides import sop_document_row_scope as row_scope

HR = "hr@example.com"
STAFF = "staff@example.com"
OTHER = "other@example.com"
NOBODY = "nobody@example.com"

EMPLOYEES = {
	# user_id: (name, department, status)
	STAFF: ("HR-EMP-001", "Operations - N", "Active"),
	OTHER: ("HR-EMP-002", "Finance - N", "Active"),
	HR: ("HR-EMP-003", "People's Office - N", "Active"),
	"left@example.com": ("HR-EMP-004", "Operations - N", "Left"),
	"nodept@example.com": ("HR-EMP-005", None, "Active"),
}

# Department is a nested-set tree: only leaf departments have direct members
DEPARTMENTS = {
	# name: is_group
	"Operations - N": 0,
	"Finance - N": 0,
	"All Departments - N": 1,
}

SOPS = [
	{
		"name": "HR-SOP-00001",
		"title": "Code of Conduct",
		"scope": "General",
		"department": None,
		"pinned": 0,
		"published": 1,
		"modified": "2026-08-01 10:00:00",
		"attachment": None,
	},
	{
		"name": "HR-SOP-00002",
		"title": "Emergency Contacts",
		"scope": "General",
		"department": None,
		"pinned": 1,
		"published": 1,
		"modified": "2026-08-02 10:00:00",
		"attachment": "/files/contacts.pdf",
	},
	{
		"name": "HR-SOP-00003",
		"title": "Ops Shift Handover",
		"scope": "Department",
		"department": "Operations - N",
		"pinned": 0,
		"published": 1,
		"modified": "2026-08-03 10:00:00",
		"attachment": None,
	},
	{
		"name": "HR-SOP-00004",
		"title": "Finance Petty Cash",
		"scope": "Department",
		"department": "Finance - N",
		"pinned": 0,
		"published": 1,
		"modified": "2026-08-04 10:00:00",
		"attachment": None,
	},
	{
		"name": "HR-SOP-00005",
		"title": "Draft Policy",
		"scope": "General",
		"department": None,
		"pinned": 0,
		"published": 0,
		"modified": "2026-08-05 10:00:00",
		"attachment": None,
	},
]


def _escape(value):
	return "'" + str(value).replace("'", "''") + "'"


def _fake_db():
	db = MagicMock()
	db.escape.side_effect = _escape

	def get_value(doctype, filters, fieldname=None, **kwargs):
		if doctype == "Employee":
			if not isinstance(filters, dict):
				return None
			row = EMPLOYEES.get(filters.get("user_id"))
			if not row:
				return None
			name, department, status = row
			if filters.get("status") and filters["status"] != status:
				return None
			values = {"name": name, "department": department, "status": status}
			if kwargs.get("as_dict") or isinstance(fieldname, list | tuple):
				if kwargs.get("as_dict"):
					keys = fieldname if isinstance(fieldname, list | tuple) else [fieldname]
					return frappe._dict({k: values.get(k) for k in keys})
				return [values.get(k) for k in fieldname]
			return values.get(fieldname)
		if doctype == "File":
			return "contacts.pdf"
		if doctype == "Department" and fieldname == "is_group":
			return DEPARTMENTS.get(filters)
		return None

	db.get_value.side_effect = get_value
	return db


def _fresh_local():
	local = types.SimpleNamespace()
	local.flags = frappe._dict(in_test=False)
	local.response = frappe._dict()
	return local


def _roles_for(user):
	if user == HR:
		return ["HR Manager", "Employee"]
	return ["Employee"]


class _Ctx:
	"""Patch the frappe surface these modules touch, for one session user."""

	def __init__(self, user, sops=None, file_rows=None):
		self.user = user
		self.sops = sops if sops is not None else SOPS
		self.file_rows = file_rows or []

	def __enter__(self):
		def get_list(doctype, filters=None, fields=None, **kwargs):
			# deliberately ignores filters: the modules under test must filter
			# in code as well (defense in depth), not rely on the query alone
			return [frappe._dict(row) for row in self.sops]

		def get_all(doctype, filters=None, fields=None, pluck=None, **kwargs):
			# only the File-table attachment fallback queries get_all here
			if doctype != "File":
				return []
			rows = [frappe._dict(row) for row in self.file_rows]
			if pluck:
				return [row.get(pluck) for row in rows]
			return rows

		self.patches = [
			patch.object(frappe, "db", _fake_db()),
			patch.object(frappe, "session", frappe._dict(user=self.user)),
			patch.object(frappe, "local", _fresh_local()),
			patch.object(frappe, "get_roles", side_effect=_roles_for),
			patch.object(frappe, "get_list", side_effect=get_list),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "has_permission", return_value=True),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()


class TestSopRowScope(unittest.TestCase):
	def test_employee_sees_published_general_and_own_department(self):
		with _Ctx(STAFF):
			condition = row_scope.get_permission_query_conditions(STAFF)
		self.assertIn("`published` = 1", condition)
		self.assertIn("'General'", condition)
		self.assertIn("'Operations - N'", condition)
		self.assertNotIn("Finance", condition)

	def test_hr_is_unrestricted(self):
		with _Ctx(HR):
			self.assertEqual(row_scope.get_permission_query_conditions(HR), "")

	def test_administrator_is_unrestricted(self):
		with _Ctx("Administrator"):
			self.assertEqual(row_scope.get_permission_query_conditions("Administrator"), "")

	def test_user_without_employee_record_fails_closed(self):
		with _Ctx(NOBODY):
			self.assertEqual(row_scope.get_permission_query_conditions(NOBODY), "1=0")

	def test_guest_fails_closed(self):
		with _Ctx("Guest"):
			self.assertEqual(row_scope.get_permission_query_conditions("Guest"), "1=0")

	def test_left_employee_fails_closed(self):
		with _Ctx("left@example.com"):
			self.assertEqual(row_scope.get_permission_query_conditions("left@example.com"), "1=0")

	def test_employee_without_department_sees_general_only(self):
		with _Ctx("nodept@example.com"):
			condition = row_scope.get_permission_query_conditions("nodept@example.com")
		self.assertIn("'General'", condition)
		self.assertNotIn("`department`", condition)

	def test_department_name_with_apostrophe_is_escaped(self):
		with _Ctx(HR):
			# HR user, but ask for the row scope of a plain employee whose
			# department name carries an apostrophe
			with patch.object(frappe, "get_roles", side_effect=lambda u: ["Employee"]):
				condition = row_scope.get_permission_query_conditions(HR)
		self.assertIn("'People''s Office - N'", condition)

	# --- has_permission ---

	def _doc(self, name):
		return frappe._dict(next(row for row in SOPS if row["name"] == name))

	def test_has_permission_allows_own_department_read(self):
		with _Ctx(STAFF):
			self.assertTrue(row_scope.has_permission(self._doc("HR-SOP-00003"), "read", STAFF))
			self.assertTrue(row_scope.has_permission(self._doc("HR-SOP-00001"), "select", STAFF))

	def test_has_permission_denies_other_department_and_unpublished(self):
		with _Ctx(STAFF):
			self.assertFalse(row_scope.has_permission(self._doc("HR-SOP-00004"), "read", STAFF))
			self.assertFalse(row_scope.has_permission(self._doc("HR-SOP-00005"), "read", STAFF))

	def test_has_permission_denies_writes_for_non_hr(self):
		with _Ctx(STAFF):
			for ptype in ("write", "create", "delete", "submit"):
				self.assertFalse(row_scope.has_permission(self._doc("HR-SOP-00001"), ptype, STAFF))

	def test_has_permission_allows_hr_everything(self):
		with _Ctx(HR):
			self.assertTrue(row_scope.has_permission(self._doc("HR-SOP-00005"), "read", HR))
			self.assertTrue(row_scope.has_permission(self._doc("HR-SOP-00004"), "write", HR))


class TestGetSops(unittest.TestCase):
	def test_employee_payload_is_scoped(self):
		with _Ctx(STAFF):
			data = sop_api.get_sops()

		self.assertFalse(data["is_hr"])
		self.assertEqual(data["my_department"], "Operations - N")
		# pinned SOPs appear only under "pinned"
		self.assertEqual([c["name"] for c in data["pinned"]], ["HR-SOP-00002"])
		self.assertEqual([c["name"] for c in data["general"]], ["HR-SOP-00001"])
		departments = {d["department"]: [c["name"] for c in d["sops"]] for d in data["departments"]}
		self.assertEqual(departments, {"Operations - N": ["HR-SOP-00003"]})
		# no unpublished, no other department, no bodies
		names = [c["name"] for group in ("pinned", "general") for c in data[group]]
		self.assertNotIn("HR-SOP-00005", names)
		self.assertNotIn("HR-SOP-00004", names)
		self.assertNotIn("content", data["general"][0])
		self.assertTrue(data["pinned"][0]["has_attachment"])
		self.assertFalse(data["general"][0]["has_attachment"])

	def test_file_row_fallback_sets_has_attachment(self):
		# field empty but a File row is attached (Desk sidebar / older uploads)
		file_rows = [
			{
				"attached_to_name": "HR-SOP-00001",
				"file_name": "guide.pdf",
				"file_url": "/private/files/guide.pdf",
			}
		]
		with _Ctx(STAFF, file_rows=file_rows):
			data = sop_api.get_sops()
		self.assertTrue(data["general"][0]["has_attachment"])

	def test_employee_without_department_sees_general_only(self):
		with _Ctx("nodept@example.com"):
			data = sop_api.get_sops()
		self.assertIsNone(data["my_department"])
		self.assertEqual(data["departments"], [])
		self.assertEqual([c["name"] for c in data["general"]], ["HR-SOP-00001"])

	def test_user_without_employee_is_denied(self):
		# frappe's translator needs a bench log dir — stub it out
		with (
			_Ctx(NOBODY),
			patch("hrms.api.sop._", lambda msg: msg),
			self.assertRaises(frappe.PermissionError),
		):
			sop_api.get_sops()

	def test_hr_sees_everything_including_unpublished(self):
		with _Ctx(HR):
			data = sop_api.get_sops()
		self.assertTrue(data["is_hr"])
		general = [c["name"] for c in data["general"]]
		self.assertIn("HR-SOP-00005", general)
		self.assertEqual(
			[d["department"] for d in data["departments"]],
			["Finance - N", "Operations - N"],
		)


class TestGetSop(unittest.TestCase):
	def _get(self, user, name):
		doc = frappe._dict(next(row for row in SOPS if row["name"] == name))
		doc.content = "<p>body</p>"
		# frappe's translator needs a bench log dir — the denial messages only
		# need a string
		with (
			_Ctx(user, file_rows=self.file_rows),
			patch.object(frappe, "get_doc", return_value=doc),
			patch("hrms.api.sop._", lambda msg: msg),
		):
			return sop_api.get_sop(name)

	def setUp(self):
		self.file_rows = []

	def test_detail_serves_attachment_via_file_row_fallback(self):
		self.file_rows = [
			{
				"attached_to_name": "HR-SOP-00003",
				"file_name": "opening.pdf",
				"file_url": "/private/files/opening.pdf",
			}
		]
		data = self._get(STAFF, "HR-SOP-00003")
		self.assertEqual(
			data["attachment"],
			{
				"file_name": "opening.pdf",
				"file_url": "/private/files/opening.pdf",
				"content_url": "/api/method/hrms.api.sop.attachment_content?name=HR-SOP-00003",
			},
		)

	def test_employee_reads_own_department_sop(self):
		data = self._get(STAFF, "HR-SOP-00003")
		self.assertEqual(data["name"], "HR-SOP-00003")
		self.assertEqual(data["content"], "<p>body</p>")
		self.assertIsNone(data["attachment"])

	def test_employee_denied_other_department_sop(self):
		with self.assertRaises(frappe.PermissionError) as caught:
			self._get(STAFF, "HR-SOP-00004")
		# denials carry a translated message, like get_sops (not a bare raise)
		self.assertEqual(str(caught.exception), sop_api.OUT_OF_SCOPE_MSG)

	def test_user_without_employee_is_denied_with_message(self):
		with self.assertRaises(frappe.PermissionError) as caught:
			self._get(NOBODY, "HR-SOP-00001")
		self.assertEqual(str(caught.exception), sop_api.NO_EMPLOYEE_MSG)

	def test_employee_denied_unpublished_sop(self):
		with self.assertRaises(frappe.PermissionError):
			self._get(STAFF, "HR-SOP-00005")

	def test_detail_carries_is_hr_flag(self):
		self.assertFalse(self._get(STAFF, "HR-SOP-00003")["is_hr"])
		self.assertTrue(self._get(HR, "HR-SOP-00002")["is_hr"])

	def test_hr_reads_unpublished_sop_with_attachment(self):
		data = self._get(HR, "HR-SOP-00002")
		self.assertEqual(
			data["attachment"],
			{
				"file_name": "contacts.pdf",
				"file_url": "/files/contacts.pdf",
				"content_url": "/api/method/hrms.api.sop.attachment_content?name=HR-SOP-00002",
			},
		)

	def test_attachment_content_denied_out_of_scope(self):
		with self.assertRaises(frappe.PermissionError):
			doc = frappe._dict(next(row for row in SOPS if row["name"] == "HR-SOP-00004"))
			with (
				_Ctx(STAFF),
				patch.object(frappe, "get_doc", return_value=doc),
				patch("hrms.api.sop._", lambda msg: msg),
			):
				sop_api.attachment_content("HR-SOP-00004")


class TestS3PresignedLocation(unittest.TestCase):
	S3_URL = (
		"/api/method/frappe_s3_attachment.controller.generate_file"
		"?key=2026%2F08%2F07%2FSOP+Document%2FYUE3OPT3_handbook.pdf&file_name=handbook.pdf"
	)

	def test_plain_file_url_is_not_s3(self):
		self.assertIsNone(sop_api._s3_presigned_location("/private/files/handbook.pdf"))

	def test_s3_redirect_resolved_in_process(self):
		captured = {}

		def fake_generate_file(key=None, file_name=None):
			captured["key"] = key
			captured["file_name"] = file_name
			frappe.local.response["location"] = "https://bucket.s3.amazonaws.com/presigned"

		with _Ctx(HR), patch.object(frappe, "get_attr", return_value=fake_generate_file):
			original_response = frappe.local.response
			location = sop_api._s3_presigned_location(self.S3_URL)
			# the request-scoped response object must survive the in-process call
			self.assertIs(frappe.local.response, original_response)

		self.assertEqual(location, "https://bucket.s3.amazonaws.com/presigned")
		self.assertEqual(captured["key"], "2026/08/07/SOP Document/YUE3OPT3_handbook.pdf")
		self.assertEqual(captured["file_name"], "handbook.pdf")


def _no_translation():
	"""frappe's translator needs a bench log dir; the controller only needs a
	message string and a throw that raises."""
	return _MultiPatch(
		patch("hrms.hr.doctype.sop_document.sop_document._", lambda msg: msg),
		patch(
			"hrms.hr.doctype.sop_document.sop_document.frappe.throw",
			side_effect=frappe.ValidationError,
		),
		# validate_scope reads Department.is_group
		patch.object(frappe, "db", _fake_db()),
	)


class _MultiPatch:
	def __init__(self, *patches):
		self.patches = patches

	def __enter__(self):
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()


class TestSopDocumentController(unittest.TestCase):
	def _doc(self, scope, department=None):
		doc = types.SimpleNamespace(name="HR-SOP-00009", scope=scope, department=department)
		doc.validate_scope = lambda: SOPDocument.validate_scope(doc)
		return doc

	def test_department_scope_requires_department(self):
		doc = self._doc("Department", None)
		with _no_translation():
			with self.assertRaises(frappe.ValidationError):
				SOPDocument.validate(doc)

	def test_department_scope_accepts_department(self):
		doc = self._doc("Department", "Operations - N")
		with _no_translation():
			SOPDocument.validate(doc)
		self.assertEqual(doc.department, "Operations - N")

	def test_department_scope_rejects_group_department(self):
		# exact-equality row scope means a group department publishes to nobody
		doc = self._doc("Department", "All Departments - N")
		with _no_translation():
			with self.assertRaises(frappe.ValidationError):
				SOPDocument.validate(doc)

	def test_department_scope_accepts_leaf_department(self):
		doc = self._doc("Department", "Finance - N")
		with _no_translation():
			SOPDocument.validate(doc)
		self.assertEqual(doc.department, "Finance - N")

	def test_general_scope_clears_department(self):
		doc = self._doc("General", "Operations - N")
		with _no_translation():
			SOPDocument.validate(doc)
		self.assertIsNone(doc.department)


if __name__ == "__main__":
	unittest.main()
