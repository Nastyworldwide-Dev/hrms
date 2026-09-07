"""Un-fence HR users who carry the self `allow=Employee` User Permission.

THE SYMPTOM: an HR person opens the Employee list and sees one row — herself —
behind a "Restrictions: ID = <her employee>" dialog. Every per-employee report
and list behaves the same. "With more than the HR role I still cannot view
employees."

WHAT IT IS: the User Permission ERPNext creates for every employee-user
(`Employee.create_user_permission`, default on), there so self-service staff
see only their own rows. On a holder of HR User / HR Manager it fences the
Employee doctype itself to that one record. Measured: 1 of 15 with the row,
15 of 15 without. A colleague with the same roles but no such row sees
everyone — which is why it looked like a server glitch and is not.

The hook (hrms/overrides/employee_hrms_scope.py) now removes it on every
Employee and User save. This patch is the one-off for everyone provisioned
before that. It deletes only allow=Employee rows of HR-sight users; the
allow=Company fence rows and every self-service user's own fence are untouched.
Idempotent — a second run finds nothing.
"""

import frappe

from hrms.hr.utils import HR_SEE_ALL_ROLES
from hrms.overrides.employee_hrms_scope import drop_self_employee_permission_for_hr


def execute():
	hr_users = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "role": ["in", sorted(HR_SEE_ALL_ROLES)]},
		pluck="parent",
		distinct=True,
	)
	dropped = {}
	for user in sorted(set(hr_users)):
		frappe.clear_cache(user=user)
		rows = drop_self_employee_permission_for_hr(user)
		if rows:
			dropped[user] = rows
	frappe.logger("hrms").info(
		"[patch] drop_self_employee_permission_for_hr_users: %d HR user(s) checked, %d un-fenced: %s",
		len(set(hr_users)),
		len(dropped),
		dropped,
	)
