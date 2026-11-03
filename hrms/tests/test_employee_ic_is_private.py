"""An employee's IC number: HR sees everyone's, a person sees only their own
(owner, 3 Nov 2026).

* The field is `ic_number` on Employee, on the Personal Details tab, at
  permlevel 2: a level nobody else's rules touch. HR (HR User, HR Manager)
  gets read and write at level 2; no staff role gets any row there.
* So a staff user who can open someone else's Employee in Desk sees no IC: Frappe
  strips a field the reader has no level for (`apply_fieldlevel_read_permissions`).
* Their OWN IC comes back through `Employee.onload`, which Frappe runs before
  that strip: it is put in `__onload` only when the record is the reader's own,
  and the form script shows it read-only on their own profile.
* HR sees and edits every IC through the level-2 rows.

Rules lifted by AST so this runs without a bench:

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_employee_ic_is_private.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

HRMS = pathlib.Path(__file__).resolve().parent.parent
MODULE = HRMS / "utils" / "employee_ic.py"


def _lift(name, namespace):
	tree = ast.parse(MODULE.read_text())
	fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(MODULE), "exec"), namespace)
	return namespace[name]


def _const(name):
	tree = ast.parse(MODULE.read_text())
	for node in tree.body:
		if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
			return ast.literal_eval(node.value)
	raise AssertionError(f"{name} missing")


class TestTheFieldIsLockedAtItsOwnLevel(unittest.TestCase):
	def test_the_field_sits_at_permlevel_2_on_personal_details(self):
		ns = {"_": lambda s: s}
		fields = _lift("get_ic_fields", ns)()["Employee"]
		ic = next(f for f in fields if f["fieldname"] == "ic_number")
		self.assertEqual(ic["permlevel"], 2)
		self.assertEqual(ic["insert_after"], "passport_number")

	def test_only_hr_roles_get_the_level(self):
		self.assertEqual(set(_const("IC_ROLES")), {"HR User", "HR Manager"})


class TestOnlyYourOwnICComesBack(unittest.TestCase):
	def run_onload(self, user, user_id, ic="900101-14-5678"):
		frappe = MagicMock()
		frappe.session.user = user
		frappe.db.get_value.return_value = ic
		ns = {
			"frappe": frappe,
			"logger": MagicMock(),
			"FIELD": "ic_number",
			"normalize_login": lambda v: (v or "").strip().lower(),
		}
		share = _lift("share_own_ic", ns)
		onload = {}
		doc = SimpleNamespace(
			name="HR-EMP-00001",
			user_id=user_id,
			get=lambda f: {"user_id": user_id, "additional_login_email": None}.get(f),
			set_onload=lambda k, v: onload.__setitem__(k, v),
		)
		share(doc)
		return onload

	def test_your_own_record_carries_your_ic(self):
		self.assertEqual(self.run_onload("siti@x.com", "Siti@X.com")["own_ic_number"], "900101-14-5678")

	def test_someone_elses_record_carries_nothing(self):
		self.assertNotIn("own_ic_number", self.run_onload("ali@x.com", "siti@x.com"))

	def test_a_record_with_no_login_carries_nothing(self):
		self.assertNotIn("own_ic_number", self.run_onload("ali@x.com", None))


class TestTheGuardRestoresTheLevel(unittest.TestCase):
	def test_the_general_guard_leaves_level_2_alone(self):
		# permlevel_guard grants every restricted level to all HR_ROLES, System
		# Manager included; the IC level must not be one of them.
		guard = (HRMS / "utils" / "permlevel_guard.py").read_text()
		self.assertIn('OWNED_ELSEWHERE = frozenset({("Employee", 2)})', guard)
		self.assertIn("return guarded_only(needed) - OWNED_ELSEWHERE", guard)

	def test_system_manager_is_not_given_the_ic(self):
		self.assertNotIn("System Manager", _const("IC_ROLES"))

	def test_after_migrate_runs_the_ic_rows(self):
		hooks = (HRMS / "hooks.py").read_text()
		self.assertIn("hrms.utils.employee_ic.after_migrate", hooks)

	def test_the_onload_is_wired(self):
		hooks = (HRMS / "hooks.py").read_text()
		self.assertIn("hrms.utils.employee_ic.share_own_ic", hooks)


if __name__ == "__main__":
	unittest.main()
