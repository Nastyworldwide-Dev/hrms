"""Who can see the HR Issue Board — and who SHOULDN'T.

The board (and its "see everyone's tickets" data scope) is gated on one rule:
is_hr_operator = holds 'HR User' or 'HR Manager' (or Administrator). A supervisor
/ team-leader / approver is NONE of these by role — approver authority is a data
relationship (reports_to / named approver), not a role. So any NON-HR person who
can see the board is holding an HR role by mistake.

This lists every enabled user the board is open to, flags the suspicious ones
(they manage people via reports_to but were also given an HR role), so you can
strip the role from whoever shouldn't have it.

  cd ~/verify-bench/sites
  ../env/bin/python -c "import frappe; frappe.init(site='SITE'); frappe.connect(); \
      exec(open('<repo>/docs/glass/runbook/who-can-see-the-issue-board.py').read())"
"""

import frappe

from hrms.hr.utils import HR_SEE_ALL_ROLES, is_hr_operator

holders = set()
for role in HR_SEE_ALL_ROLES:
	holders |= set(frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"))
holders.discard("Administrator")

print(f"\nBoard is gated on: {sorted(HR_SEE_ALL_ROLES)} (+ Administrator)")
print(f"{len(holders)} non-admin user(s) can see the HR Issue Board:\n")
print(f"{'user':40} {'enabled':8} {'HR roles held':22} {'manages_people':14} flag")
print("-" * 100)
for u in sorted(holders):
	enabled = frappe.db.get_value("User", u, "enabled")
	hr_roles = [r for r in frappe.get_roles(u) if r in HR_SEE_ALL_ROLES]
	# does this person supervise anyone? (reports_to points at their Employee)
	emp = frappe.db.get_value("Employee", {"user_id": u}, "name")
	manages = frappe.db.count("Employee", {"reports_to": emp}) if emp else 0
	# a real HR operator manages HR content; a team-leader who ALSO has an HR role
	# is the misconfig this script exists to surface
	flag = "SUSPECT: team-leader with an HR role?" if manages else ""
	print(f"{u:40} {bool(enabled)!s:8} {','.join(hr_roles):22} {manages:<14} {flag}")
print()
