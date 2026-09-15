"""Lifecycle probe for every request type the Nadi PWA files.

Walks each doctype the way the PWA does — the employee creates it (PWA payload
shape: no company, no posting_date), the approver / HR / a stranger look at it,
the approver decides it through the controller path hrms.api.approval uses
(set the decision field, submit; routed approvers run elevated), HR / the
approver / the employee try to cancel it (approved_request_guard), and the
downstream rows are read back (Attendance, leave balance, Replacement Leave
allocation, Shift Assignment, GL, check-in flags, PWA Notifications).

Every step runs in its own try/except and lands in one row:

    doctype | step | persona | result

`result` starts with OK / REFUSED (clean ValidationError or PermissionError
with a plain message) / MANDATORY (a MandatoryError — the PWA payload is
short a field) / ERROR (anything else: a traceback the user would see) /
WRONG (a silent wrong state, checked against the owner rulings).

Run on a bench site, from `bench --site <site> console`:

    import sys, hrms, frappe
    WT = "/path/to/worktree"
    hrms.__path__.insert(0, WT + "/hrms")
    for k in [k for k in list(sys.modules) if k.startswith("hrms.")]: del sys.modules[k]
    frappe.controllers = {}
    exec(open(WT + "/hrms/tests/probes/lifecycle_probe.py").read(), globals())
    run("/tmp/lifecycle_probe.md")

Everything it creates sits under a savepoint and is rolled back at the end;
nothing is committed. Fixture names all start with `lp_` / `LP `.
"""

import traceback
from datetime import timedelta

import frappe
from frappe.utils import add_days, get_datetime, getdate, nowdate

COMPANY = "_Test Company"
OTHER_COMPANY = "_Test Company 1"
SAVEPOINT = "lifecycle_probe"
INSTANCE = "test-sync-source"

ROWS: list[tuple[str, str, str, str]] = []

# The decision field per doctype — the same table hrms.api.approval.decide uses.
DECIDE = {
	"Leave Application": ("status", "Open"),
	"Shift Request": ("status", "Draft"),
	"Expense Claim": ("approval_status", "Draft"),
	"OT Request": ("status", "Open"),
	"Attendance Request": ("status", "Open"),
	"Replacement Leave Claim": ("status", "Open"),
}


# --------------------------------------------------------------------------- #
# recording
# --------------------------------------------------------------------------- #
def _clean(exc) -> bool:
	return isinstance(exc, frappe.ValidationError | frappe.PermissionError)


def _msg(exc) -> str:
	text = str(exc) or exc.__class__.__name__
	text = frappe.utils.strip_html(text) if hasattr(frappe.utils, "strip_html") else text
	return " ".join(text.split())[:140]


def record(doctype, step, persona, result):
	ROWS.append((doctype, step, persona, result))


def step(doctype, name, persona, fn, expect=None):
	"""Run one step; classify its outcome. `expect` is a callable on the
	returned value that yields None when the state is right, else a WRONG text."""
	# One savepoint per step: a web request rolls the whole transaction back
	# when a controller throws, so a half-written row (docstatus flipped, then
	# on_submit failed) must not leak into the next step here either.
	sp = f"lp_step_{len(ROWS)}"
	frappe.db.savepoint(sp)
	try:
		value = fn()
	except frappe.MandatoryError as exc:
		frappe.db.rollback(save_point=sp)
		record(doctype, name, persona, f"MANDATORY {_msg(exc)}")
		return None
	except Exception as exc:
		frappe.db.rollback(save_point=sp)
		frappe.set_user("Administrator")
		kind = "REFUSED" if _clean(exc) else "ERROR"
		record(doctype, name, persona, f"{kind} {exc.__class__.__name__}: {_msg(exc)}")
		return None
	wrong = expect(value) if expect else None
	record(doctype, name, persona, f"WRONG {wrong}" if wrong else f"OK {value if value is not None else ''}")
	return value


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _user(email, first, roles=()):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": first, "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	doc = frappe.get_doc("User", email)
	doc.add_roles(*roles)
	return email


def _employee(email, company=COMPANY, **extra):
	doc = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": email.split("@")[0],
			"company": company,
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2020-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name"),
			"status": "Active",
			"user_id": email,
			**extra,
		}
	)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc.name


def _holiday_list():
	name = "LP Weekends 2026"
	if frappe.db.exists("Holiday List", name):
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Holiday List",
			"holiday_list_name": name,
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
		}
	)
	day = getdate("2026-01-01")
	while day <= getdate("2026-12-31"):
		if day.weekday() >= 5:
			doc.append("holidays", {"holiday_date": day, "description": day.strftime("%A"), "weekly_off": 1})
		day = add_days(day, 1)
	doc.insert(ignore_permissions=True)
	return name


def _assign_holiday_list(employee, holiday_list):
	"""This fork resolves calendars through a submitted Holiday List Assignment
	(hrms.utils.holiday_list.get_holiday_list_for_employee), not Employee.holiday_list."""
	doc = frappe.get_doc(
		{
			"doctype": "Holiday List Assignment",
			"applicable_for": "Employee",
			"assigned_to": employee,
			"holiday_list": holiday_list,
			"from_date": "2026-01-01",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def _shift(name, start, end):
	if frappe.db.exists("Shift Type", name):
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"__newname": name,
			"start_time": start,
			"end_time": end,
			"enable_auto_attendance": 0,
			"enable_overtime": 1,
			"minimum_overtime_minutes": 0,
		}
	)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return name


def _assign_shift(employee, shift, start, end=None):
	doc = frappe.get_doc(
		{
			"doctype": "Shift Assignment",
			"employee": employee,
			"company": frappe.db.get_value("Employee", employee, "company"),
			"shift_type": shift,
			"start_date": start,
			"end_date": end,
			"status": "Active",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def _leave_type(name, **extra):
	if not frappe.db.exists("Leave Type", name):
		frappe.get_doc({"doctype": "Leave Type", "leave_type_name": name, **extra}).insert(
			ignore_permissions=True
		)
	return name


def _allocate(employee, leave_type, days, from_date, to_date):
	doc = frappe.get_doc(
		{
			"doctype": "Leave Allocation",
			"employee": employee,
			"leave_type": leave_type,
			"from_date": from_date,
			"to_date": to_date,
			"new_leaves_allocated": days,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def _attendance(employee, date, status, shift=None):
	doc = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": date,
			"status": status,
			"company": frappe.db.get_value("Employee", employee, "company"),
			"shift": shift,
		}
	)
	doc.flags.ignore_validate = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def _punch(employee, when, log_type, **flags):
	doc = frappe.get_doc(
		{"doctype": "Employee Checkin", "employee": employee, "log_type": log_type, "time": when}
	)
	doc.flags.ignore_permissions = True
	for k, v in flags.items():
		setattr(doc, k, v)
	doc.insert(ignore_permissions=True)
	return doc.name


def _notified(doctype, name):
	rows = frappe.get_all(
		"PWA Notification",
		filters={"reference_document_type": doctype, "reference_document_name": name},
		fields=["to_user"],
		order_by="creation asc",
	)
	return sorted({r.to_user.split("@")[0] for r in rows})


def _list_sees(doctype, name, user):
	frappe.set_user(user)
	try:
		return bool(frappe.get_list(doctype, filters={"name": name}, pluck="name"))
	finally:
		frappe.set_user("Administrator")


def _read_allowed(doctype, name, user):
	return bool(frappe.has_permission(doctype, "read", doc=frappe.get_doc(doctype, name), user=user))


def _visibility(doctype, name, users: dict):
	"""One row per persona: list + form read, as the PWA's list and detail page."""
	out = {}
	for label, user in users.items():
		out[label] = (
			f"list={int(_list_sees(doctype, name, user))} read={int(_read_allowed(doctype, name, user))}"
		)
	return out


# --------------------------------------------------------------------------- #
# the three transitions, the way hrms.api.approval performs them
# --------------------------------------------------------------------------- #
def decide(doctype, name, status, user):
	"""hrms.api.approval.decide minus the whitelist: routed approvers run
	elevated (ignore_permissions), then the controller's own validators
	(self-submission, attachment, status gate) decide."""
	from hrms.api.approval import _is_routed_approver

	frappe.set_user(user)
	try:
		doc = frappe.get_doc(doctype, name)
		if _is_routed_approver(doc):
			doc.flags.ignore_permissions = True
		doc.set(DECIDE[doctype][0], status)
		doc.submit()
		doc.reload()
		return f"docstatus={doc.docstatus} {DECIDE[doctype][0]}={doc.get(DECIDE[doctype][0])}"
	finally:
		frappe.set_user("Administrator")


def submit_as(doctype, name, user):
	"""finalize(docstatus=1) for a doctype with no decision field: DocPerm only."""
	frappe.set_user(user)
	try:
		doc = frappe.get_doc(doctype, name)
		doc.submit()
		doc.reload()
		return f"docstatus={doc.docstatus}"
	finally:
		frappe.set_user("Administrator")


def cancel_as(doctype, name, user):
	"""finalize(docstatus=2): a routed approver of an APPROVED request is
	elevated; the guard on before_cancel still has the final word."""
	from hrms.api.approval import _is_routed_approver
	from hrms.utils.approved_request_guard import is_approved_request, is_own_request

	frappe.set_user(user)
	try:
		doc = frappe.get_doc(doctype, name)
		if (
			not frappe.has_permission(doctype, "cancel", doc=doc)
			and is_approved_request(doc)
			and not is_own_request(doc)
			and _is_routed_approver(doc)
		):
			doc.flags.ignore_permissions = True
		doc.cancel()
		doc.reload()
		return f"docstatus={doc.docstatus}"
	finally:
		frappe.set_user("Administrator")


def insert_as(user, payload):
	frappe.set_user(user)
	try:
		doc = frappe.get_doc(payload)
		doc.insert()
		return doc
	finally:
		frappe.set_user("Administrator")


def save_as(doctype, name, user, **values):
	frappe.set_user(user)
	try:
		doc = frappe.get_doc(doctype, name)
		doc.update(values)
		doc.save()
		doc.reload()
		return doc
	finally:
		frappe.set_user("Administrator")


# --------------------------------------------------------------------------- #
# scenarios
# --------------------------------------------------------------------------- #
class Fixture:
	pass


def build_fixture():
	f = Fixture()
	f.today = getdate(nowdate())
	# Users. HR holds HR User + HR Manager but NOT System Manager (the write
	# block and the guard both treat System Manager as break-glass).
	f.hr_user = _user("lp_hr@example.com", "LP HR", ("HR User", "HR Manager", "Employee"))
	f.hr_other_user = _user("lp_hr_other@example.com", "LP HR Other", ("HR User", "Employee"))
	f.mgr_user = _user("lp_mgr@example.com", "LP Manager", ("Employee",))
	f.staff_user = _user("lp_staff@example.com", "LP Staff", ("Employee",))
	f.staff2_user = _user("lp_staff2@example.com", "LP Staff Two", ("Employee",))
	f.stranger_user = _user("lp_stranger@example.com", "LP Stranger", ("Employee",))
	f.left_user = _user("lp_left@example.com", "LP Left", ("Employee",))
	f.mirror_user = _user("lp_mirror@example.com", "LP Mirror", ("Employee",))
	f.swapper_user = _user("lp_swapper@example.com", "LP Swapper", ("Employee",))
	f.holiday_list = _holiday_list()
	f.day_shift = _shift("LP Day", "09:00:00", "18:00:00")
	# 4h evening shift: 9h day + 4h evening = 13h, inside the 14h/day roster cap
	f.night_shift = _shift("LP Evening", "19:00:00", "23:00:00")

	f.hr = _employee(f.hr_user, holiday_list=f.holiday_list)
	f.hr_other = _employee(f.hr_other_user, company=OTHER_COMPANY)
	f.mgr = _employee(f.mgr_user, holiday_list=f.holiday_list)
	common = dict(
		reports_to=f.mgr,
		leave_approver=f.mgr_user,
		expense_approver=f.mgr_user,
		shift_request_approver=f.mgr_user,
		holiday_list=f.holiday_list,
		default_shift=f.day_shift,
	)
	f.staff = _employee(f.staff_user, **common)
	f.staff2 = _employee(f.staff2_user, eligible_for_overtime_pay=1, **common)
	f.stranger = _employee(f.stranger_user, holiday_list=f.holiday_list)
	f.swapper = _employee(f.swapper_user, **common)
	f.left = _employee(f.left_user, **common)
	frappe.db.set_value("Employee", f.left, {"status": "Left", "relieving_date": add_days(f.today, -30)})
	f.mirror = _employee(f.mirror_user, **common)
	frappe.db.set_value("Employee", f.mirror, "synced_from_instance", INSTANCE)
	frappe.db.set_value("HRMS ERP Instance", INSTANCE, "unlock_mirrored_writes", 0)
	for emp in (f.hr, f.mgr, f.staff, f.staff2, f.stranger, f.swapper, f.left, f.mirror):
		_assign_holiday_list(emp, f.holiday_list)
	# hr_other is fenced to another company through an allow=Company User
	# Permission — created AFTER the Employee rows so no Employee hook can
	# reconcile it away (employee_hrms_scope.sync_company_user_permission).
	up = frappe.new_doc("User Permission")
	up.update({"user": f.hr_other_user, "allow": "Company", "for_value": OTHER_COMPANY})
	up.flags.ignore_permissions = True
	up.insert()
	frappe.clear_cache(user=f.hr_other_user)

	f.leave_type = _leave_type("LP Casual", max_continuous_days_allowed=10)
	f.comp_type = _leave_type("Compensatory Off", is_compensatory=1)
	f.rl_type = _leave_type("Replacement Leave", is_carry_forward=0)
	period = frappe.db.get_value(
		"Leave Period", {"company": COMPANY, "is_active": 1}, ["from_date", "to_date"], as_dict=True
	)
	f.period_from, f.period_to = period.from_date, period.to_date
	for emp in (f.staff, f.staff2, f.mirror, f.left):
		_allocate(emp, f.leave_type, 10, f.period_from, f.period_to)

	# A rostered day shift since two months back, and the punches of one OT day.
	frappe.db.set_single_value("HR Settings", "allow_multiple_shift_assignments", 1)
	for emp in (f.staff, f.staff2, f.mirror):
		_assign_shift(emp, f.day_shift, add_days(f.today, -60))
	f.ot_day = add_days(f.today, -6)  # a weekday six days back
	while f.ot_day.weekday() >= 5:
		f.ot_day = add_days(f.ot_day, -1)
	# in 09:00, out 23:30: 5.5h past the 18:00 shift end, so at least one
	# whole 4h replacement-leave block survives any break deduction
	start = get_datetime(f"{f.ot_day} 09:00:00")
	for emp in (f.staff, f.staff2):
		_punch(emp, start, "IN")
		_punch(emp, start + timedelta(hours=14, minutes=30), "OUT")
	# the employee's weekday attendance: one Present (with punches), one Absent
	f.present_day = f.ot_day
	f.absent_day = add_days(f.ot_day, 1)
	while f.absent_day.weekday() >= 5:
		f.absent_day = add_days(f.absent_day, 1)
	_attendance(f.staff, f.present_day, "Present", shift=f.day_shift)
	_attendance(f.staff, f.absent_day, "Absent", shift=f.day_shift)
	# next Monday and after — the future dates the leave scenarios use
	f.next_mon = add_days(f.today, (7 - f.today.weekday()) % 7 or 7)
	f.last_sat = add_days(f.today, -((f.today.weekday() + 2) % 7 or 7))
	_attendance(f.staff, f.last_sat, "Present", shift=f.day_shift)  # worked a weekly off (comp leave)
	f.personas = {
		"employee": f.staff_user,
		"approver": f.mgr_user,
		"hr": f.hr_user,
		"hr_other_co": f.hr_other_user,
		"stranger": f.stranger_user,
	}
	from hrms.overrides.company_scope import allowed_companies

	record(
		"fixture",
		"company fence of hr_other",
		"hr_other_co",
		f"allowed={allowed_companies(f.hr_other_user)} holidays={frappe.db.count('Holiday', {'parent': f.holiday_list})}",
	)
	from hrms.hr.utils import get_holiday_dates_for_employee

	record(
		"fixture",
		"holiday resolution for staff",
		"-",
		f"employee.holiday_list={frappe.db.get_value('Employee', f.staff, 'holiday_list')} "
		f"last_sat={f.last_sat} holidays={get_holiday_dates_for_employee(f.staff, f.last_sat, f.last_sat)}",
	)
	return f


def _balance(employee, leave_type, on):
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	return get_leave_balance_on(employee, leave_type, on)


def _attendance_rows(employee, start, end):
	return [
		f"{r.attendance_date}:{r.status}{'/' + r.half_day_status if r.half_day_status else ''}(d{r.docstatus})"
		for r in frappe.get_all(
			"Attendance",
			filters={"employee": employee, "attendance_date": ["between", [start, end]]},
			fields=["attendance_date", "status", "half_day_status", "docstatus"],
			order_by="attendance_date, docstatus",
		)
	]


def _rl_days(employee):
	return sum(
		r.total_leaves_allocated
		for r in frappe.get_all(
			"Leave Allocation",
			filters={"employee": employee, "leave_type": "Replacement Leave", "docstatus": 1},
			fields=["total_leaves_allocated"],
		)
	)


# ---- Leave Application ------------------------------------------------------ #
def scenario_leave(f):
	D = "Leave Application"
	P = f.personas
	from_date, to_date = f.next_mon, add_days(f.next_mon, 1)

	def payload(**over):
		base = {
			"doctype": D,
			"employee": f.staff,
			"leave_type": f.leave_type,
			"from_date": from_date,
			"to_date": to_date,
			"description": "lp probe",
			"leave_approver": f.mgr_user,
		}
		base.update(over)
		return base

	before = _balance(f.staff, f.leave_type, from_date)
	doc = step(
		D, "create (PWA payload, no posting_date)", "employee", lambda: insert_as(f.staff_user, payload())
	)
	if not doc:
		return
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	record(D, "notified on create", "-", str(_notified(D, doc.name)))
	step(D, "approve as stranger", "stranger", lambda: decide(D, doc.name, "Approved", f.stranger_user))
	step(
		D,
		"approve as fenced HR (other company)",
		"hr_other_co",
		lambda: decide(D, doc.name, "Approved", f.hr_other_user),
		expect=lambda v: f"fenced HR approved another company's leave: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	step(
		D,
		"self-approve (prevent_self_leave_approval=0)",
		"employee",
		lambda: decide(D, doc.name, "Approved", f.staff_user),
		expect=lambda v: f"the employee approved their own leave: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	frappe.db.set_single_value("HR Settings", "prevent_self_leave_approval", 1)
	step(
		D,
		"self-approve (prevent_self_leave_approval=1)",
		"employee",
		lambda: decide(D, doc.name, "Approved", f.staff_user),
		expect=lambda v: f"the employee approved their own leave: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	step(D, "approve as named approver", "approver", lambda: decide(D, doc.name, "Approved", f.mgr_user))
	record(D, "notified on approve", "-", str(_notified(D, doc.name)))
	record(D, "attendance after approve", "-", str(_attendance_rows(f.staff, from_date, to_date)))
	after = _balance(f.staff, f.leave_type, to_date)
	record(
		D,
		"balance before -> after approve",
		"-",
		f"{before} -> {after}" + ("" if after == before - 2 else " WRONG"),
	)
	step(D, "cancel approved as employee", "employee", lambda: cancel_as(D, doc.name, f.staff_user))
	step(D, "cancel approved as stranger", "stranger", lambda: cancel_as(D, doc.name, f.stranger_user))
	step(D, "cancel approved as approver", "approver", lambda: cancel_as(D, doc.name, f.mgr_user))
	record(D, "attendance after cancel", "-", str(_attendance_rows(f.staff, from_date, to_date)))
	restored = _balance(f.staff, f.leave_type, to_date)
	record(D, "balance after cancel", "-", f"{restored}" + ("" if restored == before else " WRONG"))
	record(D, "notified on cancel", "-", str(_notified(D, doc.name)))
	# HR cancels one too
	doc2 = step(D, "re-file after cancel", "employee", lambda: insert_as(f.staff_user, payload()))
	if doc2:
		step(D, "reject as approver", "approver", lambda: decide(D, doc2.name, "Rejected", f.mgr_user))
		record(D, "attendance after reject", "-", str(_attendance_rows(f.staff, from_date, to_date)))
		record(D, "notified on reject", "-", str(_notified(D, doc2.name)))
		doc3 = step(D, "re-file after rejection", "employee", lambda: insert_as(f.staff_user, payload()))
		if doc3:
			step(
				D,
				"duplicate filing while one is open",
				"employee",
				lambda: insert_as(f.staff_user, payload()),
			)
			step(D, "approve as HR", "hr", lambda: decide(D, doc3.name, "Approved", f.hr_user))
			step(D, "cancel approved as HR", "hr", lambda: cancel_as(D, doc3.name, f.hr_user))
	# half day
	hd = step(
		D,
		"half-day create",
		"employee",
		lambda: insert_as(
			f.staff_user,
			payload(
				from_date=add_days(from_date, 2),
				to_date=add_days(from_date, 2),
				half_day=1,
				half_day_date=add_days(from_date, 2),
			),
		),
	)
	if hd:
		step(D, "half-day approve", "approver", lambda: decide(D, hd.name, "Approved", f.mgr_user))
		record(
			D,
			"half-day attendance",
			"-",
			str(_attendance_rows(f.staff, add_days(from_date, 2), add_days(from_date, 2))),
		)
	# crossing a weekend: Fri -> Mon
	fri = add_days(f.next_mon, 4)
	wk = step(
		D,
		"crossing weekend create (Fri-Mon)",
		"employee",
		lambda: insert_as(f.staff_user, payload(from_date=fri, to_date=add_days(fri, 3))),
	)
	if wk:
		record(
			D,
			"crossing weekend total_leave_days",
			"-",
			f"{wk.total_leave_days}" + ("" if wk.total_leave_days == 2 else " WRONG"),
		)
		step(D, "crossing weekend approve", "approver", lambda: decide(D, wk.name, "Approved", f.mgr_user))
		record(D, "crossing weekend attendance", "-", str(_attendance_rows(f.staff, fri, add_days(fri, 3))))
	# backdated
	step(
		D,
		"backdated create (last week)",
		"employee",
		lambda: insert_as(f.staff_user, payload(from_date=add_days(f.absent_day, 0), to_date=f.absent_day)),
	)
	bd = frappe.db.get_value(D, {"employee": f.staff, "from_date": f.absent_day, "docstatus": 0}, "name")
	if bd:
		step(
			D, "backdated approve on an Absent day", "approver", lambda: decide(D, bd, "Approved", f.mgr_user)
		)
		record(
			D,
			"backdated attendance (was Absent)",
			"-",
			str(_attendance_rows(f.staff, f.absent_day, f.absent_day)),
		)
	step(
		D,
		"create on a day already Present",
		"employee",
		lambda: insert_as(f.staff_user, payload(from_date=f.present_day, to_date=f.present_day)),
	)
	step(D, "create for a Left employee", "left", lambda: insert_as(f.left_user, payload(employee=f.left)))
	step(D, "create in a colleague's name", "stranger", lambda: insert_as(f.stranger_user, payload()))
	# approver changed after filing
	ac = step(
		D,
		"approver-change: create",
		"employee",
		lambda: insert_as(
			f.staff_user, payload(from_date=add_days(from_date, 14), to_date=add_days(from_date, 14))
		),
	)
	if ac:
		frappe.db.set_value("Employee", f.staff, "leave_approver", f.stranger_user)
		step(
			D,
			"approver-change: new employee-approver (not on doc) approves",
			"stranger",
			lambda: decide(D, ac.name, "Approved", f.stranger_user),
		)
		step(
			D,
			"approver-change: old named approver approves",
			"approver",
			lambda: decide(D, ac.name, "Approved", f.mgr_user),
		)
		frappe.db.set_value("Employee", f.staff, "leave_approver", f.mgr_user)
	# mirrored employee
	m = step(
		D,
		"mirrored employee create",
		"mirror",
		lambda: insert_as(
			f.mirror_user,
			payload(employee=f.mirror, from_date=add_days(from_date, 21), to_date=add_days(from_date, 21)),
		),
	)
	if m:
		step(D, "mirrored employee approve", "approver", lambda: decide(D, m.name, "Approved", f.mgr_user))
		step(
			D,
			"mirrored employee approve as HR (no SysMgr)",
			"hr",
			lambda: decide(D, m.name, "Approved", f.hr_user),
		)


# ---- Attendance Request ----------------------------------------------------- #
def scenario_attendance_request(f):
	D = "Attendance Request"
	P = f.personas
	d1 = add_days(f.absent_day, 1)
	while d1.weekday() >= 5:
		d1 = add_days(d1, 1)

	def payload(**over):
		base = {
			"doctype": D,
			"employee": f.staff,
			"from_date": d1,
			"to_date": d1,
			"reason": "On Duty",
			"explanation": "lp probe",
		}
		base.update(over)
		return base

	doc = step(D, "create (PWA payload, no company)", "employee", lambda: insert_as(f.staff_user, payload()))
	if not doc:
		return
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	record(D, "notified on create", "-", str(_notified(D, doc.name)))
	step(D, "approve as stranger", "stranger", lambda: decide(D, doc.name, "Approved", f.stranger_user))
	step(
		D,
		"approve as fenced HR (other company)",
		"hr_other_co",
		lambda: decide(D, doc.name, "Approved", f.hr_other_user),
		expect=lambda v: f"fenced HR approved another company's request: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	step(
		D,
		"self-approve",
		"employee",
		lambda: decide(D, doc.name, "Approved", f.staff_user),
		expect=lambda v: f"the employee approved their own request: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	step(D, "approve as reports_to manager", "approver", lambda: decide(D, doc.name, "Approved", f.mgr_user))
	record(D, "notified on approve", "-", str(_notified(D, doc.name)))
	record(D, "attendance after approve", "-", str(_attendance_rows(f.staff, d1, d1)))
	step(D, "cancel approved as employee", "employee", lambda: cancel_as(D, doc.name, f.staff_user))
	step(D, "cancel approved as approver", "approver", lambda: cancel_as(D, doc.name, f.mgr_user))
	record(D, "attendance after cancel", "-", str(_attendance_rows(f.staff, d1, d1)))
	doc2 = step(D, "re-file after cancel", "employee", lambda: insert_as(f.staff_user, payload()))
	if doc2:
		step(D, "reject as approver", "approver", lambda: decide(D, doc2.name, "Rejected", f.mgr_user))
		record(D, "attendance after reject", "-", str(_attendance_rows(f.staff, d1, d1)))
		record(D, "notified on reject", "-", str(_notified(D, doc2.name)))
		doc3 = step(D, "re-file after rejection", "employee", lambda: insert_as(f.staff_user, payload()))
		if doc3:
			step(D, "duplicate filing (overlap)", "employee", lambda: insert_as(f.staff_user, payload()))
			step(D, "approve as HR", "hr", lambda: decide(D, doc3.name, "Approved", f.hr_user))
			step(D, "cancel approved as HR", "hr", lambda: cancel_as(D, doc3.name, f.hr_user))
	ab = step(
		D,
		"create on an Absent day",
		"employee",
		lambda: insert_as(f.staff_user, payload(from_date=f.absent_day, to_date=f.absent_day)),
	)
	if ab:
		step(D, "approve on an Absent day", "approver", lambda: decide(D, ab.name, "Approved", f.mgr_user))
		record(D, "Absent day after approve", "-", str(_attendance_rows(f.staff, f.absent_day, f.absent_day)))
	step(
		D,
		"create on a day already Present (unchanged)",
		"employee",
		lambda: insert_as(f.staff_user, payload(from_date=f.present_day, to_date=f.present_day)),
	)
	hd = step(
		D,
		"half-day create",
		"employee",
		lambda: insert_as(
			f.staff_user,
			payload(
				from_date=add_days(d1, 1), to_date=add_days(d1, 1), half_day=1, half_day_date=add_days(d1, 1)
			),
		),
	)
	if hd:
		step(D, "half-day approve", "approver", lambda: decide(D, hd.name, "Approved", f.mgr_user))
		record(
			D, "half-day attendance", "-", str(_attendance_rows(f.staff, add_days(d1, 1), add_days(d1, 1)))
		)
	wk = step(
		D,
		"crossing weekend create (Fri-Mon)",
		"employee",
		lambda: insert_as(
			f.staff_user, payload(from_date=add_days(f.last_sat, -1), to_date=add_days(f.last_sat, 2))
		),
	)
	if wk:
		step(D, "crossing weekend approve", "approver", lambda: decide(D, wk.name, "Approved", f.mgr_user))
		record(
			D,
			"crossing weekend attendance",
			"-",
			str(_attendance_rows(f.staff, add_days(f.last_sat, -1), add_days(f.last_sat, 2))),
		)
	step(
		D,
		"create with in/out times, only in_time",
		"employee",
		lambda: insert_as(
			f.staff_user, payload(from_date=add_days(d1, 2), to_date=add_days(d1, 2), in_time="09:00:00")
		),
	)
	step(D, "create in a colleague's name", "stranger", lambda: insert_as(f.stranger_user, payload()))
	step(D, "create for a Left employee", "left", lambda: insert_as(f.left_user, payload(employee=f.left)))
	m = step(
		D, "mirrored employee create", "mirror", lambda: insert_as(f.mirror_user, payload(employee=f.mirror))
	)
	if m:
		step(D, "mirrored employee approve", "approver", lambda: decide(D, m.name, "Approved", f.mgr_user))


# ---- Shift Request ---------------------------------------------------------- #
def scenario_shift_request(f):
	D = "Shift Request"
	P = f.personas
	start = add_days(f.next_mon, 14)

	def payload(**over):
		base = {
			"doctype": D,
			"employee": f.staff,
			"shift_type": f.night_shift,
			"from_date": start,
			"to_date": add_days(start, 4),
			"approver": f.mgr_user,
		}
		base.update(over)
		return base

	step(
		D,
		"create for the default shift",
		"employee",
		lambda: insert_as(f.staff_user, payload(shift_type=f.day_shift)),
	)
	step(
		D,
		"create with a non-approver as approver",
		"employee",
		lambda: insert_as(f.staff_user, payload(approver=f.stranger_user)),
	)
	doc = step(D, "create (PWA payload, no company)", "employee", lambda: insert_as(f.staff_user, payload()))
	if not doc:
		return
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	record(D, "notified on create", "-", str(_notified(D, doc.name)))
	step(D, "duplicate filing (overlap)", "employee", lambda: insert_as(f.staff_user, payload()))
	step(D, "approve as stranger", "stranger", lambda: decide(D, doc.name, "Approved", f.stranger_user))
	step(
		D,
		"self-approve",
		"employee",
		lambda: decide(D, doc.name, "Approved", f.staff_user),
		expect=lambda v: f"the employee approved their own request: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	step(D, "approve as named approver", "approver", lambda: decide(D, doc.name, "Approved", f.mgr_user))
	record(D, "notified on approve", "-", str(_notified(D, doc.name)))
	sa = frappe.get_all(
		"Shift Assignment", filters={"shift_request": doc.name}, fields=["name", "docstatus", "status"]
	)
	record(D, "shift assignment after approve", "-", str(sa))
	step(D, "cancel approved as employee", "employee", lambda: cancel_as(D, doc.name, f.staff_user))
	step(D, "cancel approved as approver", "approver", lambda: cancel_as(D, doc.name, f.mgr_user))
	sa = frappe.get_all("Shift Assignment", filters={"shift_request": doc.name}, fields=["name", "docstatus"])
	record(D, "shift assignment after cancel", "-", str(sa))
	doc2 = step(D, "re-file after cancel", "employee", lambda: insert_as(f.staff_user, payload()))
	if doc2:
		step(D, "reject as approver", "approver", lambda: decide(D, doc2.name, "Rejected", f.mgr_user))
		record(D, "notified on reject", "-", str(_notified(D, doc2.name)))
		doc3 = step(D, "re-file after rejection", "employee", lambda: insert_as(f.staff_user, payload()))
		if doc3:
			step(D, "approve as HR", "hr", lambda: decide(D, doc3.name, "Approved", f.hr_user))
			step(D, "cancel approved as HR", "hr", lambda: cancel_as(D, doc3.name, f.hr_user))
	step(
		D,
		"backdated create",
		"employee",
		lambda: insert_as(
			f.staff_user, payload(from_date=add_days(f.today, -10), to_date=add_days(f.today, -8))
		),
	)
	step(D, "create for a Left employee", "left", lambda: insert_as(f.left_user, payload(employee=f.left)))
	m = step(
		D, "mirrored employee create", "mirror", lambda: insert_as(f.mirror_user, payload(employee=f.mirror))
	)
	if m:
		step(D, "mirrored employee approve", "approver", lambda: decide(D, m.name, "Approved", f.mgr_user))


# ---- Compensatory Leave Request --------------------------------------------- #
def scenario_comp_leave(f):
	D = "Compensatory Leave Request"
	P = f.personas

	def payload(**over):
		base = {
			"doctype": D,
			"employee": f.staff,
			"work_from_date": f.last_sat,
			"work_end_date": f.last_sat,
			"leave_type": f.comp_type,
			"reason": "lp probe",
		}
		base.update(over)
		return base

	step(
		D,
		"create for a non-holiday",
		"employee",
		lambda: insert_as(f.staff_user, payload(work_from_date=f.present_day, work_end_date=f.present_day)),
	)
	doc = step(D, "create (worked weekly off)", "employee", lambda: insert_as(f.staff_user, payload()))
	if not doc:
		return
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	record(D, "notified on create", "-", str(_notified(D, doc.name)))
	step(D, "duplicate filing (overlap)", "employee", lambda: insert_as(f.staff_user, payload()))
	step(D, "submit(=approve) as employee", "employee", lambda: submit_as(D, doc.name, f.staff_user))
	step(D, "submit(=approve) as reports_to manager", "approver", lambda: submit_as(D, doc.name, f.mgr_user))
	before = _balance(f.staff, f.comp_type, add_days(f.last_sat, 1))
	step(D, "submit(=approve) as HR", "hr", lambda: submit_as(D, doc.name, f.hr_user))
	after = _balance(f.staff, f.comp_type, add_days(f.last_sat, 1))
	record(
		D,
		"comp balance before -> after",
		"-",
		f"{before} -> {after}" + ("" if after == before + 1 else " WRONG"),
	)
	record(D, "notified on approve", "-", str(_notified(D, doc.name)))
	step(D, "cancel approved as employee", "employee", lambda: cancel_as(D, doc.name, f.staff_user))
	step(D, "cancel approved as approver", "approver", lambda: cancel_as(D, doc.name, f.mgr_user))
	step(D, "cancel approved as HR", "hr", lambda: cancel_as(D, doc.name, f.hr_user))
	restored = _balance(f.staff, f.comp_type, add_days(f.last_sat, 1))
	record(D, "comp balance after cancel", "-", f"{restored}" + ("" if restored == before else " WRONG"))
	# HR files their own and approves it
	_attendance(f.hr, f.last_sat, "Present")
	own = step(D, "HR files own comp leave", "hr", lambda: insert_as(f.hr_user, payload(employee=f.hr)))
	if own:
		step(D, "HR submits (approves) own comp leave", "hr", lambda: submit_as(D, own.name, f.hr_user))
	step(D, "create in a colleague's name", "stranger", lambda: insert_as(f.stranger_user, payload()))
	step(D, "create for a Left employee", "left", lambda: insert_as(f.left_user, payload(employee=f.left)))


# ---- Remote Checkin Request ------------------------------------------------- #
def scenario_remote_checkin(f):
	D = "Remote Checkin Request"
	P = f.personas
	when = get_datetime(f"{f.today} 09:05:00")

	def punch_as(user, employee, log_type, when, **kw):
		frappe.set_user(user)
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Employee Checkin",
					"employee": employee,
					"log_type": log_type,
					"time": when,
					"latitude": 3.1,
					"longitude": 101.6,
					"requires_remote_approval": 1,
				}
			)
			for k, v in kw.items():
				setattr(doc.flags, k, v)
			# hrms.api.remote_checkin.punch is the staff write path: it inserts
			# with ignore_permissions and lets the geofence override flag the row.
			doc.flags.ignore_permissions = True
			doc.insert()
			if not frappe.db.exists("Remote Checkin Request", {"checkin": doc.name}):
				# no Shift Location on this site, so the geofence never flags a
				# punch as remote — replay the after_insert hook on a flagged row
				from hrms.overrides.employee_checkin_after_insert import create_remote_request_if_needed

				doc.requires_remote_approval = 1
				create_remote_request_if_needed(doc)
			return doc
		finally:
			frappe.set_user("Administrator")

	chk = step(
		D,
		"employee punches IN outside the fence",
		"employee",
		lambda: punch_as(f.staff_user, f.staff, "IN", when),
	)
	if not chk:
		return
	req = frappe.db.get_value(D, {"checkin": chk.name}, ["name", "status", "approver"], as_dict=True)
	record(
		D,
		"request auto-created",
		"-",
		str(req) + ("" if req and req.approver == f.mgr_user else " WRONG approver"),
	)
	if not req:
		return
	record(D, "visibility after create", "all", str(_visibility(D, req.name, P)))
	record(D, "notified on create", "-", str(_notified(D, req.name)))
	step(
		D,
		"approve as stranger",
		"stranger",
		lambda: save_as(D, req.name, f.stranger_user, status="Approved").status,
	)
	step(D, "self-approve", "employee", lambda: save_as(D, req.name, f.staff_user, status="Approved").status)
	step(
		D,
		"approve as HR User only (not HR Manager)",
		"hr_other_co",
		lambda: save_as(D, req.name, f.hr_other_user, status="Approved").status,
	)
	step(
		D,
		"approve as named approver",
		"approver",
		lambda: save_as(D, req.name, f.mgr_user, status="Approved").status,
	)
	flags = frappe.db.get_value(
		"Employee Checkin",
		chk.name,
		["requires_remote_approval", "remote_approval_status", "skip_auto_attendance"],
		as_dict=True,
	)
	record(
		D,
		"checkin flags after approve",
		"-",
		str(flags) + ("" if flags.remote_approval_status == "Approved" else " WRONG"),
	)
	record(D, "notified on approve", "-", str(_notified(D, req.name)))
	step(
		D,
		"re-decide (reject after approve) as HR",
		"hr",
		lambda: save_as(D, req.name, f.hr_user, status="Rejected").status,
	)
	# forgotten check-out the next morning -> late checkout request
	out_when = get_datetime(f"{f.today} 20:30:00")
	out = step(
		D,
		"employee punches OUT (inherits approval)",
		"employee",
		lambda: punch_as(f.staff_user, f.staff, "OUT", out_when),
	)
	if out:
		r2 = frappe.db.get_value(
			D, {"checkin": out.name}, ["name", "status", "parent_request", "is_late_checkout"], as_dict=True
		)
		record(
			D, "OUT request inherited", "-", str(r2) + ("" if r2 and r2.status == "Approved" else " WRONG")
		)
	# rejection path on a fresh IN for staff2
	chk2 = step(
		D,
		"staff2 punches IN outside the fence",
		"employee2",
		lambda: punch_as(f.staff2_user, f.staff2, "IN", when),
	)
	if chk2:
		r3 = frappe.db.get_value(D, {"checkin": chk2.name}, "name")
		step(
			D, "reject as approver", "approver", lambda: save_as(D, r3, f.mgr_user, status="Rejected").status
		)
		flags = frappe.db.get_value(
			"Employee Checkin", chk2.name, ["remote_approval_status", "skip_auto_attendance"], as_dict=True
		)
		record(
			D,
			"checkin flags after reject",
			"-",
			str(flags) + ("" if flags.skip_auto_attendance else " WRONG not skip-stamped"),
		)
		record(D, "notified on reject", "-", str(_notified(D, r3)))
	# forgotten check-out: a late OUT filed the next day for yesterday's shift
	late_when = get_datetime(f"{add_days(f.today, -1)} 19:00:00")
	_punch(f.staff2, get_datetime(f"{add_days(f.today, -1)} 09:00:00"), "IN")
	late = step(
		D,
		"forgotten check-out filed (is_late_checkout)",
		"stranger",
		lambda: punch_as(f.staff2_user, f.staff2, "OUT", late_when, is_late_checkout=True),
	)
	if late:
		r4 = frappe.db.get_value(
			D, {"checkin": late.name}, ["name", "status", "approver", "is_late_checkout"], as_dict=True
		)
		record(D, "late checkout request", "-", str(r4))
		if r4:
			approver = r4.approver or f.hr_user
			step(
				D,
				"approve late checkout",
				"approver-of-record",
				lambda: save_as(D, r4.name, approver, status="Approved").status,
			)
			record(
				D,
				"attendance after late checkout approve",
				"-",
				str(_attendance_rows(f.staff2, add_days(f.today, -1), add_days(f.today, -1))),
			)
	# approver == employee (HR set the employee as their own shift approver)
	frappe.db.set_value("Employee", f.swapper, "shift_request_approver", f.swapper_user)
	chk5 = step(
		D,
		"employee who is their own shift approver punches",
		"swapper",
		lambda: punch_as(f.swapper_user, f.swapper, "IN", when),
	)
	if chk5:
		r5 = frappe.db.get_value(D, {"checkin": chk5.name}, ["name", "approver"], as_dict=True)
		record(D, "approver resolved for self-approver", "-", str(r5))
		step(
			D,
			"self-approve as own approver",
			"swapper",
			lambda: save_as(D, r5.name, f.swapper_user, status="Approved").status,
			expect=lambda v: "the employee approved their own remote check-in" if v == "Approved" else None,
		)
	frappe.db.set_value("Employee", f.swapper, "shift_request_approver", f.mgr_user)


# ---- Employee Advance ------------------------------------------------------- #
def scenario_employee_advance(f):
	D = "Employee Advance"
	P = f.personas

	def payload(**over):
		base = {
			"doctype": D,
			"employee": f.staff,
			"purpose": "lp probe",
			"advance_amount": 100,
			"currency": "INR",
			"exchange_rate": 1,
			"posting_date": f.today,
			"mode_of_payment": frappe.db.get_value("Mode of Payment", {"enabled": 1}, "name"),
		}
		base.update(over)
		return base

	record(
		D,
		"create permission",
		"employee/hr",
		f"employee={int(frappe.has_permission(D, 'create', user=f.staff_user))} hr={int(frappe.has_permission(D, 'create', user=f.hr_user))}",
	)
	doc = step(D, "create (PWA payload)", "employee", lambda: insert_as(f.staff_user, payload()))
	if not doc:
		doc = step(D, "create on behalf", "hr", lambda: insert_as(f.hr_user, payload()))
	if not doc:
		frappe.set_user("Administrator")
		doc = step(D, "create as Administrator", "admin", lambda: frappe.get_doc(payload()).insert())
	if not doc:
		return
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	step(D, "submit(=approve) as employee", "employee", lambda: submit_as(D, doc.name, f.staff_user))
	step(D, "submit(=approve) as reports_to manager", "approver", lambda: submit_as(D, doc.name, f.mgr_user))
	step(D, "submit(=approve) as HR", "hr", lambda: submit_as(D, doc.name, f.hr_user))
	if frappe.db.get_value(D, doc.name, "docstatus") != 1:
		step(D, "submit as Administrator", "admin", lambda: submit_as(D, doc.name, "Administrator"))
	step(D, "cancel approved as employee", "employee", lambda: cancel_as(D, doc.name, f.staff_user))
	step(D, "cancel approved as approver", "approver", lambda: cancel_as(D, doc.name, f.mgr_user))
	step(D, "cancel approved as HR", "hr", lambda: cancel_as(D, doc.name, f.hr_user))


# ---- Expense Claim ---------------------------------------------------------- #
def scenario_expense_claim(f):
	D = "Expense Claim"
	P = f.personas

	def payload(**over):
		base = {
			"doctype": D,
			"employee": f.staff,
			"expense_approver": f.mgr_user,
			# the PWA form seeds these four (frontend/src/views/expense_claim/Form.vue)
			"company": COMPANY,
			"currency": frappe.db.get_value("Company", COMPANY, "default_currency"),
			"exchange_rate": 1,
			"posting_date": f.today,
			"cost_center": frappe.db.get_value("Company", COMPANY, "cost_center"),
			"expenses": [
				# ExpensesTable.vue copies amount into sanctioned_amount as the user types
				{
					"expense_date": f.present_day,
					"expense_type": "Medical",
					"amount": 100,
					"sanctioned_amount": 100,
					"cost_center": frappe.db.get_value("Company", COMPANY, "cost_center"),
					"description": "lp",
				}
			],
		}
		base.update(over)
		return base

	step(
		D,
		"create with a type that has no company account",
		"employee",
		lambda: insert_as(
			f.staff_user,
			payload(expenses=[{"expense_date": f.present_day, "expense_type": "Calls", "amount": 10}]),
		),
	)
	doc = step(
		D,
		"create (PWA payload, no posting_date/company)",
		"employee",
		lambda: insert_as(f.staff_user, payload()),
	)
	if not doc:
		return
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	record(D, "notified on create", "-", str(_notified(D, doc.name)))
	step(D, "approve as stranger", "stranger", lambda: decide(D, doc.name, "Approved", f.stranger_user))
	step(
		D,
		"self-approve (prevent_self_expense_approval=0)",
		"employee",
		lambda: decide(D, doc.name, "Approved", f.staff_user),
		expect=lambda v: f"the employee approved their own claim: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	frappe.db.set_single_value("HR Settings", "prevent_self_expense_approval", 1)
	step(
		D,
		"self-approve (prevent_self_expense_approval=1)",
		"employee",
		lambda: decide(D, doc.name, "Approved", f.staff_user),
		expect=lambda v: f"the employee approved their own claim: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	step(D, "approve as named approver", "approver", lambda: decide(D, doc.name, "Approved", f.mgr_user))
	row = frappe.db.get_value(
		D, doc.name, ["status", "total_sanctioned_amount", "grand_total", "payable_account"], as_dict=True
	)
	gl = frappe.db.count("GL Entry", {"voucher_no": doc.name, "is_cancelled": 0})
	record(D, "totals + GL after approve", "-", f"{row} gl_rows={gl}" + ("" if gl else " WRONG no GL"))
	record(D, "notified on approve", "-", str(_notified(D, doc.name)))
	step(D, "cancel approved as employee", "employee", lambda: cancel_as(D, doc.name, f.staff_user))
	step(D, "cancel approved as approver", "approver", lambda: cancel_as(D, doc.name, f.mgr_user))
	gl = frappe.db.count("GL Entry", {"voucher_no": doc.name, "is_cancelled": 0})
	record(D, "GL after cancel", "-", f"live_gl_rows={gl}" + ("" if gl == 0 else " WRONG"))
	doc2 = step(D, "re-file after cancel", "employee", lambda: insert_as(f.staff_user, payload()))
	if doc2:
		step(D, "reject as approver", "approver", lambda: decide(D, doc2.name, "Rejected", f.mgr_user))
		record(
			D,
			"status after reject",
			"-",
			str(frappe.db.get_value(D, doc2.name, ["status", "approval_status", "docstatus"])),
		)
		record(D, "notified on reject", "-", str(_notified(D, doc2.name)))
		doc3 = step(D, "re-file after rejection", "employee", lambda: insert_as(f.staff_user, payload()))
		if doc3:
			step(D, "approve as HR", "hr", lambda: decide(D, doc3.name, "Approved", f.hr_user))
			step(D, "cancel approved as HR", "hr", lambda: cancel_as(D, doc3.name, f.hr_user))
	ac = step(D, "approver-change: create", "employee", lambda: insert_as(f.staff_user, payload()))
	if ac:
		frappe.db.set_value("Employee", f.staff, "expense_approver", f.stranger_user)
		step(
			D,
			"approver-change: new employee-approver (not on doc)",
			"stranger",
			lambda: decide(D, ac.name, "Approved", f.stranger_user),
		)
		step(
			D,
			"approver-change: old named approver",
			"approver",
			lambda: decide(D, ac.name, "Approved", f.mgr_user),
		)
		frappe.db.set_value("Employee", f.staff, "expense_approver", f.mgr_user)
	step(D, "create in a colleague's name", "stranger", lambda: insert_as(f.stranger_user, payload()))
	step(D, "create for a Left employee", "left", lambda: insert_as(f.left_user, payload(employee=f.left)))

	# A raw API caller (not the PWA, which copies amount -> sanctioned_amount)
	# omits sanctioned_amount: what does an approval of that claim pay out?
	raw = step(
		D,
		"raw create without sanctioned_amount",
		"employee",
		lambda: insert_as(
			f.staff_user,
			payload(
				expenses=[
					{
						"expense_date": f.present_day,
						"expense_type": "Medical",
						"amount": 100,
						"cost_center": frappe.db.get_value("Company", COMPANY, "cost_center"),
					}
				]
			),
		),
	)
	if raw:
		step(
			D,
			"raw claim: approve as named approver",
			"approver",
			lambda: decide(D, raw.name, "Approved", f.mgr_user),
		)
		row = frappe.db.get_value(D, raw.name, ["total_sanctioned_amount", "grand_total"], as_dict=True)
		gl = frappe.db.count("GL Entry", {"voucher_no": raw.name, "is_cancelled": 0})
		record(D, "raw claim: totals + GL after approve", "-", f"{row} gl_rows={gl}")


# ---- OT Request ------------------------------------------------------------- #
def _fake_salary_slip(employee, start, end):
	"""A submitted Salary Slip covering the OT day, without payroll: the guard
	only reads employee / dates / docstatus."""
	name = f"LP-SLIP-{employee}"
	frappe.db.sql(
		"""insert into `tabSalary Slip` (name, creation, modified, modified_by, owner, docstatus,
		employee, start_date, end_date, posting_date, company)
		values (%s, now(), now(), 'Administrator', 'Administrator', 1, %s, %s, %s, %s, %s)""",
		(name, employee, start, end, end, COMPANY),
	)
	return name


def scenario_ot(f):
	D = "OT Request"
	P = f.personas

	def payload(employee=None, **over):
		base = {
			"doctype": D,
			"employee": employee or f.staff,
			"ot_date": f.ot_day,
			"claimed_hours": getattr(f, "ot_claim", 4),
			"explanation": "lp probe",
			"status": "Open",
		}
		base.update(over)
		return base

	from hrms.utils.ot_calculation import get_ot_claim_capacity

	cap_rl = get_ot_claim_capacity(f.staff, f.ot_day, "Replacement Leave")
	# claim whole 4h blocks only: 4h = half a day of replacement leave
	f.ot_claim = 4 if cap_rl["hours"] >= 4 else cap_rl["hours"]
	cap_pay = get_ot_claim_capacity(f.staff2, f.ot_day, "Overtime Pay")
	record(D, "capacity from punches (RL / Pay)", "-", f"{cap_rl['hours']} / {cap_pay['hours']}")
	step(
		D,
		"create for a future date",
		"employee",
		lambda: insert_as(f.staff_user, payload(ot_date=add_days(f.today, 1))),
	)
	step(
		D,
		"create out of the filing window",
		"employee",
		lambda: insert_as(f.staff_user, payload(ot_date=add_days(f.today, -200))),
	)
	step(
		D,
		"create claiming more than punches prove",
		"employee",
		lambda: insert_as(f.staff_user, payload(claimed_hours=9)),
	)
	step(
		D,
		"create on a day with no punches (Absent day)",
		"employee",
		lambda: insert_as(f.staff_user, payload(ot_date=f.absent_day, claimed_hours=1)),
	)
	doc = step(D, "create (PWA payload) RL employee", "employee", lambda: insert_as(f.staff_user, payload()))
	if not doc:
		return
	record(
		D,
		"compensation / cap stamped",
		"-",
		f"{doc.compensation} punch_cap={doc.punch_ot_hours} company={doc.company}",
	)
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	record(D, "notified on create", "-", str(_notified(D, doc.name)))
	step(D, "duplicate filing same day", "employee", lambda: insert_as(f.staff_user, payload()))
	step(D, "approve as stranger", "stranger", lambda: decide(D, doc.name, "Approved", f.stranger_user))
	step(
		D,
		"approve as fenced HR (other company)",
		"hr_other_co",
		lambda: decide(D, doc.name, "Approved", f.hr_other_user),
		expect=lambda v: f"fenced HR approved another company's OT: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	step(
		D,
		"self-approve",
		"employee",
		lambda: decide(D, doc.name, "Approved", f.staff_user),
		expect=lambda v: f"the employee approved their own OT: {v}",
	)
	if frappe.db.get_value(D, doc.name, "docstatus") == 1:
		return
	before = _rl_days(f.staff)
	step(D, "approve as reports_to manager", "approver", lambda: decide(D, doc.name, "Approved", f.mgr_user))
	after = _rl_days(f.staff)
	granted = frappe.db.get_value(D, doc.name, ["leave_allocation", "leave_days_granted"])
	record(
		D,
		"RL allocation before -> after approve",
		"-",
		f"{before} -> {after} granted={granted}" + ("" if after == before + 0.5 else " WRONG (4h = 0.5 day)"),
	)
	record(D, "notified on approve", "-", str(_notified(D, doc.name)))
	cap_after = get_ot_claim_capacity(f.staff, f.ot_day, "Replacement Leave")
	record(D, "claim capacity after approve", "-", str(cap_after["hours"]))
	step(D, "cancel approved as employee", "employee", lambda: cancel_as(D, doc.name, f.staff_user))
	step(D, "cancel approved as approver", "approver", lambda: cancel_as(D, doc.name, f.mgr_user))
	record(
		D,
		"RL allocation after cancel",
		"-",
		f"{_rl_days(f.staff)}" + ("" if _rl_days(f.staff) == before else " WRONG"),
	)
	doc2 = step(D, "re-file after cancel", "employee", lambda: insert_as(f.staff_user, payload()))
	if doc2:
		step(D, "reject as approver", "approver", lambda: decide(D, doc2.name, "Rejected", f.mgr_user))
		record(
			D,
			"RL allocation after reject",
			"-",
			f"{_rl_days(f.staff)}" + ("" if _rl_days(f.staff) == before else " WRONG"),
		)
		record(D, "notified on reject", "-", str(_notified(D, doc2.name)))
		doc3 = step(D, "re-file after rejection", "employee", lambda: insert_as(f.staff_user, payload()))
		if doc3:
			step(D, "approve as HR", "hr", lambda: decide(D, doc3.name, "Approved", f.hr_user))
			step(D, "cancel approved as HR", "hr", lambda: cancel_as(D, doc3.name, f.hr_user))
	# approver changed after filing: reports_to moves to stranger
	ac = step(D, "approver-change: create", "employee", lambda: insert_as(f.staff_user, payload()))
	if ac:
		frappe.db.set_value("Employee", f.staff, "reports_to", f.stranger)
		step(
			D,
			"approver-change: old manager approves",
			"approver",
			lambda: decide(D, ac.name, "Approved", f.mgr_user),
		)
		step(
			D,
			"approver-change: new manager approves",
			"stranger",
			lambda: decide(D, ac.name, "Approved", f.stranger_user),
		)
		frappe.db.set_value("Employee", f.staff, "reports_to", f.mgr)
	# Overtime Pay: approve, then lock once paid
	pay = step(
		D,
		"create (PWA payload) OT-Pay employee",
		"employee2",
		lambda: insert_as(f.staff2_user, payload(employee=f.staff2)),
	)
	if pay:
		record(D, "OT-Pay compensation / cap", "-", f"{pay.compensation} punch_cap={pay.punch_ot_hours}")
		step(D, "OT-Pay approve as manager", "approver", lambda: decide(D, pay.name, "Approved", f.mgr_user))
		record(
			D,
			"OT-Pay RL allocation untouched",
			"-",
			f"{_rl_days(f.staff2)}" + ("" if _rl_days(f.staff2) == 0 else " WRONG"),
		)
		step(
			D,
			"fake submitted salary slip covering the day",
			"-",
			lambda: _fake_salary_slip(f.staff2, add_days(f.ot_day, -10), add_days(f.ot_day, 10)),
		)
		step(D, "cancel PAID OT as HR", "hr", lambda: cancel_as(D, pay.name, f.hr_user))
		step(D, "cancel PAID OT as approver", "approver", lambda: cancel_as(D, pay.name, f.mgr_user))
		step(D, "cancel PAID OT as Administrator", "admin", lambda: cancel_as(D, pay.name, "Administrator"))
	step(D, "create in a colleague's name", "stranger", lambda: insert_as(f.stranger_user, payload()))
	step(
		D,
		"create for a Left employee",
		"left",
		lambda: insert_as(f.left_user, payload(employee=f.left, claimed_hours=1)),
	)
	m = step(
		D,
		"mirrored employee create (no punches)",
		"mirror",
		lambda: insert_as(f.mirror_user, payload(employee=f.mirror, claimed_hours=1)),
	)
	if m:
		step(D, "mirrored employee approve", "approver", lambda: decide(D, m.name, "Approved", f.mgr_user))


# ---- Replacement Leave Claim ------------------------------------------------ #
def scenario_rl_claim(f):
	D = "Replacement Leave Claim"
	step(
		D,
		"create (PWA payload) — bank is deprecated",
		"employee",
		lambda: insert_as(
			f.staff_user,
			{"doctype": D, "employee": f.staff, "claimed_days": 0.5, "explanation": "lp", "status": "Open"},
		),
	)
	step(
		D,
		"create with 0.3 days",
		"employee",
		lambda: insert_as(
			f.staff_user,
			{"doctype": D, "employee": f.staff, "claimed_days": 0.3, "explanation": "lp", "status": "Open"},
		),
	)


# ---- Shift Swap Request ----------------------------------------------------- #
def scenario_shift_swap(f):
	D = "Shift Swap Request"
	P = dict(f.personas, swapper=f.swapper_user)
	day = add_days(f.next_mon, 21)
	assignment = _assign_shift(f.swapper, f.day_shift, day, day)
	past = _assign_shift(f.swapper, f.day_shift, add_days(f.today, -3), add_days(f.today, -3))

	def payload(**over):
		base = {
			"doctype": D,
			"requesting_employee": f.swapper,
			"target_employee": f.stranger,
			"shift_assignment": assignment,
			"shift_type": f.day_shift,
			"shift_date": day,
			"reason": "lp probe",
		}
		base.update(over)
		return base

	step(
		D,
		"create with target = self",
		"swapper",
		lambda: insert_as(f.swapper_user, payload(target_employee=f.swapper)),
	)
	step(
		D,
		"create for a past shift",
		"swapper",
		lambda: insert_as(f.swapper_user, payload(shift_assignment=past, shift_date=add_days(f.today, -3))),
	)
	step(D, "create in a colleague's name", "stranger", lambda: insert_as(f.stranger_user, payload()))
	step(
		D,
		"create with status Approved smuggled in",
		"swapper",
		lambda: insert_as(f.swapper_user, payload(status="Approved")).status,
		expect=lambda v: f"status {v}, expected Pending" if v != "Pending" else None,
	)
	for name in frappe.get_all(D, filters={"requesting_employee": f.swapper}, pluck="name"):
		frappe.delete_doc(D, name, ignore_permissions=True, force=True)
	doc = step(D, "create (PWA payload)", "swapper", lambda: insert_as(f.swapper_user, payload()))
	if not doc:
		return
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	record(D, "notified on create", "-", str(_notified(D, doc.name)))
	step(
		D,
		"approve as reports_to manager",
		"approver",
		lambda: save_as(D, doc.name, f.mgr_user, status="Approved").status,
	)
	step(D, "self-approve", "swapper", lambda: save_as(D, doc.name, f.swapper_user, status="Approved").status)
	step(
		D,
		"approve as the covering employee",
		"stranger",
		lambda: save_as(D, doc.name, f.stranger_user, status="Approved").status,
	)
	step(D, "approve as HR", "hr", lambda: save_as(D, doc.name, f.hr_user, status="Approved").status)
	rows = frappe.get_all(
		"Shift Assignment",
		filters={
			"name": ["in", [assignment, frappe.db.get_value(D, doc.name, "new_shift_assignment") or ""]]
		},
		fields=["name", "employee", "docstatus", "status"],
	)
	record(D, "assignments after approve", "-", str(rows))
	record(D, "notified on approve", "-", str(_notified(D, doc.name)))
	step(
		D,
		"reverse approved swap as HR (set Rejected)",
		"hr",
		lambda: save_as(D, doc.name, f.hr_user, status="Rejected").status,
	)
	step(D, "delete approved swap as HR", "hr", lambda: frappe.delete_doc(D, doc.name))


# ---- Employee Issue --------------------------------------------------------- #
def scenario_employee_issue(f):
	D = "Employee Issue"
	P = f.personas

	def payload(**over):
		base = {
			"doctype": D,
			"employee": f.staff,
			"issue_type": "Other HR Issue",
			"urgency": "Medium",
			"details": "lp probe",
			"status": "In Progress",
		}
		base.update(over)
		return base

	doc = step(
		D,
		"create (PWA payload, status smuggled)",
		"employee",
		lambda: insert_as(f.staff_user, payload()),
		expect=lambda d: f"status {d.status}, expected Open" if d.status != "Open" else None,
	)
	if not doc:
		return
	record(D, "visibility after create", "all", str(_visibility(D, doc.name, P)))
	record(D, "notified on create (HR of the company)", "-", str(_notified(D, doc.name)))
	step(
		D,
		"employee moves status",
		"employee",
		lambda: save_as(D, doc.name, f.staff_user, status="Completed").status,
	)
	step(
		D,
		"manager moves status",
		"approver",
		lambda: save_as(D, doc.name, f.mgr_user, status="Completed").status,
	)
	step(
		D,
		"fenced HR (other company) moves status",
		"hr_other_co",
		lambda: save_as(D, doc.name, f.hr_other_user, status="In Progress").status,
	)
	step(D, "HR moves status", "hr", lambda: save_as(D, doc.name, f.hr_user, status="In Progress").status)
	record(D, "notified on status change", "-", str(_notified(D, doc.name)))
	step(D, "HR completes", "hr", lambda: save_as(D, doc.name, f.hr_user, status="Completed").status)
	step(D, "create in a colleague's name", "stranger", lambda: insert_as(f.stranger_user, payload()))
	step(
		D,
		"HR files on behalf",
		"hr",
		lambda: insert_as(f.hr_user, payload()).owner,
		expect=lambda owner: f"owner {owner}, expected the employee" if owner != f.staff_user else None,
	)
	step(D, "create for a Left employee", "left", lambda: insert_as(f.left_user, payload(employee=f.left)))


SCENARIOS = (
	scenario_leave,
	scenario_attendance_request,
	scenario_shift_request,
	scenario_comp_leave,
	scenario_remote_checkin,
	scenario_employee_advance,
	scenario_expense_claim,
	scenario_ot,
	scenario_rl_claim,
	scenario_shift_swap,
	scenario_employee_issue,
)


def run(out_path=None, only=None):
	ROWS.clear()
	frappe.set_user("Administrator")
	frappe.db.savepoint(SAVEPOINT)
	try:
		f = build_fixture()
		for scenario in SCENARIOS:
			if only and scenario.__name__ not in only:
				continue
			try:
				scenario(f)
			except Exception:
				record(scenario.__name__, "SCENARIO CRASH", "-", "ERROR " + traceback.format_exc()[-600:])
			frappe.set_user("Administrator")
	finally:
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.clear_cache()
	lines = ["| doctype | step | persona | result |", "|---|---|---|---|"]
	lines += [f"| {d} | {s} | {p} | {r} |" for d, s, p, r in ROWS]
	text = "\n".join(lines)
	if out_path:
		with open(out_path, "w") as fh:
			fh.write(text + "\n")
	return ROWS
