"""Audit seed — realistic content so CONTENT-class bugs are visible.

Long Malaysian names, a 40-row list, zero-row lists, long IDs, wide currency.
Runs against verify-bench/fresh.local only. Idempotent-ish: re-running skips
what exists. Credential comes from the AUDIT_PW environment variable.
"""

import json, datetime, os
import frappe
from frappe.utils import add_days, nowdate, getdate

log = []


def step(name, fn):
	try:
		r = fn()
		frappe.db.commit()
		log.append(f"OK   {name}: {r}")
	except Exception as e:
		log.append(f"FAIL {name}: {type(e).__name__}: {str(e)[:160]}")


COMPANY = "_Test Company"
EMAIL = "nurul.aisyah@nastyworldwide.com"
SECRET = os.environ["AUDIT_PW"]
FULLNAME_FIRST = "Nurul Aisyah"
FULLNAME_LAST = "binti Abdul Rahman"
EMP = None


# ---------------------------------------------------------------- holiday list
def mk_holiday_list():
	name = "Audit Holiday List 2026"
	if frappe.db.exists("Holiday List", name):
		return name
	hl = frappe.get_doc(
		{
			"doctype": "Holiday List",
			"holiday_list_name": name,
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"holidays": [
				{"holiday_date": "2026-01-01", "description": "New Year's Day"},
				{"holiday_date": "2026-02-17", "description": "Chinese New Year"},
				{"holiday_date": "2026-03-21", "description": "Hari Raya Aidilfitri"},
				{"holiday_date": "2026-05-01", "description": "Labour Day"},
				{"holiday_date": "2026-08-31", "description": "Hari Kebangsaan Malaysia"},
				{"holiday_date": "2026-09-16", "description": "Hari Malaysia"},
				{"holiday_date": "2026-11-08", "description": "Deepavali"},
				{"holiday_date": "2026-12-25", "description": "Christmas Day"},
			],
		}
	)
	hl.insert(ignore_permissions=True)
	return name


# ---------------------------------------------------------------------- user
def mk_user():
	if not frappe.db.exists("User", EMAIL):
		u = frappe.get_doc(
			{
				"doctype": "User",
				"email": EMAIL,
				"first_name": FULLNAME_FIRST,
				"last_name": FULLNAME_LAST,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		u.insert(ignore_permissions=True)
	u = frappe.get_doc("User", EMAIL)
	u.new_password = SECRET
	for r in ["Employee", "Employee Self Service"]:
		if frappe.db.exists("Role", r) and r not in [d.role for d in u.roles]:
			u.append("roles", {"role": r})
	u.save(ignore_permissions=True)
	return EMAIL


# ------------------------------------------------------------------ employee
def mk_employee():
	global EMP
	existing = frappe.db.get_value("Employee", {"user_id": EMAIL}, "name")
	if existing:
		EMP = existing
		return existing
	e = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": FULLNAME_FIRST,
			"last_name": FULLNAME_LAST,
			"gender": "Female",
			"date_of_birth": "1994-07-12",
			"date_of_joining": "2023-03-01",
			"company": COMPANY,
			"user_id": EMAIL,
			"status": "Active",
			"holiday_list": "Audit Holiday List 2026",
			"department": frappe.db.get_value("Department", {"company": COMPANY}, "name"),
		}
	)
	e.insert(ignore_permissions=True)
	EMP = e.name
	return e.name


# -------------------------------------------------------------- leave setup
def mk_leave_alloc():
	made = []
	for lt, days in [("Casual Leave", 12), ("Sick Leave", 14), ("Privilege Leave", 16)]:
		if not frappe.db.exists("Leave Type", lt):
			continue
		if frappe.db.exists("Leave Allocation", {"employee": EMP, "leave_type": lt, "docstatus": 1}):
			continue
		la = frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": EMP,
				"leave_type": lt,
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"new_leaves_allocated": days,
				"company": COMPANY,
				"carry_forward": 0,
			}
		)
		la.insert(ignore_permissions=True)
		la.submit()
		made.append(f"{lt}:{days}")
	return made


# ---------------------------------------------- 40 leave applications (list stress)
def mk_leave_apps():
	n = frappe.db.count("Leave Application", {"employee": EMP})
	if n >= 40:
		return f"already {n}"
	reasons = [
		"Family matters requiring attention at home in Kuala Terengganu over the long weekend",
		"Medical appointment",
		"Annual family trip",
		"Fever",
		"Attending my sister's wedding reception in Kota Bharu, Kelantan",
	]
	made = 0
	d = getdate("2026-01-05")
	for i in range(40 - n):
		lt = ["Casual Leave", "Sick Leave", "Privilege Leave"][i % 3]
		if not frappe.db.exists("Leave Type", lt):
			continue
		start = add_days(d, i * 4)
		try:
			la = frappe.get_doc(
				{
					"doctype": "Leave Application",
					"employee": EMP,
					"leave_type": lt,
					"from_date": start,
					"to_date": start,
					"half_day": 0,
					"description": reasons[i % len(reasons)],
					"company": COMPANY,
					"status": "Open" if i % 4 == 0 else ("Approved" if i % 4 == 1 else "Rejected"),
					"leave_approver": "Administrator",
				}
			)
			la.flags.ignore_validate = True
			la.flags.ignore_mandatory = True
			la.insert(ignore_permissions=True, ignore_mandatory=True)
			made += 1
		except Exception:
			continue
	return f"made {made}"


# ------------------------------------------------------- expense claims (wide currency)
def mk_expense_claims():
	if frappe.db.count("Expense Claim", {"employee": EMP}):
		return "exists"
	ect = frappe.db.get_value("Expense Claim Type", {}, "name")
	if not ect:
		return "no expense claim type"
	made = 0
	for amt, desc in [
		(
			128450.75,
			"Regional offsite — flights, accommodation and per diem for the Kuala Lumpur leadership summit",
		),
		(89.90, "Grab to client site"),
		(1250000.00, "Annual software licence renewal"),
	]:
		try:
			ec = frappe.get_doc(
				{
					"doctype": "Expense Claim",
					"employee": EMP,
					"company": COMPANY,
					"posting_date": nowdate(),
					"approval_status": "Draft",
					"expenses": [
						{
							"expense_date": nowdate(),
							"expense_type": ect,
							"description": desc,
							"amount": amt,
							"sanctioned_amount": amt,
						}
					],
				}
			)
			ec.flags.ignore_mandatory = True
			ec.insert(ignore_permissions=True, ignore_mandatory=True)
			made += 1
		except Exception:
			continue
	return f"made {made}"


# ------------------------------------------------------------------- checkins
def mk_checkins():
	if frappe.db.count("Employee Checkin", {"employee": EMP}):
		return "exists"
	made = 0
	base = datetime.datetime(2026, 8, 20, 8, 58)
	for i, lt in enumerate(["IN", "OUT", "IN", "OUT", "IN"]):
		try:
			frappe.get_doc(
				{
					"doctype": "Employee Checkin",
					"employee": EMP,
					"time": base - datetime.timedelta(hours=24 * (i // 2), minutes=-(i * 517)),
					"log_type": lt,
				}
			).insert(ignore_permissions=True)
			made += 1
		except Exception:
			continue
	return f"made {made}"


# -------------------------------------------------------------- shift + requests
def mk_shift():
	st = "Audit Morning Shift"
	if not frappe.db.exists("Shift Type", st):
		frappe.get_doc(
			{
				"doctype": "Shift Type",
				"name": st,
				"start_time": "09:00:00",
				"end_time": "18:00:00",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Shift Assignment", {"employee": EMP, "docstatus": 1}):
		sa = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": EMP,
				"shift_type": st,
				"start_date": "2026-08-01",
				"end_date": "2026-12-31",
				"company": COMPANY,
				"status": "Active",
			}
		)
		sa.flags.ignore_mandatory = True
		sa.insert(ignore_permissions=True, ignore_mandatory=True)
		sa.submit()
	return st


def mk_attendance_requests():
	if frappe.db.count("Attendance Request", {"employee": EMP}):
		return "exists"
	made = 0
	for i, reason in enumerate(
		[
			"Work From Home",
			"On Duty",
		]
	):
		try:
			ar = frappe.get_doc(
				{
					"doctype": "Attendance Request",
					"employee": EMP,
					"company": COMPANY,
					"from_date": add_days(nowdate(), -(i + 3)),
					"to_date": add_days(nowdate(), -(i + 3)),
					"reason": reason,
					"explanation": "Client workshop ran past the last LRT service from KL Sentral, worked remotely the following morning",
				}
			)
			ar.flags.ignore_mandatory = True
			ar.insert(ignore_permissions=True, ignore_mandatory=True)
			made += 1
		except Exception:
			continue
	return f"made {made}"


# ----------------------------------------------------------- employee issues
def mk_issues():
	if not frappe.db.exists("DocType", "Employee Issue"):
		return "no doctype"
	if frappe.db.count("Employee Issue", {"employee": EMP}):
		return "exists"
	made = 0
	for subj in [
		"Payslip for July 2026 shows an EPF deduction that does not match my statement",
		"Access card not working",
	]:
		try:
			d = frappe.get_doc(
				{
					"doctype": "Employee Issue",
					"employee": EMP,
					"subject": subj,
					"description": subj,
					"company": COMPANY,
				}
			)
			d.flags.ignore_mandatory = True
			d.insert(ignore_permissions=True, ignore_mandatory=True)
			made += 1
		except Exception:
			continue
	return f"made {made}"


# ------------------------------------------------------------------ OT requests
def mk_ot():
	if not frappe.db.exists("DocType", "OT Request"):
		return "no doctype"
	if frappe.db.count("OT Request", {"employee": EMP}):
		return "exists"
	try:
		d = frappe.get_doc(
			{
				"doctype": "OT Request",
				"employee": EMP,
				"company": COMPANY,
				"date": add_days(nowdate(), -2),
				"hours": 3.5,
				"reason": "Month-end close — payroll cut-off extended past the scheduled shift end",
			}
		)
		d.flags.ignore_mandatory = True
		d.insert(ignore_permissions=True, ignore_mandatory=True)
		return "made 1"
	except Exception as e:
		return f"skip {str(e)[:80]}"


step("holiday list", mk_holiday_list)
step("user", mk_user)
step("employee", mk_employee)
step("leave allocation", mk_leave_alloc)
step("leave applications", mk_leave_apps)
step("expense claims", mk_expense_claims)
step("checkins", mk_checkins)
step("shift", mk_shift)
step("attendance requests", mk_attendance_requests)
step("employee issues", mk_issues)
step("ot requests", mk_ot)

frappe.db.commit()
print("SEEDRESULT " + json.dumps({"employee": EMP, "log": log}))
