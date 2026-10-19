"""Notices pushed before alpha.57 are marked so the daily job does not push them again.

PYTHONPATH=. python3 -m pytest -q hrms/tests/test_mark_pushed_announcements.py
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

from hrms.patches.v16_0 import mark_pushed_announcements as patch_mod

ROOT = pathlib.Path(__file__).resolve().parent.parent


class MarkPushed(unittest.TestCase):
	def _run(self, live, marked):
		inserted = []
		doc = MagicMock()
		doc.insert.side_effect = lambda **k: None
		with (
			patch.object(frappe, "get_all", return_value=live) as get_all,
			patch.object(frappe.db, "exists", side_effect=lambda dt, f: f["reference_name"] in marked),
			patch.object(frappe, "get_doc", side_effect=lambda d: inserted.append(d) or doc),
		):
			patch_mod.execute()
		return get_all.call_args.kwargs["filters"], inserted

	def test_marks_each_live_notice_not_yet_marked(self):
		filters, inserted = self._run(["ANN-1", "ANN-2"], marked={"ANN-1"})
		self.assertEqual([d["reference_name"] for d in inserted], ["ANN-2"])
		self.assertEqual(inserted[0]["content"], "Push sent")
		self.assertEqual(filters["published"], 1)
		self.assertEqual(filters["notify_on_publish"], 1)
		self.assertEqual(filters["publish_from"][0], "<=")

	def test_running_twice_marks_nothing_new(self):
		_, inserted = self._run(["ANN-1"], marked={"ANN-1"})
		self.assertEqual(inserted, [])

	def test_registered(self):
		self.assertIn("hrms.patches.v16_0.mark_pushed_announcements", (ROOT / "patches.txt").read_text())


if __name__ == "__main__":
	unittest.main()
