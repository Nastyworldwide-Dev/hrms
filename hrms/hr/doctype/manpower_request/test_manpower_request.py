"""Manpower Request: who may send one, what a valid one looks like, who may read it.

Bench-free (frappe stubbed when no bench is on the path), through the controller's
public methods on a FakeDocument-shaped request, plus static checks of the doctype JSON
and hooks. Expected values come from the owner's rulings (22 Oct 2026), not from the code:

  * only someone with an ACTIVE direct report may send one; HR may file for anyone;
  * headcount >= 1; a location, or "Other" = no location + text saying where;
  * Replacement names a leaver/active person of the SAME department (Active, or relieved
    within 6 months); any other type clears that field;
  * how soon -> urgency: Within 2 weeks High, 3-4 weeks Medium, 1-2 months Low;
  * a start date, when given, is after today while the request is still a draft;
  * both salaries above zero; every required question answered;
  * sent -> shared with the first designated approver and told; submit only as a decision;
  * readable by the sender, the shared approver and HR only.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/hr/doctype/manpower_request/test_manpower_request.py
"""

import ast
import datetime
import json
import sys
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock, patch

HRMS_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HRMS_ROOT / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
from _fake_document import FakeDocument, fake_employees
from dateutil.relativedelta import relativedelta

import frappe

from hrms.hr import utils as hr_utils
from hrms.hr.doctype.manpower_request import manpower_request as mr
from hrms.overrides import employee_owned_row_scope as scope

DOCTYPE_DIR = HRMS_ROOT / "hr" / "doctype"
TODAY = datetime.date.today()

SIX_MONTHS_AGO = TODAY - relativedelta(months=6)


class _Request(mr.ManpowerRequest, FakeDocument):
	"""A request that behaves like a Document: attributes, get/set/db_set, no item access."""

	def __init__(self, **fields):
		values = dict(
			employee="EMP-HAFIZ",
			employee_name="Hafiz",
			department="Ops",
			position_title="Welder",
			headcount=2,
			location="HQ",
			location_other=None,
			employment_type="Full-Time",
			request_type="New Headcount",
			replacing_employee=None,
			how_soon="3–4 weeks",
			start_date=None,
			justification="Two jobs are waiting",
			band="C",
			budgeted_salary=3000,
			proposed_salary=3200,
			answers=[],
			status="Open",
			docstatus=0,
			name=None,
		)
		values.update(fields)
		before = values.pop("before_save", None)
		FakeDocument.__init__(self, "Manpower Request", **values)
		object.__setattr__(self, "_before_save", before)

	def get_doc_before_save(self):
		return self._before_save


#: HR's questions for the answer tests (validate rebuilds the answers from HR's settings). The default
#: world asks none, so the tests of other rules are not refused for answers they never meant to give.
HR_QUESTIONS = [
	frappe._dict(step="5 Requirements", question=q, answer_type="Long text", required=1, active=1, idx=i)
	for i, q in enumerate(("Draft job description", "Key deliverables"), 1)
]


@contextmanager
def world(*, team=True, hr=False, employees=None, user="hafiz@example.com", me="EMP-HAFIZ", questions=None):
	"""The database the rules read: who has a team, who is HR, the Employee rows.

	The team rule is the one hrms.api.team.has_team asks (an Active Employee reporting
	to the sender), HR exempt. The shared filing fence has its own tests below.
	"""
	db = MagicMock()
	db.exists.side_effect = lambda doctype, filters=None: bool(
		team and doctype == "Employee" and isinstance(filters, dict) and filters.get("reports_to")
	)
	db.get_value.side_effect = fake_employees(employees or {})
	seen = SimpleNamespace(db=db, filing=MagicMock(name="validate_filing_for_self"))
	with ExitStack() as stack:
		stack.enter_context(patch.object(frappe, "db", db))
		stack.enter_context(patch.object(frappe, "session", MagicMock(user=user)))
		stack.enter_context(patch.object(mr, "get_employee", return_value=me))
		stack.enter_context(patch.object(mr, "sees_all_employee_data", return_value=hr))
		stack.enter_context(patch.object(mr, "validate_filing_for_self", seen.filing))
		stack.enter_context(
			patch.object(
				frappe,
				"get_cached_doc",
				return_value=SimpleNamespace(questions=questions or []),
			)
		)
		yield seen


def refusal(doc, exc=frappe.ValidationError):
	"""The message validate() refuses with, or None when it lets the request through."""
	try:
		doc.validate()
	except exc as error:
		return str(error)
	return None


class TestWhoMayRequest(unittest.TestCase):
	def test_someone_with_an_active_direct_report_may(self):
		with world(team=True):
			self.assertIsNone(refusal(_Request()))

	def test_someone_without_a_team_is_refused_on_insert(self):
		with world(team=False):
			message = refusal(_Request(), frappe.PermissionError)
		self.assertEqual(message, "Only someone with a team can request manpower.")

	def test_the_team_must_be_active_reports(self):
		with world(team=True) as w:
			_Request().validate()
		filters = w.db.exists.call_args.args[1]
		self.assertEqual(filters, {"reports_to": "EMP-HAFIZ", "status": "Active"})

	def test_hr_may_file_for_anyone_even_without_a_team(self):
		with world(team=False, hr=True):
			self.assertIsNone(refusal(_Request()))

	def test_a_request_naming_no_employee_is_refused_for_a_team_it_cannot_have(self):
		with world(team=True):
			message = refusal(_Request(employee=None), frappe.PermissionError)
		self.assertEqual(message, "Only someone with a team can request manpower.")

	def test_a_saved_request_is_not_rechecked_for_a_team(self):
		# the approver or HR editing it later is not "sending"
		with world(team=False):
			self.assertIsNone(refusal(_Request(name="HR-MPR-26-10-00001")))

	def test_filing_in_a_colleagues_name_goes_through_the_shared_filing_fence(self):
		doc = _Request()
		with world(team=True) as w:
			doc.validate()
		w.filing.assert_called_once_with(doc)


class TestFilingFenceIsTheRealOne(unittest.TestCase):
	"""No patching of the fence itself: a manager with a team still cannot send in someone else's name."""

	def _file(self, employee, roles=("Employee",)):
		with (
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "session", MagicMock(user="hafiz@example.com")),
			patch.object(frappe, "get_roles", return_value=list(roles)),
			patch.object(frappe, "has_permission", return_value=False),
			patch.object(hr_utils, "own_employees", return_value=["EMP-HAFIZ"]),
			patch.object(mr, "sees_all_employee_data", return_value=False),
		):
			frappe.db.exists.return_value = True
			frappe.db.get_value.side_effect = fake_employees({})
			return refusal(_Request(employee=employee), frappe.PermissionError)

	def test_his_own_request_passes(self):
		self.assertIsNone(self._file("EMP-HAFIZ"))

	def test_a_colleagues_name_is_refused(self):
		self.assertEqual(self._file("EMP-OTHER"), "You can only file requests for yourself.")


class TestHeadcountAndLocation(unittest.TestCase):
	def test_headcount_below_one_is_refused(self):
		for bad in (0, -1, None):
			with self.subTest(headcount=bad), world():
				self.assertEqual(refusal(_Request(headcount=bad)), "Headcount must be at least 1.")

	def test_headcount_one_passes(self):
		with world():
			self.assertIsNone(refusal(_Request(headcount=1)))

	def test_a_location_alone_passes(self):
		with world():
			self.assertIsNone(refusal(_Request(location="HQ", location_other=None)))

	def test_other_is_no_location_plus_the_text(self):
		with world():
			self.assertIsNone(refusal(_Request(location=None, location_other="Port Klang yard")))

	def test_neither_is_refused(self):
		for blank in (None, "", "   "):
			with self.subTest(other=blank), world():
				message = refusal(_Request(location=None, location_other=blank))
				self.assertEqual(message, "Say where they will work.")

	def test_a_location_clears_a_stale_other_text(self):
		doc = _Request(location="HQ", location_other="old text")
		with world():
			doc.validate()
		self.assertIsNone(doc.location_other)


class TestReplacement(unittest.TestCase):
	STAFF: ClassVar[dict] = {
		"EMP-ACTIVE": {"department": "Ops", "status": "Active"},
		"EMP-OTHERDEPT": {"department": "Finance", "status": "Active"},
		"EMP-LEFT-RECENT": {
			"department": "Ops",
			"status": "Left",
			"relieving_date": TODAY - relativedelta(months=2),
		},
		# the very day six months back still counts; the day before does not
		"EMP-LEFT-EDGE": {"department": "Ops", "status": "Left", "relieving_date": SIX_MONTHS_AGO},
		"EMP-LEFT-OLD": {
			"department": "Ops",
			"status": "Left",
			"relieving_date": SIX_MONTHS_AGO - datetime.timedelta(days=1),
		},
		"EMP-LEFT-NODATE": {"department": "Ops", "status": "Left"},
	}

	def _replace(self, who, **extra):
		doc = _Request(request_type="Replacement", replacing_employee=who, **extra)
		with world(employees=self.STAFF):
			return refusal(doc)

	def test_a_replacement_must_name_who(self):
		self.assertEqual(self._replace(None), "Name the staff being replaced.")

	def test_an_active_person_of_the_department_is_fine(self):
		self.assertIsNone(self._replace("EMP-ACTIVE"))

	def test_a_leaver_of_the_last_six_months_is_fine(self):
		self.assertIsNone(self._replace("EMP-LEFT-RECENT"))
		self.assertIsNone(self._replace("EMP-LEFT-EDGE"))

	def test_a_leaver_of_six_months_and_a_day_ago_is_refused(self):
		self.assertEqual(
			self._replace("EMP-LEFT-OLD"),
			"The staff being replaced must be active or have left in the last 6 months.",
		)

	def test_a_leaver_with_no_relieving_date_is_refused(self):
		self.assertIn("last 6 months", self._replace("EMP-LEFT-NODATE"))

	def test_another_department_is_refused(self):
		self.assertEqual(
			self._replace("EMP-OTHERDEPT"), "The staff being replaced must be in the Ops department."
		)

	def test_an_unknown_person_is_refused(self):
		self.assertIn("Ops department", self._replace("EMP-NOBODY"))

	def test_any_other_type_clears_the_replaced_person(self):
		for kind in ("New Headcount", "Project-Based", "Business Expansion"):
			with self.subTest(kind=kind):
				doc = _Request(request_type=kind, replacing_employee="EMP-OTHERDEPT")
				with world(employees=self.STAFF):
					self.assertIsNone(refusal(doc))
				self.assertIsNone(doc.replacing_employee)


class TestUrgency(unittest.TestCase):
	def test_urgency_for_each_answer(self):
		self.assertEqual(mr.urgency_for("Within 2 weeks"), "High")
		self.assertEqual(mr.urgency_for("3–4 weeks"), "Medium")
		self.assertEqual(mr.urgency_for("1–2 months"), "Low")

	def test_urgency_for_something_else_is_none(self):
		self.assertIsNone(mr.urgency_for("tomorrow"))
		self.assertIsNone(mr.urgency_for(None))

	def test_validate_sets_it_from_how_soon(self):
		for how_soon, urgency in (("Within 2 weeks", "High"), ("3–4 weeks", "Medium"), ("1–2 months", "Low")):
			doc = _Request(how_soon=how_soon, urgency="Low" if urgency != "Low" else "High")
			with self.subTest(how_soon=how_soon), world():
				doc.validate()
				self.assertEqual(doc.urgency, urgency)

	def test_how_soon_options_are_the_ones_the_map_knows(self):
		fields = {f["fieldname"]: f for f in _doctype_json("manpower_request")["fields"]}
		declared = set(fields["how_soon"]["options"].split("\n")) - {""}
		self.assertEqual(declared, set(mr.URGENCY_BY_HOW_SOON))


class TestStartDate(unittest.TestCase):
	def _start(self, start, **extra):
		with world():
			return refusal(_Request(start_date=start, **extra))

	def test_no_start_date_is_fine(self):
		self.assertIsNone(self._start(None))

	def test_tomorrow_is_fine(self):
		self.assertIsNone(self._start(TODAY + datetime.timedelta(days=1)))
		self.assertIsNone(self._start((TODAY + datetime.timedelta(days=30)).isoformat()))

	def test_today_and_the_past_are_refused(self):
		for start in (TODAY, TODAY - datetime.timedelta(days=1), TODAY.isoformat()):
			with self.subTest(start=start):
				self.assertEqual(self._start(start), "The start date must be after today.")

	def test_a_decided_request_is_not_held_to_the_date(self):
		# only while still a draft: an old submitted request keeps its date
		self.assertIsNone(self._start(TODAY - datetime.timedelta(days=30), docstatus=1, name="HR-MPR-1"))

	def test_a_waiting_request_whose_date_has_since_passed_can_still_be_decided(self):
		# the approver's dry-run Approve runs validate() on the still-draft row, weeks after it was
		# sent; the date the sender chose must not stop the approval
		past = TODAY - datetime.timedelta(days=3)
		unchanged = _Request(
			start_date=past, name="HR-MPR-1", before_save=_Request(start_date=past, name="HR-MPR-1")
		)
		with world():
			self.assertIsNone(refusal(unchanged))

	def test_editing_the_date_of_a_waiting_request_to_a_past_day_is_refused(self):
		past = TODAY - datetime.timedelta(days=3)
		later = TODAY + datetime.timedelta(days=10)
		edited = _Request(
			start_date=past, name="HR-MPR-1", before_save=_Request(start_date=later, name="HR-MPR-1")
		)
		with world():
			self.assertEqual(refusal(edited), "The start date must be after today.")


class TestSalaries(unittest.TestCase):
	def test_each_salary_must_be_above_zero(self):
		for field in ("budgeted_salary", "proposed_salary"):
			for bad in (0, -5, None):
				with self.subTest(field=field, value=bad), world():
					message = refusal(_Request(**{field: bad}))
					self.assertIn("must be more than zero", message)

	def test_positive_salaries_pass(self):
		with world():
			self.assertIsNone(refusal(_Request(budgeted_salary=1, proposed_salary=0.5)))


class TestRequiredAnswers(unittest.TestCase):
	def row(self, question, answer, required=1):
		return frappe._dict(question=question, answer=answer, required=required)

	def test_gaps_name_every_required_question_left_blank(self):
		rows = [
			self.row("Draft job description", "Weld pipes"),
			self.row("Key deliverables", ""),
			self.row("Minimum qualification", None),
			self.row("Years of experience", "   "),
		]
		self.assertEqual(
			mr.required_answer_gaps(rows),
			["Key deliverables", "Minimum qualification", "Years of experience"],
		)

	def test_an_optional_blank_is_not_a_gap(self):
		self.assertEqual(mr.required_answer_gaps([self.row("Impact if delayed", "", required=0)]), [])

	def test_nothing_to_answer_is_no_gaps(self):
		self.assertEqual(mr.required_answer_gaps([]), [])
		self.assertEqual(mr.required_answer_gaps(None), [])

	def test_a_zero_or_no_is_an_answer(self):
		self.assertEqual(mr.required_answer_gaps([self.row("Years", 0), self.row("Industry", "No")]), [])

	def test_validate_refuses_and_names_the_question(self):
		doc = _Request(answers=[self.row("Draft job description", ""), self.row("Key deliverables", "")])
		with world(questions=HR_QUESTIONS):
			message = refusal(doc)
		self.assertIn("Draft job description", message)
		self.assertIn("Key deliverables", message)

	def test_validate_passes_when_answered(self):
		answers = [self.row("Draft job description", "Weld pipes"), self.row("Key deliverables", "On time")]
		with world(questions=HR_QUESTIONS):
			self.assertIsNone(refusal(_Request(answers=answers)))

	def test_validate_asks_hrs_question_even_when_the_phone_left_it_out(self):
		with world(questions=HR_QUESTIONS):
			message = refusal(_Request(answers=[self.row("Draft job description", "Weld pipes")]))
		self.assertEqual(message, "Please answer: Key deliverables")


class TestAfterSend(unittest.TestCase):
	def _insert(self, approvers):
		doc = _Request(name="HR-MPR-26-10-00001")
		with (
			patch.object(mr, "get_designated_approvers", return_value=approvers) as designated,
			patch.object(mr, "share_doc_with_approver") as share,
			patch.object(mr.ManpowerRequest, "notify_approver") as notify,
		):
			doc.after_insert()
		return designated, share, notify, doc

	def test_it_is_shared_with_the_first_designated_approver_and_they_are_told(self):
		designated, share, notify, doc = self._insert(["boss@example.com", "director@example.com"])
		designated.assert_called_once_with("EMP-HAFIZ", "leave_approver", "leave_approvers")
		share.assert_called_once_with(doc, "boss@example.com")
		notify.assert_called_once_with()

	def test_the_approver_is_the_first_of_the_line(self):
		# the line can hand back a login with case drift; a share needs the User's own name
		with patch.object(
			mr, "get_designated_approvers", return_value=[" Boss@Example.com", "d@example.com"]
		):
			self.assertEqual(_Request(name="X")._get_doc_approver(), "boss@example.com")

	def test_no_approver_on_the_line_shares_with_nobody(self):
		with patch.object(mr, "get_designated_approvers", return_value=[]):
			self.assertIsNone(_Request(name="X")._get_doc_approver())


class TestOnSubmit(unittest.TestCase):
	def _submit(self, status, **extra):
		doc = _Request(name="HR-MPR-26-10-00001", docstatus=1, status=status, **extra)
		with patch.object(mr, "validate_self_submission") as self_fence:
			doc.on_submit()
		return doc, self_fence

	def test_only_a_decision_may_be_submitted(self):
		for status in ("Open", "Withdrawn", None):
			with self.subTest(status=status), self.assertRaises(frappe.ValidationError) as caught:
				self._submit(status)
			self.assertIn("must be Approved or Rejected", str(caught.exception))

	def test_approved_waits_for_hr(self):
		doc, _ = self._submit("Approved")
		self.assertEqual(doc.db_writes, [("hiring_status", "Waiting for HR")])

	def test_rejected_sets_no_hiring_status(self):
		doc, _ = self._submit("Rejected")
		self.assertEqual(doc.db_writes, [])

	def test_the_sender_cannot_submit_their_own_request(self):
		doc = _Request(name="HR-MPR-26-10-00001", docstatus=1, status="Approved")
		with patch.object(
			mr, "validate_self_submission", side_effect=frappe.ValidationError("Self-approval")
		):
			with self.assertRaises(frappe.ValidationError):
				doc.on_submit()
		self.assertEqual(doc.db_writes, [])


def _doctype_json(folder):
	return json.loads((DOCTYPE_DIR / folder / f"{folder}.json").read_text(encoding="utf-8"))


def _fields(folder):
	return {f["fieldname"]: f for f in _doctype_json(folder)["fields"]}


def _perms(folder, role, permlevel=0):
	return [
		p
		for p in _doctype_json(folder)["permissions"]
		if p["role"] == role and (p.get("permlevel") or 0) == permlevel
	]


def _rights(row):
	return {k for k, v in row.items() if v == 1}


class TestDoctypeShape(unittest.TestCase):
	def test_every_doctype_is_a_module(self):
		for folder in (
			"manpower_request",
			"manpower_request_question",
			"manpower_request_answer",
			"manpower_request_settings",
		):
			with self.subTest(folder=folder):
				self.assertTrue((DOCTYPE_DIR / folder / "__init__.py").exists())
				self.assertTrue((DOCTYPE_DIR / folder / f"{folder}.py").exists())
				self.assertEqual(_doctype_json(folder)["module"], "HR")

	def test_the_request_is_a_submittable_tracked_titled_by_position(self):
		doc = _doctype_json("manpower_request")
		self.assertEqual(doc["name"], "Manpower Request")
		self.assertEqual(doc["autoname"], "HR-MPR-.YY.-.MM.-.#####")
		self.assertEqual(doc["is_submittable"], 1)
		self.assertEqual(doc["track_changes"], 1)
		self.assertEqual(doc["title_field"], "position_title")

	def test_the_fixed_fields_exist_with_the_agreed_types_and_mandatory_flags(self):
		fields = _fields("manpower_request")
		expected = {
			"employee": ("Link", "Employee", 1),
			"employee_name": ("Data", None, 0),
			"company": ("Link", "Company", 0),
			"department": ("Link", "Department", 1),
			"position_title": ("Data", None, 1),
			"headcount": ("Int", None, 1),
			"location": ("Link", "Shift Location", 0),
			"location_other": ("Small Text", None, 0),
			"employment_type": ("Select", None, 1),
			"request_type": ("Select", None, 1),
			"replacing_employee": ("Link", "Employee", 0),
			"how_soon": ("Select", None, 1),
			"urgency": ("Select", None, 0),
			"start_date": ("Date", None, 0),
			"justification": ("Small Text", None, 1),
			"band": ("Select", None, 1),
			"budgeted_salary": ("Currency", None, 1),
			"proposed_salary": ("Currency", None, 1),
			"answers": ("Table", "Manpower Request Answer", 0),
			"status": ("Select", None, 0),
			"hiring_status": ("Select", None, 0),
			"hr_note": ("Small Text", None, 0),
			"withdrawn_reason": ("Small Text", None, 0),
			"amended_from": ("Link", "Manpower Request", 0),
		}
		for name, (fieldtype, options, reqd) in expected.items():
			with self.subTest(field=name):
				self.assertIn(name, fields)
				self.assertEqual(fields[name]["fieldtype"], fieldtype)
				if options:
					self.assertEqual(fields[name].get("options"), options)
				self.assertEqual(fields[name].get("reqd", 0), reqd)

	def test_select_words_are_the_agreed_ones(self):
		fields = _fields("manpower_request")
		options = lambda name: fields[name]["options"].split("\n")  # noqa: E731
		# A mandatory Select starts blank: Frappe fills a Select with its FIRST option when nothing was
		# sent, which would pass "mandatory" with Full-Time / Within 2 weeks / band B nobody chose.
		self.assertEqual(options("employment_type"), ["", "Full-Time", "Contract", "Part-Time", "Internship"])
		self.assertEqual(
			options("request_type"),
			["", "New Headcount", "Replacement", "Project-Based", "Business Expansion"],
		)
		self.assertEqual(options("how_soon"), ["", "Within 2 weeks", "3–4 weeks", "1–2 months"])
		self.assertEqual(options("urgency"), ["", "High", "Medium", "Low"])
		self.assertEqual(options("band"), ["", "B", "C", "D", "E1", "E2", "F"])
		self.assertEqual(options("status"), ["Open", "Approved", "Rejected", "Withdrawn"])
		self.assertEqual(
			options("hiring_status"), ["", "Waiting for HR", "Recruiting", "Filled", "Not proceeding"]
		)

	def test_defaults_and_flags(self):
		fields = _fields("manpower_request")
		self.assertEqual(fields["headcount"]["default"], "1")
		self.assertEqual(fields["status"]["default"], "Open")
		self.assertEqual(fields["status"].get("permlevel", 0), 0)
		self.assertEqual(fields["status"].get("in_list_view"), 1)
		self.assertEqual(fields["urgency"].get("read_only"), 1)
		self.assertEqual(fields["company"].get("read_only"), 1)
		self.assertEqual(fields["company"].get("fetch_from"), "employee.company")
		self.assertEqual(fields["employee_name"].get("fetch_from"), "employee.employee_name")
		for name in ("hiring_status", "hr_note"):
			self.assertEqual(fields[name].get("permlevel"), 1, name)
			self.assertEqual(fields[name].get("allow_on_submit"), 1, name)
		self.assertEqual(fields["withdrawn_reason"].get("read_only"), 1)
		self.assertEqual(fields["withdrawn_reason"].get("allow_on_submit"), 1)

	def test_permissions_match_the_brief(self):
		folder = "manpower_request"
		system = _rights(_perms(folder, "System Manager")[0])
		self.assertTrue({"read", "write", "create", "delete", "submit", "cancel"} <= system)
		hr = {"read", "write", "create", "submit", "cancel", "report", "export"}
		for role in ("HR Manager", "HR User"):
			self.assertTrue(hr <= _rights(_perms(folder, role)[0]), role)
			self.assertNotIn("delete", _rights(_perms(folder, role)[0]), role)
			level_one = _rights(_perms(folder, role, 1)[0])
			self.assertTrue({"read", "write"} <= level_one, role)
		employee = _rights(_perms(folder, "Employee")[0])
		self.assertEqual(employee & {"read", "write", "create"}, {"read", "write", "create"})
		self.assertFalse(employee & {"submit", "cancel", "delete", "amend"})
		self.assertEqual(_rights(_perms(folder, "Employee", 1)[0]) & {"read", "write"}, {"read"})

	def test_the_question_table(self):
		doc = _doctype_json("manpower_request_question")
		self.assertEqual(doc["istable"], 1)
		fields = _fields("manpower_request_question")
		self.assertEqual(
			[o.split(" ")[0] for o in fields["step"]["options"].split("\n")], ["1", "2", "3", "4", "5"]
		)
		self.assertEqual(
			[o.split(" ", 1)[1] for o in fields["step"]["options"].split("\n")],
			["Position", "Type", "Why", "Pay", "Requirements"],
		)
		self.assertEqual(fields["question"]["fieldtype"], "Data")
		self.assertEqual(fields["question"].get("reqd"), 1)
		self.assertEqual(
			fields["answer_type"]["options"].split("\n"),
			["Short text", "Long text", "Choice", "Number", "Money", "Date", "Yes-No"],
		)
		self.assertEqual(fields["choices"]["fieldtype"], "Small Text")
		self.assertEqual(fields["required"]["fieldtype"], "Check")
		self.assertEqual(fields["help"]["fieldtype"], "Small Text")
		self.assertEqual(fields["active"]["fieldtype"], "Check")
		self.assertEqual(fields["active"]["default"], "1")

	def test_the_answer_table_copies_what_was_asked(self):
		doc = _doctype_json("manpower_request_answer")
		self.assertEqual(doc["istable"], 1)
		fields = _fields("manpower_request_answer")
		for name in ("step", "question", "answer_type", "answer", "required"):
			self.assertIn(name, fields)
		self.assertEqual(fields["question"]["fieldtype"], "Data")
		self.assertEqual(fields["answer"]["fieldtype"], "Small Text")
		self.assertEqual(fields["required"]["fieldtype"], "Check")

	def test_the_settings_single(self):
		doc = _doctype_json("manpower_request_settings")
		self.assertEqual(doc["issingle"], 1)
		self.assertEqual(doc["track_changes"], 1)
		fields = _fields("manpower_request_settings")
		self.assertEqual(fields["questions"]["fieldtype"], "Table")
		self.assertEqual(fields["questions"]["options"], "Manpower Request Question")
		hr_manager = _rights(_perms("manpower_request_settings", "HR Manager")[0])
		self.assertTrue({"read", "write"} <= hr_manager)
		hr_user = _rights(_perms("manpower_request_settings", "HR User")[0])
		self.assertIn("read", hr_user)
		self.assertNotIn("write", hr_user)
		system = _rights(_perms("manpower_request_settings", "System Manager")[0])
		self.assertTrue({"read", "write"} <= system)
		roles = {p["role"] for p in doc["permissions"]}
		self.assertEqual(roles, {"HR Manager", "HR User", "System Manager"})


def _hook_paths(hook_name):
	tree = ast.parse((HRMS_ROOT / "hooks.py").read_text(encoding="utf-8"))
	for node in ast.walk(tree):
		if isinstance(node, ast.Assign) and any(
			isinstance(t, ast.Name) and t.id == hook_name for t in node.targets
		):
			return {
				key.value: value.value
				for key, value in zip(node.value.keys, node.value.values, strict=True)
				if isinstance(key, ast.Constant) and isinstance(value, ast.Constant)
			}
	return {}


class TestWhoMayRead(unittest.TestCase):
	DOCTYPE = "Manpower Request"

	def _db(self):
		db = MagicMock()
		db.escape.side_effect = lambda value: f"'{value}'"
		return db

	def _ask(self, *, hr=False, own=(), shared=()):
		stack = ExitStack()
		stack.enter_context(patch.object(frappe, "db", self._db()))
		stack.enter_context(patch.object(scope, "_is_hr", return_value=hr))
		stack.enter_context(patch.object(scope, "_own_employees", return_value=list(own)))
		stack.enter_context(patch.object(scope, "get_shared", return_value=list(shared)))
		return stack

	def _row(self, employee="EMP-HAFIZ"):
		return frappe._dict(
			doctype=self.DOCTYPE, name="HR-MPR-26-10-00001", employee=employee, company="TNME"
		)

	def test_the_doctype_is_owned_by_its_employee(self):
		self.assertEqual(scope.OWNED_DOCTYPES[self.DOCTYPE], ("employee",))
		self.assertNotIn(self.DOCTYPE, scope._COMPANY_VIA_EMPLOYEE)
		self.assertNotIn(self.DOCTYPE, scope.TEAM_REVIEWED_DOCTYPES)
		self.assertTrue(callable(scope.query_manpower_request))

	def test_hooks_wire_both_the_list_and_the_document(self):
		self.assertEqual(
			_hook_paths("permission_query_conditions")[self.DOCTYPE],
			"hrms.overrides.employee_owned_row_scope.query_manpower_request",
		)
		self.assertEqual(
			_hook_paths("has_permission")[self.DOCTYPE],
			"hrms.overrides.employee_owned_row_scope.has_permission",
		)

	def test_the_sender_lists_and_opens_their_own(self):
		with self._ask(own=["EMP-HAFIZ"]):
			condition = scope.get_permission_query_conditions(self.DOCTYPE, "hafiz@example.com")
			self.assertIn("`tabManpower Request`.`employee` in ('EMP-HAFIZ')", condition)
			self.assertTrue(scope.has_permission(self._row(), "read", "hafiz@example.com"))

	def test_another_employee_sees_nothing(self):
		with self._ask(own=["EMP-OTHER"]):
			condition = scope.get_permission_query_conditions(self.DOCTYPE, "other@example.com")
			self.assertNotIn("EMP-HAFIZ", condition)
			self.assertFalse(scope.has_permission(self._row(), "read", "other@example.com"))

	def test_a_user_with_no_employee_and_no_share_sees_nothing(self):
		with self._ask():
			self.assertEqual(scope.get_permission_query_conditions(self.DOCTYPE, "x@example.com"), "1=0")
			self.assertFalse(scope.has_permission(self._row(), "read", "x@example.com"))

	def test_the_manager_does_not_see_it_just_for_managing_him(self):
		# the line approver reads through the share made when it was sent, not through reports_to
		with self._ask(own=["EMP-BOSS"]):
			self.assertFalse(scope.has_permission(self._row(), "read", "boss@example.com"))

	def test_the_shared_approver_lists_and_opens_it(self):
		with self._ask(own=["EMP-BOSS"], shared=["HR-MPR-26-10-00001"]):
			condition = scope.get_permission_query_conditions(self.DOCTYPE, "boss@example.com")
			self.assertIn("`tabManpower Request`.`name` in ('HR-MPR-26-10-00001')", condition)
			self.assertTrue(scope.has_permission(self._row(), "read", "boss@example.com"))

	def test_hr_sees_it_inside_its_company_fence_only(self):
		with self._ask(hr=True), patch.object(scope, "allowed_companies", return_value=[]):
			self.assertEqual(scope.get_permission_query_conditions(self.DOCTYPE, "hr@example.com"), "")
		with self._ask(hr=True), patch.object(scope, "company_visible", return_value=True):
			self.assertTrue(scope.has_permission(self._row(), "read", "hr@example.com"))
		with self._ask(hr=True), patch.object(scope, "company_visible", return_value=False):
			self.assertFalse(scope.has_permission(self._row(), "read", "hr@example.com"))


if __name__ == "__main__":
	unittest.main()


class TestTheReplacedPersonIsNamed(unittest.TestCase):
	"""S3 browser check (22 Oct): the detail read "Replacement for HR-EMP-00007" — the record carried
	only the id, and the sender and approver should see a name."""

	def test_the_name_is_fetched_beside_the_link(self):
		fields = {f["fieldname"]: f for f in _doctype_json("manpower_request")["fields"]}
		self.assertEqual(fields["replacing_employee_name"]["fetch_from"], "replacing_employee.employee_name")
		self.assertTrue(fields["replacing_employee_name"].get("read_only"))
		order = _doctype_json("manpower_request")["field_order"]
		self.assertEqual(order.index("replacing_employee_name"), order.index("replacing_employee") + 1)


class TestAnswersAreHrsQuestions(unittest.TestCase):
	"""Frappe review of the HR report slice (22 Oct): the answer rows carried whatever question text the
	phone sent, and the Desk report turns each distinct question into a column label. So a hand-made
	request could add a junk column, or put markup in a header HR opens. The server now keeps only
	answers to questions HR asked, and takes the question's words, type and required flag from HR's
	settings — the answer is the only thing the sender supplies."""

	SETTINGS: ClassVar[list] = [
		frappe._dict(
			step="5 Requirements",
			question="Draft job description",
			answer_type="Long text",
			required=1,
			active=1,
			idx=1,
		),
		frappe._dict(
			step="5 Requirements", question="KPIs", answer_type="Long text", required=0, active=1, idx=2
		),
		frappe._dict(
			step="3 Why", question="Retired question", answer_type="Short text", required=1, active=0, idx=3
		),
	]

	def test_only_hrs_questions_survive_and_keep_hrs_words(self):
		sent = [
			frappe._dict(
				step="5",
				question="Draft job description",
				answer_type="Short text",
				required=0,
				answer="Weld pipes",
			),
			frappe._dict(
				step="5",
				question="<img src=x onerror=alert(1)>",
				answer_type="Short text",
				required=0,
				answer="junk",
			),
			frappe._dict(step="5", question="KPIs", answer_type="Long text", required=0, answer=""),
		]
		kept = mr.answers_from_settings(sent, self.SETTINGS)
		self.assertEqual([a["question"] for a in kept], ["Draft job description", "KPIs"])
		self.assertEqual(kept[0]["answer"], "Weld pipes")
		# HR's type and required flag, not the phone's
		self.assertEqual((kept[0]["answer_type"], kept[0]["required"]), ("Long text", 1))
		self.assertEqual(kept[0]["step"], "5 Requirements")

	def test_a_required_question_left_out_entirely_is_still_asked(self):
		kept = mr.answers_from_settings([], self.SETTINGS)
		self.assertEqual(mr.required_answer_gaps(kept), ["Draft job description"])

	def test_a_question_hr_switched_off_is_not_asked(self):
		kept = mr.answers_from_settings([], self.SETTINGS)
		self.assertNotIn("Retired question", [a["question"] for a in kept])
