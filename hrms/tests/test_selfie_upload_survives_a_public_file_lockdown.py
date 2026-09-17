"""The punch photo must reach the server on a site that forbids public uploads.

The PWA used to POST the captured frame to frappe's generic `upload_file` as a
PUBLIC file. A site with System Settings ->
`only_allow_system_managers_to_upload_public_files` on refuses that for every
non-System-Manager, and frappe's own friendly guard catches the BUILTIN
`PermissionError` instead of `frappe.exceptions.PermissionError`, so the
refusal never became a sentence: the phone showed the bare class name
("Selfie failed / frappe.exceptions.PermissionError", live 15 Sep 2026).

Reproduced on a bench 17 Sep 2026 — a staff user, that setting on, a public
File insert, `frappe.exceptions.PermissionError`; the same insert private, or
with the setting off, goes through.

So the frame now goes to this endpoint, which stores it for the caller the
same way `punch()` stores the punch itself: staff have no create rights of
their own on either doctype, and the endpoint is the whole write path.

    PYTHONPATH=. python3 -m pytest -q \
        hrms/tests/test_selfie_upload_survives_a_public_file_lockdown.py
"""

from __future__ import annotations

import base64
import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import remote_checkin

PIXEL = base64.b64encode(b"\xff\xd8\xff" + b"0" * 64).decode()
JPEG = f"data:image/jpeg;base64,{PIXEL}"


class FakeFile:
	def __init__(self, doc):
		self.doc = doc
		self.inserted_with = None
		self.file_url = "/files/selfie.jpg"
		self.name = "FILE-0001"

	def insert(self, **kwargs):
		self.inserted_with = kwargs
		return self


class UploadSelfieCase(unittest.TestCase):
	def _upload(self, image=JPEG, employee="HR-EMP-0001"):
		created: list[FakeFile] = []

		def get_doc(doc):
			created.append(FakeFile(doc))
			return created[-1]

		with (
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(remote_checkin, "require_employee", MagicMock(return_value=employee)),
			patch.object(frappe, "session", frappe._dict(user="staff@example.com")),
		):
			result = remote_checkin.upload_selfie(image)
		return result, created

	def test_it_returns_the_stored_url(self):
		result, created = self._upload()
		self.assertEqual(result["file_url"], "/files/selfie.jpg")
		self.assertEqual(created[0].doc["doctype"], "File")

	def test_the_file_is_stored_for_the_caller_not_by_their_own_rights(self):
		"""Staff have no File create rights of their own on a locked-down site."""
		_, created = self._upload()
		self.assertEqual(created[0].inserted_with, {"ignore_permissions": True})

	def test_the_decoded_frame_is_what_gets_stored(self):
		_, created = self._upload()
		self.assertEqual(created[0].doc["content"], base64.b64decode(PIXEL))

	def test_only_the_caller_with_an_employee_may_upload(self):
		with patch.object(
			remote_checkin,
			"require_employee",
			MagicMock(side_effect=frappe.PermissionError("no employee")),
		):
			with self.assertRaises(frappe.PermissionError):
				remote_checkin.upload_selfie(JPEG)

	def test_a_frame_that_is_not_an_image_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self._upload(image="data:text/html;base64," + base64.b64encode(b"<script>").decode())

	def test_a_frame_too_large_to_be_a_selfie_is_refused(self):
		huge = base64.b64encode(b"0" * (remote_checkin.SELFIE_MAX_BYTES + 1)).decode()
		with self.assertRaises(frappe.ValidationError):
			self._upload(image=f"data:image/jpeg;base64,{huge}")


if __name__ == "__main__":
	unittest.main()
