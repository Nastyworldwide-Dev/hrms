"""Approval routing follows each employee's OWN chain, bottom-up — never a department blanket.

Owner ruling, 21 Sep 2026, after "Superior cannot approve on duty application ...
because it persist again":

    "it always follow from bottom up, everyone has their own assinged reported
     to, and the one who will be their approver from desk. respect that nature.
     ... each employee will have their approver. and the chain goes until they
     dont have which will be be several people but dont hardcode, respect the
     configuration set from hr (desk) but the function must work."

Two things were wrong, and they are opposite errors:

  * TOO WIDE — `Department Approver` rows admitted EVERY active employee of that
    department. After 3409a2c7b that admission also reached list queries, so one
    department approver's Team queue returned the whole department's pay-adjacent
    rows although no employee record routes to them. The owner refused that
    outright ("no, dont").

  * TOO NARROW — the walk stopped at the first level. A grand-manager, the person
    an escalation actually reaches when the immediate approver forgets, was not a
    designated approver at all: `get_designated_approvers` said in so many words
    "It does not walk up the department tree", and the reporting line got the same
    single hop.

The rule pinned here: an approver is someone the employee's OWN configuration
reaches — the approver field on their Employee record, or their `reports_to` —
applied again to each person it reaches, until nobody is reached. Several people,
no department shortcut, no hardcoded depth or names, and `get_employees_routed_to`
is the exact inverse so the read fence and the save fence cannot disagree.

Bench-free:
    PYTHONPATH=. python3 hrms/tests/test_approver_chain_follows_each_employee.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr import utils as hr_utils

FIELD = "leave_approver"
PARENTFIELD = "leave_approvers"

#: name -> the Employee row. STAFF -> LEAD -> HEAD is the reporting line; HEAD is
#: the top, so the chain ends there. PEER shares STAFF's department and reports to
#: nobody: they are the employee a department blanket wrongly admitted.
ORG = {
	"HR-EMP-STAFF": {
		"user_id": "staff@example.com",
		"leave_approver": None,
		"reports_to": "HR-EMP-LEAD",
		"department": "Ops - X",
		"status": "Active",
	},
	"HR-EMP-LEAD": {
		"user_id": "lead@example.com",
		"leave_approver": None,
		"reports_to": "HR-EMP-HEAD",
		"department": "Ops - X",
		"status": "Active",
	},
	"HR-EMP-HEAD": {
		"user_id": "head@example.com",
		"leave_approver": None,
		"reports_to": None,
		"department": "Ops - X",
		"status": "Active",
	},
	"HR-EMP-PEER": {
		"user_id": "peer@example.com",
		"leave_approver": None,
		"reports_to": None,
		"department": "Ops - X",
		"status": "Active",
	},
	# named approver instead of a reporting line — the reported shape
	"HR-EMP-NAMED": {
		"user_id": "named@example.com",
		"leave_approver": "lead@example.com",
		"reports_to": None,
		"department": "Ops - X",
		"status": "Active",
	},
}

#: Department Approver rows HR configured on Ops. Nobody's Employee record names
#: this person, which is the whole point.
DEPARTMENT_APPROVERS = {("Ops - X", PARENTFIELD): ["dept.approver@example.com"]}


def _as_list(value):
	return list(value) if isinstance(value, list | tuple | set) else [value]


class _Org:
	"""The frappe surface both functions read, backed by ORG."""

	def __enter__(self):
		db = MagicMock()
		db.get_value.side_effect = self._get_value

		self.patches = [
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", side_effect=self._get_all),
			patch.object(frappe, "session", frappe._dict(user="Administrator")),
			patch.object(hr_utils, "own_employees", side_effect=self._own_employees),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()

	# --- seams -------------------------------------------------------------
	def _own_employees(self, user=None):
		login = (user or "").strip().lower()
		return [name for name, row in ORG.items() if (row["user_id"] or "").lower() == login]

	def _get_value(self, doctype, filters, fieldname=None, **kwargs):
		if doctype == "Department Approver":
			# The old prefill: row 1 of the department's approver table. Answered
			# honestly here so "the default is never a department approver" cannot
			# pass just because the fixture went quiet.
			rows = DEPARTMENT_APPROVERS.get((filters.get("parent"), filters.get("parentfield")), [])
			return rows[0] if rows else None
		if doctype == "User":
			return f"{filters} (full name)" if isinstance(filters, str) else None
		if doctype != "Employee":
			return None
		row = ORG.get(filters if isinstance(filters, str) else "")
		if not row:
			return None
		if kwargs.get("as_dict"):
			return frappe._dict({key: row.get(key) for key in _as_list(fieldname)})
		return row.get(fieldname)

	def _get_all(self, doctype, filters=None, pluck=None, fields=None, **kwargs):
		filters = filters or {}
		if doctype == "Department Approver":
			rows = DEPARTMENT_APPROVERS.get((filters.get("parent"), filters.get("parentfield")), [])
			return rows if pluck else [{"approver": r} for r in rows]

		if doctype != "Employee":
			return []

		matched = []
		for name, row in ORG.items():
			candidate = {**row, "name": name}
			if all(self._matches(candidate, key, want) for key, want in filters.items()):
				matched.append(candidate)

		if pluck:
			return [row[pluck] for row in matched]
		wanted = fields or ["name"]
		return [frappe._dict({key: row.get(key) for key in wanted}) for row in matched]

	@staticmethod
	def _matches(row, key, want):
		value = row.get(key)
		if isinstance(want, list | tuple) and len(want) == 2 and want[0] == "in":
			return value in want[1]
		return value == want


def approvers(employee):
	return hr_utils.get_designated_approvers(employee, FIELD, PARENTFIELD)


def routed_to(user):
	return hr_utils.get_employees_routed_to(user, FIELD, PARENTFIELD)


class TestTheChainWalksUpward(unittest.TestCase):
	"""'the chain goes until they dont have which will be be several people'."""

	def test_the_grand_manager_is_a_designated_approver(self):
		with _Org():
			self.assertEqual(approvers("HR-EMP-STAFF"), ["lead@example.com", "head@example.com"])

	def test_the_immediate_approver_still_comes_first(self):
		"""Preference order is bottom-up: the PWA selector and the OT notification
		both take the first entry as the default recipient."""
		with _Org():
			self.assertEqual(approvers("HR-EMP-STAFF")[0], "lead@example.com")

	def test_a_named_approver_carries_the_chain_too(self):
		"""The reported shape — a superior named on the Employee record, no
		reporting line. Their own approver is the next rung."""
		with _Org():
			self.assertEqual(approvers("HR-EMP-NAMED"), ["lead@example.com", "head@example.com"])

	def test_the_top_of_the_chain_has_nobody_above_them(self):
		with _Org():
			self.assertEqual(approvers("HR-EMP-HEAD"), [])

	def test_nobody_is_their_own_approver(self):
		with _Org():
			self.assertNotIn("staff@example.com", approvers("HR-EMP-STAFF"))

	def test_a_loop_in_the_configuration_terminates(self):
		"""HR can save a cycle in Desk; the walk must end rather than hang."""
		with _Org():
			with patch.dict(ORG["HR-EMP-HEAD"], {"reports_to": "HR-EMP-STAFF"}):
				self.assertEqual(approvers("HR-EMP-STAFF"), ["lead@example.com", "head@example.com"])


class TestTheDepartmentIsNotAShortcut(unittest.TestCase):
	"""'no, dont' — a Department Approver is not routed to by anyone's record."""

	def test_a_department_approver_is_not_offered_to_the_employee(self):
		with _Org():
			self.assertNotIn("dept.approver@example.com", approvers("HR-EMP-STAFF"))

	def test_a_department_approver_does_not_see_the_department(self):
		"""SEC-W1: after 3409a2c7b this admission reached LIST queries, so one
		department approver's Team queue returned every colleague's pay rows."""
		with _Org():
			self.assertEqual(routed_to("dept.approver@example.com"), [])


class TestTheInverseAgreesWithTheChain(unittest.TestCase):
	"""The read fence and the save fence read one answer, from both ends."""

	def test_the_grand_manager_sees_the_whole_line_below_them(self):
		"""Everyone whose chain reaches HEAD — the two rungs below, and the
		employee who names LEAD directly. Not PEER, who routes to nobody."""
		with _Org():
			self.assertEqual(
				sorted(routed_to("head@example.com")),
				["HR-EMP-LEAD", "HR-EMP-NAMED", "HR-EMP-STAFF"],
			)

	def test_a_named_approvers_own_senior_sees_that_employee(self):
		with _Org():
			self.assertIn("HR-EMP-NAMED", routed_to("head@example.com"))

	def test_nobody_routes_to_a_colleague_with_no_reports(self):
		with _Org():
			self.assertEqual(routed_to("peer@example.com"), [])

	def test_the_two_directions_never_disagree(self):
		"""The invariant for the class: whoever the employee may route to must be
		able to see them, and nobody else."""
		with _Org():
			for employee in ORG:
				for approver in approvers(employee):
					self.assertIn(
						employee,
						routed_to(approver),
						f"{approver} may approve for {employee} but cannot see the request",
					)


class TestTheSelectorDefaultIsOneTheFenceAccepts(unittest.TestCase):
	"""The prefilled approver must come from the same list as the options.

	This is the ORIGINAL defect of this file, one layer up: the three PWA
	approver endpoints prefilled their default from `Department Approver` row 1
	while `validate_staff_approver` read `get_designated_approvers`. A form that
	suggests a value the save rejects is the shape of "{0} is not one of your
	designated approvers" — and with the department arm gone, every default it
	prefilled would now be rejected.
	"""

	def _details(self, endpoint, employee):
		from hrms import api

		with _Org():
			with (
				patch.object(api, "_ensure_own_employee_or_permitted", lambda _e: None),
				patch.object(
					frappe,
					"get_cached_value",
					side_effect=lambda dt, name, fields: [ORG[name].get(f) for f in fields],
				),
			):
				return getattr(api, endpoint)(employee)

	def test_the_prefilled_approver_is_never_a_department_approver(self):
		for endpoint, employee in (
			("get_leave_approval_details", "HR-EMP-STAFF"),
			("get_expense_approval_details", "HR-EMP-STAFF"),
		):
			with self.subTest(endpoint=endpoint):
				details = self._details(endpoint, employee)
				default = details.get("leave_approver") or details.get("expense_approver")
				self.assertNotEqual(default, "dept.approver@example.com")

	def test_the_prefilled_approver_is_the_first_option_offered(self):
		details = self._details("get_leave_approval_details", "HR-EMP-STAFF")
		offered = [option["name"] for option in details["department_approvers"]]
		self.assertEqual(details["leave_approver"], offered[0])

	def test_an_employee_with_nobody_above_them_is_offered_nobody(self):
		details = self._details("get_leave_approval_details", "HR-EMP-HEAD")
		self.assertFalse(details["leave_approver"])
		self.assertEqual(details["department_approvers"], [])


if __name__ == "__main__":
	unittest.main(verbosity=2)
