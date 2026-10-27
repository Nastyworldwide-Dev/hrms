"""The notice page shows an Event's day (owner-approved mockup, 27 Oct 2026).

`get_announcement` builds its answer from `_payload(doc)`. The page draws a "When" row for an
Event from `event_date`, so the payload has to carry it; the field already exists on the doctype.

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_announcement_payload_event_date.py
"""

import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import announcements

EVENT_DAY = datetime.date(2026, 10, 30)


def _doc(**kw):
	fields = dict(
		name="A1",
		title="Hari Raya potluck",
		category="Event",
		body="<p>Pantry</p>",
		pinned=0,
		acknowledge_required=0,
		publish_from=datetime.date(2026, 10, 26),
		publish_until=datetime.date(2026, 10, 30),
		summary="Pantry, Fri 30 Oct at 12:30.",
		cover_image=None,
		urgent=0,
		version=1,
		published=1,
		event_date=EVENT_DAY,
	)
	fields.update(kw)
	return frappe._dict(**fields)


class PayloadCarriesTheEventDay(unittest.TestCase):
	def test_an_event_notice_carries_the_day_it_happens(self):
		self.assertEqual(announcements._payload(_doc())["event_date"], EVENT_DAY)

	def test_a_notice_with_no_event_day_says_none_rather_than_dropping_the_key(self):
		out = announcements._payload(_doc(event_date=None))
		self.assertIn("event_date", out)
		self.assertIsNone(out["event_date"])

	def test_what_the_page_already_read_is_still_there(self):
		out = announcements._payload(_doc())
		for key in (
			"name",
			"title",
			"category",
			"body",
			"summary",
			"cover_image",
			"publish_from",
			"publish_until",
		):
			self.assertIn(key, out)


if __name__ == "__main__":
	unittest.main()
