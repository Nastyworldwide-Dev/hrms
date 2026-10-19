"""A notice is pushed when it goes LIVE, not when HR saves it (alpha.57, owner 19 Oct 2026:
"if any announcement is made, it will notify everyone").

A notice published today with Publish From next Monday was pushed the moment HR ticked
Published: staff tapped the notification, and the board did not show it until Monday. Now
on_update pushes only a notice that is live today; a daily job pushes each notice whose
Publish From is today and that has not been pushed yet. "Pushed once" is the job id per
notice, as before, so an edit or a second run never buzzes twice.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_announcement_push_on_its_day.py
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
from _fake_document import FakeDocument

import frappe

from hrms.hr.doctype.hr_announcement import hr_announcement as ann

TODAY = "2026-10-19"


class _Announcement(FakeDocument):
	def __init__(self, before=None, **kw):
		super().__init__(
			"HR Announcement",
			name=kw.pop("name", "ANN-1"),
			published=kw.pop("published", 1),
			notify_on_publish=kw.pop("notify_on_publish", 1),
			publish_from=kw.pop("publish_from", TODAY),
			publish_until=kw.pop("publish_until", "2026-11-19"),
			**kw,
		)
		self._before = before

	def get_doc_before_save(self):
		return self._before


def _on_update(doc):
	with patch.object(frappe, "enqueue") as enqueue, patch.object(ann, "nowdate", return_value=TODAY):
		ann.HRAnnouncement.on_update(doc)
	return enqueue


class PushOnItsDay(unittest.TestCase):
	def test_published_and_live_today_is_pushed_now(self):
		enqueue = _on_update(_Announcement(before=_Announcement(published=0)))
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["job_id"], "announcement_publish_push::ANN-1")

	def test_published_for_a_later_day_is_not_pushed_yet(self):
		enqueue = _on_update(_Announcement(publish_from="2026-10-26", before=_Announcement(published=0)))
		enqueue.assert_not_called()

	def test_notify_off_is_never_pushed(self):
		enqueue = _on_update(_Announcement(notify_on_publish=0, before=_Announcement(published=0)))
		enqueue.assert_not_called()

	def test_an_edit_to_a_published_notice_is_not_pushed_again(self):
		enqueue = _on_update(_Announcement(before=_Announcement(published=1)))
		enqueue.assert_not_called()

	def test_the_daily_job_pushes_notices_that_go_live_today(self):
		with (
			patch.object(frappe, "get_all", return_value=["ANN-7", "ANN-8"]) as get_all,
			patch.object(frappe, "enqueue") as enqueue,
			patch.object(ann, "nowdate", return_value=TODAY),
		):
			ann.push_notices_going_live_today()
		filters = get_all.call_args.kwargs["filters"]
		self.assertEqual(filters["published"], 1)
		self.assertEqual(filters["notify_on_publish"], 1)
		self.assertEqual(filters["publish_from"], TODAY)
		self.assertEqual(
			[c.kwargs["job_id"] for c in enqueue.call_args_list],
			["announcement_publish_push::ANN-7", "announcement_publish_push::ANN-8"],
		)

	def test_the_daily_job_is_scheduled(self):
		hooks = (pathlib.Path(__file__).resolve().parents[1] / "hooks.py").read_text()
		self.assertIn("hrms.hr.doctype.hr_announcement.hr_announcement.push_notices_going_live_today", hooks)


if __name__ == "__main__":
	unittest.main()
