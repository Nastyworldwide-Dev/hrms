"""The Approvals page list (audit-flows 4B, AUDIT-PLAN P1-B, owner ruling 23 Sep:
approvals appear only where they can be done). One list of everything waiting
on the caller, across every request type, decided by the SAME routed-approver
check that Home's count and `approval.decide` use, so the page can never show
a row the approver cannot decide, or hide one Home counted.
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import approvals_list

DOCS = {
	("Leave Application", "LA-1"): frappe._dict(
		doctype="Leave Application",
		name="LA-1",
		employee="E1",
		employee_name="Aisyah",
		leave_type="Annual Leave",
		from_date="2026-09-22",
		to_date="2026-09-23",
		total_leave_days=2,
		description="Sister's wedding",
		modified="2026-09-20 10:00:00",
	),
	("Leave Application", "LA-2"): frappe._dict(
		doctype="Leave Application",
		name="LA-2",
		employee="E2",
		employee_name="Not mine",
		leave_type="Annual Leave",
		from_date="2026-09-24",
		to_date="2026-09-24",
		total_leave_days=1,
		description="",
		modified="2026-09-21 10:00:00",
	),
	("OT Request", "OT-1"): frappe._dict(
		doctype="OT Request",
		name="OT-1",
		employee="E3",
		employee_name="Ria",
		ot_date="2026-09-05",
		claimed_hours=1.5,
		explanation="Stock count",
		modified="2026-09-19 09:00:00",
	),
}


def fake_get_all(doctype, filters=None, pluck=None, **kw):
	return [name for (dt, name) in DOCS if dt == doctype]


class TestApprovalsList(unittest.TestCase):
	def _list(self, readable=lambda doc: True):
		with (
			patch.object(frappe, "get_all", side_effect=fake_get_all, create=True),
			patch.object(frappe, "get_doc", side_effect=lambda dt, name: DOCS[(dt, name)]),
			patch.object(approvals_list, "_is_routed_approver", side_effect=lambda doc: doc.name != "LA-2"),
			patch.object(approvals_list, "_request_read_allowed", side_effect=readable, create=True),
			patch.object(approvals_list, "_types_on_site", return_value=["Leave Application", "OT Request"]),
		):
			return approvals_list.get_waiting_for_me()

	def test_only_requests_routed_to_me_are_listed(self):
		names = [row["name"] for row in self._list()["rows"]]
		self.assertIn("LA-1", names)
		self.assertIn("OT-1", names)
		self.assertNotIn("LA-2", names)

	def test_routing_alone_does_not_list_a_request_the_caller_may_not_read(self):
		# Review of be4b81edf: _is_routed_approver's HR branch admits System
		# Manager, which approval_row_scope deliberately denies read. decide()
		# checks read first; this list skipped it, so an admin-only login saw
		# every team's requests and their reasons. Same two gates as decide.
		names = [row["name"] for row in self._list(readable=lambda doc: doc.name != "LA-1")["rows"]]
		self.assertNotIn("LA-1", names)
		self.assertIn("OT-1", names)

	def test_oldest_first_and_each_row_says_who_what_when_why(self):
		rows = self._list()["rows"]
		self.assertEqual([r["name"] for r in rows], ["OT-1", "LA-1"])
		leave = rows[1]
		self.assertEqual(leave["who"], "Aisyah")
		self.assertEqual(leave["kind"], "Time off")
		self.assertEqual(leave["detail"], "Annual Leave · 2 days")
		self.assertEqual(leave["reason"], "Sister's wedding")
		self.assertEqual(leave["modified"], "2026-09-20 10:00:00")

	def test_overtime_row_reads_in_hours_and_minutes(self):
		ot = self._list()["rows"][0]
		self.assertEqual(ot["kind"], "Overtime")
		self.assertEqual(ot["detail"], "1h 30m")

	def test_the_caller_is_never_a_parameter(self):
		import inspect

		self.assertEqual(list(inspect.signature(approvals_list.get_waiting_for_me).parameters), [])


if __name__ == "__main__":
	unittest.main()


class TestHomeCountsWhatThePageLists(unittest.TestCase):
	def test_home_count_uses_the_same_two_gates(self):
		# Home's "N to approve" opens this page. If the count admits a row the
		# list refuses, the approver is told of work they cannot find.
		import inspect

		from hrms.api import needs_you

		# One scan for both since review of 474d12d34: Home counts what the
		# page lists, by the page's own function.
		self.assertIn(
			"_mine_of(doctype, field, pending, cap=SCAN_CAP)", inspect.getsource(needs_you._pending_for)
		)
		self.assertIn(
			"_request_read_allowed(doc) and _is_routed_approver(doc)",
			inspect.getsource(approvals_list._mine_of),
		)


class TestRemoteCheckinsJoinTheList(unittest.TestCase):
	"""Owner ruling 23 Sep: approvals appear only where they can be done, and
	the plan (AUDIT-PLAN, Approvals row) folds "check-ins outside the area"
	into the one list instead of their own page. The rows come from the SAME
	fenced query the old page read (remote_checkin.list_pending_for_approver),
	so the fold changes where they show, never who sees them."""

	REMOTE = (
		frappe._dict(
			name="RCR-1",
			employee="E9",
			employee_name="Hafiz",
			checkin_time="2026-09-18 08:05:00",
			log_type="IN",
			distance_m=1250,
			employee_remarks="Client site",
			selfie_image="/files/s.jpg",
		),
	)

	def _list(self, remote):
		with (
			patch.object(frappe, "get_all", side_effect=fake_get_all, create=True),
			patch.object(frappe, "get_doc", side_effect=lambda dt, name: DOCS[(dt, name)]),
			patch.object(approvals_list, "_is_routed_approver", side_effect=lambda doc: doc.name != "LA-2"),
			patch.object(approvals_list, "_request_read_allowed", side_effect=lambda doc: True),
			patch.object(approvals_list, "_types_on_site", return_value=["Leave Application"]),
			patch.object(approvals_list, "_remote_checkins", side_effect=remote),
		):
			return approvals_list.get_waiting_for_me()

	def test_a_check_in_outside_the_area_is_a_row_like_any_other(self):
		rows = self._list(lambda: self.REMOTE)["rows"]
		remote = next(r for r in rows if r["doctype"] == "Remote Checkin Request")
		self.assertEqual(remote["kind"], "Check-in outside the area")
		self.assertEqual(remote["who"], "Hafiz")
		self.assertEqual(remote["detail"], "In · 1.25 km away")
		self.assertEqual(remote["reason"], "Client site")
		self.assertEqual(remote["selfie_image"], "/files/s.jpg")
		# Oldest first across every type: the check-in (18 Sep) before the leave (20 Sep).
		self.assertEqual(rows[0]["name"], "RCR-1")

	def test_the_remote_rows_come_from_the_old_pages_fenced_query(self):
		import inspect

		self.assertIn("list_pending_for_approver", inspect.getsource(approvals_list._remote_checkins))

	def test_a_failing_remote_query_does_not_take_the_page_down(self):
		def boom():
			raise RuntimeError("table missing")

		names = [r["name"] for r in self._list(boom)["rows"]]
		self.assertEqual(names, ["LA-1"])


class TestDatesReadLikeACalendar(unittest.TestCase):
	"""Seen live on fresh.local 23 Sep: rows read "2026-09-15 · Nadi W0 Annual".
	An approver reads "Tue 15 Sep", the Home title's format."""

	def test_one_day(self):
		self.assertEqual(approvals_list._range("2026-09-15", "2026-09-15"), "Tue 15 Sep")

	def test_a_span(self):
		self.assertEqual(approvals_list._range("2026-09-22", "2026-09-23"), "Tue 22 Sep – Wed 23 Sep")

	def test_a_check_in_time(self):
		self.assertEqual(approvals_list._moment("2026-09-18 08:05:00"), "Fri 18 Sep, 8:05 am")

	def test_nothing_stays_nothing(self):
		self.assertEqual(approvals_list._range(None, None), "")


class TestTheCapCountsMyRowsNotTheSites(unittest.TestCase):
	"""Review of 474d12d34: the cap was applied to every pending request on the
	site BEFORE asking whose it was. With 60 older requests routed elsewhere,
	the one routed to me fell past the cap: missing from the page and from
	Home's count, with no other door left."""

	def test_my_request_behind_sixty_others_is_still_found(self):
		others = [f"LA-{i:03d}" for i in range(60)]
		names = [*others, "LA-MINE"]

		def paged(doctype, filters=None, pluck=None, order_by=None, limit=None, start=0, **kw):
			return names[start : start + limit] if doctype == "Leave Application" else []

		docs = {
			n: frappe._dict(
				doctype="Leave Application",
				name=n,
				employee="E",
				employee_name=n,
				modified=f"2026-09-{1 + i % 20:02d} 00:00:00",
			)
			for i, n in enumerate(names)
		}
		with (
			patch.object(frappe, "get_all", side_effect=paged, create=True),
			patch.object(frappe, "get_doc", side_effect=lambda dt, n: docs[n]),
			patch.object(approvals_list, "_request_read_allowed", side_effect=lambda d: True),
			patch.object(approvals_list, "_is_routed_approver", side_effect=lambda d: d.name == "LA-MINE"),
			patch.object(approvals_list, "_types_on_site", return_value=["Leave Application"]),
			patch.object(approvals_list, "_remote_checkins", return_value=[]),
		):
			result = approvals_list.get_waiting_for_me()
		self.assertEqual([r["name"] for r in result["rows"]], ["LA-MINE"])
		self.assertFalse(result["capped"])


class TestHomeStopsAtItsOwnCap(unittest.TestCase):
	def test_home_reads_no_more_than_it_can_show(self):
		reads = []
		names = [f"LA-{i:03d}" for i in range(300)]

		def paged(doctype, filters=None, pluck=None, order_by=None, limit=None, start=0, **kw):
			return names[start : start + limit]

		def doc(dt, n):
			reads.append(n)
			return frappe._dict(doctype=dt, name=n, employee="E")

		with (
			patch.object(frappe, "get_all", side_effect=paged, create=True),
			patch.object(frappe, "get_doc", side_effect=doc),
			patch.object(approvals_list, "_request_read_allowed", side_effect=lambda d: True),
			patch.object(approvals_list, "_is_routed_approver", side_effect=lambda d: True),
		):
			mine, more = approvals_list._mine_of("Leave Application", "status", "Open", cap=20)
		self.assertEqual((len(mine), more), (20, True))
		self.assertEqual(len(reads), 21, "stops at cap + 1")


class TestGivingUpIsNotMore(unittest.TestCase):
	"""Review of f0cd01580: when the scan stopped at SCAN_LIMIT with only a
	few of mine found, Home said "20+" while the page listed those few."""

	def test_a_long_scan_with_three_of_mine_reports_three(self):
		names = [f"LA-{i:04d}" for i in range(approvals_list.SCAN_LIMIT + 200)]
		mine_names = {"LA-0005", "LA-0400", "LA-0900"}

		def paged(doctype, filters=None, pluck=None, order_by=None, limit=None, start=0, **kw):
			return names[start : start + limit]

		with (
			patch.object(frappe, "get_all", side_effect=paged, create=True),
			patch.object(frappe, "get_doc", side_effect=lambda dt, n: frappe._dict(doctype=dt, name=n)),
			patch.object(approvals_list, "_request_read_allowed", side_effect=lambda d: True),
			patch.object(approvals_list, "_is_routed_approver", side_effect=lambda d: d.name in mine_names),
		):
			mine, more = approvals_list._mine_of("Leave Application", "status", "Open", cap=20)
		self.assertEqual(len(mine), 3)
		self.assertFalse(more, "gave up scanning, did not find more than the cap")
