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
			"_mine_of(doctype, field, pending, cap=SCAN_CAP, yours_only=True)",
			inspect.getsource(needs_you._pending_for),
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


# --- Grouped approvals (owner-approved design, 23 Sep 2026) ------------------
#
# The page splits into YOURS (sent to you: the request's own approver field, the
# approver named on the employee's record, or they report to you) and OTHER
# TEAMS (everything else you already receive because you are higher up the
# chain, or HR). Access does not change: the same rows, the same two gates. Each
# row only gains where it belongs: section, department, whose team it is.

CALLER = "boss@example.com"
CALLER_EMPLOYEE = "EMP-BOSS"

EMPLOYEES = {
	# Sent to the caller by the employee's own record (leave_approver), with
	# the case and spacing drift a mirror leaves behind.
	"E-LEAVE": frappe._dict(
		department="Production - NSTY",
		leave_approver="Boss@Example.com ",
		shift_request_approver=None,
		reports_to="EMP-OTHER",
	),
	# Reports to the caller's own employee.
	"E-REPORT": frappe._dict(
		department="Production - NSTY",
		leave_approver=None,
		shift_request_approver=None,
		reports_to=CALLER_EMPLOYEE,
	),
	# Someone else's team: the caller receives it only from higher up.
	"E-QC": frappe._dict(
		department="QC - NSTY",
		leave_approver="ahmad@example.com",
		shift_request_approver=None,
		reports_to="EMP-SITI",
	),
	# Someone else's team with no named approver: the manager's name.
	"E-LOG": frappe._dict(
		department="Logistics - NSTY",
		leave_approver=None,
		shift_request_approver=None,
		reports_to="EMP-SITI",
	),
	# Check-ins outside the area are sent by the shift approver.
	"E-REMOTE": frappe._dict(
		department=None,
		leave_approver="ahmad@example.com",
		shift_request_approver="boss@example.com",
		reports_to="EMP-SITI",
	),
}


def fake_get_value(doctype, name, fields=None, as_dict=False, **kw):
	if doctype == "Employee" and isinstance(fields, list):
		return EMPLOYEES.get(name)
	if doctype == "Employee" and fields == "employee_name":
		return {"EMP-SITI": "Siti Aminah"}.get(name)
	if doctype == "User" and fields == "full_name":
		return {"ahmad@example.com": "Ahmad Faiz"}.get(name)
	raise AssertionError(f"unexpected get_value {doctype} {name} {fields}")


GROUPED_DOCS = {
	("Leave Application", "LA-MINE"): frappe._dict(
		doctype="Leave Application",
		name="LA-MINE",
		employee="E-QC",
		employee_name="Farid",
		leave_approver="boss@example.com",
		modified="2026-09-10 10:00:00",
	),
	("OT Request", "OT-REPORT"): frappe._dict(
		doctype="OT Request",
		name="OT-REPORT",
		employee="E-REPORT",
		employee_name="Mohd Shazwan",
		claimed_hours=2.5,
		modified="2026-09-11 10:00:00",
	),
	("Attendance Request", "AR-LEAVE"): frappe._dict(
		doctype="Attendance Request",
		name="AR-LEAVE",
		employee="E-LEAVE",
		employee_name="Aisyah",
		modified="2026-09-12 10:00:00",
	),
	("OT Request", "OT-QC"): frappe._dict(
		doctype="OT Request",
		name="OT-QC",
		employee="E-QC",
		employee_name="Farid",
		claimed_hours=1,
		modified="2026-09-13 10:00:00",
	),
	("Attendance Request", "AR-LOG"): frappe._dict(
		doctype="Attendance Request",
		name="AR-LOG",
		employee="E-LOG",
		employee_name="Rosli",
		modified="2026-09-14 10:00:00",
	),
}

REMOTE_ROWS = (
	frappe._dict(name="RCR-SHIFT", employee="E-REMOTE", employee_name="Hafiz", approver="hr@example.com"),
	frappe._dict(name="RCR-STAMPED", employee="E-LOG", employee_name="Rosli", approver="boss@example.com"),
	frappe._dict(name="RCR-OTHER", employee="E-QC", employee_name="Farid", approver="ahmad@example.com"),
)


def grouped_get_all(doctype, filters=None, pluck=None, **kw):
	return [name for (dt, name) in GROUPED_DOCS if dt == doctype]


def grouped_patches(user=CALLER, own=(CALLER_EMPLOYEE,), routed=lambda doc: True):
	return [
		patch.object(frappe, "get_all", side_effect=grouped_get_all, create=True),
		patch.object(frappe, "get_doc", side_effect=lambda dt, name: GROUPED_DOCS[(dt, name)]),
		patch.object(frappe, "session", frappe._dict(user=user)),
		patch.object(frappe.db, "get_value", side_effect=fake_get_value),
		patch.object(frappe.db, "table_exists", return_value=True),
		patch.object(approvals_list, "own_employees", return_value=list(own)),
		patch.object(approvals_list, "_is_routed_approver", side_effect=routed),
		patch.object(approvals_list, "_request_read_allowed", side_effect=lambda doc: True),
		patch.object(
			approvals_list,
			"_types_on_site",
			return_value=["Leave Application", "OT Request", "Attendance Request"],
		),
		patch.object(approvals_list, "_remote_checkins", return_value=list(REMOTE_ROWS)),
	]


class _Patched:
	def __init__(self, patches):
		self._patches = patches

	def __enter__(self):
		for p in self._patches:
			p.start()

	def __exit__(self, *exc):
		for p in reversed(self._patches):
			p.stop()
		return False


class TestGroupedApprovals(unittest.TestCase):
	def _list(self, **kw):
		with _Patched(grouped_patches(**kw)):
			return {row["name"]: row for row in approvals_list.get_waiting_for_me()["rows"]}

	def test_a_request_naming_me_as_its_approver_is_mine(self):
		self.assertEqual(self._list()["LA-MINE"]["section"], "yours")

	def test_a_request_from_someone_who_reports_to_me_is_mine(self):
		self.assertEqual(self._list()["OT-REPORT"]["section"], "yours")

	def test_a_request_from_someone_whose_record_names_me_is_mine(self):
		# The login on the record drifted in case and spacing; still me.
		self.assertEqual(self._list()["AR-LEAVE"]["section"], "yours")

	def test_a_request_sent_to_someone_below_me_is_another_teams(self):
		rows = self._list()
		self.assertEqual(rows["OT-QC"]["section"], "other")
		self.assertEqual(rows["AR-LOG"]["section"], "other")

	def test_another_team_is_named_by_its_direct_approver(self):
		rows = self._list()
		# The employee's leave approver, by full name ...
		self.assertEqual(rows["OT-QC"]["approver_name"], "Ahmad Faiz")
		# ... else the manager they report to.
		self.assertEqual(rows["AR-LOG"]["approver_name"], "Siti Aminah")

	def test_the_department_is_its_plain_name(self):
		rows = self._list()
		self.assertEqual(rows["OT-REPORT"]["department"], "Production")
		self.assertEqual(rows["OT-QC"]["department"], "QC")
		self.assertEqual(rows["RCR-SHIFT"]["department"], "")

	def test_overtime_rows_carry_their_hours_and_every_row_its_employee(self):
		rows = self._list()
		self.assertEqual(rows["OT-REPORT"]["hours"], 2.5)
		self.assertEqual(rows["AR-LEAVE"]["hours"], 0)
		self.assertEqual(rows["OT-REPORT"]["employee"], "E-REPORT")
		self.assertEqual(rows["RCR-SHIFT"]["employee"], "E-REMOTE")

	def test_a_check_in_goes_by_the_shift_approver_or_the_name_stamped_on_it(self):
		rows = self._list()
		self.assertEqual(rows["RCR-SHIFT"]["section"], "yours")
		self.assertEqual(rows["RCR-STAMPED"]["section"], "yours")
		self.assertEqual(rows["RCR-OTHER"]["section"], "other")

	def test_grouping_never_changes_which_rows_are_listed(self):
		# Access is the two gates, unchanged: a row they refuse stays out.
		names = set(self._list(routed=lambda doc: doc.name != "OT-QC"))
		self.assertEqual(
			names,
			{"LA-MINE", "OT-REPORT", "AR-LEAVE", "AR-LOG", "RCR-SHIFT", "RCR-STAMPED", "RCR-OTHER"},
		)

	def test_an_hr_operator_sees_every_team_but_nothing_is_theirs_unless_sent(self):
		# HR is routed everything; what was not sent to them is another team's.
		rows = self._list(user="hr@example.com", own=())
		self.assertEqual(sorted(n for n, r in rows.items() if r["section"] == "yours"), ["RCR-SHIFT"])
		self.assertEqual(len(rows), 8)


class TestHomeCountsYoursOnly(unittest.TestCase):
	"""Rule 7: Home's "waiting on you" counts what was sent to you, not the
	other teams you can also see."""

	def _needs_you(self):
		from hrms.api import needs_you

		with _Patched(grouped_patches()):
			return needs_you.get_needs_you()

	def test_home_counts_only_what_was_sent_to_me(self):
		out = self._needs_you()
		counts = {row["doctype"]: row["count"] for row in out["rows"]}
		# LA-MINE, OT-REPORT, AR-LEAVE are mine; OT-QC and AR-LOG are other teams'.
		self.assertEqual(counts, {"Leave Application": 1, "OT Request": 1, "Attendance Request": 1})
		self.assertEqual(out["total"], 3)

	def test_home_counts_only_my_check_ins(self):
		# RCR-SHIFT (my shift approvee) and RCR-STAMPED (stamped to me); not RCR-OTHER.
		self.assertEqual(self._needs_you()["checkins"], 2)


class TestHalfDaySessionOnTheApproverRow(unittest.TestCase):
	"""The approver reads which half (owner, 25 Sep 2026): 'Half day · AM'."""

	def test_a_half_day_names_its_session(self):
		doc = frappe._dict(
			doctype="Leave Application",
			leave_type="Annual Leave",
			from_date="2026-10-14",
			to_date="2026-10-14",
			total_leave_days=0.5,
			half_day=1,
			half_day_session="AM",
		)
		self.assertEqual(approvals_list._row(doc)["detail"], "Annual Leave · Half day · AM")

	def test_an_older_half_day_without_a_session_reads_as_before(self):
		doc = frappe._dict(
			doctype="Leave Application", leave_type="Annual Leave", total_leave_days=0.5, half_day=1
		)
		self.assertEqual(approvals_list._row(doc)["detail"], "Annual Leave · 0.5 days")
