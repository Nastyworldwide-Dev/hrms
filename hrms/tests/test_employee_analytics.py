"""Employee Analytics counts "Not Set" from the same population as its bars.

360 audit (Desk reports): the per-parameter bars were counted with the
native Employee match conditions, but the "Not Set" slice was
`frappe.db.count` over the whole company — no user permissions, no company
fence — so a caller who may see ten employees was told how many the company
really has, and the donut's remainder disclosed the hidden headcount. Both
now come from one authorized population: the requested company resolved
against the caller's fence (a foreign company is refused) and the native
Employee restrictions.

Bench-free: the query builder runs in memory (_qb_stub); the fence, the
native match conditions and the list read are the boundaries.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_employee_analytics.py
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub
import _qb_stub

_frappe_stub.install()
_erpnext_stub.install()
_qb_stub.install()
import frappe

from hrms.hr.report.employee_analytics import employee_analytics as report
from hrms.utils import report_scope

A, B = "Company A", "Company B"


def employee(name, company, branch=None, status="Active"):
	return dict(name=name, employee_name=name.title(), company=company, branch=branch, status=status)


TABLES = {
	"Employee": [
		employee("alice", A, "North"),
		employee("amir", A, None),
		employee("ana", A, None),
		employee("bob", B, "North"),
		employee("bea", B, None),
	],
	"Branch": [dict(name="North"), dict(name="South")],
}


class TestNotSetComesFromTheAuthorizedPopulation(unittest.TestCase):
	def run_report(self, filters, *, fence, match=None):
		_qb_stub.install(TABLES)
		fenced = types.SimpleNamespace(allowed_companies=lambda user=None: list(fence))
		predicates = list(match or [])

		def get_list(doctype, filters=None, fields=None, as_list=False, **kwargs):
			# the native list read honours user permissions: same predicates
			out = []
			for row in _qb_stub.rows(doctype):
				plain = all(row.get(k) == v for k, v in filters.items() if not isinstance(v, list))
				is_set = all(
					(row.get(k) is not None) == (v[1] == "set")
					for k, v in filters.items()
					if isinstance(v, list)
				)
				if plain and is_set and all(p(row) for p in predicates):
					out.append(tuple(row.get(f) for f in fields))
			return out

		with (
			patch.object(report_scope, "is_hr", return_value=True),
			patch.dict(sys.modules, {"hrms.overrides.company_scope": fenced}),
			patch.object(report, "build_qb_match_conditions", lambda doctype, user=None: predicates),
			patch.object(frappe, "get_list", get_list, create=True),
			patch.object(
				frappe, "get_all", lambda doctype, **kw: [r["name"] for r in _qb_stub.rows(doctype)]
			),
			patch.object(frappe.db, "count", side_effect=AssertionError("db.count ignores permissions")),
		):
			return report.execute(frappe._dict({"parameter": "Branch", **filters}))

	def test_the_remainder_never_reveals_hidden_employees(self):
		Employee = frappe.qb.DocType("Employee")
		_c, _rows, _m, chart = self.run_report({"company": A}, fence=[], match=[Employee.name != "ana"])
		self.assertEqual(chart["data"]["labels"], ["North", "Not Set"])
		self.assertEqual(chart["data"]["datasets"][0]["values"], [1, 1], "ana is hidden: Not Set is 1, not 2")

	def test_a_fenced_hr_user_asking_for_another_company_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.run_report({"company": B}, fence=[A])

	def test_an_unrestricted_caller_gets_the_whole_company(self):
		_c, rows, _m, chart = self.run_report({"company": A}, fence=[])
		self.assertEqual([r[0] for r in rows], ["alice"], "the table lists employees with the parameter set")
		self.assertEqual(chart["data"]["datasets"][0]["values"], [1, 2])


if __name__ == "__main__":
	unittest.main()
