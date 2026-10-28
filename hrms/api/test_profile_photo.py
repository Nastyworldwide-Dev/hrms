"""Profile photo set/remove endpoints (owner 28 Oct 2026 — everyone using Nadi
sets their own photo, S3, 5 MB, private).

	PYTHONPATH=. python3 -m pytest -q hrms/api/test_profile_photo.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
for module in ("pypika", "pypika.terms", "pypika.functions"):
	sys.modules.setdefault(module, MagicMock())

from _fake_document import FakeDocument

import frappe
from frappe import _

from hrms.api import profile_photo


class TestProfilePhoto(unittest.TestCase):
	def setUp(self):
		self.employee_id = "EMP-001"
		self.user_id = "employee@example.com"

	@patch("hrms.api.profile_photo.require_employee")
	@patch("frappe.get_doc")
	@patch("frappe.db.get_value")
	@patch("frappe.db.set_value")
	@patch("frappe.get_all")
	@patch("frappe.delete_doc")
	def test_jpeg_data_url_under_5mb_creates_file(
		self,
		mock_delete_doc,
		mock_get_all,
		mock_set_value,
		mock_db_get_value,
		mock_get_doc,
		mock_require_employee,
	):
		"""JPEG data URL under 5 MB creates File with correct attributes."""
		mock_require_employee.return_value = self.employee_id

		# Mock the File document with an insert method
		file_doc = MagicMock()
		file_doc.name = "file-123"
		file_doc.file_url = "/files/photo-emp-001-1234567890.jpg"
		file_doc.insert = MagicMock(return_value=file_doc)
		mock_get_doc.return_value = file_doc

		# Mock db.get_value for reading back the file_url and user_id
		def db_get_side_effect(doctype, name, field=None):
			if doctype == "File":
				return "/files/photo-emp-001-1234567890.jpg"
			if doctype == "Employee":
				return self.user_id if field == "user_id" else None
			if doctype == "User":
				return None
			return None

		mock_db_get_value.side_effect = db_get_side_effect

		# Mock get_all to return no old files
		mock_get_all.return_value = []

		# Create a minimal JPEG data URL
		jpeg_data = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAA=="

		profile_photo.set_photo(jpeg_data)

		# Verify File creation
		mock_get_doc.assert_called_once()
		call_args = mock_get_doc.call_args[0][0]
		self.assertEqual(call_args["doctype"], "File")
		self.assertEqual(call_args["is_private"], 1)
		self.assertEqual(call_args["attached_to_doctype"], "Employee")
		self.assertEqual(call_args["attached_to_name"], self.employee_id)
		self.assertEqual(call_args["attached_to_field"], "image")

		file_doc.insert.assert_called_once_with(ignore_permissions=True)
		mock_set_value.assert_any_call(
			"Employee",
			self.employee_id,
			"image",
			"/files/photo-emp-001-1234567890.jpg",
			update_modified=False,
		)
		mock_set_value.assert_any_call(
			"User", self.user_id, "user_image", "/files/photo-emp-001-1234567890.jpg", update_modified=False
		)

	@patch("hrms.api.profile_photo.require_employee")
	@patch("frappe.throw")
	def test_5mb_plus_1_byte_rejected(self, mock_throw, mock_require_employee):
		"""5 MB + 1 byte is rejected with ValidationError."""
		mock_require_employee.return_value = self.employee_id
		mock_throw.side_effect = frappe.ValidationError("over 5 MB")

		# Create data that is 5 MB + 1 byte when decoded
		size = 5 * 1024 * 1024 + 1
		import base64

		data_bytes = b"\xff\xd8\xff" + b"x" * (size - 3)
		encoded = base64.b64encode(data_bytes).decode()
		data_url = f"data:image/jpeg;base64,{encoded}"

		with patch("frappe.get_doc") as mock_get_doc:
			with self.assertRaises(frappe.ValidationError):
				profile_photo.set_photo(data_url)
			mock_get_doc.assert_not_called()

		# Verify frappe.throw was called with the right message
		mock_throw.assert_called_once()
		args = mock_throw.call_args[0]
		self.assertIn("5 MB", str(args[0]))

	@patch("hrms.api.profile_photo.require_employee")
	@patch("frappe.get_doc")
	@patch("frappe.db.get_value")
	@patch("frappe.db.set_value")
	@patch("frappe.get_all")
	def test_exactly_5mb_accepted(
		self, mock_get_all, mock_set_value, mock_db_get_value, mock_get_doc, mock_require_employee
	):
		"""Exactly 5 MB is accepted."""
		mock_require_employee.return_value = self.employee_id

		size = 5 * 1024 * 1024
		import base64

		data_bytes = b"\xff\xd8\xff" + b"x" * (size - 3)
		encoded = base64.b64encode(data_bytes).decode()
		data_url = f"data:image/jpeg;base64,{encoded}"

		file_doc = MagicMock()
		file_doc.name = "file-123"
		file_doc.file_url = "/files/photo.jpg"
		file_doc.insert = MagicMock(return_value=file_doc)
		mock_get_doc.return_value = file_doc

		def db_get_side_effect(doctype, name, field=None):
			if doctype == "File":
				return "/files/photo.jpg"
			if doctype == "Employee":
				return self.user_id if field == "user_id" else None
			return None

		mock_db_get_value.side_effect = db_get_side_effect
		mock_get_all.return_value = []

		result = profile_photo.set_photo(data_url)

		self.assertIn("image", result)
		file_doc.insert.assert_called_once_with(ignore_permissions=True)
		self.assertEqual(len(mock_get_doc.call_args[0][0]["content"]), 5 * 1024 * 1024)

	@patch("hrms.api.profile_photo.require_employee")
	@patch("frappe.throw")
	def test_pdf_data_url_rejected(self, mock_throw, mock_require_employee):
		"""PDF data URL is rejected with JPEG/PNG/WebP message."""
		mock_require_employee.return_value = self.employee_id
		mock_throw.side_effect = frappe.ValidationError("JPEG")

		pdf_url = "data:application/pdf;base64,JVBERi0xLjQK"

		with patch("frappe.get_doc") as mock_get_doc:
			with self.assertRaises(frappe.ValidationError):
				profile_photo.set_photo(pdf_url)
			mock_get_doc.assert_not_called()

		mock_throw.assert_called_once()
		args = mock_throw.call_args[0]
		self.assertIn("JPEG", str(args[0]))

	@patch("hrms.api.profile_photo.require_employee")
	@patch("frappe.throw")
	def test_invalid_base64_rejected(self, mock_throw, mock_require_employee):
		"""Invalid base64 is rejected with 'could not be read' message."""
		mock_require_employee.return_value = self.employee_id
		mock_throw.side_effect = frappe.ValidationError("could not be read")

		invalid_url = "data:image/jpeg;base64,!!!invalid!!!"

		with self.assertRaises(frappe.ValidationError):
			profile_photo.set_photo(invalid_url)

		mock_throw.assert_called_once()
		args = mock_throw.call_args[0]
		self.assertIn("could not be read", str(args[0]))

	@patch("hrms.api.profile_photo.require_employee")
	@patch("frappe.get_doc")
	@patch("frappe.db.get_value")
	@patch("frappe.db.set_value")
	@patch("frappe.get_all")
	@patch("frappe.delete_doc")
	def test_old_file_deleted_new_not(
		self,
		mock_delete_doc,
		mock_get_all,
		mock_set_value,
		mock_db_get_value,
		mock_get_doc,
		mock_require_employee,
	):
		"""Old File is deleted, new one is not."""
		mock_require_employee.return_value = self.employee_id

		# Mock the new File document insert
		file_doc = MagicMock()
		file_doc.name = "file-new"
		file_doc.file_url = "/files/photo-new.jpg"
		file_doc.insert = MagicMock(return_value=file_doc)
		mock_get_doc.return_value = file_doc

		# Mock db.get_value
		def db_get_side_effect(doctype, name, field=None):
			if doctype == "File":
				return "/files/photo-new.jpg"
			if doctype == "Employee":
				return self.user_id if field == "user_id" else None
			return None

		mock_db_get_value.side_effect = db_get_side_effect

		# Mock get_all to return just one old file name (pluck="name" returns a list of strings)
		mock_get_all.return_value = ["file-old"]

		jpeg_data = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAA=="

		profile_photo.set_photo(jpeg_data)

		# Verify old file was deleted
		mock_delete_doc.assert_called_once_with("File", "file-old", ignore_permissions=True)

	@patch("hrms.api.profile_photo.require_employee")
	@patch("frappe.db.set_value")
	@patch("frappe.get_all")
	@patch("frappe.delete_doc")
	def test_remove_photo_clears_fields_and_deletes_files(
		self,
		mock_delete_doc,
		mock_get_all,
		mock_set_value,
		mock_require_employee,
	):
		"""remove_photo clears both fields and deletes the Files."""
		mock_require_employee.return_value = self.employee_id

		def db_get_side_effect(doctype, name, field=None):
			if doctype == "Employee":
				return self.user_id if field == "user_id" else None
			return None

		# Mock get_all to return file names (pluck="name" returns strings)
		mock_get_all.return_value = ["file-1", "file-2"]

		# Mock db.get_value for getting user_id
		with patch("frappe.db.get_value", side_effect=db_get_side_effect):
			profile_photo.remove_photo()

		mock_set_value.assert_any_call("Employee", self.employee_id, "image", "", update_modified=False)
		mock_set_value.assert_any_call("User", self.user_id, "user_image", "", update_modified=False)

		# Verify both files were deleted
		self.assertEqual(mock_delete_doc.call_count, 2)
		delete_calls = [
			call("File", "file-1", ignore_permissions=True),
			call("File", "file-2", ignore_permissions=True),
		]
		mock_delete_doc.assert_has_calls(delete_calls, any_order=True)

		# Verify Employee.image and User.user_image set to empty

	@patch("hrms.api.profile_photo.require_employee")
	@patch("frappe.throw")
	def test_non_image_bytes_with_jpeg_header_rejected(self, mock_throw, mock_require_employee):
		"""A JPEG data-url header over non-image bytes (e.g. a script) is refused."""
		import base64

		mock_require_employee.return_value = self.employee_id
		mock_throw.side_effect = frappe.ValidationError("JPEG")
		for body in (b"<script>alert(1)</script>", b"%PDF-1.4", b"RIFF\x00\x00\x00\x00WAVE"):
			mock_throw.reset_mock()
			url = "data:image/jpeg;base64," + base64.b64encode(body).decode()
			with patch("frappe.get_doc") as mock_get_doc:
				with self.assertRaises(frappe.ValidationError):
					profile_photo.set_photo(url)
				mock_get_doc.assert_not_called()
			self.assertIn("JPEG, PNG or WebP", str(mock_throw.call_args[0][0]))

	def test_png_and_webp_signatures_accepted(self):
		self.assertTrue(profile_photo._has_image_signature(b"\x89PNG\r\n\x1a\n"))
		self.assertTrue(profile_photo._has_image_signature(b"RIFF\x01\x02\x03\x04WEBPVP8 "))
		self.assertFalse(profile_photo._has_image_signature(b""))

	@patch("hrms.api.profile_photo.require_employee")
	def test_set_photo_has_no_employee_parameter(self, mock_require_employee):
		"""set_photo has no `employee` parameter."""
		import inspect

		sig = inspect.signature(profile_photo.set_photo)
		self.assertNotIn("employee", sig.parameters)

	@patch("hrms.api.profile_photo.require_employee")
	def test_remove_photo_has_no_employee_parameter(self, mock_require_employee):
		"""remove_photo has no `employee` parameter."""
		import inspect

		sig = inspect.signature(profile_photo.remove_photo)
		self.assertNotIn("employee", sig.parameters)


if __name__ == "__main__":
	unittest.main()
