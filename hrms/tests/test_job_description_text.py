"""The draft job description fills itself from an attached JD (owner, 29 Oct 2026).

"when hiring manager attach the attachment of the JD it will auto reflect the job
description but still can be edit". The text comes out of PDF, Word (.docx) and plain
text; anything else (a photo, a scan, an old .doc) gives "" and the person types it.

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_job_description_text.py
"""

import io
import pathlib
import sys
import types
import unittest
import zipfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.utils import job_description_text as jd


def _docx(*paragraphs):
	body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" if p else "<w:p/>" for p in paragraphs)
	xml = (
		'<?xml version="1.0" encoding="UTF-8"?>'
		'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
		f"<w:body>{body}</w:body></w:document>"
	)
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as z:
		z.writestr("word/document.xml", xml)
	return out.getvalue()


def _fake_pypdf(pages):
	module = types.ModuleType("pypdf")
	reader = MagicMock()
	reader.pages = [MagicMock(extract_text=MagicMock(return_value=t)) for t in pages]
	module.PdfReader = MagicMock(return_value=reader)
	return module


class TestTextFromFile(unittest.TestCase):
	def test_word_paragraphs_become_lines(self):
		text = jd.text_from_file(
			"JD.docx", _docx("Marketing Executive", "", "Plan campaigns", "Report to CMO")
		)
		self.assertEqual(text, "Marketing Executive\n\nPlan campaigns\nReport to CMO")

	def test_pdf_pages_are_joined(self):
		with patch.dict(sys.modules, {"pypdf": _fake_pypdf(["Marketing Executive\nPlan", "Report to CMO"])}):
			text = jd.text_from_file("JD Marketing.PDF", b"%PDF-1.7")
		self.assertEqual(text, "Marketing Executive\nPlan\n\nReport to CMO")

	def test_plain_text(self):
		self.assertEqual(jd.text_from_file("jd.txt", b"Duties:\r\n  - sell  \r\n"), "Duties:\n  - sell")

	def test_scanned_pdf_with_no_text_gives_nothing(self):
		with patch.dict(sys.modules, {"pypdf": _fake_pypdf(["", None, "  "])}):
			self.assertEqual(jd.text_from_file("scan.pdf", b"%PDF"), "")

	def test_broken_file_gives_nothing_instead_of_an_error(self):
		self.assertEqual(jd.text_from_file("JD.docx", b"not a zip"), "")
		bad = types.ModuleType("pypdf")
		bad.PdfReader = MagicMock(side_effect=ValueError("bad pdf"))
		with patch.dict(sys.modules, {"pypdf": bad}):
			self.assertEqual(jd.text_from_file("JD.pdf", b"junk"), "")

	def test_a_word_file_that_inflates_past_the_cap_is_not_opened(self):
		# a small upload can unpack to hundreds of MB; the size is read from the zip index first
		big = io.BytesIO()
		with zipfile.ZipFile(big, "w", zipfile.ZIP_DEFLATED) as z:
			z.writestr("word/document.xml", "<w:document/>" + " " * (jd.MAX_XML_BYTES + 1))
		with patch.object(jd.ElementTree, "fromstring", side_effect=AssertionError("parsed")):
			self.assertEqual(jd.text_from_file("JD.docx", big.getvalue()), "")

	def test_pdf_reading_stops_at_the_page_cap_and_once_there_is_enough_text(self):
		module = _fake_pypdf(["page"] * (jd.MAX_PDF_PAGES + 20))
		with patch.dict(sys.modules, {"pypdf": module}):
			jd.text_from_file("long.pdf", b"%PDF")
		pages = module.PdfReader.return_value.pages
		self.assertEqual(sum(p.extract_text.called for p in pages), jd.MAX_PDF_PAGES)

		module = _fake_pypdf(["x" * jd.MAX_CHARS, "never read"])
		with patch.dict(sys.modules, {"pypdf": module}):
			jd.text_from_file("dense.pdf", b"%PDF")
		self.assertFalse(module.PdfReader.return_value.pages[1].extract_text.called)

	def test_photos_and_old_word_are_not_read(self):
		for name in ("jd.png", "jd.jpg", "jd.doc", "noextension"):
			self.assertEqual(jd.text_from_file(name, b"whatever"), "", name)

	def test_blank_runs_are_squeezed_and_long_text_is_capped(self):
		self.assertEqual(jd.tidy("a\n\n\n\n\nb   \n"), "a\n\nb")
		self.assertEqual(len(jd.tidy("x" * (jd.MAX_CHARS + 500))), jd.MAX_CHARS)


class TestReadJobDescription(unittest.TestCase):
	def _read(self, row, user="hafiz@x", content=b"Duties: sell"):
		db = MagicMock()
		db.get_value.return_value = row
		file_doc = MagicMock(get_content=MagicMock(return_value=content))
		with (
			patch.object(jd.frappe, "db", db),
			patch.object(jd.frappe, "session", frappe._dict(user=user)),
			patch.object(jd.frappe, "get_doc", return_value=file_doc),
			patch.object(jd.frappe, "throw", side_effect=frappe.PermissionError("no")),
		):
			return jd.read_job_description("/private/files/jd.txt")

	def test_own_loose_upload_is_read(self):
		row = frappe._dict(name="F1", file_name="jd.txt", owner="hafiz@x", attached_to_name=None)
		self.assertEqual(self._read(row), {"text": "Duties: sell", "file_name": "jd.txt"})

	def test_someone_elses_file_is_refused(self):
		row = frappe._dict(name="F1", file_name="jd.txt", owner="nik@x", attached_to_name=None)
		with self.assertRaises(frappe.PermissionError):
			self._read(row)

	def test_a_file_already_filed_under_a_document_is_refused(self):
		row = frappe._dict(name="F1", file_name="jd.txt", owner="hafiz@x", attached_to_name="MPR-1")
		with self.assertRaises(frappe.PermissionError):
			self._read(row)

	def test_only_the_callers_own_loose_upload_is_looked_up(self):
		db = MagicMock()
		db.get_value.return_value = None
		with (
			patch.object(jd.frappe, "db", db),
			patch.object(jd.frappe, "session", frappe._dict(user="hafiz@x")),
			patch.object(jd.frappe, "throw", side_effect=frappe.PermissionError("no")),
		):
			with self.assertRaises(frappe.PermissionError):
				jd.read_job_description("/private/files/jd.txt")
		filters = db.get_value.call_args.args[1]
		self.assertEqual(filters["owner"], "hafiz@x")
		self.assertEqual(filters["attached_to_name"], ("is", "not set"))
		self.assertEqual(db.get_value.call_args.kwargs.get("order_by"), "creation desc")

	def test_unknown_url_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self._read(None)

	def test_is_whitelisted_post_only(self):
		src = pathlib.Path(jd.__file__).read_text()
		self.assertIn('@frappe.whitelist(methods=["POST"])\ndef read_job_description', src)


if __name__ == "__main__":
	unittest.main()
