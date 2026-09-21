"""The PWA's API surface answers cleanly, stays bounded, and reads the
employee's calendar — pinned from the 15 Sep 2026 persona matrix
(hrms/tests/probes/nadi_api_matrix.py, run on fresh.local as nine personas).

Three classes the matrix turned up, one test each plus a class lock:

  * CLEAN ERRORS — `delete_attachment` on an unknown file unpacked None and
    answered a 500 (TypeError) to every persona. An unknown row is a clean
    "not found", never a stack trace.
  * BOUNDED LISTS — the five request readers took `limit=None` straight into
    `frappe.get_list`, which then set NO LIMIT: a caller who omits the argument
    (or a Desk script) pulls every row the fence allows. The PWA always sends
    10 or 20; the server must not depend on that. `helpdesk.list_tickets` cast
    any `limit` to int with no cap.
  * EMPLOYEE'S DAY — "today" in the claimable-OT window, the RL bank balance,
    the leave-balance map and the team-status default resolved on the SITE
    clock (`getdate()`), which on a Dubai site is four hours behind the
    Malaysian staff it serves: between midnight and 04:00 local the window
    ended a day early and the team view showed yesterday. hrms.utils.timezone
    exists for exactly this; the AST lock below keeps the class closed.

    PYTHONPATH=. python3 hrms/tests/test_api_clean_errors_and_bounds.py
"""

import ast
import datetime
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

API_DIR = pathlib.Path(__file__).resolve().parent.parent / "api"

#: "file.py:function" -> why a bare server-clock date is right there.
SERVER_CLOCK_EXEMPT = {
	# Desk-only HR master edit: HR corrects days from Desk on the site clock,
	# and its "not in the future" guard is a coarse sanity check, not attendance
	# wall-clock logic. Not called by the PWA.
	"attendance_master_edit.py:_today": "Desk HR tool; coarse future guard on the site clock",
}


class TestCleanErrors(unittest.TestCase):
	def test_delete_attachment_on_an_unknown_file_is_a_clean_not_found(self):
		import hrms.api as api

		db = MagicMock()
		db.get_value.return_value = None
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user="x@example.com")),
			# a real frappe.throw needs a bound site; the stub's raises anyway
			patch.object(
				frappe,
				"throw",
				side_effect=lambda msg, exc=Exception, *a, **k: (_ for _ in ()).throw(exc(msg)),
			),
		):
			with self.assertRaises(frappe.DoesNotExistError):
				api.delete_attachment("no-such-file")
		db.delete_doc.assert_not_called()


class TestBoundedLists(unittest.TestCase):
	READERS = (
		"get_shift_requests",
		"get_attendance_requests",
		"get_ot_requests",
		"get_replacement_leave_claims",
		"get_leave_applications",
		"get_expense_claims",
	)

	def _limit_sent(self, reader, **kwargs):
		import hrms.api as api

		get_list = MagicMock(return_value=[])
		with (
			patch.object(frappe, "get_list", get_list),
			patch.object(api, "_ensure_own_employee_or_permitted"),
			patch.object(api, "get_workflow_state_field", return_value=None),
		):
			getattr(api, reader)(employee="HR-EMP-00001", **kwargs)
		return get_list.call_args.kwargs.get("limit")

	def test_a_reader_called_without_a_limit_still_sends_one(self):
		for reader in self.READERS:
			with self.subTest(reader=reader):
				limit = self._limit_sent(reader)
				self.assertIsNotNone(limit, f"{reader} passed limit=None to get_list — unbounded")
				self.assertLessEqual(limit, 500)

	def test_a_huge_limit_is_capped(self):
		self.assertLessEqual(self._limit_sent("get_shift_requests", limit=10**9), 500)

	def test_the_pwa_page_size_passes_through_untouched(self):
		self.assertEqual(self._limit_sent("get_leave_applications", limit=10), 10)

	def test_list_rows_carry_docstatus_so_a_decided_draft_is_not_shown_approved(self):
		# Audit 21 Sep 2026 A-H4: Desk can save status=Approved without
		# submitting. The PWA chip can only show that row as still pending
		# when the list payload says docstatus=0.
		import hrms.api as api

		for reader in ("get_leave_applications", "get_shift_requests"):
			with self.subTest(reader=reader):
				get_list = MagicMock(return_value=[])
				with (
					patch.object(frappe, "get_list", get_list),
					patch.object(api, "_ensure_own_employee_or_permitted"),
					patch.object(api, "get_workflow_state_field", return_value=None),
				):
					getattr(api, reader)(employee="HR-EMP-00001")
				self.assertIn("docstatus", get_list.call_args.kwargs["fields"])

	def test_helpdesk_ticket_list_is_capped(self):
		from hrms.api import helpdesk

		get_list = MagicMock(return_value=[])
		with (
			patch.object(frappe, "get_list", get_list),
			patch.object(helpdesk, "_require_helpdesk"),
			patch.object(helpdesk, "_attach_raiser_names", side_effect=lambda rows: rows),
		):
			helpdesk.list_tickets(limit=10**9)
		self.assertLessEqual(get_list.call_args.kwargs["limit_page_length"], 200)


class TestEmployeesDay(unittest.TestCase):
	def test_claimable_ot_window_ends_on_the_employees_own_day(self):
		"""00:30 on the 16th in Malaysia is still the 15th on a Dubai site clock."""
		import hrms.api as api

		local_now = datetime.datetime(2026, 9, 16, 0, 30)
		get_all = MagicMock(return_value=[])
		db = MagicMock()
		db.get_value.return_value = 0
		with (
			patch.object(api, "employee_now", return_value=local_now),
			patch.object(api, "_ensure_own_employee_or_permitted"),
			patch.object(api, "_incomplete_ot_days", return_value=[]),
			patch.object(frappe, "get_all", get_all),
			patch.object(frappe, "db", db),
		):
			out = api.get_claimable_ot_summary("HR-EMP-00001")
		self.assertEqual(out["to_date"], "2026-09-16")

	def test_team_status_defaults_to_the_callers_day(self):
		from hrms.api import team

		local_now = datetime.datetime(2026, 9, 16, 0, 30)
		with (
			patch.object(team, "employee_now", return_value=local_now),
			patch.object(team, "_my_employee", return_value="HR-EMP-00001"),
			patch.object(team, "_is_hr", return_value=False),
			patch.object(team, "allowed_companies", return_value=[]),
			patch.object(frappe, "get_all", MagicMock(return_value=[])),
		):
			out = team.get_team_status()
		self.assertEqual(out["date"], "2026-09-16")

	def test_no_api_reader_defaults_a_date_to_the_site_clock(self):
		"""Class lock: a zero-argument getdate()/nowdate()/today() inside hrms/api
		is a site-clock date. Attendance, leave and claims are the employee's
		wall clock — use hrms.utils.timezone.employee_now(employee).date()."""
		offenders = []
		for path in sorted(API_DIR.glob("*.py")):
			if path.name.startswith("test_"):
				continue
			tree = ast.parse(path.read_text(), filename=str(path))
			for func in ast.walk(tree):
				if not isinstance(func, ast.FunctionDef):
					continue
				for node in ast.walk(func):
					if (
						isinstance(node, ast.Call)
						and not node.args
						and not node.keywords
						and (
							(
								isinstance(node.func, ast.Name)
								and node.func.id in ("getdate", "nowdate", "today")
							)
							or (
								isinstance(node.func, ast.Attribute)
								and node.func.attr in ("getdate", "nowdate", "today")
							)
						)
					):
						key = f"{path.name}:{func.name}"
						if key not in SERVER_CLOCK_EXEMPT:
							offenders.append(f"{key} line {node.lineno}")
		self.assertEqual(offenders, [], "site-clock date defaults in hrms/api:\n" + "\n".join(offenders))

	def test_every_exemption_still_names_a_real_function(self):
		for key in SERVER_CLOCK_EXEMPT:
			file_name, func_name = key.split(":")
			tree = ast.parse((API_DIR / file_name).read_text())
			names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
			self.assertIn(func_name, names, f"stale exemption {key}")


if __name__ == "__main__":
	unittest.main()
