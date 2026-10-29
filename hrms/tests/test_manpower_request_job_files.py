"""Optional files with the draft job description (owner, 29 Oct 2026).

"at the draft job description I want to add that requester can put attachment
there and it is not required". Several files; the same people who can open the
request can open them. The wizard uploads each file loose (no parent yet) and
sends their URLs as `job_files`; after_insert attaches the sender's own loose
files to the request, as ExpenseClaim.link_receipts does for receipts.

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_manpower_request_job_files.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.hr.doctype.manpower_request import manpower_request as mr


def _request(job_files, owner="hafiz@x", name="MPR-0001"):
	doc = mr.ManpowerRequest.__new__(mr.ManpowerRequest)
	doc.__dict__.update(frappe._dict(doctype="Manpower Request", name=name, owner=owner, job_files=job_files))
	return doc


def _file(name, url, owner="hafiz@x", dt=None, dn=None):
	return frappe._dict(name=name, file_url=url, owner=owner, attached_to_doctype=dt, attached_to_name=dn)


class TestLinkJobFiles(unittest.TestCase):
	def _link(self, doc, files, user="hafiz@x"):
		db = MagicMock()
		with (
			patch.object(
				mr.frappe,
				"get_all",
				side_effect=lambda dt, filters=None, **kw: [
					f for f in files if f.file_url == filters["file_url"]
				],
			),
			patch.object(mr.frappe, "db", db),
			patch.object(mr.frappe, "session", frappe._dict(user=user)),
		):
			mr.link_job_files(doc)
		return {c.args[1]: c.args[2] for c in db.set_value.call_args_list}

	def test_each_of_the_senders_loose_files_is_attached_to_the_request(self):
		files = [_file("F1", "/private/files/jd.pdf"), _file("F2", "/private/files/org.png")]
		done = self._link(_request(["/private/files/jd.pdf", "/private/files/org.png"]), files)
		self.assertEqual(set(done), {"F1", "F2"})
		self.assertEqual(
			done["F1"],
			{
				"attached_to_doctype": "Manpower Request",
				"attached_to_name": "MPR-0001",
				"attached_to_field": "job_files",
			},
		)

	def test_no_files_is_fine(self):
		self.assertEqual(self._link(_request(None), []), {})
		self.assertEqual(self._link(_request([]), []), {})

	def test_another_persons_file_is_not_taken(self):
		files = [_file("F9", "/private/files/salary.pdf", owner="someone@x")]
		self.assertEqual(self._link(_request(["/private/files/salary.pdf"]), files), {})

	def test_a_file_already_on_another_document_stays_there(self):
		files = [_file("F3", "/private/files/jd.pdf", dt="Expense Claim", dn="EXP-1")]
		self.assertEqual(self._link(_request(["/private/files/jd.pdf"]), files), {})

	def test_hr_sending_for_someone_may_attach_their_own_upload(self):
		files = [_file("F4", "/private/files/jd.pdf", owner="lina@x")]
		self.assertEqual(
			set(self._link(_request(["/private/files/jd.pdf"], owner="lina@x"), files, user="lina@x")), {"F4"}
		)

	def test_a_text_list_from_the_api_is_read_too(self):
		files = [_file("F1", "/private/files/jd.pdf")]
		self.assertEqual(set(self._link(_request('["/private/files/jd.pdf"]'), files)), {"F1"})

	def test_after_insert_attaches_them(self):
		src = (
			pathlib.Path(__file__).resolve().parents[1] / "hr/doctype/manpower_request/manpower_request.py"
		).read_text()
		body = src[src.index("	def after_insert(self):") :]
		body = body[: body.index("\n	def ")]
		self.assertIn("link_job_files(self)", body)


if __name__ == "__main__":
	unittest.main()
