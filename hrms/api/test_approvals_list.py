"""The Approvals page list (audit-flows 4B, AUDIT-PLAN P1-B, owner ruling 23 Sep:
approvals appear only where they can be done). One list of everything waiting
on the caller, across every request type, decided by the SAME routed-approver
check that Home's count and `approval.decide` use, so the page can never show
a row the approver cannot decide, or hide one Home counted.

Owner ruling, 8 Oct 2026: the page lists only requests SENT to the caller; the
"Other teams" rows are gone from it (stepping in from Desk or a notification is
untouched). Bulk approvals v2 also put row details on each line.
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import approvals_list
from hrms.tests._fake_document import FakeDocument

BOSS = "boss@example.com"

# The live leave balance needs the leave controller and a database. Tests that are not about it get
# "no number", which is what a leave without pay gets; the ones that are patch their own value.
_NO_BALANCE = patch.object(approvals_list, "_leave_balance_now", return_value=None)


def setUpModule():
	_NO_BALANCE.start()


def tearDownModule():
	_NO_BALANCE.stop()


def sent_to_boss():
	"""Patches that make the caller `boss` and every Employee record name boss as approver.

	The page lists only what was sent to the caller (owner, 8 Oct 2026), so a fixture that wants
	its rows listed has to send them.
	"""

	def employee_facts(doctype, name, fields=None, **kw):
		if doctype == "Employee" and isinstance(fields, list):
			return frappe._dict(
				department=None, leave_approver=BOSS, shift_request_approver=BOSS, reports_to=None
			)
		return None

	return [
		patch.object(approvals_list, "_me", return_value={"login": BOSS, "employee": None}),
		patch.object(frappe.db, "get_value", side_effect=employee_facts),
	]


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
	def _list(self, readable=lambda doc: True, reason_readable=lambda doc: True):
		with (
			patch.object(frappe, "get_all", side_effect=fake_get_all, create=True),
			patch.object(frappe, "get_doc", side_effect=lambda dt, name: DOCS[(dt, name)]),
			patch.object(approvals_list, "_is_routed_approver", side_effect=lambda doc: doc.name != "LA-2"),
			patch.object(approvals_list, "_request_read_allowed", side_effect=readable, create=True),
			patch.object(
				approvals_list,
				"may_read_leave_reasons",
				side_effect=lambda docs, user=None: [reason_readable(doc) for doc in docs],
				create=True,
			),
			patch.object(approvals_list, "_types_on_site", return_value=["Leave Application", "OT Request"]),
			_Patched(sent_to_boss()),
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

	def test_the_reason_is_withheld_from_a_reader_the_helper_refuses(self):
		# owner ruling 5 Oct 2026: approvers on the line read the reason, others do not; the page
		# asks the SAME helper as the leave list
		rows = self._list(reason_readable=lambda doc: False)["rows"]
		leave = next(row for row in rows if row["name"] == "LA-1")
		self.assertEqual(leave["reason"], "")
		self.assertEqual(leave["who"], "Aisyah")  # the request itself is still listed

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
			patch.object(
				approvals_list,
				"may_read_leave_reasons",
				side_effect=lambda docs, user=None: [True] * len(list(docs)),
				create=True,
			),
			patch.object(approvals_list, "_types_on_site", return_value=["Leave Application"]),
			patch.object(approvals_list, "_remote_checkins", side_effect=remote),
			_Patched(sent_to_boss()),
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
			_Patched(sent_to_boss()),
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
			"may_read_leave_reasons",
			side_effect=lambda docs, user=None: [True] * len(list(docs)),
			create=True,
		),
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

	def _every(self, **kw):
		"""Every row the two gates admit, placed but not narrowed: `_row` is where placement lives.

		The page itself lists YOURS only (owner, 8 Oct 2026); other teams' rows are still placed
		the same way for Desk and notification step-ins, so their placement is read here.
		"""
		with _Patched(grouped_patches(**kw)):
			me, cache = approvals_list._me(), {}
			rows = [
				approvals_list._row(doc, me, cache, may_read_reason=True) for doc in GROUPED_DOCS.values()
			]
			rows += [approvals_list._remote_row(req, me, cache) for req in REMOTE_ROWS]
		return {row["name"]: row for row in rows}

	def test_a_request_naming_me_as_its_approver_is_mine(self):
		self.assertEqual(self._list()["LA-MINE"]["section"], "yours")

	def test_a_request_from_someone_who_reports_to_me_is_mine(self):
		self.assertEqual(self._list()["OT-REPORT"]["section"], "yours")

	def test_a_request_from_someone_whose_record_names_me_is_mine(self):
		# The login on the record drifted in case and spacing; still me.
		self.assertEqual(self._list()["AR-LEAVE"]["section"], "yours")

	def test_a_request_sent_to_someone_below_me_is_another_teams(self):
		rows = self._every()
		self.assertEqual(rows["OT-QC"]["section"], "other")
		self.assertEqual(rows["AR-LOG"]["section"], "other")

	def test_another_team_is_named_by_its_direct_approver(self):
		rows = self._every()
		# The employee's leave approver, by full name ...
		self.assertEqual(rows["OT-QC"]["approver_name"], "Ahmad Faiz")
		# ... else the manager they report to.
		self.assertEqual(rows["AR-LOG"]["approver_name"], "Siti Aminah")

	def test_the_department_is_its_plain_name(self):
		rows = self._every()
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
		rows = self._every()
		self.assertEqual(rows["RCR-SHIFT"]["section"], "yours")
		self.assertEqual(rows["RCR-STAMPED"]["section"], "yours")
		self.assertEqual(rows["RCR-OTHER"]["section"], "other")

	def test_a_row_the_gates_refuse_stays_out_of_the_page(self):
		# Access is the two gates, unchanged: a row they refuse is not listed, sent to me or not.
		names = set(self._list(routed=lambda doc: doc.name != "OT-REPORT"))
		self.assertEqual(names, {"LA-MINE", "AR-LEAVE", "RCR-SHIFT", "RCR-STAMPED"})

	def test_an_hr_operator_is_routed_everything_but_the_page_lists_only_what_was_sent_to_them(self):
		rows = self._list(user="hr@example.com", own=())
		self.assertEqual(sorted(rows), ["RCR-SHIFT"])
		self.assertEqual(len(self._every(user="hr@example.com", own=())), 8)


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


# --- One reason check per page, not per row (6 Oct 2026, alpha.36 slice O1) ---------------------
# `_row` asked `may_read_leave_reason(doc)` for every leave request: one routing/company check per
# row. `approval.may_read_leave_reasons` is the same rule for a list (alpha.35); the page hands it
# the whole leave list once and each row its own answer.

READER = "boss@example.com"
READER_EMPLOYEE = "E-BOSS"

BATCH_LEAVE_DOCS = {
	("Leave Application", f"LA-{i}"): frappe._dict(
		doctype="Leave Application",
		name=f"LA-{i}",
		employee=employee,
		employee_name=employee,
		leave_type="Annual Leave",
		leave_approver=approver,
		description=f"reason {i}",
		modified=f"2026-09-1{i} 10:00:00",
	)
	for i, (employee, approver) in enumerate(
		[
			(READER_EMPLOYEE, "someone@example.com"),  # the reader's own request
			("E-TEAM", READER),  # the reader is on its approval line
			("E-STRANGER", "other@example.com"),  # managed by a stranger, reader not on the line
			("E-TEAM", READER),
			("E-STRANGER", "other@example.com"),
			(READER_EMPLOYEE, "someone@example.com"),
		]
	)
}
BATCH_OT_DOCS = {
	("OT Request", "OT-1"): frappe._dict(
		doctype="OT Request",
		name="OT-1",
		employee="E-TEAM",
		employee_name="Ria",
		claimed_hours=1,
		explanation="Stock count",
		modified="2026-09-05 09:00:00",
	)
}


class TestTheReasonsAreAskedInOneBatch(unittest.TestCase):
	#: what the 5 Oct 2026 ruling says the reader may read, row order = LA-0 .. LA-5
	RULED = (True, True, False, True, False, True)

	def _list(self, batch, single, types=("Leave Application",)):
		docs = {**BATCH_LEAVE_DOCS, **BATCH_OT_DOCS}
		with (
			patch.object(
				frappe, "get_all", side_effect=lambda dt, **kw: [n for (d, n) in docs if d == dt], create=True
			),
			patch.object(frappe, "get_doc", side_effect=lambda dt, name: docs[(dt, name)]),
			patch.object(frappe, "session", frappe._dict(user=READER)),
			# everyone reports to the reader: the page lists what was sent to them (8 Oct 2026)
			patch.object(frappe.db, "get_value", return_value={"reports_to": READER_EMPLOYEE}),
			patch.object(approvals_list, "own_employees", return_value=[READER_EMPLOYEE]),
			patch.object(approvals_list, "_is_routed_approver", return_value=True),
			patch.object(approvals_list, "_request_read_allowed", return_value=True),
			patch.object(approvals_list, "may_read_leave_reasons", batch, create=True),
			patch.object(approvals_list, "may_read_leave_reason", single),
			patch.object(approvals_list, "_types_on_site", return_value=list(types)),
			patch.object(approvals_list, "_remote_checkins", return_value=[]),
		):
			return {row["name"]: row for row in approvals_list.get_waiting_for_me()["rows"]}

	def test_a_page_of_leave_rows_asks_the_batch_once_and_the_single_form_never(self):
		batch = MagicMock(side_effect=lambda docs, user=None: [True] * len(list(docs)))
		single = MagicMock(return_value=True)
		rows = self._list(batch, single)
		self.assertEqual(len(rows), 6)
		self.assertEqual(batch.call_count, 1, "one batch per page, however many rows")
		self.assertEqual(single.call_count, 0, "the per-row question is the N+1 this removes")
		asked = [doc.name for doc in batch.call_args.args[0]]
		self.assertEqual(sorted(asked), [f"LA-{i}" for i in range(6)])

	def test_other_request_types_do_not_ask_for_a_leave_reason(self):
		batch = MagicMock(side_effect=lambda docs, user=None: [True] * len(list(docs)))
		single = MagicMock(return_value=True)
		rows = self._list(batch, single, types=("Leave Application", "OT Request"))
		self.assertEqual(batch.call_count, 1, "only the leave list is asked")
		self.assertEqual(single.call_count, 0)
		self.assertEqual(rows["OT-1"]["reason"], "Stock count")  # the overtime reason is not gated

	def test_each_row_keeps_or_blanks_its_reason_as_the_rule_says(self):
		from hrms.api import approval

		# the REAL rule, through its real seams; the per-row form must not be the one consulted
		def refused(*a, **k):
			raise AssertionError("the page asked the per-row form")

		with (
			patch("hrms.utils.identity.own_employees", return_value=[READER_EMPLOYEE]),
			patch("hrms.hr.utils.sees_all_employee_data", return_value=False),
			patch("hrms.overrides.company_scope.company_visible", return_value=False),
			patch.object(
				approval,
				"_is_routed_approver",
				side_effect=lambda doc, user=None, **k: doc.get("leave_approver") == user,
			),
			patch.object(approval.frappe, "session", frappe._dict(user=READER)),
		):
			rows = self._list(approval.may_read_leave_reasons, refused)
			docs = [BATCH_LEAVE_DOCS[("Leave Application", f"LA-{i}")] for i in range(6)]
			single_answers = [approval.may_read_leave_reason(doc, READER) for doc in docs]
		self.assertEqual(single_answers, list(self.RULED))
		kept = [rows[f"LA-{i}"]["reason"] for i in range(6)]
		self.assertEqual(kept, [f"reason {i}" if ok else "" for i, ok in enumerate(self.RULED)])


# --- Other teams are off the page (owner ruling, 8 Oct 2026) -----------------------------------


class TestOtherTeamsAreOffThePage(unittest.TestCase):
	"""The page lists only requests sent to the caller. A caller who is merely higher up the chain,
	or HR, can still step in from Desk or a notification (decide and needs_you are untouched)."""

	def _page(self, **kw):
		with _Patched(grouped_patches(**kw)):
			return approvals_list.get_waiting_for_me()

	def test_every_listed_row_was_sent_to_the_caller_and_still_says_so(self):
		rows = self._page()["rows"]
		self.assertEqual(
			sorted(r["name"] for r in rows), ["AR-LEAVE", "LA-MINE", "OT-REPORT", "RCR-SHIFT", "RCR-STAMPED"]
		)
		# calendar.py filters on the key: it stays on every row
		self.assertEqual({r["section"] for r in rows}, {"yours"})

	def test_another_teams_check_in_is_dropped_like_its_requests(self):
		names = [r["name"] for r in self._page()["rows"]]
		self.assertNotIn("RCR-OTHER", names)
		self.assertNotIn("OT-QC", names)
		self.assertNotIn("AR-LOG", names)

	def test_the_balance_is_not_looked_up_for_a_row_the_page_will_not_show(self):
		docs = {
			("Leave Application", "LA-OTHER"): FakeDocument(
				"Leave Application",
				name="LA-OTHER",
				employee="E-QC",
				employee_name="Farid",
				leave_type="Annual Leave",
				total_leave_days=1,
				modified="2026-09-10 10:00:00",
			),
		}
		balance = MagicMock(return_value=4.0)
		patches = [
			*grouped_patches(),
			patch.object(frappe, "get_all", side_effect=lambda dt, **kw: [n for (d, n) in docs if d == dt]),
			patch.object(frappe, "get_doc", side_effect=lambda dt, name: docs[(dt, name)]),
			patch.object(approvals_list, "_types_on_site", return_value=["Leave Application"]),
			patch.object(approvals_list, "_remote_checkins", return_value=[]),
			patch.object(approvals_list, "_leave_balance_now", balance),
		]
		with _Patched(patches):
			rows = approvals_list.get_waiting_for_me()["rows"]
		self.assertEqual(rows, [])
		balance.assert_not_called()

	def test_the_scan_that_needs_you_and_step_ins_use_still_admits_other_teams_rows(self):
		# the narrowing is this page's alone: the scan without yours_only still sees them
		with _Patched(grouped_patches()):
			mine, _more = approvals_list._mine_of("OT Request", "status", "Open")
		self.assertEqual(sorted(doc.name for doc in mine), ["OT-QC", "OT-REPORT"])


# --- One hundred a type: bulk handles 100 per action (owner, 8 Oct 2026) ----------------------


class TestThePageHoldsAHundredPerType(unittest.TestCase):
	def _page(self, how_many):
		names = [f"LA-{i:03d}" for i in range(how_many)]
		docs = {
			n: FakeDocument(
				"Leave Application",
				name=n,
				employee="E",
				employee_name=n,
				leave_type="Annual Leave",
				leave_approver=BOSS,
				modified=f"2026-09-{1 + i % 20:02d} 00:00:00",
			)
			for i, n in enumerate(names)
		}

		def paged(doctype, filters=None, pluck=None, order_by=None, limit=None, start=0, **kw):
			if doctype == "File":
				return []
			return names[start : start + limit] if doctype == "Leave Application" else []

		with (
			patch.object(frappe, "get_all", side_effect=paged),
			patch.object(frappe, "get_doc", side_effect=lambda dt, n: docs[n]),
			patch.object(approvals_list, "_request_read_allowed", return_value=True),
			patch.object(approvals_list, "_is_routed_approver", return_value=True),
			patch.object(
				approvals_list, "may_read_leave_reasons", side_effect=lambda d, user=None: [True] * len(d)
			),
			patch.object(approvals_list, "_types_on_site", return_value=["Leave Application"]),
			patch.object(approvals_list, "_remote_checkins", return_value=[]),
			_Patched(sent_to_boss()),
		):
			return approvals_list.get_waiting_for_me()

	def test_a_hundred_of_mine_are_listed_and_the_list_is_not_capped(self):
		result = self._page(100)
		self.assertEqual(len(result["rows"]), 100)
		self.assertFalse(result["capped"])

	def test_past_a_hundred_the_page_says_there_are_more(self):
		result = self._page(120)
		self.assertEqual(len(result["rows"]), 100)
		self.assertTrue(result["capped"])

	def test_home_keeps_its_own_cap(self):
		from hrms.api import needs_you

		self.assertEqual(needs_you.SCAN_CAP, 20)
		self.assertEqual(approvals_list.LIST_CAP, 100)


# --- Row details (bulk approvals v2 slice S1) ---------------------------------------------------

ME = {"login": BOSS, "employee": None}


def a_row(doc, **kw):
	"""One request as a row, placement quiet: the employee's facts are already known."""
	return approvals_list._row(doc, ME, {doc.get("employee"): {}}, **kw)


def leave(**fields):
	return FakeDocument(
		"Leave Application",
		**{
			"name": "LA-1",
			"employee": "E1",
			"employee_name": "Aisyah",
			"leave_type": "Annual Leave",
			"from_date": "2026-10-14",
			"to_date": "2026-10-15",
			"total_leave_days": 2,
			"description": "Sister's wedding",
			"modified": "2026-10-01 09:00:00",
			**fields,
		},
	)


class TestLeaveRowDetails(unittest.TestCase):
	def _row(self, balance, **fields):
		with patch.object(approvals_list, "_leave_balance_now", return_value=balance):
			return a_row(leave(**fields), may_read_reason=True, attached=set())

	def test_the_balance_after_approving_is_the_live_balance_less_the_days_asked(self):
		row = self._row(5.0)
		self.assertEqual(row["balance_after"], 3.0)
		self.assertEqual(row["days"], 2.0)

	def test_a_balance_that_would_go_negative_is_shown_as_it_is(self):
		self.assertEqual(self._row(1.0)["balance_after"], -1.0)

	def test_no_number_stays_none_not_zero(self):
		# leave without pay, missing dates or a failed lookup: nothing to subtract from
		self.assertIsNone(self._row(None)["balance_after"])

	def test_float_noise_is_not_shown(self):
		self.assertEqual(self._row(1.1, total_leave_days=0.2)["balance_after"], 0.9)

	def test_it_asks_the_one_live_balance_helper_for_this_request(self):
		doc = leave()
		with patch.object(approvals_list, "_leave_balance_now", return_value=4.0) as ask:
			a_row(doc, may_read_reason=True, attached=set())
		ask.assert_called_once_with(doc)

	def test_half_day_is_a_plain_yes_no(self):
		half = self._row(3.0, half_day=1, half_day_session="AM", total_leave_days=0.5)
		self.assertIs(half["half_day"], True)
		self.assertIs(self._row(3.0)["half_day"], False)

	def test_existing_keys_are_unchanged(self):
		row = self._row(5.0)
		self.assertEqual(row["detail"], "Annual Leave · 2 days")
		self.assertEqual(row["reason"], "Sister's wedding")
		self.assertEqual(row["kind"], "Time off")
		self.assertEqual(row["when"], "Wed 14 Oct – Thu 15 Oct")

	def test_the_reason_rule_is_untouched_a_refused_reader_still_gets_a_blank_reason(self):
		with patch.object(approvals_list, "_leave_balance_now", return_value=5.0):
			row = a_row(leave(), may_read_reason=False, attached=set())
		self.assertEqual(row["reason"], "")
		self.assertEqual(row["balance_after"], 3.0)

	def test_attached_comes_from_the_names_the_page_already_looked_up(self):
		with patch.object(approvals_list, "_leave_balance_now", return_value=5.0):
			self.assertIs(a_row(leave(), may_read_reason=True, attached={"LA-1", "LA-9"})["attached"], True)
			self.assertIs(a_row(leave(), may_read_reason=True, attached={"LA-9"})["attached"], False)

	def test_a_single_caller_without_the_set_asks_for_this_one_request(self):
		with (
			patch.object(approvals_list, "_leave_balance_now", return_value=5.0),
			patch.object(frappe, "get_all", return_value=["LA-1"]) as files,
		):
			row = a_row(leave(), may_read_reason=True)
		self.assertIs(row["attached"], True)
		files.assert_called_once_with(
			"File",
			filters={"attached_to_doctype": "Leave Application", "attached_to_name": ["in", ["LA-1"]]},
			pluck="attached_to_name",
		)


class TestExpenseRowDetails(unittest.TestCase):
	def _claim(self, **fields):
		return FakeDocument(
			"Expense Claim",
			**{
				"name": "EC-1",
				"employee": "E1",
				"employee_name": "Aisyah",
				"company": "NSTY",
				"posting_date": "2026-10-03",
				"grand_total": 150,
				"modified": "2026-10-01 09:00:00",
				**fields,
			},
		)

	def _lines(self, *types):
		return [FakeDocument("Expense Claim Detail", expense_type=t) for t in types]

	def _row(self, claim, attached=frozenset()):
		with patch.object(frappe, "get_cached_value", return_value="MYR", create=True) as default:
			row = a_row(claim, attached=attached)
		return row, default

	def test_item_count_and_distinct_types_in_the_order_they_were_claimed(self):
		claim = self._claim(expenses=self._lines("Travel", "Meal", "Travel", "Parking", "Meal"))
		row, _ = self._row(claim)
		self.assertEqual(row["items"], 5)
		self.assertEqual(row["expense_types"], ["Travel", "Meal", "Parking"])

	def test_a_claim_with_no_lines_has_zero_items_and_no_types(self):
		row, _ = self._row(self._claim())
		self.assertEqual((row["items"], row["expense_types"]), (0, []))

	def test_a_line_without_a_type_is_counted_but_not_named(self):
		row, _ = self._row(self._claim(expenses=self._lines("Travel", None)))
		self.assertEqual((row["items"], row["expense_types"]), (2, ["Travel"]))

	def test_the_claims_own_currency_wins(self):
		row, default = self._row(self._claim(currency="USD"))
		self.assertEqual(row["currency"], "USD")
		default.assert_not_called()

	def test_without_one_it_is_the_companys_default_currency(self):
		row, default = self._row(self._claim())
		self.assertEqual(row["currency"], "MYR")
		default.assert_called_once_with("Company", "NSTY", "default_currency")

	def test_attached_comes_from_the_page_lookup(self):
		self.assertIs(self._row(self._claim(), attached={"EC-1"})[0]["attached"], True)
		self.assertIs(self._row(self._claim(), attached=set())[0]["attached"], False)

	def test_existing_keys_are_unchanged(self):
		row, _ = self._row(self._claim(remark="Client lunch"))
		self.assertEqual(row["kind"], "Expense")
		self.assertEqual(row["reason"], "Client lunch")
		self.assertEqual(row["hours"], 0)


class TestShiftRowDetails(unittest.TestCase):
	"""Shift change: the shift they work now, then the one they ask for."""

	def _request(self, **fields):
		return FakeDocument(
			"Shift Request",
			**{
				"name": "SR-1",
				"employee": "E1",
				"employee_name": "Aisyah",
				"shift_type": "Night",
				"from_date": "2026-10-14",
				"to_date": "2026-10-20",
				"modified": "2026-10-01 09:00:00",
				**fields,
			},
		)

	def _roster(self, assigned=None, default=None):
		"""The roster assignment covering the day (if any) and the Employee's default shift."""
		from hrms.utils import geofence

		found = frappe._dict(shift_type=assigned) if assigned else None

		def employee_field(doctype, name, field=None, *a, **k):
			return default if (doctype, field) == ("Employee", "default_shift") else None

		return [
			patch.object(geofence, "resolve_assignment", return_value=found),
			patch.object(frappe.db, "get_value", side_effect=employee_field),
		]

	def test_the_new_shift_is_the_one_asked_for(self):
		with _Patched(self._roster(default="Day")):
			row = a_row(self._request())
		self.assertEqual(row["new_shift"], "Night")
		self.assertEqual(row["detail"], "Night")

	def test_the_current_shift_is_the_roster_assignment_covering_the_first_day(self):
		with _Patched(self._roster(assigned="Evening", default="Day")):
			self.assertEqual(a_row(self._request())["current_shift"], "Evening")

	def test_the_assignment_is_asked_for_on_the_first_day_of_the_request(self):
		from hrms.utils import geofence

		with _Patched(self._roster(assigned="Evening")):
			a_row(self._request())
			asked = geofence.resolve_assignment.call_args
		self.assertEqual(asked.args[0], "E1")
		self.assertEqual(str(asked.args[1])[:10], "2026-10-14")

	def test_with_no_assignment_it_is_the_employees_default_shift(self):
		with _Patched(self._roster(default="Day")):
			self.assertEqual(a_row(self._request())["current_shift"], "Day")

	def test_no_assignment_and_no_default_is_blank(self):
		with _Patched(self._roster()):
			self.assertEqual(a_row(self._request())["current_shift"], "")

	def test_a_request_with_no_first_day_is_blank_without_asking(self):
		from hrms.utils import geofence

		with _Patched(self._roster(assigned="Evening", default="Day")):
			self.assertEqual(a_row(self._request(from_date=None))["current_shift"], "")
			geofence.resolve_assignment.assert_not_called()

	def test_a_failing_lookup_is_blank_and_logged_never_raised(self):
		from hrms.utils import geofence

		with (
			patch.object(geofence, "resolve_assignment", side_effect=RuntimeError("roster table missing")),
			self.assertLogs("hrms.api.approvals_list", level="WARNING") as logged,
		):
			row = a_row(self._request())
		self.assertEqual(row["current_shift"], "")
		self.assertEqual(row["new_shift"], "Night")
		self.assertIn("SR-1", "\n".join(logged.output))

	def test_why_get_employee_shift_is_not_asked_it_names_the_default_shift_outside_a_shifts_window(self):
		# get_employee_shift counts a shift only when the asked time is inside its check-in window, and
		# otherwise falls back to the DEFAULT shift. Asked for 00:00 on the day (or noon), it names
		# the default for anyone on an evening or night roster: the wrong "current shift".
		import datetime

		from hrms.hr.doctype.shift_assignment import shift_assignment as sa

		def a_shift(name, start, end):
			return frappe._dict(
				name=name,
				start_time=datetime.timedelta(hours=start),
				end_time=datetime.timedelta(hours=end),
				begin_check_in_before_shift_start_time=60,
				allow_check_out_after_shift_end_time=60,
				allow_overtime=0,
				overtime_type=None,
			)

		types = {"Evening": a_shift("Evening", 15, 22), "Day": a_shift("Day", 8, 17)}
		assignment = frappe._dict(
			name="SA-1",
			shift_type="Evening",
			start_date=datetime.date(2026, 10, 1),
			end_date=None,
			overtime_type=None,
		)
		with (
			patch.object(sa, "get_shifts_for_date", return_value=[assignment]),
			patch.object(sa, "get_shift_type", side_effect=lambda name: types[name]),
			patch.object(frappe.db, "get_value", return_value="Day"),
		):
			at_midnight = sa.get_employee_shift(
				"E1", datetime.datetime(2026, 10, 14, 0, 0), consider_default_shift=True
			)
		self.assertEqual(at_midnight.shift_type.name, "Day", "the default shift, not the Evening roster")


class TestAttendanceRowDetails(unittest.TestCase):
	def _request(self, **fields):
		return FakeDocument(
			"Attendance Request",
			**{
				"name": "AR-1",
				"employee": "E1",
				"employee_name": "Aisyah",
				"from_date": "2026-10-14",
				"to_date": "2026-10-14",
				"reason": "On Duty",
				"explanation": "Client visit",
				"modified": "2026-10-01 09:00:00",
				**fields,
			},
		)

	def test_in_and_out_read_as_hours_and_minutes(self):
		import datetime

		row = a_row(
			self._request(in_time=datetime.timedelta(hours=9, minutes=5), out_time=datetime.time(18, 30))
		)
		self.assertEqual((row["in_time"], row["out_time"]), ("09:05", "18:30"))

	def test_a_time_stored_as_text_is_trimmed_the_same_way(self):
		row = a_row(self._request(in_time="9:05:00", out_time="18:30:00"))
		self.assertEqual((row["in_time"], row["out_time"]), ("09:05", "18:30"))

	def test_no_time_is_blank_not_the_word_none(self):
		row = a_row(self._request())
		self.assertEqual((row["in_time"], row["out_time"]), ("", ""))

	def test_midnight_is_a_time_not_an_absence(self):
		import datetime

		row = a_row(self._request(in_time=datetime.timedelta(0), out_time=datetime.timedelta(hours=8)))
		self.assertEqual((row["in_time"], row["out_time"]), ("00:00", "08:00"))

	def test_the_detail_stays_the_reason_and_the_note_stays_the_explanation(self):
		row = a_row(self._request())
		self.assertEqual(row["detail"], "On Duty")
		self.assertEqual(row["reason"], "Client visit")


class TestOvertimeRowKeepsItsNote(unittest.TestCase):
	def test_the_page_gets_the_explanation_as_the_reason(self):
		ot = FakeDocument(
			"OT Request",
			name="OT-1",
			employee="E3",
			employee_name="Ria",
			ot_date="2026-09-05",
			claimed_hours=1.5,
			explanation="Stock count",
			modified="2026-09-19 09:00:00",
		)
		row = a_row(ot)
		self.assertEqual(row["reason"], "Stock count")
		self.assertEqual(row["detail"], "1h 30m")


# --- The request's own dates, for the page's date filter -------------------------------------


class TestRowsCarryTheirOwnDates(unittest.TestCase):
	def _dates(self, doc):
		row = a_row(doc)
		return row["from_date"], row["to_date"]

	def test_leave_shift_and_attendance_use_their_from_and_to(self):
		for doctype in ("Leave Application", "Shift Request", "Attendance Request"):
			doc = FakeDocument(
				doctype, name="X", employee="E1", from_date="2026-10-14", to_date="2026-10-16", modified="m"
			)
			with patch.object(approvals_list, "_leave_balance_now", return_value=None):
				self.assertEqual(self._dates(doc), ("2026-10-14", "2026-10-16"), doctype)

	def test_overtime_is_the_one_day(self):
		ot = FakeDocument("OT Request", name="X", employee="E1", ot_date="2026-09-05", modified="m")
		self.assertEqual(self._dates(ot), ("2026-09-05", "2026-09-05"))

	def test_an_expense_claim_is_its_posting_day(self):
		claim = FakeDocument("Expense Claim", name="X", employee="E1", posting_date="2026-10-03", company="C")
		with patch.object(frappe, "get_cached_value", return_value="MYR", create=True):
			self.assertEqual(self._dates(claim), ("2026-10-03", "2026-10-03"))

	def test_replacement_leave_is_its_bank_month(self):
		claim = FakeDocument("Replacement Leave Claim", name="X", employee="E1", bank_month="2026-09-01")
		self.assertEqual(self._dates(claim), ("2026-09-01", "2026-09-01"))

	def test_time_in_lieu_uses_the_days_worked(self):
		comp = FakeDocument(
			"Compensatory Leave Request",
			name="X",
			employee="E1",
			work_from_date="2026-09-06",
			work_end_date="2026-09-07",
		)
		self.assertEqual(self._dates(comp), ("2026-09-06", "2026-09-07"))

	def test_date_and_datetime_objects_become_plain_iso_days(self):
		import datetime

		ot = FakeDocument("OT Request", name="X", employee="E1", ot_date=datetime.date(2026, 9, 5))
		self.assertEqual(self._dates(ot), ("2026-09-05", "2026-09-05"))
		comp = FakeDocument(
			"Compensatory Leave Request",
			name="X",
			employee="E1",
			work_from_date=datetime.datetime(2026, 9, 6, 8, 30),
			work_end_date="2026-09-07 17:00:00",
		)
		self.assertEqual(self._dates(comp), ("2026-09-06", "2026-09-07"))

	def test_a_date_that_is_not_there_is_a_blank_string(self):
		ot = FakeDocument("OT Request", name="X", employee="E1")
		self.assertEqual(self._dates(ot), ("", ""))
		part = FakeDocument("Leave Application", name="X", employee="E1", from_date="2026-10-14")
		self.assertEqual(self._dates(part), ("2026-10-14", ""))

	def test_a_check_in_is_the_day_it_was_made(self):
		req = frappe._dict(name="RCR-1", employee="E9", checkin_time="2026-09-18 08:05:00", log_type="IN")
		row = approvals_list._remote_row(req, ME, {"E9": {}})
		self.assertEqual((row["from_date"], row["to_date"]), ("2026-09-18", "2026-09-18"))


# --- Attachments: one File query per type, never one per row ---------------------------------


class TestAttachmentsAreLookedUpOncePerType(unittest.TestCase):
	def _page(self, files):
		docs = {
			**{
				("Leave Application", f"LA-{i}"): FakeDocument(
					"Leave Application",
					name=f"LA-{i}",
					employee="E1",
					employee_name="A",
					leave_type="Annual Leave",
					leave_approver=BOSS,
					modified=f"2026-09-0{i + 1} 00:00:00",
				)
				for i in range(3)
			},
			**{
				("Expense Claim", f"EC-{i}"): FakeDocument(
					"Expense Claim",
					name=f"EC-{i}",
					employee="E1",
					employee_name="A",
					company="C",
					expense_approver=BOSS,
					modified=f"2026-09-1{i} 00:00:00",
				)
				for i in range(2)
			},
		}
		calls = []

		def get_all(doctype, **kw):
			if doctype == "File":
				calls.append(kw)
				return [n for n in files if n in kw["filters"]["attached_to_name"][1]]
			return [n for (d, n) in docs if d == doctype]

		with (
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "get_doc", side_effect=lambda dt, n: docs[(dt, n)]),
			patch.object(frappe, "get_cached_value", return_value="MYR", create=True),
			patch.object(approvals_list, "_request_read_allowed", return_value=True),
			patch.object(approvals_list, "_is_routed_approver", return_value=True),
			patch.object(
				approvals_list, "may_read_leave_reasons", side_effect=lambda d, user=None: [True] * len(d)
			),
			patch.object(
				approvals_list, "_types_on_site", return_value=["Leave Application", "Expense Claim"]
			),
			patch.object(approvals_list, "_remote_checkins", return_value=[]),
			_Patched(sent_to_boss()),
		):
			rows = {r["name"]: r for r in approvals_list.get_waiting_for_me()["rows"]}
		return rows, calls

	def test_one_file_query_per_type_whatever_the_number_of_rows(self):
		_rows, calls = self._page(files=[])
		self.assertEqual(len(calls), 2, "one for leave, one for expense: five rows, not five queries")
		asked = {c["filters"]["attached_to_doctype"]: c["filters"]["attached_to_name"] for c in calls}
		self.assertEqual(sorted(asked), ["Expense Claim", "Leave Application"])
		self.assertEqual(asked["Leave Application"][0], "in")
		self.assertEqual(sorted(asked["Leave Application"][1]), ["LA-0", "LA-1", "LA-2"])
		self.assertEqual(sorted(asked["Expense Claim"][1]), ["EC-0", "EC-1"])
		self.assertTrue(all(c["pluck"] == "attached_to_name" for c in calls))

	def test_each_row_is_marked_from_the_one_answer(self):
		rows, _calls = self._page(files=["LA-1", "EC-0"])
		self.assertEqual(
			{n: r["attached"] for n, r in rows.items()},
			{"LA-0": False, "LA-1": True, "LA-2": False, "EC-0": True, "EC-1": False},
		)

	def test_a_type_with_no_rows_asks_nothing(self):
		with (
			patch.object(frappe, "get_all", return_value=[]) as get_all,
			patch.object(
				approvals_list, "_types_on_site", return_value=["Leave Application", "Expense Claim"]
			),
			patch.object(approvals_list, "_remote_checkins", return_value=[]),
			_Patched(sent_to_boss()),
		):
			self.assertEqual(approvals_list.get_waiting_for_me()["rows"], [])
		self.assertNotIn("File", [c.args[0] for c in get_all.call_args_list])


if __name__ == "__main__":
	unittest.main()
