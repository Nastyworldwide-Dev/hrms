"""Manpower Requests, the Desk report HR monitors hiring with (S4, 22 Oct 2026).

What is pinned: the fixed columns and their types; one extra column per question found in the rows'
answers, in first-seen order, with a safe fieldname; the pivot; the two ages (days open, days to
approve from the Version log); the location text; that the rows come through frappe.get_list (so the
row scope and the company fence apply) and that a person who is not HR is refused. Expected values are
the owner's words (.claude/plans/manpower-plan.md), not re-derived from the code.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/hr/report/manpower_requests/test_manpower_requests.py
"""

import datetime
import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HRMS_ROOT / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.report.manpower_requests import manpower_requests as report

TODAY = datetime.date(2026, 10, 22)
HERE = pathlib.Path(__file__).resolve().parent


def request(name="HR-MPR-26-10-00001", **extra):
	row = dict(
		name=name,
		position_title="Welder",
		headcount=2,
		department="Ops - NW",
		employee_name="W0 employee",
		status="Open",
		hiring_status=None,
		urgency="High",
		how_soon="Within 2 weeks",
		band="D",
		budgeted_salary=3500,
		proposed_salary=3600,
		location="Shah Alam HQ",
		location_other=None,
		start_date=None,
		creation=datetime.datetime(2026, 10, 12, 9, 0),
		modified=datetime.datetime(2026, 10, 12, 9, 0),
		withdrawn_reason=None,
		docstatus=0,
		company="NW",
	)
	row.update(extra)
	return frappe._dict(row)


def answer(parent, question, text, idx=1):
	return frappe._dict(parent=parent, idx=idx, question=question, answer=text)


def version(docname, when, old, new, field="status", owner="boss@example.com"):
	return frappe._dict(
		docname=docname,
		owner=owner,
		creation=when,
		data=json.dumps({"changed": [[field, old, new]]}),
	)


class TestFixedColumns(unittest.TestCase):
	def setUp(self):
		self.columns = report.fixed_columns()
		self.by_name = {c["fieldname"]: c for c in self.columns}

	def test_the_order_is_the_owners_list(self):
		self.assertEqual(
			[c["label"] for c in self.columns],
			[
				"ID",
				"Position",
				"Headcount",
				"Department",
				"Requested by",
				"Status",
				"Hiring status",
				"Urgency",
				"How soon",
				"Band",
				"Budgeted",
				"Proposed",
				"Location",
				"Start date",
				"Sent on",
				"Days open",
				"Days to approve",
				"Withdrawn reason",
			],
		)

	def test_the_id_links_to_the_request_and_the_pay_is_currency(self):
		self.assertEqual(
			(self.by_name["name"]["fieldtype"], self.by_name["name"]["options"]), ("Link", "Manpower Request")
		)
		for field in ("budgeted_salary", "proposed_salary"):
			self.assertEqual(self.by_name[field]["fieldtype"], "Currency")

	def test_dates_and_counts_have_their_own_types(self):
		self.assertEqual(self.by_name["start_date"]["fieldtype"], "Date")
		self.assertEqual(self.by_name["sent_on"]["fieldtype"], "Date")
		for field in ("headcount", "days_open", "days_to_approve"):
			self.assertEqual(self.by_name[field]["fieldtype"], "Int")


class TestQuestionColumns(unittest.TestCase):
	def test_one_column_per_question_in_first_seen_order(self):
		answers = [
			answer("A", "Minimum qualification", "Diploma"),
			answer("A", "KPIs", "Output"),
			answer("B", "KPIs", "Quality"),
			answer("B", "Experience", "3 years"),
		]
		columns = report.question_columns(answers)
		self.assertEqual([c["label"] for c in columns], ["Minimum qualification", "KPIs", "Experience"])

	def test_each_is_a_data_column_with_a_plain_slug_fieldname(self):
		(column,) = report.question_columns([answer("A", "What happens if it is late?", "x")])
		self.assertEqual(column["fieldtype"], "Data")
		self.assertEqual(column["fieldname"], "q_what_happens_if_it_is_late")

	def test_two_questions_that_slug_alike_get_two_different_fieldnames(self):
		columns = report.question_columns([answer("A", "KPIs?", "x"), answer("A", "KPIs!", "y")])
		self.assertEqual(len({c["fieldname"] for c in columns}), 2)

	def test_a_question_with_no_letters_still_gets_a_usable_fieldname(self):
		(column,) = report.question_columns([answer("A", "???", "x")])
		self.assertRegex(column["fieldname"], r"^q_[a-z0-9_]+$")

	def test_a_fieldname_never_clashes_with_a_fixed_column(self):
		fixed = {c["fieldname"] for c in report.fixed_columns()}
		(column,) = report.question_columns(
			[
				answer("A", "Status", "x"),
			]
		)
		self.assertNotIn(column["fieldname"], fixed)

	def test_a_blank_question_text_is_skipped(self):
		self.assertEqual(report.question_columns([answer("A", "  ", "x"), answer("A", None, "y")]), [])

	def test_no_answers_no_extra_columns(self):
		self.assertEqual(report.question_columns([]), [])


class TestAges(unittest.TestCase):
	def test_days_to_approve_is_creation_to_the_first_decision_in_the_log(self):
		decided = report.decision_days(
			[version("A", datetime.datetime(2026, 10, 15, 8, 0), "Open", "Approved")],
			{"A": datetime.datetime(2026, 10, 12, 9, 0)},
		)
		self.assertEqual(decided, {"A": 3})

	def test_a_rejection_is_a_decision_too(self):
		decided = report.decision_days(
			[version("A", datetime.datetime(2026, 10, 13, 8, 0), "Open", "Rejected")],
			{"A": datetime.datetime(2026, 10, 12, 9, 0)},
		)
		self.assertEqual(decided, {"A": 1})

	def test_an_undecided_request_has_no_entry_at_all(self):
		decided = report.decision_days(
			[
				version(
					"A",
					datetime.datetime(2026, 10, 15, 8, 0),
					"Waiting for HR",
					"Recruiting",
					"hiring_status",
				)
			],
			{"A": datetime.datetime(2026, 10, 12, 9, 0)},
		)
		self.assertEqual(decided, {})

	def test_each_request_reads_its_own_log(self):
		decided = report.decision_days(
			[
				version("A", datetime.datetime(2026, 10, 14, 8, 0), "Open", "Approved"),
				version("B", datetime.datetime(2026, 10, 20, 8, 0), "Open", "Approved"),
			],
			{"A": datetime.datetime(2026, 10, 12, 9, 0), "B": datetime.datetime(2026, 10, 12, 9, 0)},
		)
		self.assertEqual(decided, {"A": 2, "B": 8})


class TestLocation(unittest.TestCase):
	def test_a_listed_site_is_the_site(self):
		self.assertEqual(report.location_text(request()), "Shah Alam HQ")

	def test_no_site_is_other_with_the_senders_words(self):
		row = request(location=None, location_other="Customer yard, Klang")
		self.assertEqual(report.location_text(row), "Other: Customer yard, Klang")

	def test_neither_is_blank(self):
		self.assertEqual(report.location_text(request(location=None)), "")


class TestBuildRows(unittest.TestCase):
	def _rows(self, requests, answers=(), decided=None):
		columns = report.question_columns(list(answers))
		return report.build_rows(requests, list(answers), decided or {}, columns, TODAY), columns

	def test_the_answers_are_pivoted_into_their_own_columns(self):
		rows, columns = self._rows(
			[request("A"), request("B")],
			[
				answer("A", "KPIs", "Output"),
				answer("A", "Experience", "3 years", 2),
				answer("B", "Experience", "1 year"),
			],
		)
		kpis, experience = (c["fieldname"] for c in columns)
		self.assertEqual((rows[0][kpis], rows[0][experience]), ("Output", "3 years"))
		self.assertEqual((rows[1][kpis], rows[1][experience]), ("", "1 year"))

	def test_a_blank_answer_is_an_empty_cell(self):
		rows, columns = self._rows([request("A")], [answer("A", "KPIs", "   ")])
		self.assertEqual(rows[0][columns[0]["fieldname"]], "")

	def test_days_open_and_days_to_approve_and_sent_on(self):
		rows, _ = self._rows([request("A", creation=datetime.datetime(2026, 10, 12, 9, 0))], decided={"A": 3})
		self.assertEqual((rows[0]["days_open"], rows[0]["days_to_approve"]), (10, 3))
		self.assertEqual(str(rows[0]["sent_on"]), "2026-10-12")

	def test_an_undecided_request_leaves_days_to_approve_blank(self):
		rows, _ = self._rows([request("A")])
		self.assertIsNone(rows[0]["days_to_approve"])

	def test_a_finished_request_stops_counting_the_day_it_closed(self):
		rows, _ = self._rows(
			[
				request(
					"A",
					status="Approved",
					hiring_status="Filled",
					creation=datetime.datetime(2026, 9, 14, 9, 0),
					modified=datetime.datetime(2026, 10, 12, 10, 0),
				)
			]
		)
		self.assertEqual(rows[0]["days_open"], 28)

	def test_the_location_is_the_site_or_other_words(self):
		rows, _ = self._rows([request("A"), request("B", location=None, location_other="Klang yard")])
		self.assertEqual([r["location"] for r in rows], ["Shah Alam HQ", "Other: Klang yard"])

	def test_the_order_it_was_given_is_kept(self):
		rows, _ = self._rows([request("B"), request("A")])
		self.assertEqual([r["name"] for r in rows], ["B", "A"])


class TestExecute(unittest.TestCase):
	def _run(self, filters=None, *, hr=True, requests=(), answers=(), versions=()):
		asked = []

		def get_list(doctype, **ask):
			asked.append(dict(ask, doctype=doctype))
			return list(requests)

		def get_all(doctype, **ask):
			asked.append(dict(ask, doctype=doctype, via="get_all"))
			return list(versions) if doctype == "Version" else list(answers)

		with (
			patch.object(report, "is_hr_operator", return_value=hr),
			patch.object(frappe, "get_list", side_effect=get_list),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(report, "today", return_value=TODAY),
		):
			return report.execute(filters), asked

	def test_someone_who_is_not_hr_is_refused_and_nothing_is_read(self):
		with self.assertRaises(frappe.PermissionError):
			self._run(hr=False)
		with (
			patch.object(report, "is_hr_operator", return_value=False),
			patch.object(frappe, "get_list") as getter,
			patch.object(frappe, "get_all") as getall,
			self.assertRaises(frappe.PermissionError),
		):
			report.execute({})
		getter.assert_not_called()
		getall.assert_not_called()

	def test_the_requests_come_through_get_list_so_the_company_fence_applies(self):
		_, asked = self._run({})
		first = asked[0]
		self.assertEqual((first["doctype"], first.get("via")), ("Manpower Request", None))
		self.assertFalse(first.get("ignore_permissions"))

	def test_every_filter_becomes_a_condition(self):
		_, asked = self._run(
			{
				"from_date": "2026-08-01",
				"to_date": "2026-10-22",
				"company": "NW",
				"department": "Ops - NW",
				"status": "Approved",
				"hiring_status": "Recruiting",
				"urgency": "High",
			}
		)
		conditions = asked[0]["filters"]
		for expected in (
			["creation", ">=", "2026-08-01 00:00:00"],
			["creation", "<=", "2026-10-22 23:59:59.999999"],
			["company", "=", "NW"],
			["department", "=", "Ops - NW"],
			["status", "=", "Approved"],
			["hiring_status", "=", "Recruiting"],
			["urgency", "=", "High"],
		):
			self.assertIn(expected, conditions)

	def test_a_cancelled_request_is_never_listed(self):
		_, asked = self._run({})
		self.assertIn(["docstatus", "!=", 2], asked[0]["filters"])

	def test_no_filter_means_no_date_bound(self):
		_, asked = self._run({})
		self.assertEqual([c for c in asked[0]["filters"] if c[0] == "creation"], [])

	def test_the_answers_and_the_log_are_read_only_for_the_requests_get_list_returned(self):
		_, asked = self._run({}, requests=[request("A"), request("B")])
		child, log = asked[1], asked[2]
		self.assertEqual(child["doctype"], "Manpower Request Answer")
		self.assertEqual(child["filters"]["parent"], ["in", ["A", "B"]])
		self.assertEqual(log["doctype"], "Version")
		self.assertEqual(log["filters"]["docname"], ["in", ["A", "B"]])

	def test_no_requests_means_no_second_read(self):
		(columns, rows), asked = self._run({}, requests=[])
		self.assertEqual(rows, [])
		self.assertEqual(len(asked), 1)
		self.assertEqual(len(columns), len(report.fixed_columns()))

	def test_the_answer_columns_follow_the_fixed_ones(self):
		(columns, rows), _ = self._run(
			{},
			requests=[request("A")],
			answers=[answer("A", "KPIs", "Output")],
			versions=[version("A", datetime.datetime(2026, 10, 15, 8, 0), "Open", "Approved")],
		)
		self.assertEqual(columns[-1]["label"], "KPIs")
		self.assertEqual(rows[0][columns[-1]["fieldname"]], "Output")
		self.assertEqual(rows[0]["days_to_approve"], 3)


class TestDefinition(unittest.TestCase):
	def setUp(self):
		self.definition = json.loads((HERE / "manpower_requests.json").read_text(encoding="utf-8"))

	def test_it_is_a_standard_script_report_on_manpower_request(self):
		self.assertEqual(self.definition["report_type"], "Script Report")
		self.assertEqual(self.definition["ref_doctype"], "Manpower Request")
		self.assertEqual(self.definition["is_standard"], "Yes")
		self.assertEqual(self.definition["module"], "HR")
		self.assertEqual(self.definition["prepared_report"], 0)

	def test_hr_and_system_manager_only_never_staff(self):
		roles = {r["role"] for r in self.definition["roles"]}
		self.assertEqual(roles, {"HR User", "HR Manager", "System Manager"})

	def test_the_name_matches_the_folder(self):
		self.assertEqual(self.definition["name"], "Manpower Requests")
		self.assertEqual(self.definition["report_name"], "Manpower Requests")


class TestItWritesNothing(unittest.TestCase):
	def test_the_module_has_no_write_call(self):
		source = (HERE / "manpower_requests.py").read_text(encoding="utf-8")
		for call in (
			".insert(",
			".save(",
			".submit(",
			"db.set_value",
			"db.sql",
			".db_set(",
			"delete_doc",
			"ignore_permissions",
		):
			self.assertNotIn(call, source)


if __name__ == "__main__":
	unittest.main()
