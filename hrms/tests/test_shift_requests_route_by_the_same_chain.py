"""A shift request routes up the employee's own chain, like every other request.

Owner ruling, 21 Sep 2026, extended on being shown the gap: "close it".

`cf94549e7` took `Department Approver` out of the routing set for Leave,
Expense and OT, because that is what the report was about. Shift Request kept
the older model in two places:

  * `hrms.api.get_shift_request_approvers` built its dropdown from
    `get_department_approvers`, the department ANCESTOR walk — every approver
    named on the employee's department OR any department above it;
  * `ShiftRequest.validate_approver` accepted anyone in the department's own
    `Department Approver` table plus the employee's `shift_request_approver`.

So one ticked name still reached a whole department tree for this one doctype —
the shape the ruling refused, just scoped smaller. Worse, the two lists were
not even the same list: the selector offered the ancestor chain and the
validator accepted only the immediate department, so a pick from the dropdown
could fail on save.

Both now read `get_designated_approvers`, so the shift request routes exactly
where a leave application does: the approver on the Employee record, the
reporting manager, and the same two questions asked of each person that
reaches.

Bench-free:
    PYTHONPATH=. python3 hrms/tests/test_shift_requests_route_by_the_same_chain.py
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

FIELD = "shift_request_approver"

#: STAFF -> LEAD -> HEAD. DEPT_APPROVER is ticked on the department and on the
#: department ABOVE it, and is nobody's named approver: the person the old code
#: admitted and the ruling refuses.
ORG = {
	"HR-EMP-STAFF": {
		"user_id": "staff@example.com",
		FIELD: None,
		"reports_to": "HR-EMP-LEAD",
		"department": "Ops - X",
		"status": "Active",
	},
	"HR-EMP-LEAD": {
		"user_id": "lead@example.com",
		FIELD: None,
		"reports_to": "HR-EMP-HEAD",
		"department": "Ops - X",
		"status": "Active",
	},
	"HR-EMP-HEAD": {
		"user_id": "head@example.com",
		FIELD: None,
		"reports_to": None,
		"department": "Ops - X",
		"status": "Active",
	},
}

DEPARTMENT_APPROVER = "dept.approver@example.com"


def _as_list(value):
	return list(value) if isinstance(value, list | tuple | set) else [value]


class _Org:
	"""The frappe surface the selector and the validator read, backed by ORG."""

	def __enter__(self):
		db = MagicMock()
		db.get_value.side_effect = self._get_value

		self.patches = [
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", side_effect=self._get_all),
			patch.object(frappe, "get_value", side_effect=self._get_value),
			patch.object(
				frappe,
				"get_cached_value",
				side_effect=lambda dt, name, fields: (
					[ORG[name].get(f) for f in fields] if isinstance(fields, list) else ORG[name].get(fields)
				),
			),
			patch.object(frappe, "session", frappe._dict(user="staff@example.com")),
			patch.object(hr_utils, "own_employees", side_effect=self._own_employees),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()

	def _own_employees(self, user=None):
		login = (user or "").strip().lower()
		return [name for name, row in ORG.items() if (row["user_id"] or "").lower() == login]

	def _get_value(self, doctype, filters, fieldname=None, **kwargs):
		if doctype == "Department Approver":
			return DEPARTMENT_APPROVER
		if doctype == "User":
			return f"{filters} (full name)" if isinstance(filters, str) else None
		if doctype != "Employee":
			return None
		row = ORG.get(filters if isinstance(filters, str) else "")
		if not row:
			return None
		if kwargs.get("as_dict"):
			return frappe._dict({key: row.get(key) for key in _as_list(fieldname)})
		if isinstance(fieldname, list):
			return [row.get(key) for key in fieldname]
		return row.get(fieldname)

	def _get_all(self, doctype, filters=None, pluck=None, fields=None, **kwargs):
		filters = filters or {}
		if doctype == "Department Approver":
			rows = [DEPARTMENT_APPROVER]
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


def offered(employee):
	from hrms import api

	with _Org():
		with patch.object(api, "_ensure_own_employee_or_permitted", lambda _e: None):
			return [option["name"] for option in api.get_shift_request_approvers(employee)]


def files_with(approver, employee="HR-EMP-STAFF"):
	"""Run ShiftRequest.validate_approver for a new request naming `approver`."""
	from hrms.hr.doctype.shift_request.shift_request import ShiftRequest

	doc = frappe._dict(
		doctype="Shift Request",
		name=None,
		employee=employee,
		approver=approver,
		status="Draft",
	)
	doc.is_new = lambda: True
	doc.has_value_changed = lambda _f: True
	with _Org():
		ShiftRequest.validate_approver(doc)


class TestTheShiftSelectorOffersTheChain(unittest.TestCase):
	def test_the_reporting_line_is_offered(self):
		self.assertEqual(offered("HR-EMP-STAFF"), ["lead@example.com", "head@example.com"])

	def test_a_department_approver_is_not_offered(self):
		self.assertNotIn(DEPARTMENT_APPROVER, offered("HR-EMP-STAFF"))

	def test_the_top_of_the_chain_is_offered_nobody(self):
		self.assertEqual(offered("HR-EMP-HEAD"), [])


class TestTheShiftValidatorAcceptsTheSameList(unittest.TestCase):
	"""A dropdown that offers what the save refuses is the original defect."""

	def test_the_immediate_superior_is_accepted(self):
		files_with("lead@example.com")  # must not raise

	def test_a_rung_further_up_is_accepted(self):
		"""The escalation when the immediate approver forgets."""
		files_with("head@example.com")  # must not raise

	def test_a_department_approver_is_never_the_approver(self):
		# 25 Sep 2026 (owner: nobody chooses their approver): the employee's own
		# request is routed to their own approver; filed by someone else
		# (HR in Desk) a department approver is still refused.
		from hrms.hr import utils as hr_utils

		with patch.object(hr_utils, "_is_own_request", return_value=False):
			with self.assertRaises(frappe.ValidationError):
				files_with(DEPARTMENT_APPROVER)
		with patch.object(hr_utils, "_is_own_request", return_value=True):
			doc = frappe._dict(
				doctype="Shift Request",
				name=None,
				employee="HR-EMP-STAFF",
				approver=DEPARTMENT_APPROVER,
				status="Draft",
			)
			doc.is_new = lambda: True
			doc.has_value_changed = lambda _f: True
			from hrms.hr.doctype.shift_request.shift_request import ShiftRequest

			with _Org():
				ShiftRequest.validate_approver(doc)
			self.assertEqual(doc.approver, "lead@example.com")

	def test_everything_offered_is_accepted(self):
		"""The invariant: the selector and the fence read one list."""
		for approver in offered("HR-EMP-STAFF"):
			with self.subTest(approver=approver):
				files_with(approver)


if __name__ == "__main__":
	unittest.main(verbosity=2)
