"""Every request type, both sides, on a real site: can staff file it, does the
right approver see it, can they approve AND decline it, does staff see the result.

Run (disposable, everything is rolled back at the end; 87 checks, 24 Sep 2026: 0 fail):
    cd ~/verify-bench && bench --site fresh.local execute hrms.scripts_journey.run
(the runner copies this file to hrms/scripts_journey.py for the call, then removes it)

Uses the W0 fixture on fresh.local:
    W0 employee  (HR-EMP-00009)  leave_approver = W0 approver, reports_to = W0 manager
Every call goes through the SAME whitelisted methods the PWA calls, as the
signed-in person, so permission and routing are tested, not bypassed.
"""

import logging
import traceback

import frappe
from frappe.utils import add_days, getdate, nowdate

log = logging.getLogger(__name__)

STAFF = "nadi.w0.employee@example.invalid"
APPROVER = "nadi.w0.approver@example.invalid"
MANAGER = "nadi.w0.manager@example.invalid"
OUTSIDER = "nadi.w0.ceo@example.invalid"
EMP = "HR-EMP-00009"
COMPANY = "Nadi W0 A"

RESULTS = []


def say(*a):
	log.info(" ".join(str(x) for x in a))
	print(*a)


def step(kind, name, fn):
	"""One observable claim. Records PASS/FAIL with the server's own words."""
	try:
		out = fn()
		RESULTS.append((kind, name, "PASS", out if out is not None else ""))
	except Exception as e:
		msg = (getattr(e, "message", None) or str(e) or type(e).__name__).strip().splitlines()[-1][:160]
		RESULTS.append((kind, name, "FAIL", f"{type(e).__name__}: {msg}"))
		log.debug(traceback.format_exc())
		frappe.local.message_log = []
		return None
	return out


def as_user(user, fn, *args, **kwargs):
	frappe.set_user(user)
	try:
		return fn(*args, **kwargs)
	finally:
		frappe.set_user("Administrator")


def insert_as(user, doc):
	"""What the PWA does: frappe.client.insert as the person (no permission bypass)."""
	from frappe.client import insert

	return as_user(user, insert, doc)


def queue_of(user):
	from hrms.api.approvals_list import get_waiting_for_me

	rows = as_user(user, get_waiting_for_me)["rows"]
	return {(r["doctype"], r["name"]) for r in rows}, rows


def decide_as(user, doctype, name, status, reason=None):
	from hrms.api.approval import decide

	frappe.db.savepoint("decide")
	try:
		return as_user(user, decide, doctype=doctype, name=name, status=status, reason=reason)
	except Exception:
		frappe.db.rollback(save_point="decide")
		raise


def staff_sees(doctype, name, want):
	from frappe.client import get

	doc = as_user(STAFF, get, doctype, name)
	from hrms.api.approval import decision_field

	got = doc.get(decision_field(doctype))
	assert got == want and doc.get("docstatus") == 1, f"staff sees {got} docstatus={doc.get('docstatus')}"
	return got


def journey(kind, doctype, build, approver=APPROVER):
	"""File two of `doctype` as staff; approver approves one, declines the other."""
	docs = []
	for i in range(2):
		d = step(kind, f"staff files #{i + 1}", lambda i=i: insert_as(STAFF, build(i)))
		if d:
			docs.append(d["name"])
	if len(docs) < 2:
		return
	names, rows = queue_of(approver)
	step(
		kind,
		"approver sees both in Approvals",
		lambda: _assert(
			all((doctype, n) in names for n in docs),
			f"queue has {len([n for n in docs if (doctype, n) in names])}/2",
		),
	)
	row = next((r for r in rows if r["name"] == docs[0]), {})
	step(
		kind,
		"row says who/what in plain words",
		lambda: (
			_assert(row.get("kind") and row.get("who") and row.get("detail"), f"row {row}")
			or f"{row.get('kind')} · {row.get('who')} · {row.get('when')} · {row.get('detail')}"
		),
	)
	outsider_names, _ = queue_of(OUTSIDER)
	step(
		kind,
		"an unrelated person does NOT see it",
		lambda: _assert(not any((doctype, n) in outsider_names for n in docs), "outsider sees it"),
	)
	step(
		kind,
		"outsider cannot approve",
		lambda: _expect_refusal(lambda: decide_as(OUTSIDER, doctype, docs[0], "Approved")),
	)
	step(
		kind,
		"staff cannot approve own",
		lambda: _expect_refusal(lambda: decide_as(STAFF, doctype, docs[0], "Approved")),
	)
	from hrms.api.approval import get_decision_actions

	offered = as_user(approver, get_decision_actions, doctype, docs[0]).get("actions", [])
	step(
		kind,
		"approver's sheet shows Approve + Reject",
		lambda: _assert({"Approved", "Rejected"} <= set(offered), f"offered {offered}") or ", ".join(offered),
	)
	step(
		kind,
		"decline needs a reason",
		lambda: _expect_refusal(lambda: decide_as(approver, doctype, docs[1], "Rejected")),
	)
	step(
		kind,
		"approver APPROVES",
		lambda: decide_as(approver, doctype, docs[0], "Approved") and "ok",
	)
	step(
		kind,
		"approver DECLINES with reason",
		lambda: decide_as(approver, doctype, docs[1], "Rejected", reason="Journey check") and "ok",
	)
	step(kind, "staff sees Approved", lambda: staff_sees(doctype, docs[0], "Approved"))
	step(kind, "staff sees Rejected", lambda: staff_sees(doctype, docs[1], "Rejected"))
	after, _ = queue_of(approver)
	step(
		kind,
		"decided rows leave the queue",
		lambda: _assert(not any((doctype, n) in after for n in docs), "still queued"),
	)


def _assert(cond, msg):
	if not cond:
		raise AssertionError(msg)
	return None


def _expect_refusal(fn):
	try:
		fn()
	except (frappe.PermissionError, frappe.ValidationError) as e:
		frappe.local.message_log = []
		return f"refused ({type(e).__name__})"
	raise AssertionError("was allowed")


def _day(n):
	# Working days in the past: requests about the past are the common case.
	return add_days(getdate(nowdate()), -n)


def run():
	frappe.flags.mute_emails = True
	frappe.db.savepoint("journey")
	try:
		_run()
	finally:
		frappe.db.rollback(save_point="journey")
		frappe.set_user("Administrator")
	_report()


def _fixture():
	"""What a configured site already has. Inside the rollback, so nothing persists."""
	hla = frappe.new_doc("Holiday List Assignment")
	hla.update(
		{
			"holiday_list": "Nadi W0 2026",
			"assigned_to": COMPANY,
			"applicable_for": "Company",
			"from_date": "2026-01-01",
		}
	)
	hla.flags.ignore_permissions = True
	hla.insert()
	hla.submit()
	acct = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_type": "Payable", "is_group": 0}, "name"
	)
	exp = frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Expense", "is_group": 0}, "name")
	frappe.db.set_value("Company", COMPANY, "default_expense_claim_payable_account", acct)
	t = frappe.get_doc("Expense Claim Type", "Travel")
	if not any(a.company == COMPANY for a in t.accounts):
		t.append("accounts", {"company": COMPANY, "default_account": exp})
		t.flags.ignore_permissions = True
		t.save()
	for n in (10, 11):
		day = _day(n)
		for tm, lt in (("08:55:00", "IN"), ("20:05:00", "OUT")):
			c = frappe.new_doc("Employee Checkin")
			c.update({"employee": EMP, "time": f"{day} {tm}", "log_type": lt})
			c.flags.ignore_permissions = True
			c.insert()
	# The nightly job turns punches into Attendance; OT and replacement leave are
	# priced from that. Built the way the job builds it (the controller computes
	# ot_hours from the punches), not by writing a number in.
	frappe.db.set_value("Employee", EMP, "eligible_for_overtime_pay", 1)
	# Nadi's own overtime switch on the shift (Overtime tab), as HR sets it.
	st = frappe.get_doc("Shift Type", "Nadi W0 Day")
	st.enable_overtime = 1
	st.set("overtime_rates", [{"day_type": "Normal Day", "from_hour": 0, "to_hour": 24, "rate": 1.5}])
	st.flags.ignore_permissions = True
	st.save()
	frappe.clear_document_cache("Shift Type", "Nadi W0 Day")
	# Time off in lieu is for working on a rest day: make two past days holidays.
	hl = frappe.get_doc("Holiday List", "Nadi W0 2026")
	for n in (60, 61):
		hl.append("holidays", {"holiday_date": _day(n), "description": "journey rest day"})
	hl.flags.ignore_permissions = True
	hl.save()
	for n in (10, 11):
		a = frappe.new_doc("Attendance")
		a.update(
			{
				"employee": EMP,
				"attendance_date": _day(n),
				"status": "Present",
				"company": COMPANY,
				"shift": "Nadi W0 Day",
			}
		)
		a.flags.ignore_permissions = True
		a.insert()
		a.submit()
		say("attendance", _day(n), "ot_hours", frappe.db.get_value("Attendance", a.name, "ot_hours"))
	say("fixture: company holidays, expense accounts", acct, exp, "punches on", _day(10), _day(11))


def _run():
	_fixture()
	routing()
	# Routing facts the PWA offers the employee (the approver pickers).
	from hrms.api import get_shift_request_approvers

	step(
		"setup", "shift approvers offered to staff", lambda: as_user(STAFF, get_shift_request_approvers, EMP)
	)

	journey(
		"Time off",
		"Leave Application",
		lambda i: {
			"doctype": "Leave Application",
			"employee": EMP,
			"company": COMPANY,
			"leave_type": "Nadi W0 Annual",
			"from_date": _day(40 + i * 3),
			"to_date": _day(40 + i * 3),
			"leave_approver": APPROVER,
			"description": "journey",
		},
	)
	journey(
		"Fix a day",
		"Attendance Request",
		lambda i: {
			"doctype": "Attendance Request",
			"employee": EMP,
			"company": COMPANY,
			"from_date": _day(20 + i),
			"to_date": _day(20 + i),
			"reason": "On Duty",
			"explanation": "journey",
		},
	)
	journey(
		"Shift change",
		"Shift Request",
		lambda i: {
			"doctype": "Shift Request",
			"employee": EMP,
			"company": COMPANY,
			"shift_type": "NP Night 19-4",
			"from_date": add_days(getdate(nowdate()), 30 + i * 3),
			"to_date": add_days(getdate(nowdate()), 30 + i * 3),
			"approver": MANAGER,
		},
		approver=MANAGER,
	)
	journey(
		"Expense",
		"Expense Claim",
		lambda i: {
			"doctype": "Expense Claim",
			"employee": EMP,
			"company": COMPANY,
			"expense_approver": MANAGER,
			"posting_date": nowdate(),
			"exchange_rate": 1,
			"currency": "MYR",
			"cost_center": frappe.db.get_value("Company", COMPANY, "cost_center"),
			"expenses": [
				{
					"expense_date": _day(3),
					"expense_type": "Travel",
					"cost_center": frappe.db.get_value("Company", COMPANY, "cost_center"),
					"amount": 10 + i,
					"sanctioned_amount": 10 + i,
				}
			],
		},
		approver=MANAGER,
	)
	journey(
		"Overtime",
		"OT Request",
		lambda i: {
			"doctype": "OT Request",
			"employee": EMP,
			"company": COMPANY,
			"ot_date": _day(10 + i),
			"claimed_hours": 1,
			"reason": "journey",
		},
	)
	# Not filed from Nadi: Time off in lieu is created in Desk, and Replacement
	# Leave Claim is retired (HR policy 23 Sep: no banked overtime). Only the
	# APPROVER side must still work, for the ones that exist.
	approver_only(
		"Time off in lieu (filed in Desk)",
		"Compensatory Leave Request",
		{
			"doctype": "Compensatory Leave Request",
			"employee": EMP,
			"leave_type": "Nadi W0 Annual",
			"work_from_date": _day(60),
			"work_end_date": _day(60),
			"reason": "journey",
		},
	)


def _report():
	say("\n=== JOURNEY: every request type, staff -> approver -> staff ===")
	kinds = []
	for k, *_ in RESULTS:
		if k not in kinds:
			kinds.append(k)
	fails = 0
	for k in kinds:
		say(f"\n{k}")
		for kk, name, verdict, detail in RESULTS:
			if kk != k:
				continue
			fails += verdict == "FAIL"
			say(f"  {verdict:4}  {name:38} {str(detail)[:110]}")
	say(f"\nTOTAL {len(RESULTS)} checks, {fails} FAIL")


def approver_only(kind, doctype, doc):
	from hrms.api.approval import get_decision_actions

	if not frappe.db.exists("Leave Period", {"company": COMPANY, "is_active": 1}):
		lp = frappe.new_doc("Leave Period")
		lp.update({"from_date": "2026-01-01", "to_date": "2026-12-31", "company": COMPANY, "is_active": 1})
		lp.flags.ignore_permissions = True
		lp.insert()
	# The day worked must be a rest day the employee was present on.
	a = frappe.new_doc("Attendance")
	a.update(
		{"employee": EMP, "attendance_date": doc["work_from_date"], "status": "Present", "company": COMPANY}
	)
	a.flags.ignore_permissions = True
	a.insert()
	a.submit()
	d = frappe.get_doc(doc)
	d.flags.ignore_permissions = True
	name = step(kind, "HR files it in Desk", lambda: d.insert() and d.name)
	if not name:
		return
	names, _ = queue_of(APPROVER)
	step(kind, "approver sees it", lambda: _assert((doctype, name) in names, "missing"))
	offered = as_user(APPROVER, get_decision_actions, doctype, name).get("actions", [])
	step(
		kind,
		"approver's sheet shows Approve + Reject",
		lambda: _assert({"Approved", "Rejected"} <= set(offered), f"offered {offered}") or "both",
	)
	step(kind, "approver APPROVES", lambda: decide_as(APPROVER, doctype, name, "Approved") and "ok")


def routing():
	"""The routing cases that break in real life, beyond the direct approver."""
	from hrms.api.approval import get_decision_actions

	def leave(i):
		return insert_as(
			STAFF,
			{
				"doctype": "Leave Application",
				"employee": EMP,
				"company": COMPANY,
				"leave_type": "Nadi W0 Annual",
				"from_date": _day(70 + i),
				"to_date": _day(70 + i),
				"leave_approver": APPROVER,
				"description": "routing",
			},
		)["name"]

	k = "Routing"
	a = step(k, "file time off to the named approver", lambda: leave(0))
	if not a:
		return
	# The manager above them (reports_to) can step in when the approver forgets.
	names, _ = queue_of(MANAGER)
	step(
		k,
		"manager up the chain sees it (Other teams)",
		lambda: _assert(("Leave Application", a) in names, "not in manager queue"),
	)
	offered = as_user(MANAGER, get_decision_actions, "Leave Application", a).get("actions", [])
	step(
		k,
		"manager up the chain may decide",
		lambda: _assert("Approved" in offered, f"offered {offered}") or "yes",
	)
	# HR sees every company (ruling 23 Sep).
	hr_names, _ = queue_of("nadi.w0.hr@example.invalid")
	step(k, "HR sees it", lambda: _assert(("Leave Application", a) in hr_names, "not in HR queue") or "yes")
	# Two approvers deciding at once: the second gets the first one's answer, not a duplicate.
	step(k, "approver approves", lambda: decide_as(APPROVER, "Leave Application", a, "Approved") and "ok")
	step(
		k,
		"a second decision cannot overturn it",
		lambda: _expect_refusal(
			lambda: decide_as(MANAGER, "Leave Application", a, "Rejected", reason="late")
		),
	)
	step(
		k,
		"same decision twice is harmless",
		lambda: decide_as(MANAGER, "Leave Application", a, "Approved") and "no-op",
	)

	# Remote check-in: punch outside the area, the approver decides it in the same queue.
	from hrms.api import remote_checkin as rc

	# A real punch the geofence flagged; the after_insert hook files the request.
	ck = frappe.new_doc("Employee Checkin")
	ck.update({"employee": EMP, "time": f"{_day(1)} 09:00:00", "log_type": "IN"})
	ck.flags.ignore_permissions = True
	ck.insert()
	req = frappe.new_doc("Remote Checkin Request")
	req.update(
		{
			"employee": EMP,
			"checkin": ck.name,
			"checkin_time": ck.time,
			"log_type": "IN",
			"distance_m": 900,
			"reason": "Outside Radius",
			"status": "Pending",
			"approver": APPROVER,
		}
	)
	req.flags.ignore_permissions = True
	req.flags.ignore_mandatory = True
	r = step(k, "remote check-in filed", lambda: req.insert() and req.name)
	if r:
		names, _ = queue_of(APPROVER)
		step(
			k,
			"approver sees the remote check-in",
			lambda: _assert(("Remote Checkin Request", r) in names, "missing"),
		)
		step(
			k, "outsider cannot decide it", lambda: _expect_refusal(lambda: as_user(OUTSIDER, rc.approve, r))
		)
		step(k, "approver approves it", lambda: as_user(APPROVER, rc.approve, r) and "ok")
		step(
			k,
			"stored as Approved",
			lambda: _assert(
				frappe.db.get_value("Remote Checkin Request", r, "status") == "Approved", "not approved"
			),
		)
