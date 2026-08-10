# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

"""Company fencing for the HR row scopes (multi-company hardening, v16).

Pure unit tests: `frappe` is mocked, so these run without a bench or site (same
runnable pattern as hrms/hr/doctype/sop_document/test_sop_document.py).

What they pin down:

  1. SOP Document and Employee Issue row scopes exclude another company's rows
     EVEN WHEN the department names collide — isolation no longer rides on
     Frappe's "Sales - WWSB" naming convention.
  2. A company-fenced HR user cannot read another company's Employee.
  3. A user with NO allow=Company User Permission is completely unaffected —
     every predicate is the pre-fence one, byte for byte.
  4. The `allow=Company` User Permission provisioning plan: only "HR (Company)"
     is fenced, group HR and everyone else are left alone, and a fenced user
     ends up with exactly one Company UP — their own.
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.overrides import company_scope, employee_hrms_scope, employee_issue_row_scope
from hrms.overrides import sop_document_row_scope as sop_scope
from hrms.utils.company_fence import (
	ACTION_FENCE,
	ACTION_SKIP,
	COMPANY_HR_ROLE,
	GROUP_HR_ROLE,
	plan_company_fence,
)

WWSB = "Wonder World Sdn Bhd"
VRFC = "Verifica FZ LLC"

# the collision the old department-only scope could not survive: same
# department name in two companies
SHARED_DEPARTMENT = "Sales"

GROUP_HR = "grouphr@example.com"
COMPANY_HR = "companyhr@example.com"
STAFF_WWSB = "staff.wwsb@example.com"
STAFF_VRFC = "staff.vrfc@example.com"
PLAIN_HR = "plainhr@example.com"

EMPLOYEES = {
	# user_id: (name, department, company, status)
	STAFF_WWSB: ("HR-EMP-001", SHARED_DEPARTMENT, WWSB, "Active"),
	STAFF_VRFC: ("HR-EMP-002", SHARED_DEPARTMENT, VRFC, "Active"),
	COMPANY_HR: ("HR-EMP-003", "People", WWSB, "Active"),
	GROUP_HR: ("HR-EMP-004", "People", WWSB, "Active"),
	PLAIN_HR: ("HR-EMP-005", "People", WWSB, "Active"),
}

# user -> allow=Company User Permission for_values
COMPANY_PERMISSIONS = {
	COMPANY_HR: [WWSB],
	# GROUP_HR / PLAIN_HR deliberately absent: no fence
}

HR_USERS = {GROUP_HR, COMPANY_HR, PLAIN_HR}


def _escape(value):
	return "'" + str(value).replace("'", "''") + "'"


def _fake_db():
	db = MagicMock()
	db.escape.side_effect = _escape

	def get_value(doctype, filters, fieldname=None, **kwargs):
		if doctype != "Employee" or not isinstance(filters, dict):
			return None
		row = EMPLOYEES.get(filters.get("user_id"))
		if not row:
			return None
		name, department, company, status = row
		if filters.get("status") and filters["status"] != status:
			return None
		values = {"name": name, "department": department, "company": company, "status": status}
		if kwargs.get("as_dict"):
			return frappe._dict({key: values.get(key) for key in fieldname})
		return values.get(fieldname)

	db.get_value.side_effect = get_value
	return db


class _Ctx:
	"""Patch the frappe surface the row scopes touch, for one session user."""

	def __init__(self, user):
		self.user = user

	def _get_all(self, doctype, filters=None, pluck=None, **kwargs):
		if doctype == "User Permission":
			return list(COMPANY_PERMISSIONS.get(filters.get("user"), []))
		if doctype == "Employee":
			rows = [
				(name, company)
				for user_id, (name, _dept, company, _status) in EMPLOYEES.items()
				if user_id == filters.get("user_id")
			]
			allowed = filters.get("company")
			if allowed:
				rows = [row for row in rows if row[1] in allowed[1]]
			return [row[0] for row in rows]
		return []

	def __enter__(self):
		self.patches = [
			patch.object(frappe, "db", _fake_db()),
			patch.object(frappe, "session", frappe._dict(user=self.user)),
			patch.object(frappe, "get_all", side_effect=self._get_all),
			patch.object(
				frappe,
				"get_roles",
				side_effect=lambda user: ["HR Manager", "Employee"] if user in HR_USERS else ["Employee"],
			),
			patch.object(employee_issue_row_scope, "get_shared", return_value=[]),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()


def _sop(company, department=SHARED_DEPARTMENT, scope="Department", published=1):
	return frappe._dict(
		name="HR-SOP-00001",
		title="Sales Playbook",
		scope=scope,
		department=department,
		company=company,
		published=published,
		pinned=0,
	)


class TestSopCompanyFence(unittest.TestCase):
	def test_query_scope_carries_an_explicit_company_predicate(self):
		with _Ctx(STAFF_WWSB):
			condition = sop_scope.get_permission_query_conditions(STAFF_WWSB)
		self.assertIn("`tabSOP Document`.`department` = 'Sales'", condition)
		self.assertIn("`tabSOP Document`.`company` = 'Wonder World Sdn Bhd'", condition)
		# blank company still means group-wide
		self.assertIn("ifnull(`tabSOP Document`.`company`, '') = ''", condition)
		self.assertNotIn(VRFC, condition)

	def test_colliding_department_name_in_another_company_is_hidden(self):
		"""The whole point: identical department names, different companies."""
		with _Ctx(STAFF_WWSB):
			self.assertFalse(sop_scope.has_permission(_sop(VRFC), "read", STAFF_WWSB))
			self.assertTrue(sop_scope.has_permission(_sop(WWSB), "read", STAFF_WWSB))

	def test_blank_company_sop_is_group_wide(self):
		with _Ctx(STAFF_VRFC):
			self.assertTrue(sop_scope.has_permission(_sop(None), "read", STAFF_VRFC))

	def test_record_visible_defaults_keep_legacy_callers_group_wide(self):
		# old 4-argument call site: no company argument, no company term
		self.assertTrue(sop_scope.record_visible(1, "Department", SHARED_DEPARTMENT, SHARED_DEPARTMENT))

	def test_company_hr_query_scope_is_fenced(self):
		with _Ctx(COMPANY_HR):
			condition = sop_scope.get_permission_query_conditions(COMPANY_HR)
		self.assertIn("'Wonder World Sdn Bhd'", condition)
		self.assertNotIn(VRFC, condition)

	def test_company_hr_cannot_read_another_companys_sop(self):
		with _Ctx(COMPANY_HR):
			self.assertFalse(sop_scope.has_permission(_sop(VRFC), "read", COMPANY_HR))
			self.assertTrue(sop_scope.has_permission(_sop(WWSB), "write", COMPANY_HR))

	def test_group_hr_is_unfenced(self):
		with _Ctx(GROUP_HR):
			self.assertEqual(sop_scope.get_permission_query_conditions(GROUP_HR), "")
			self.assertTrue(sop_scope.has_permission(_sop(VRFC), "read", GROUP_HR))


class TestEmployeeIssueCompanyFence(unittest.TestCase):
	def _issue(self, company):
		return frappe._dict(name="HR-ISS-00001", employee="HR-EMP-002", company=company)

	def test_hr_without_company_permission_is_unrestricted(self):
		with _Ctx(PLAIN_HR):
			self.assertEqual(employee_issue_row_scope.get_permission_query_conditions(PLAIN_HR), "")

	def test_company_hr_query_scope_is_fenced(self):
		with _Ctx(COMPANY_HR):
			condition = employee_issue_row_scope.get_permission_query_conditions(COMPANY_HR)
		self.assertEqual(condition, "(`tabEmployee Issue`.`company` in ('Wonder World Sdn Bhd'))")

	def test_company_hr_cannot_read_another_companys_ticket(self):
		with _Ctx(COMPANY_HR):
			self.assertFalse(employee_issue_row_scope.has_permission(self._issue(VRFC), "read", COMPANY_HR))
			self.assertTrue(employee_issue_row_scope.has_permission(self._issue(WWSB), "read", COMPANY_HR))

	def test_own_employee_lookup_is_company_filtered(self):
		"""The audited hole: get_all("Employee", {"user_id": user}) unfenced."""
		with _Ctx(COMPANY_HR), patch.object(frappe, "get_all") as get_all:
			get_all.side_effect = _Ctx(COMPANY_HR)._get_all
			employee_issue_row_scope._own_employees(COMPANY_HR)
			employee_filters = [
				call.kwargs.get("filters") for call in get_all.call_args_list if call.args[0] == "Employee"
			]
		self.assertEqual(employee_filters, [{"user_id": COMPANY_HR, "company": ("in", [WWSB])}])

	def test_unfenced_own_employee_lookup_is_unchanged(self):
		with _Ctx(STAFF_WWSB), patch.object(frappe, "get_all") as get_all:
			get_all.side_effect = _Ctx(STAFF_WWSB)._get_all
			employee_issue_row_scope._own_employees(STAFF_WWSB)
			employee_filters = [
				call.kwargs.get("filters") for call in get_all.call_args_list if call.args[0] == "Employee"
			]
		self.assertEqual(employee_filters, [{"user_id": STAFF_WWSB}])

	def test_staff_scope_is_unchanged_for_unfenced_users(self):
		with _Ctx(STAFF_WWSB):
			condition = employee_issue_row_scope.get_permission_query_conditions(STAFF_WWSB)
		self.assertEqual(condition, "(`tabEmployee Issue`.`employee` in ('HR-EMP-001'))")


class TestEmployeeCompanyFence(unittest.TestCase):
	def _employee(self, company):
		return frappe._dict(name="HR-EMP-002", company=company)

	def test_company_hr_cannot_read_another_companys_employee(self):
		with _Ctx(COMPANY_HR):
			self.assertFalse(company_scope.employee_has_permission(self._employee(VRFC), "read", COMPANY_HR))
			self.assertTrue(company_scope.employee_has_permission(self._employee(WWSB), "read", COMPANY_HR))

	def test_company_hr_employee_list_is_fenced(self):
		with _Ctx(COMPANY_HR):
			self.assertEqual(
				company_scope.employee_query_conditions(COMPANY_HR),
				"(`tabEmployee`.`company` in ('Wonder World Sdn Bhd'))",
			)

	def test_user_without_company_permission_is_untouched(self):
		with _Ctx(PLAIN_HR):
			self.assertEqual(company_scope.employee_query_conditions(PLAIN_HR), "")
			self.assertTrue(company_scope.employee_has_permission(self._employee(VRFC), "read", PLAIN_HR))

	def test_administrator_is_never_fenced(self):
		with _Ctx("Administrator"):
			self.assertEqual(company_scope.allowed_companies("Administrator"), [])
			self.assertEqual(company_scope.employee_query_conditions("Administrator"), "")


class TestPlanCompanyFence(unittest.TestCase):
	def test_company_hr_gets_their_own_company(self):
		self.assertEqual(plan_company_fence([COMPANY_HR_ROLE], WWSB, []), (ACTION_FENCE, WWSB, []))

	def test_existing_correct_permission_is_left_alone(self):
		self.assertEqual(plan_company_fence([COMPANY_HR_ROLE], WWSB, [WWSB]), (ACTION_FENCE, None, []))

	def test_stale_company_permission_is_dropped(self):
		self.assertEqual(
			plan_company_fence([COMPANY_HR_ROLE], WWSB, [VRFC]),
			(ACTION_FENCE, WWSB, [VRFC]),
		)

	def test_group_hr_is_never_fenced(self):
		self.assertEqual(plan_company_fence([GROUP_HR_ROLE], WWSB, []), (ACTION_SKIP, None, []))
		# group wins when a user somehow holds both
		self.assertEqual(
			plan_company_fence([GROUP_HR_ROLE, COMPANY_HR_ROLE], WWSB, [VRFC]),
			(ACTION_SKIP, None, []),
		)

	def test_user_with_neither_role_is_untouched(self):
		self.assertEqual(plan_company_fence(["HR Manager"], WWSB, [VRFC]), (ACTION_SKIP, None, []))

	def test_employee_without_company_is_untouched(self):
		self.assertEqual(plan_company_fence([COMPANY_HR_ROLE], None, []), (ACTION_SKIP, None, []))


class TestSyncCompanyUserPermission(unittest.TestCase):
	def _run(self, roles, company, existing):
		doc = frappe._dict(name="HR-EMP-003", user_id=COMPANY_HR, company=company)
		inserted = MagicMock()
		inserted.update = MagicMock()
		inserted.flags = frappe._dict()

		with (
			patch.object(
				frappe,
				"get_all",
				return_value=[frappe._dict(name=f"UP-{c}", for_value=c) for c in existing],
			),
			patch.object(frappe, "get_roles", return_value=roles),
			patch.object(frappe, "new_doc", return_value=inserted),
			patch.object(frappe, "delete_doc") as delete_doc,
			patch.object(frappe, "clear_cache"),
		):
			employee_hrms_scope.sync_company_user_permission(doc, COMPANY_HR)
		return inserted, delete_doc

	def test_fenced_user_gets_one_company_permission(self):
		inserted, delete_doc = self._run([COMPANY_HR_ROLE], WWSB, [])
		inserted.update.assert_called_once_with(
			{
				"user": COMPANY_HR,
				"allow": "Company",
				"for_value": WWSB,
				"apply_to_all_doctypes": 1,
			}
		)
		inserted.insert.assert_called_once()
		delete_doc.assert_not_called()

	def test_stale_permission_is_deleted_and_replaced(self):
		inserted, delete_doc = self._run([COMPANY_HR_ROLE], WWSB, [VRFC])
		delete_doc.assert_called_once_with("User Permission", f"UP-{VRFC}", ignore_permissions=True)
		inserted.insert.assert_called_once()

	def test_user_without_the_role_is_never_touched(self):
		inserted, delete_doc = self._run(["HR Manager"], WWSB, [VRFC])
		inserted.insert.assert_not_called()
		delete_doc.assert_not_called()

	def test_group_hr_keeps_every_company(self):
		inserted, delete_doc = self._run([GROUP_HR_ROLE, "HR Manager"], WWSB, [])
		inserted.insert.assert_not_called()
		delete_doc.assert_not_called()


class TestFenceRolesAreWiredForFreshInstallAndMigrate(unittest.TestCase):
	def test_after_install_creates_the_roles(self):
		from hrms import setup

		self.assertIn("create_company_fence_roles", setup.after_install.__code__.co_names)

	def test_patch_is_registered(self):
		import pathlib

		patches = (pathlib.Path(__file__).resolve().parents[1] / "patches.txt").read_text(encoding="utf-8")
		self.assertIn("hrms.patches.v16_0.create_company_fence_roles", patches)

	def test_roles_are_created_idempotently(self):
		from hrms.utils.company_fence import COMPANY_FENCE_ROLES, create_company_fence_roles

		db = MagicMock()
		db.exists.return_value = False
		with patch.object(frappe, "db", db), patch.object(frappe, "get_doc") as get_doc:
			created = create_company_fence_roles()
		self.assertEqual(created, list(COMPANY_FENCE_ROLES))
		self.assertEqual(get_doc.call_count, len(COMPANY_FENCE_ROLES))

		db.exists.return_value = True
		with patch.object(frappe, "db", db), patch.object(frappe, "get_doc") as get_doc:
			self.assertEqual(create_company_fence_roles(), [])
		get_doc.assert_not_called()

	def test_fence_roles_carry_no_docperm_rows(self):
		"""They are fences, not permission carriers — nothing to validate, so
		they cannot reintroduce the cancel-without-submit fresh-install abort."""
		import ast
		import pathlib

		hrms_root = pathlib.Path(__file__).resolve().parents[1]
		tree = ast.parse((hrms_root / "utils/company_fence.py").read_text(encoding="utf-8"))
		# docstrings talk about the permission tables; the CODE must not touch them
		code = ast.unparse(
			ast.Module(body=[node for node in tree.body if not isinstance(node, ast.Expr)], type_ignores=[])
		)
		for forbidden in ("add_permission", "update_permission_property", "DocPerm"):
			self.assertNotIn(forbidden, code)


if __name__ == "__main__":
	unittest.main()
