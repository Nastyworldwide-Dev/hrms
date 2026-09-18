"""Anyone who can use Nadi can attach a file to their own request.

Live, 18 Sep 2026. The owner filed a Leave Application from the PWA. It saved —
"Leave Application created successfully!" — and every attachment on it failed:

    File upload failed for CamScanner 28-08-2026 00.31.pdf.
    Not allowed via controller permission check

Owner ruling in the same message: "there is s3 installed, and will and must be
used and everyone must able regardless of their permission, as long as they can
use nadi, they can upload properly."

TWO causes, and the first is the selfie bug of 17 September in a second place:

* `.insert()` with no `ignore_permissions`. Staff hold no CREATE right on File —
  this app's whole PWA write path is server-side for exactly that reason — so
  the File controller refuses, and Frappe reports it as the controller check.
* the endpoint demanded WRITE on the request. Read is the honest bar: the PWA
  only ever shows a person their own requests, so if they can read it, it is
  theirs. Demanding write also refuses an approver attaching to a request they
  are judging, and a staff member whose own request has moved past draft.

And one plain bug beside them: the write check was made TWICE, the second time
without the `if dt and dn` guard, so a standalone file with no parent asked
permission on doctype `None`.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_nadi_attachments_do_not_need_desk_rights.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parents[1] / "api/__init__.py"
TREE = ast.parse(API.read_text())


def body(name: str) -> str:
	return next(
		ast.unparse(node)
		for node in ast.walk(TREE)
		if isinstance(node, ast.FunctionDef) and node.name == name
	)


class TheUploadDoesNotNeedDeskRightsCase(unittest.TestCase):
	def setUp(self):
		self.upload = body("upload_base64_file")

	def test_the_file_is_inserted_as_the_server(self):
		"""Staff hold no create right on File; every PWA write path is
		server-side for that reason (see hrms.api.remote_checkin.upload_selfie,
		the same defect on 17 Sep)."""
		self.assertIn("insert(ignore_permissions=True)", self.upload)

	def test_reading_the_request_is_the_bar_not_writing_it(self):
		self.assertNotIn('"write"', self.upload)
		self.assertNotIn("ptype='write'", self.upload)
		self.assertIn("'read'", self.upload)

	def test_the_check_is_made_once_and_only_with_a_parent(self):
		self.assertEqual(self.upload.count("has_permission"), 1)
		self.assertIn("if dt and dn", self.upload)

	def test_it_still_refuses_a_request_the_caller_cannot_see(self):
		self.assertIn("throw=True", self.upload)

	def test_the_file_type_rule_is_untouched(self):
		self.assertIn("ALLOWED_MIMETYPES", self.upload)


class DeletingYourOwnAttachmentCase(unittest.TestCase):
	def setUp(self):
		self.delete = body("delete_attachment")

	def test_the_person_who_uploaded_it_may_remove_it(self):
		"""They could attach it, so they can take it back — and needing WRITE on
		the parent refused them their own file for the same reason the upload
		refused them."""
		self.assertIn("owner == frappe.session.user", self.delete)

	def test_someone_else_still_needs_the_right_on_the_parent(self):
		self.assertIn("has_permission", self.delete)

	def test_an_orphan_file_is_still_its_owners_alone(self):
		self.assertIn("only delete your own attachments", self.delete)

	def test_the_delete_itself_runs_as_the_server(self):
		self.assertIn("ignore_permissions=True", self.delete)


class ListingThemIsUnchangedCase(unittest.TestCase):
	def test_reading_the_parent_is_already_the_bar(self):
		listing = body("get_attachments")
		self.assertIn("has_permission", listing)
		self.assertNotIn('"write"', listing)


if __name__ == "__main__":
	unittest.main()
