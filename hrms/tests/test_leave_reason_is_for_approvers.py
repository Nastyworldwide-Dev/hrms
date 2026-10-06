"""Who may read the REASON on a leave request (owner ruling, 5 Oct 2026).

The access matrix said "Leave REASON: manager never" while the code sent it to anyone who could open
the request. A team lead who was not an approver read a report's medical reason (probe on fresh.local,
5 Oct 2026). The ruling: the employee, an approver on the request's line, and HR see it; a manager
who is not an approver does not.

One question, asked in one place (`approval.may_read_leave_reason`), by both doors: the leave list
endpoint (hrms.api.get_leave_applications) and the Approvals page (approvals_list._row).

	PYTHONPATH=. python3 hrms/tests/test_leave_reason_is_for_approvers.py
"""

import pathlib
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import approval

EMPLOYEE = "HR-EMP-1"
DOC = frappe._dict(doctype="Leave Application", name="LAP-1", employee=EMPLOYEE, description="medical")


def _asks(user, *, own=(), hr=False, routed=False, doc=DOC):
	with (
		patch.object(approval.frappe, "session", frappe._dict(user=user)),
		patch("hrms.utils.identity.own_employees", return_value=list(own)),
		patch("hrms.hr.utils.sees_all_employee_data", return_value=hr),
		patch.object(approval, "_is_routed_approver", return_value=routed),
		patch("hrms.overrides.company_scope.company_visible", return_value=True),
		patch.object(approval.frappe.db, "get_value", return_value="Company A"),
	):
		return approval.may_read_leave_reason(doc, user)


class TestWhoReadsTheLeaveReason(unittest.TestCase):
	def test_the_employee_reads_their_own(self):
		self.assertTrue(_asks("me@example.com", own=(EMPLOYEE,)))

	def test_an_approver_on_the_line_reads_it(self):
		self.assertTrue(_asks("boss@example.com", routed=True))

	def test_hr_reads_it(self):
		self.assertTrue(_asks("hr@example.com", hr=True))

	def test_a_manager_who_is_not_an_approver_does_not(self):
		# the case the probe proved: reports_to only, not on the approval line
		self.assertFalse(_asks("lead@example.com", routed=False))

	def test_a_stranger_does_not(self):
		self.assertFalse(_asks("who@example.com"))

	def test_a_system_manager_alone_does_not(self):
		# sees no one's HR data (ACCESS-MATRIX); HR_SEE_ALL_ROLES excludes the role
		self.assertFalse(_asks("admin@example.com", hr=False, routed=False))

	def test_the_requests_with_no_reason_ask_nothing(self):
		self.assertTrue(
			approval.may_read_leave_reason(
				frappe._dict(doctype="OT Request", employee=EMPLOYEE), "x@example.com"
			)
		)


# ---- 6 Oct 2026: one reason check per PERSON, not per row (alpha.35, slice O1) ---------------------
# The leave list asked the question once per row: own_employees, a company read, a company-fence read
# and the routing walk, 50 rows = 50+ reads for an answer that only depends on (user, employee, the
# request's own approver). The batch asks once per distinct person; the single-doc form is the batch
# with one row, so the two cannot drift.

COMPANY_OF = {"E-OWN": "A", "E-A1": "A", "E-A2": "A", "E-B": "B"}


def _row(name, employee, approver=None):
	return frappe._dict(doctype="Leave Application", name=name, employee=employee, leave_approver=approver)


# owner / in-company / out-of-company / routed approver / stranger, with one employee filed under two
# different named approvers so a cache that keyed on the employee alone would be caught.
FIXTURE_ROWS = [
	_row("LAP-1", "E-OWN", "boss@example.com"),
	_row("LAP-2", "E-A1", "boss@example.com"),
	_row("LAP-3", "E-A1", "other@example.com"),
	_row("LAP-4", "E-A2", None),
	_row("LAP-5", "E-B", "boss@example.com"),
	_row("LAP-6", "E-B", None),
]

#: user -> (own employees, sees all employee data, companies the user is fenced to; empty = unfenced)
PEOPLE = {
	"me@example.com": (("E-OWN",), False, ()),
	"hr-a@example.com": ((), True, ("A",)),
	"hr-all@example.com": ((), True, ()),
	"boss@example.com": ((), False, ()),
	"who@example.com": ((), False, ()),
}


class _World:
	"""A small fake database the single-row and batch paths both read through."""

	def __init__(self):
		self.get_value = MagicMock(side_effect=self._get_value)
		self.get_all = MagicMock(side_effect=self._get_all)
		self.routed = MagicMock(side_effect=self._routed)
		self.own = MagicMock(side_effect=lambda user=None: list(PEOPLE[user][0]))
		self.sees_all = MagicMock(side_effect=lambda user=None: PEOPLE[user][1])
		self.visible = MagicMock(side_effect=self._visible)

	@staticmethod
	def _get_value(doctype, name, field=None, *a, **k):
		return COMPANY_OF.get(name)

	@staticmethod
	def _get_all(doctype, filters=None, fields=None, **k):
		wanted = filters["name"][1]
		return [frappe._dict(name=n, company=COMPANY_OF[n]) for n in wanted if n in COMPANY_OF]

	@staticmethod
	def _routed(doc, user=None, **k):
		return doc.get("leave_approver") == user

	@staticmethod
	def _visible(company, user=None, allow_blank=False):
		fence = PEOPLE[user][2]
		return not fence or (bool(company) and company in fence)

	def patched(self, user):
		stack = ExitStack()
		stack.enter_context(patch.object(approval.frappe, "session", frappe._dict(user=user)))
		stack.enter_context(patch.object(approval.frappe, "get_all", self.get_all))
		stack.enter_context(patch.object(approval.frappe.db, "get_value", self.get_value))
		stack.enter_context(patch.object(approval, "_is_routed_approver", self.routed))
		stack.enter_context(patch("hrms.utils.identity.own_employees", self.own))
		stack.enter_context(patch("hrms.hr.utils.sees_all_employee_data", self.sees_all))
		stack.enter_context(patch("hrms.overrides.company_scope.company_visible", self.visible))
		return stack


class TestTheBatchAnswersLikeTheRow(unittest.TestCase):
	def test_every_row_gets_the_answer_the_single_form_gives_it(self):
		# the per-row function is the spec (its own tests above pin it); the batch must agree on a
		# mixed list for every kind of reader
		answers = set()
		for user in PEOPLE:
			with self.subTest(user=user), _World().patched(user):
				expected = [approval.may_read_leave_reason(row, user) for row in FIXTURE_ROWS]
				self.assertEqual(approval.may_read_leave_reasons(FIXTURE_ROWS, user), expected)
				answers.update(expected)
		# the fixture really exercises both answers, or the equality above proves nothing
		self.assertEqual(answers, {True, False})

	def test_each_kind_of_reader_gets_the_ruled_answer(self):
		# expected values from the 5 Oct 2026 ruling, row order = FIXTURE_ROWS
		ruled = {
			"me@example.com": [True, False, False, False, False, False],  # only their own
			"hr-a@example.com": [True, True, True, True, False, False],  # HR inside company A
			"hr-all@example.com": [True] * 6,  # unfenced HR
			"boss@example.com": [True, True, False, False, True, False],  # only where named
			"who@example.com": [False] * 6,
		}
		for user, expected in ruled.items():
			with self.subTest(user=user), _World().patched(user):
				self.assertEqual(approval.may_read_leave_reasons(FIXTURE_ROWS, user), expected)

	def test_other_request_types_and_an_empty_list_ask_nothing(self):
		with _World().patched("who@example.com") as _:
			self.assertEqual(approval.may_read_leave_reasons([], "who@example.com"), [])
			ot = frappe._dict(doctype="OT Request", employee="E-A1")
			self.assertEqual(approval.may_read_leave_reasons([ot], "who@example.com"), [True])


class TestTheLeaveListAsksOncePerPerson(unittest.TestCase):
	def _list(self, user, world, rows):
		import hrms.api as api

		with (
			world.patched(user),
			patch.object(frappe, "get_list", return_value=rows),
			patch.object(api, "_ensure_own_employee_or_permitted"),
			patch.object(api, "get_workflow_state_field", return_value=None),
			patch.object(api, "name_approvers"),
		):
			return api.get_leave_applications(employee="E-A1")

	@staticmethod
	def _fifty():
		employees = ["E-A1", "E-A2", "E-B"]
		return [
			{
				"name": f"LAP-{i}",
				"employee": employees[i % 3],
				"leave_approver": None,
				"description": "medical",
			}
			for i in range(50)
		]

	def test_fifty_rows_for_three_people_cost_a_handful_of_reads(self):
		world = _World()
		# HR fenced to company A: E-B falls through to the routing question, the rest are inside the fence
		rows = self._list("hr-a@example.com", world, self._fifty())
		self.assertEqual(world.get_value.call_count, 0, "a per-row company read is the N+1 this removes")
		employee_reads = [c for c in world.get_all.call_args_list if c.args[0] == "Employee"]
		self.assertEqual(len(employee_reads), 1, "the companies of all the people come in ONE read")
		self.assertLessEqual(world.routed.call_count, 3, "routing is asked once per distinct person/approver")
		self.assertEqual(world.own.call_count, 1)
		self.assertEqual(world.sees_all.call_count, 1)
		self.assertLessEqual(world.visible.call_count, 2, "once per distinct company, never per row")
		# and the answers did not change: A's people keep the reason, B's is blanked
		kept = {r["employee"]: r["description"] for r in rows}
		self.assertEqual(kept, {"E-A1": "medical", "E-A2": "medical", "E-B": ""})

	def test_a_stranger_reading_fifty_rows_gets_blank_reasons_and_cheap_routing(self):
		world = _World()
		rows = self._list("who@example.com", world, self._fifty())
		self.assertEqual({r["description"] for r in rows}, {""})
		self.assertEqual(world.get_value.call_count, 0)
		self.assertLessEqual(world.routed.call_count, 3)


class TestBothDoorsAskIt(unittest.TestCase):
	def test_the_leave_list_blanks_the_reason_for_a_reader_who_may_not(self):
		src = (pathlib.Path(__file__).resolve().parents[1] / "api/__init__.py").read_text()
		body = src[src.index("def get_leave_applications") : src.index("def name_approvers")]
		self.assertIn("may_read_leave_reason", body)

	def test_the_approvals_page_asks_the_same_helper(self):
		src = (pathlib.Path(__file__).resolve().parents[1] / "api/approvals_list.py").read_text()
		self.assertIn("may_read_leave_reason", src)


if __name__ == "__main__":
	unittest.main()
