"""A check-in photo is private, and hangs on the punch it proves.

Live, 18 Sep 2026: Remote Approvals showed a broken image where each face
should be. The photo had uploaded fine — the 17 Sep crash was gone — but the
approver could not fetch it.

The chain: `upload_selfie` stored the File PUBLIC, and with S3 configured the
S3 hook rewrites a public file's url to the bucket object itself
(`{endpoint}/{bucket}/{key}`). That object is only readable if it was uploaded
with a public-read ACL, which needs `s3_use_acl` in site config and a bucket
that permits public objects. Neither is true here, so the url 403s and the
approver sees a broken image.

Private is the answer, and not only for S3: a face photo readable by anyone
holding the link was always the wrong default (the `# ceiling:` on that function
said so). But a private File with NO parent is readable by its owner and a
System Manager alone — the employee who took it, and not the approver who has
to look at it. So it is attached to its punch as soon as the punch exists, and
`File.is_downloadable` then grants exactly the people who can read that
Employee Checkin.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_selfie_is_private_and_attached.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import remote_checkin as rc

SOURCE = pathlib.Path(rc.__file__).read_text()


def body(name):
	return next(
		ast.unparse(node)
		for node in ast.walk(ast.parse(SOURCE))
		if isinstance(node, ast.FunctionDef) and node.name == name
	)


class TheFileIsPrivateCase(unittest.TestCase):
	def test_the_selfie_is_stored_private(self):
		self.assertIn("'is_private': 1", body("upload_selfie"))

	def test_it_is_not_stored_public(self):
		self.assertNotIn("'is_private': 0", body("upload_selfie"))


class ItHangsOnThePunchCase(unittest.TestCase):
	def test_the_punch_attaches_it(self):
		self.assertIn("_attach_selfie_to_punch", body("punch"))

	def test_it_is_attached_after_the_punch_exists(self):
		"""The File is uploaded before the punch, so it cannot carry the link at
		insert time — the attach has to follow `doc.insert()`."""
		punch_body = body("punch")
		self.assertLess(
			punch_body.index("doc.insert()"),
			punch_body.index("_attach_selfie_to_punch"),
			"a punch has no name to attach to until it is inserted",
		)

	def test_it_names_the_punch_doctype(self):
		attach = body("_attach_selfie_to_punch")
		self.assertIn("'attached_to_doctype': 'Employee Checkin'", attach)
		self.assertIn("'attached_to_name': punch", attach)

	def test_a_punch_with_no_selfie_attaches_nothing(self):
		self.assertIn("if selfie_image:\n        _attach_selfie_to_punch", body("punch"))

	def test_a_url_with_no_file_behind_it_is_logged_not_raised(self):
		attach = body("_attach_selfie_to_punch")
		self.assertIn("if not file_name:", attach)
		self.assertIn("return", attach)


class TheRepairReadsTheUrlItWasGivenCase(unittest.TestCase):
	"""The already-broken ones: public S3 urls that have to become private."""

	def test_a_bucket_url_yields_its_key(self):
		self.assertEqual(
			rc.s3_key_from_public_url("https://s3.ap-southeast-1.amazonaws.com/nasty/2026/09/18/x.jpg"),
			"2026/09/18/x.jpg",
		)

	def test_a_quoted_key_comes_back_quoted(self):
		# the key is used to rebuild a url, so it stays exactly as stored
		self.assertEqual(
			rc.s3_key_from_public_url("https://host/bucket/2026/09/Employee%20Checkin/x.jpg"),
			"2026/09/Employee%20Checkin/x.jpg",
		)

	def test_a_local_url_is_not_an_s3_url(self):
		self.assertIsNone(rc.s3_key_from_public_url("/files/selfie-HR-EMP-00069-1.jpg"))

	def test_a_private_api_url_is_already_right(self):
		self.assertIsNone(
			rc.s3_key_from_public_url("/api/method/frappe_s3_attachment.controller.generate_file?key=a/b.jpg")
		)

	def test_nothing_is_nothing(self):
		for value in (None, "", "   "):
			self.assertIsNone(rc.s3_key_from_public_url(value))

	def test_a_url_with_no_key_after_the_bucket_is_refused(self):
		self.assertIsNone(rc.s3_key_from_public_url("https://host/bucket"))
		self.assertIsNone(rc.s3_key_from_public_url("https://host/bucket/"))


class TheRepairPatchCase(unittest.TestCase):
	PATCH = "hrms/patches/v16_0/repair_public_selfies.py"

	def source(self):
		return (pathlib.Path(__file__).resolve().parents[2] / self.PATCH).read_text()

	def test_it_is_registered(self):
		txt = (pathlib.Path(__file__).resolve().parents[2] / "hrms/patches.txt").read_text()
		self.assertIn("hrms.patches.v16_0.repair_public_selfies", txt)

	def test_it_makes_them_private_and_attached(self):
		body = self.source()
		self.assertIn('"is_private": 1', body)
		self.assertIn('"attached_to_doctype": "Employee Checkin"', body)

	def test_it_reuses_the_one_url_parser(self):
		self.assertIn("from hrms.api.remote_checkin import s3_key_from_public_url", self.source())

	def test_a_local_photo_is_not_readdressed(self):
		# `key` is None for a /files url, so only the private+attach fields are
		# written and the punch keeps the url it has.
		self.assertIn("if key:", self.source())

	def test_it_skips_one_that_is_already_repaired(self):
		self.assertIn("if stored.is_private and stored.attached_to_name == punch.name:", self.source())

	def test_a_punch_naming_a_missing_file_is_logged_not_raised(self):
		self.assertIn("names a photo with no File", self.source())


if __name__ == "__main__":
	unittest.main()
