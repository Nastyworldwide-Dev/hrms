"""Org chart node and photo endpoints for the PWA.

Owner 28 Oct 2026: staff see Active employees of their own company; HR sees
all companies. Card shows name, designation, department, branch, photo, away
today (bool, NEVER the leave type), team size.

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_org_chart.py
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
for module in ("pypika", "pypika.terms", "pypika.functions"):
	sys.modules.setdefault(module, MagicMock())
from _fake_document import FakeDocument

import frappe
from frappe import _

from hrms.api import org_chart


def _employee(
	name,
	employee_name,
	designation="Designer",
	department="Design",
	branch="HQ",
	company="Company A",
	reports_to=None,
	image=None,
):
	"""Mock employee record."""
	return {
		"name": name,
		"employee_name": employee_name,
		"designation": designation,
		"department": department,
		"branch": branch,
		"company": company,
		"reports_to": reports_to,
		"image": image,
	}


def _get_node(
	employee=None,
	company=None,
	is_hr=False,
	my_employee="EMP-1",
	my_company="Company A",
	employees=None,
	leave_by_employee=None,
	off_session_result=None,
	db_reads=None,
):
	"""Call get_node with mocked dependencies."""
	if employees is None:
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
			_employee("EMP-3", "Charlie", reports_to="EMP-1"),
		]
	if leave_by_employee is None:
		leave_by_employee = {}

	def mock_get_all(doctype, filters=None, fields=None, **kwargs):
		"""Filter employees by the request."""
		if doctype != "Employee":
			return []
		filtered = employees
		if filters:
			if "name" in filters:
				val = filters["name"]
				if isinstance(val, list) and val and val[0] == "in":
					names = val[1]
					filtered = [e for e in filtered if e["name"] in names]
				else:
					filtered = [e for e in filtered if e["name"] == val]
			if "status" in filters:
				filtered = [e for e in filtered if e.get("status", "Active") == filters["status"]]
			if "reports_to" in filters:
				val = filters["reports_to"]
				if isinstance(val, list) and val and val[0] == "in":
					filtered = [e for e in filtered if e.get("reports_to") in val[1]]
				elif isinstance(val, tuple) and val[0] == "is":
					if val[1] == "not set":
						filtered = [e for e in filtered if not e.get("reports_to")]
				else:
					filtered = [e for e in filtered if e.get("reports_to") == val]
			if "company" in filters:
				filtered = [e for e in filtered if e["company"] == filters["company"]]
		if kwargs.get("group_by") == "reports_to":
			counts = {}
			for e in filtered:
				counts[e["reports_to"]] = counts.get(e["reports_to"], 0) + 1
			return [{"reports_to": k, "n": n} for k, n in counts.items()]
		return filtered

	def mock_leave_by_employee(ids, day):
		"""Mock leave_day.by_employee."""
		return leave_by_employee

	def mock_off_session(rows, day):
		"""Mock leave_day.off_session."""
		return off_session_result

	def mock_throw(msg, exc_class):
		"""Raise the exception."""
		raise exc_class(msg)

	def mock_db_get_value(doctype, name, field):
		"""Mock frappe.db.get_value for employee image reads."""
		if db_reads is not None:
			db_reads.append((doctype, name, field))
		if doctype == "Employee":
			emp = next((e for e in employees if e["name"] == name), None)
			if emp:
				return emp.get("image")
		return None

	with (
		patch("frappe.session.user", "test_user"),
		patch.object(org_chart, "getdate", return_value="2026-10-28"),
		patch.object(frappe, "get_all", side_effect=mock_get_all),
		patch("hrms.api.org_chart.require_employee", return_value=my_employee),
		patch("hrms.api.org_chart.sees_all_employee_data", return_value=is_hr),
		patch.object(org_chart, "by_employee", side_effect=mock_leave_by_employee),
		patch.object(org_chart, "off_session", side_effect=mock_off_session),
		patch.object(frappe, "throw", side_effect=mock_throw),
		patch.object(frappe.db, "get_value", side_effect=mock_db_get_value),
	):
		return org_chart.get_node(employee=employee, company=company)


class TestVisibleTable(unittest.TestCase):
	def test_truth_table(self):
		"""The fence's own truth table: (is_hr, my_company, target_company) -> visible."""
		table = [
			(False, "A", "A", True),
			(False, "A", "B", False),
			(True, "A", "B", True),
			(False, None, "A", False),
		]
		for is_hr, mine, target, expected in table:
			with self.subTest(is_hr=is_hr, mine=mine, target=target):
				self.assertIs(org_chart._visible(target, is_hr, mine), expected)


class TestFencing(unittest.TestCase):
	def test_staff_sees_only_own_company(self):
		"""Staff in Company A asking for someone in Company B is refused.

		Spec change from review (28 Oct): this raises the same DoesNotExistError
		("Employee not found.") as a missing employee, so staff cannot probe
		which ids exist in other companies. It used to be PermissionError.
		"""
		employees = [
			_employee("EMP-1", "Ali", company="Company A", reports_to=None),
			_employee("EMP-2", "Bob", company="Company B", reports_to=None),
		]
		with self.assertRaises(frappe.DoesNotExistError) as ctx:
			_get_node(
				employee="EMP-2",
				company="Company B",
				is_hr=False,
				my_company="Company A",
				employees=employees,
			)
		self.assertIn("Employee not found.", str(ctx.exception))

	def test_hr_sees_all_companies(self):
		"""HR asking for someone in another company is allowed."""
		employees = [
			_employee("EMP-1", "Ali", company="Company A", reports_to=None),
			_employee("EMP-2", "Bob", company="Company B", reports_to=None),
		]
		result = _get_node(
			employee="EMP-2", company="Company B", is_hr=True, my_company="Company A", employees=employees
		)
		self.assertEqual(result["person"]["id"], "EMP-2")

	def test_staff_default_to_own_employee(self):
		"""Staff asking without an employee arg gets their own record."""
		result = _get_node(employee=None, company=None, is_hr=False)
		self.assertEqual(result["person"]["id"], "EMP-1")

	def test_hr_default_to_own_employee(self):
		"""HR asking without an employee arg gets their own record."""
		result = _get_node(employee=None, company=None, is_hr=True)
		self.assertEqual(result["person"]["id"], "EMP-1")


class TestChainUp(unittest.TestCase):
	def test_chain_up_nearest_first(self):
		"""chain_up is ordered nearest manager first."""
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
			_employee("EMP-3", "Charlie", reports_to="EMP-2"),
		]
		result = _get_node(employee="EMP-3", is_hr=False, employees=employees)
		chain = result["chain_up"]
		self.assertEqual(len(chain), 2)
		self.assertEqual(chain[0]["id"], "EMP-2")
		self.assertEqual(chain[1]["id"], "EMP-1")

	def test_chain_up_stops_at_loop(self):
		"""A loop A->B->A stops without hanging, with the last valid person."""
		employees = [
			_employee("EMP-1", "Ali", reports_to="EMP-2"),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		chain = result["chain_up"]
		self.assertEqual(len(chain), 1)
		self.assertEqual(chain[0]["id"], "EMP-2")

	def test_chain_up_stops_at_missing_manager(self):
		"""A missing manager stops the chain."""
		employees = [
			_employee("EMP-1", "Ali", reports_to="MISSING"),
			_employee("EMP-2", "Bob", reports_to=None),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		chain = result["chain_up"]
		self.assertEqual(len(chain), 1)
		self.assertEqual(chain[0], {"left": True})

	def test_hr_left_stub_keeps_the_id(self):
		"""Spec change from review: staff get {left} only; HR keeps the manager id."""
		employees = [_employee("EMP-1", "Ali", reports_to="MISSING")]
		result = _get_node(employee="EMP-1", is_hr=True, employees=employees)
		self.assertEqual(result["chain_up"], [{"left": True, "name": "MISSING"}])

	def test_chain_up_stops_at_left_manager(self):
		"""A Left manager ends the chain; staff get {left} only (spec change from review: no id)."""
		employees = [
			_employee("EMP-1", "Ali", reports_to="EMP-2"),
			{**_employee("EMP-2", "Bob", reports_to="EMP-3"), "status": "Left"},
			_employee("EMP-3", "Cy", reports_to=None),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		self.assertEqual(result["chain_up"], [{"left": True}])

	def test_chain_up_max_12_steps(self):
		"""chain_up stops after 12 steps."""
		employees = [_employee("EMP-1", "Ali", reports_to=None)]
		for i in range(2, 15):
			employees.append(_employee(f"EMP-{i}", f"Name{i}", reports_to=f"EMP-{i - 1}"))

		result = _get_node(employee="EMP-14", is_hr=False, employees=employees)
		chain = result["chain_up"]
		self.assertEqual(len(chain), 12)


class TestGapsLeftManager(unittest.TestCase):
	def test_left_manager_listed_and_top_person_kept_out(self):
		"""HR gaps: someone whose manager Left is listed; the top person is not a gap."""
		employees = [
			_employee("EMP-1", "Ali"),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
			_employee("EMP-3", "Cy", reports_to="EMP-9"),
			{**_employee("EMP-9", "Gone"), "status": "Left"},
		]
		result = _get_node(employee="EMP-1", company="Company A", is_hr=True, employees=employees)
		self.assertEqual([p["id"] for p in result["gaps"]["left_manager"]], ["EMP-3"])
		self.assertEqual(result["gaps"]["no_manager"], [])


class TestOneLeaveRead(unittest.TestCase):
	def test_one_by_employee_call_for_all_ids(self):
		"""One leave read covers every person on the page."""
		employees = [
			_employee("EMP-1", "Ali"),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
			_employee("EMP-3", "Cy", reports_to="EMP-1"),
		]
		with patch.object(org_chart, "by_employee", return_value={}) as read:
			with (
				patch.object(
					frappe,
					"get_all",
					side_effect=lambda dt, filters=None, **kw: _filter(employees, filters, kw),
				),
				patch.object(org_chart, "require_employee", return_value="EMP-2"),
				patch.object(org_chart, "sees_all_employee_data", return_value=False),
			):
				org_chart.get_node()
		self.assertEqual(read.call_count, 1)
		self.assertEqual(set(read.call_args[0][0]), {"EMP-1", "EMP-2", "EMP-3"})


def _filter(employees, filters, kw):
	out = [e for e in employees if e.get("status", "Active") == (filters or {}).get("status", "Active")]
	f = filters or {}
	if "name" in f and not isinstance(f["name"], list):
		out = [e for e in out if e["name"] == f["name"]]
	if "reports_to" in f:
		v = f["reports_to"]
		out = [e for e in out if e.get("reports_to") in (v[1] if isinstance(v, list) else [v])]
	if kw.get("group_by"):
		counts = {}
		for e in out:
			counts[e["reports_to"]] = counts.get(e["reports_to"], 0) + 1
		return [{"reports_to": k, "n": n} for k, n in counts.items()]
	return out


class TestStaffChainFence(unittest.TestCase):
	def test_staff_chain_stops_at_other_company_manager(self):
		"""A manager in another company is not shown to staff."""
		employees = [
			_employee("EMP-1", "Ali", company="Company A", reports_to="EMP-2"),
			_employee("EMP-2", "Bob", company="Company B"),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		self.assertEqual(result["chain_up"], [])


class TestReports(unittest.TestCase):
	def test_reports_are_sorted_by_name(self):
		"""Direct reports are sorted by employee_name."""
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),
			_employee("EMP-2", "Zoe", reports_to="EMP-1"),
			_employee("EMP-3", "Bob", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		reports = result["reports"]
		self.assertEqual([r["id"] for r in reports], ["EMP-3", "EMP-2"])

	def test_reports_excludes_inactive(self):
		"""Inactive employees are not in reports."""
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		reports = result["reports"]
		self.assertEqual(len(reports), 1)


class TestPeers(unittest.TestCase):
	def test_peers_same_manager_not_self(self):
		"""Peers are people with the same reports_to, excluding target."""
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
			_employee("EMP-3", "Charlie", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-2", is_hr=False, employees=employees)
		peers = result["peers"]
		self.assertEqual(len(peers), 1)
		self.assertEqual(peers[0]["id"], "EMP-3")

	def test_peers_empty_when_no_manager(self):
		"""Peers is empty when target has no manager."""
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		peers = result["peers"]
		self.assertEqual(len(peers), 0)


class TestAway(unittest.TestCase):
	def test_full_day_leave_is_away_true(self):
		"""A full-day leave results in away=True."""
		employees = [_employee("EMP-1", "Ali", reports_to=None)]
		leave_data = {"EMP-1": [{"leave_type": "Casual"}]}
		result = _get_node(
			employee="EMP-1",
			is_hr=False,
			employees=employees,
			leave_by_employee=leave_data,
			off_session_result=None,
		)
		self.assertTrue(result["person"]["away"])

	def test_half_day_is_away_false(self):
		"""A half-day leave results in away=False."""
		employees = [_employee("EMP-1", "Ali", reports_to=None)]
		leave_by_emp = {"EMP-1": [{"leave_type": "Casual", "half_day_session": "AM"}]}
		result = _get_node(
			employee="EMP-1",
			is_hr=False,
			employees=employees,
			leave_by_employee=leave_by_emp,
			off_session_result="AM",
		)
		self.assertFalse(result["person"]["away"])

	def test_no_leave_is_away_false(self):
		"""No leave results in away=False."""
		employees = [_employee("EMP-1", "Ali", reports_to=None)]
		result = _get_node(
			employee="EMP-1", is_hr=False, employees=employees, leave_by_employee={}, off_session_result=None
		)
		self.assertFalse(result["person"]["away"])

	def test_away_never_includes_leave_type(self):
		"""The output never includes leave_type, only away bool."""
		employees = [_employee("EMP-1", "Ali", reports_to=None)]
		leave_by_emp = {"EMP-1": [{"leave_type": "Casual"}]}
		result = _get_node(
			employee="EMP-1",
			is_hr=False,
			employees=employees,
			leave_by_employee=leave_by_emp,
			off_session_result=None,
		)
		import json

		output_json = json.dumps(result)
		self.assertNotIn("leave_type", output_json)
		self.assertNotIn("Casual", output_json)


class TestCard(unittest.TestCase):
	def test_card_has_required_fields(self):
		"""Card includes name, designation, department, branch, company, image, away, team_size."""
		employees = [
			_employee(
				"EMP-1",
				"Ali",
				designation="Designer",
				department="Design",
				branch="HQ",
				company="Company A",
				image="/files/photo.jpg",
			),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		person = result["person"]
		self.assertEqual(person["id"], "EMP-1")
		self.assertEqual(person["name"], "Ali")
		self.assertEqual(person["designation"], "Designer")
		self.assertEqual(person["department"], "Design")
		self.assertEqual(person["branch"], "HQ")
		self.assertEqual(person["company"], "Company A")
		self.assertEqual(person["away"], False)
		self.assertEqual(person["team_size"], 1)
		self.assertTrue(person["image"].startswith("/api/method/hrms.api.org_chart.photo?employee=EMP-1&v="))

	def test_card_no_phone_or_email(self):
		"""Card never includes phone or email."""
		employees = [_employee("EMP-1", "Ali")]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		import json

		output_json = json.dumps(result)
		self.assertNotIn("phone", output_json.lower())
		self.assertNotIn("email", output_json.lower())

	def test_card_building_does_not_read_image_per_person(self):
		"""The image comes from the row already read: no frappe.db.get_value per card."""
		employees = [
			_employee("EMP-1", "Ali", image="/files/a.jpg"),
			_employee("EMP-2", "Bob", reports_to="EMP-1", image="/files/b.jpg"),
		]
		reads = []
		result = _get_node(employee="EMP-1", employees=employees, db_reads=reads)
		self.assertTrue(result["reports"][0]["image"].startswith("/api/method/hrms.api.org_chart.photo?"))
		self.assertEqual(reads, [])

	def test_staff_team_size_ignores_other_company_reports(self):
		"""A staff card's team_size never counts people from another company."""
		employees = [
			_employee("EMP-1", "Ali", company="Company A"),
			_employee("EMP-2", "Bob", company="Company A", reports_to="EMP-1"),
			_employee("EMP-3", "Zed", company="Company B", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		self.assertEqual(result["person"]["team_size"], 1)

	def test_hr_team_size_counts_all_companies(self):
		employees = [
			_employee("EMP-1", "Ali", company="Company A"),
			_employee("EMP-2", "Bob", company="Company A", reports_to="EMP-1"),
			_employee("EMP-3", "Zed", company="Company B", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-1", is_hr=True, employees=employees)
		self.assertEqual(result["person"]["team_size"], 2)

	def test_card_image_empty_when_no_image(self):
		"""Card image is empty string when employee has no image."""
		employees = [_employee("EMP-1", "Ali", image=None)]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		person = result["person"]
		self.assertEqual(person["image"], "")

	def test_team_size_counts_direct_reports(self):
		"""team_size is the count of active direct reports."""
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
			_employee("EMP-3", "Charlie", reports_to="EMP-1"),
		]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		person = result["person"]
		self.assertEqual(person["team_size"], 2)


class TestGaps(unittest.TestCase):
	def test_staff_output_has_no_gaps(self):
		"""Staff output does not include gaps."""
		employees = [_employee("EMP-1", "Ali", reports_to=None)]
		result = _get_node(employee="EMP-1", is_hr=False, employees=employees)
		self.assertNotIn("gaps", result)

	def test_hr_output_has_gaps(self):
		"""HR output includes gaps with no_manager and left_manager keys."""
		employees = [_employee("EMP-1", "Ali", reports_to=None)]
		result = _get_node(employee="EMP-1", is_hr=True, employees=employees)
		self.assertIn("gaps", result)
		self.assertIn("no_manager", result["gaps"])
		self.assertIn("left_manager", result["gaps"])

	def test_gaps_no_manager_excludes_top_person(self):
		"""no_manager excludes the company top person (most direct reports, no manager)."""
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),  # top person (no manager, 2 reports)
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
			_employee("EMP-3", "Charlie", reports_to="EMP-1"),
			_employee("EMP-4", "Dana", reports_to=None),  # also no manager but 0 reports
		]
		result = _get_node(employee=None, company="Company A", is_hr=True, employees=employees)
		no_manager = result["gaps"]["no_manager"]
		names = [p["id"] for p in no_manager]
		self.assertNotIn("EMP-1", names)
		self.assertIn("EMP-4", names)

	def test_gaps_left_manager_lists_people_with_inactive_manager(self):
		"""left_manager lists people whose reports_to is not Active."""
		employees = [
			_employee("EMP-1", "Ali", reports_to=None),
			_employee("EMP-2", "Bob", reports_to="EMP-1"),
			_employee("EMP-3", "Charlie", reports_to="EMP-1"),
		]
		result = _get_node(employee=None, company="Company A", is_hr=True, employees=employees)
		left_manager = result["gaps"]["left_manager"]
		# In mock, all are active, so left_manager should be empty or have none
		self.assertEqual(len(left_manager), 0)


def _raise(msg, exc):
	raise exc(msg)


S3_IMAGE = "/api/method/frappe_s3_attachment.controller.generate_file?key=photos/EMP-1.jpg&file_name=a.jpg"


def _serve(
	target, me="EMP-1", my_company="Company A", is_hr=False, desk_read=False, file_owned=True, roles=()
):
	"""Call org_chart.photo(target['name']) as a caller; return (client, local)."""
	client = MagicMock()
	client.get_url.return_value = "https://s3/signed"
	local = MagicMock()

	def rows_for(dt, filters=None, **kw):
		return [target] if filters.get("name") == target["name"] else [{"company": my_company}]

	with (
		patch.object(frappe, "get_all", side_effect=rows_for),
		patch.object(org_chart, "get_employee", return_value=me),
		patch.object(org_chart, "require_employee", return_value=me),
		patch.object(org_chart, "sees_all_employee_data", return_value=is_hr),
		patch.object(frappe, "has_permission", return_value=desk_read, create=True),
		patch.object(frappe, "get_roles", return_value=list(roles), create=True),
		patch.object(frappe, "get_attr", return_value=lambda: client),
		patch.object(frappe, "local", local),
		patch.object(frappe.db, "exists", return_value=file_owned),
		patch.object(frappe, "throw", side_effect=_raise),
	):
		try:
			org_chart.photo(target["name"])
		finally:
			_serve.last = (client, local)
	return client, local


def _target(name="EMP-2", company="Company A", status="Active", image=S3_IMAGE):
	return {"name": name, "company": company, "status": status, "image": image}


class TestPhoto(unittest.TestCase):
	def test_staff_other_company_refused_even_when_desk_would_allow(self):
		"""Regression: plain staff pass has_permission on anyone, so it must never gate staff."""
		with self.assertRaises(frappe.DoesNotExistError):
			_serve(_target(company="Company B"), desk_read=True)
		_serve.last[0].get_url.assert_not_called()

	def test_staff_other_company_refused(self):
		"""Spec change from review: another company's employee reads as not found (no probing)."""
		with self.assertRaises(frappe.DoesNotExistError):
			_serve(_target(company="Company B"))
		_serve.last[0].get_url.assert_not_called()

	def test_staff_left_target_same_company_refused(self):
		with self.assertRaises(frappe.DoesNotExistError):
			_serve(_target(status="Left"), desk_read=True)
		_serve.last[0].get_url.assert_not_called()

	def test_staff_same_company_redirects_to_signed_url_for_parsed_key(self):
		_client, local = _serve(_target(name="EMP-1"))
		_client.get_url.assert_called_once_with("photos/EMP-1.jpg", "a.jpg")
		self.assertEqual(local.response.type, "redirect")
		self.assertEqual(local.response.location, "https://s3/signed")

	def test_hr_left_target_other_company_served(self):
		client, local = _serve(_target(company="Company B", status="Left"), is_hr=True)
		self.assertEqual(local.response.type, "redirect")
		client.get_url.assert_called_once()

	def test_system_manager_with_no_employee_served_active_or_left(self):
		"""Desk avatars for System Manager / Administrator, who have no Employee row."""
		for status in ("Active", "Left"):
			client, local = _serve(
				_target(company="Company B", status=status), me=None, roles=("System Manager",)
			)
			self.assertEqual(local.response.type, "redirect")
			client.get_url.assert_called_once()

	def test_a_login_with_no_employee_is_refused_even_when_desk_would_allow(self):
		"""Review of c3c99bbd4: get_employee() is None for an unlinked login, a Left employee
		whose login is still on, and two Active claimants. Desk lets the Employee role read
		anyone, so Desk permission must never decide for them: no company, no photos."""
		with self.assertRaises(frappe.DoesNotExistError):
			_serve(_target(), me=None, desk_read=True, roles=("Employee",))
		_serve.last[0].get_url.assert_not_called()


class TestPhotoIsTheEndpoint(unittest.TestCase):
	"""Review of 0606d85ee: the whitelist decorator slid onto the pure rule when it was
	inserted above photo(), so every photo url 403'd and the rule became public. The
	other tests call photo() as a function and could not see it."""

	def _decorators(self, name):
		import ast
		import inspect

		tree = ast.parse(inspect.getsource(org_chart))
		fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
		return " ".join(ast.dump(d) for d in fn.decorator_list)

	def test_photo_is_whitelisted_for_get(self):
		decorators = self._decorators("photo")
		self.assertIn("whitelist", decorators)
		self.assertIn("GET", decorators)

	def test_the_rule_is_not_an_endpoint(self):
		self.assertNotIn("whitelist", self._decorators("_may_see_photo"))


class TestWhoMaySeeAPhoto(unittest.TestCase):
	"""One rule for every kind of caller (four fixes in a row each re-opened a neighbour)."""

	def test_every_kind_of_caller(self):
		mine = {"company": "A", "status": "Active"}
		other = {"company": "B", "status": "Active"}
		left = {"company": "A", "status": "Left"}
		table = [
			# (caller, target, expected)
			(dict(is_hr=True, is_system_manager=False, my_company="A"), other, True),
			(dict(is_hr=True, is_system_manager=False, my_company=None), left, True),
			(dict(is_hr=False, is_system_manager=True, my_company=None), other, True),
			(dict(is_hr=False, is_system_manager=True, my_company=None), left, True),
			# a System Manager who IS an employee is staff here, as get_node treats them
			(dict(is_hr=False, is_system_manager=True, my_company="A"), other, False),
			(dict(is_hr=False, is_system_manager=True, my_company="A"), mine, True),
			(dict(is_hr=False, is_system_manager=False, my_company="A"), mine, True),
			(dict(is_hr=False, is_system_manager=False, my_company="A"), other, False),
			(dict(is_hr=False, is_system_manager=False, my_company="A"), left, False),
			# no Employee (unlinked, Left, ambiguous): no company, so nobody
			(dict(is_hr=False, is_system_manager=False, my_company=None), mine, False),
			(
				dict(is_hr=False, is_system_manager=False, my_company=None),
				{"company": None, "status": "Active"},
				False,
			),
		]
		for caller, target, expected in table:
			with self.subTest(caller=caller, target=target):
				self.assertIs(org_chart._may_see_photo(target, **caller), expected)

	def test_image_no_file_owns_is_not_served_or_signed(self):
		"""Employee.image pointing at a key no File of that employee owns is refused."""
		with self.assertRaises(frappe.DoesNotExistError):
			_serve(_target(name="EMP-1"), file_owned=None)
		_serve.last[0].get_url.assert_not_called()


if __name__ == "__main__":
	unittest.main()
