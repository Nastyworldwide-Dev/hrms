# FAMILY — an HR user's Desk roles changed with nobody editing the User

CLASS: a needless programmatic User save. Frappe re-derives a User's roles
from its Role Profile on EVERY save (`User.populate_role_profile_roles`,
frappe/core/doctype/user/user.py:263): roles not in the profile are dropped.
So any code path that saves a User for no reason silently resets hand-granted
roles. Reported 21 Sep 2026 (Amy, HR, verifica-live).

Call sites the machine lists for update_approver_role / add_roles:

* hrms/hooks.py:386 Employee.on_update → update_approver_role — same-root:
  saved the approver's User on EVERY Employee save naming them (add_roles
  saves unconditionally). Now reads get_roles first; saves only when a role
  is missing.
* hrms/overrides/employee_master.py:135 ensure_employee_role → add_roles —
  not-affected: already guarded by `"Employee" in frappe.get_roles(user)`
  before the save.
* hrms/overrides/employee_master.py:173 (this function) — same-root, fixed here.
* hrms/sync/runner.py:745 _reconcile_user_enabled → user.save — not-affected:
  saves only when `enabled` actually differs; a legitimate change.
* erpnext Employee.update_user (erpnext/setup/doctype/employee/employee.py:309)
  — not-affected — upstream: saves the linked User on that employee's OWN
  record. By design; the Role Profile is the truth for such a User.

Site note (config, not code): a User carrying a Role Profile keeps only that
profile's roles across any save. Roles Amy needs beyond the "HR" profile go
INTO the profile (or the profile comes off her User). The User's Version log
names the save that reset her: modified_by Administrator = programmatic.

Regression test: hrms/tests/test_approver_role_grant_is_idempotent.py
