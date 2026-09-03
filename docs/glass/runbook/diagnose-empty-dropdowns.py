"""Why is a 'type' dropdown empty in the Nadi PWA?

Run on ANY site as an employee and it answers, per master/config doctype that
feeds a PWA dropdown, the only two questions that make one empty:

  1. is the doctype MIGRATED (present in the DB schema at all)?   -> if not,
     `bench --site <site> migrate` was not run / a fixture import was skipped.
  2. does it hold any RECORDS the caller may read?                -> if zero,
     the dropdown is correctly empty: it is config absence, not a code defect.

Usage:
  cd ~/verify-bench/sites
  ../env/bin/python -c "import frappe; frappe.init(site='SITE'); frappe.connect(); \
      exec(open('<repo>/docs/glass/runbook/diagnose-empty-dropdowns.py').read())"
  # optional: set AS_USER=someone@company.com to test a specific employee's view
"""

import os

import frappe

# master/config doctypes that populate a "type"/lookup dropdown somewhere in the PWA
FEEDS = [
	"Leave Type",
	"Expense Claim Type",
	"Shift Type",
	"Shift Location",
	"Overtime Type",
	"Holiday List",
	"Leave Period",
	"Leave Policy",
	"Department",
	"Designation",
	"Cost Center",
	"Mode of Payment",
	"Branch",
	"Location",
	"Project",
]

who = os.environ.get("AS_USER")
if who:
	frappe.set_user(who)

print(f"\nsite={frappe.local.site}  user={frappe.session.user}")
print(f"{'doctype':28} {'migrated':9} {'records':>8}  verdict")
print("-" * 64)
for dt in FEEDS:
	migrated = bool(frappe.db.exists("DocType", dt)) and frappe.db.table_exists(dt)
	if not migrated:
		print(f"{dt:28} {'NO':9} {'-':>8}  RUN MIGRATE — doctype not in DB")
		continue
	try:
		n = len(frappe.get_list(dt, limit_page_length=0))
		readable = True
	except frappe.PermissionError:
		n, readable = 0, False
	verdict = (
		"empty: NO PERMISSION (by design for employee)"
		if not readable
		else "empty: NO RECORDS — set up this master"
		if n == 0
		else "ok"
	)
	print(f"{dt:28} {'yes':9} {n:>8}  {verdict}")
print()
