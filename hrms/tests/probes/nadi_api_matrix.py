"""Nadi PWA API call matrix — every whitelisted hrms.api endpoint the PWA calls,
called as every persona, with the PWA's real argument shape.

NOT a unit test and NOT run by the suite. It needs a real bench and a site;
run it inside `bench console` (the console executes the file with exec):

    cd ~/verify-bench
    printf 'exec(open("%s").read(), globals())\\n' \\
        /path/to/hrms/tests/probes/nadi_api_matrix.py > /tmp/in.txt
    HRMS_WORKTREE=/path/to/worktree bench --site fresh.local console < /tmp/in.txt

Everything it creates lives under ONE savepoint that is always rolled back,
and every single call runs under its own inner savepoint, so a write endpoint
(withdraw, mark-as-read) never leaks into the next persona's row. Fixture
names carry the `nadiaud.` prefix so a leaked row is recognisable.

What each row checks:
  (a) outcome class — OK / PERM / VALID / NOTFOUND are clean; ERR:<Type> is a
      500 (TypeError, AttributeError, KeyError ...) and is always a finding.
  (b) fence — the EXPECTED class per persona for endpoints that name an
      employee (own / colleague / direct report / other company). A row whose
      outcome differs from its expectation is printed under MISMATCHES.
  (c) missing required params — one pass calling each endpoint with no args.
  (d) list bounds — length of every list answer, printed when > 50.
  (e) guest — whitelist membership without allow_guest (the handler refuses
      Guest before the body runs, so this is a static check).

Personas: plain employee; colleague (same company, reports to mgr, named
leave/shift approver = appr); mgr (reports_to of peer); appr (named approver
of peer, manages nobody); HR User (unfenced); HR Manager (unfenced, "across
companies"); HR User fenced to company A (allow=Company User Permission);
System Manager who is also an employee; foreign employee (company B); Guest.
"""

import base64
import os
import sys
import traceback

import frappe

WT = os.environ.get("HRMS_WORKTREE")
if WT:
	import hrms

	hrms.__path__.insert(0, WT + "/hrms")
	for key in [k for k in sys.modules if k.startswith("hrms.")]:
		del sys.modules[key]
	frappe.controllers = {}

import hrms.api as api
from hrms.api import approval, geofence, helpdesk, hr_contacts, kpi, remote_checkin, sop, team
from hrms.api import erp_instance as erp

PREFIX = "nadiaud"
COMPANY_A = os.environ.get("HRMS_PROBE_COMPANY_A") or "Nadi W0 A"
COMPANY_B = os.environ.get("HRMS_PROBE_COMPANY_B") or "Nadi W0 B"

CLEAN = {"OK", "PERM", "VALID", "NOTFOUND"}


def classify(exc):
	if exc is None:
		return "OK"
	if isinstance(exc, frappe.PermissionError):
		return "PERM"
	if isinstance(exc, frappe.DoesNotExistError):
		return "NOTFOUND"
	if isinstance(exc, frappe.ValidationError):
		return "VALID"
	return "ERR:" + type(exc).__name__


def main():
	rows = []  # (persona, label, outcome, expected, note)

	frappe.db.savepoint(PREFIX)
	try:
		f = build_fixtures()
		matrix(f, rows)
		missing_params(f, rows)
		guest_check(rows)
	finally:
		frappe.db.rollback(save_point=PREFIX)
		frappe.set_user("Administrator")

	report(rows)


# --------------------------------------------------------------------------- fixtures


def _user(email, roles=()):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.add_roles("Employee", *roles)
	return email


def _employee(email, company, **extra):
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
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert()
	frappe.db.set_value("Employee", doc.name, "user_id", email, update_modified=False)
	return doc.name


def build_fixtures():
	f = frappe._dict()
	mail = lambda who: f"{PREFIX}.{who}@example.invalid"  # noqa: E731
	f.emp_u = _user(mail("emp"))
	f.mgr_u = _user(mail("mgr"))
	f.appr_u = _user(mail("appr"))
	f.peer_u = _user(mail("peer"))
	f.hr_user_u = _user(mail("hruser"), ["HR User"])
	f.hr_mgr_u = _user(mail("hrmgr"), ["HR Manager", "HR User"])
	f.hr_fenced_u = _user(mail("hrfenced"), ["HR User"])
	f.sysman_u = _user(mail("sysman"), ["System Manager"])
	f.foreign_u = _user(mail("foreign"))

	f.emp = _employee(f.emp_u, COMPANY_A)
	f.mgr = _employee(f.mgr_u, COMPANY_A)
	f.appr = _employee(f.appr_u, COMPANY_A)
	f.peer = _employee(
		f.peer_u,
		COMPANY_A,
		reports_to=f.mgr,
		leave_approver=f.appr_u,
		shift_request_approver=f.appr_u,
		expense_approver=f.appr_u,
	)
	f.hr_user = _employee(f.hr_user_u, COMPANY_A)
	f.hr_mgr = _employee(f.hr_mgr_u, COMPANY_A)
	f.hr_fenced = _employee(f.hr_fenced_u, COMPANY_A)
	f.sysman = _employee(f.sysman_u, COMPANY_A)
	f.foreign = _employee(f.foreign_u, COMPANY_B)

	frappe.get_doc(
		{"doctype": "User Permission", "user": f.hr_fenced_u, "allow": "Company", "for_value": COMPANY_A}
	).insert(ignore_permissions=True)

	f.notification = frappe.get_doc(
		{
			"doctype": "PWA Notification",
			"to_user": f.emp_u,
			"from_user": f.mgr_u,
			"message": "probe",
			"reference_document_type": "Employee",
			"reference_document_name": f.emp,
		}
	).insert(ignore_permissions=True)

	f.shift_type = frappe.get_all("Shift Type", pluck="name", limit=1)[0]
	f.shift_request = None
	try:
		doc = frappe.get_doc(
			{
				"doctype": "Shift Request",
				"employee": f.peer,
				"shift_type": f.shift_type,
				"from_date": frappe.utils.add_days(frappe.utils.nowdate(), 30),
				"to_date": frappe.utils.add_days(frappe.utils.nowdate(), 31),
				"approver": f.appr_u,
			}
		)
		doc.flags.ignore_permissions = True
		frappe.set_user(f.peer_u)
		doc.insert()
		f.shift_request = doc.name
	except Exception as exc:  # the decision rows are skipped, the rest still runs
		f.shift_request_error = f"{type(exc).__name__}: {exc}"
	finally:
		frappe.set_user("Administrator")
	frappe.clear_cache()
	return f


# --------------------------------------------------------------------------- matrix

PERSONAS = ("emp", "peer", "mgr", "appr", "hr_user", "hr_mgr", "hr_fenced", "sysman", "foreign")


def call(persona, f, label, fn, rows, expected=None, **kwargs):
	frappe.set_user(f[persona + "_u"])
	frappe.local.response = frappe._dict()
	if hasattr(frappe.local, "_hrms_attendance_tz"):
		del frappe.local._hrms_attendance_tz
	frappe.db.savepoint("nadiaud_call")
	exc, result, note = None, None, ""
	try:
		result = fn(**kwargs)
	except Exception as e:  # classification is the point
		exc = e
		note = str(e)[:90].replace("\n", " ")
		if classify(e).startswith("ERR"):
			note = traceback.format_exc().strip().splitlines()[-1][:120]
	finally:
		frappe.db.rollback(save_point="nadiaud_call")
		frappe.clear_messages()
	outcome = classify(exc)
	if outcome == "OK" and isinstance(result, list):
		note = f"{len(result)} rows"
	rows.append((persona, label, outcome, expected, note))
	return result


def fence_expect(persona, target):
	"""Expected class for an employee-scoped read (`_ensure_own_employee_or_permitted`)."""
	if target == "self":
		return "OK"
	if target == "peer":  # same company; reports to mgr; appr is the named approver
		return "OK" if persona in ("mgr", "appr", "hr_user", "hr_mgr", "hr_fenced") else "PERM"
	if target == "foreign":  # other company
		return "OK" if persona in ("hr_user", "hr_mgr") else "PERM"
	raise ValueError(target)


EMPLOYEE_READS = [
	(
		"get_attendance_calendar_events",
		lambda e: dict(employee=e, from_date="2026-09-01", to_date="2026-09-30"),
	),
	("get_shift_requests", lambda e: dict(employee=e, limit=10)),
	("get_attendance_requests", lambda e: dict(employee=e, limit=10)),
	("get_ot_requests", lambda e: dict(employee=e, limit=10)),
	("get_replacement_leave_claims", lambda e: dict(employee=e, limit=10)),
	("get_leave_applications", lambda e: dict(employee=e, limit=10)),
	("get_expense_claims", lambda e: dict(employee=e, limit=10)),
	("get_ot_claim_summary", lambda e: dict(employee=e, date="2026-09-10")),
	("get_claimable_ot_summary", lambda e: dict(employee=e)),
	("get_replacement_leave_bank_summary", lambda e: dict(employee=e)),
	("get_shift_request_approvers", lambda e: dict(employee=e)),
	("get_shifts", lambda e: dict(employee=e)),
	("get_holidays_for_employee", lambda e: dict(employee=e)),
	("get_leave_approval_details", lambda e: dict(employee=e)),
	("get_expense_approval_details", lambda e: dict(employee=e)),
	("get_expense_claim_summary", lambda e: dict(employee=e)),
	("get_leave_types", lambda e: dict(employee=e, date="2026-09-15")),
	(
		"geofence.check_geofence",
		lambda e: dict(employee=e, log_type="IN", latitude=3.1, longitude=101.6, accuracy=20),
	),
	("geofence.get_active_shift_location", lambda e: dict(employee=e)),
	("hr_contacts.get_reporting_manager", lambda e: dict(employee=e)),
]


def _resolve(label):
	mod, _, name = label.rpartition(".")
	module = {
		"": api,
		"geofence": geofence,
		"hr_contacts": hr_contacts,
		"kpi": kpi,
		"team": team,
		"remote_checkin": remote_checkin,
		"approval": approval,
		"sop": sop,
		"helpdesk": helpdesk,
		"erp_instance": erp,
	}[mod]
	return getattr(module, name)


def matrix(f, rows):
	targets = {"self": None, "peer": f.peer, "foreign": f.foreign}
	for persona in PERSONAS:
		own = f[persona]
		# (b) employee-scoped reads: own, a colleague, another company's employee
		for label, args in EMPLOYEE_READS:
			for target, emp in targets.items():
				if target != "self" and emp == own:
					continue
				expected = fence_expect(persona, target)
				if label == "get_leave_types" and target != "self":
					expected = None  # its own guard (get_leave_details) admits the leave approver too
				call(persona, f, f"{label}[{target}]", _resolve(label), rows, expected, **args(emp or own))

		# session-scoped reads and writes: must never 500 for anybody
		for label, kwargs in [
			("get_current_user_info", {}),
			("get_current_employee_info", {}),
			("get_employee_identity_status", {}),
			("get_all_employees", {}),
			("get_hr_settings", {}),
			("get_unread_notifications_count", {}),
			("mark_all_notifications_as_read", {}),
			("are_push_notifications_enabled", {}),
			("get_leave_balance_map", {}),
			("get_expense_claim_types", {}),
			("get_company_currencies", {}),
			("get_currency_symbols", {}),
			(
				"get_company_cost_center_and_expense_account[own]",
				{"company": COMPANY_A if persona != "foreign" else COMPANY_B},
			),
			("get_expense_cost_tags[own]", {"company": COMPANY_A if persona != "foreign" else COMPANY_B}),
			("get_doctype_fields", {"doctype": "Leave Application"}),
			("get_doctype_states", {"doctype": "Leave Application"}),
			("get_workflow", {"doctype": "Leave Application"}),
			("get_permitted_fields_for_write", {"doctype": "Leave Application"}),
			("get_attachments[own employee]", {"dt": "Employee", "dn": own}),
			("team.has_team", {}),
			("team.is_approver", {}),
			("team.get_managers", {}),
			("team.get_team_status", {"date": "2026-09-15"}),
			("team.get_team_roster", {"start_date": "2026-09-14", "end_date": "2026-09-20"}),
			("remote_checkin.list_pending_for_approver", {}),
			("remote_checkin.list_decided_for_approver", {"limit": 50}),
			("remote_checkin.get_pending_count", {}),
			("remote_checkin.get_unresolved_stale_in", {}),
			("sop.get_sops", {}),
			("helpdesk.is_available", {}),
			("helpdesk.list_tickets", {}),
			("helpdesk.get_options", {}),
			("hr_contacts.list_hr_contacts", {}),
			("hr_contacts.get_reporting_manager[none]", {}),
			("kpi.can_view_team_kpi", {}),
			("kpi.get_my_kpi_dashboard", {}),
			("kpi.get_employee_kpi[self]", {"employee": own}),
			("erp_instance.get_my_erp_instance", {}),
			("withdraw_request[unknown]", {"doctype": "Shift Request", "name": "nope-nadiaud"}),
			("withdraw_request[bad doctype]", {"doctype": "Employee", "name": own}),
			("mark_notification_as_read[unknown]", {"name": "nope-nadiaud"}),
			("delete_attachment[unknown]", {"filename": "nope-nadiaud"}),
			(
				"upload_base64_file[bad type]",
				{
					"content": base64.b64encode(b"x").decode(),
					"filename": "a.exe",
					"dt": "Employee",
					"dn": own,
				},
			),
			(
				"upload_base64_file[unattached]",
				{"content": base64.b64encode(b"x").decode(), "filename": "a.txt"},
			),
			("approval.get_decision_actions[unknown]", {"doctype": "Leave Application", "name": "nope"}),
			("approval.can_cancel_approved[unknown]", {"doctype": "Leave Application", "name": "nope"}),
			(
				"approval.decide[unknown]",
				{"doctype": "Leave Application", "name": "nope", "status": "Approved"},
			),
			("approval.finalize[unknown]", {"doctype": "OT Request", "name": "nope", "docstatus": 1}),
			("remote_checkin.submit_remarks[unknown]", {"request": "nope", "employee_remarks": "x"}),
			("remote_checkin.approve[unknown]", {"request": "nope"}),
			(
				"remote_checkin.submit_late_checkout[unknown]",
				{"in_checkin": "nope", "checkout_datetime": "2026-09-14 18:00:00", "reason": "x"},
			),
			(
				"remote_checkin.punch[self]",
				{"employee": own, "log_type": "IN", "latitude": 3.1, "longitude": 101.6, "accuracy": 15},
			),
			(
				"remote_checkin.punch[peer]",
				{"employee": f.peer if own != f.peer else f.emp, "log_type": "IN"},
			),
			("sop.get_sop[unknown]", {"name": "nope"}),
			("helpdesk.get_ticket[unknown]", {"name": "nope"}),
			("get_reports_to_employee_name[mgr]", {"employee": f.mgr}),
			("get_company_cost_center_and_expense_account[other]", {"company": COMPANY_B}),
			("get_expense_cost_tags[other]", {"company": COMPANY_B}),
			("kpi.get_employee_kpi[peer]", {"employee": f.peer}),
			("kpi.get_team_kpi", {}),
		]:
			expected = None
			if label == "remote_checkin.punch[peer]":
				expected = "PERM"
			if label == "get_reports_to_employee_name[mgr]":
				expected = "OK" if persona == "peer" else "PERM"
			if label in ("mark_notification_as_read[unknown]", "withdraw_request[bad doctype]"):
				expected = "PERM" if label.startswith("mark") else "VALID"
			call(persona, f, label, _resolve(label.split("[")[0]), rows, expected, **kwargs)

		# writes on real rows
		call(
			persona,
			f,
			"mark_notification_as_read[emp's]",
			api.mark_notification_as_read,
			rows,
			"OK" if persona == "emp" else "PERM",
			name=f.notification.name,
		)
		if f.shift_request:
			call(
				persona,
				f,
				"withdraw_request[peer draft]",
				api.withdraw_request,
				rows,
				"OK" if persona == "peer" else "PERM",
				doctype="Shift Request",
				name=f.shift_request,
			)
			actions = call(
				persona,
				f,
				"approval.get_decision_actions[peer draft]",
				approval.get_decision_actions,
				rows,
				"OK",
				doctype="Shift Request",
				name=f.shift_request,
			)
			if actions is not None:
				rows.append((persona, "  -> actions", str(actions.get("actions")), None, ""))
			call(
				persona,
				f,
				"approval.decide[peer draft, wrong user]",
				approval.decide,
				rows,
				# routed approvers: the named approver, the reports_to manager, HR inside the fence
				None if persona in ("mgr", "appr", "hr_user", "hr_mgr", "hr_fenced") else "PERM",
				doctype="Shift Request",
				name=f.shift_request,
				status="Rejected",
			)
			call(
				persona,
				f,
				"approval.can_cancel_approved[peer draft]",
				approval.can_cancel_approved,
				rows,
				None,
				doctype="Shift Request",
				name=f.shift_request,
			)
			call(
				persona,
				f,
				"get_attachments[peer draft]",
				api.get_attachments,
				rows,
				None,
				dt="Shift Request",
				dn=f.shift_request,
			)

	# fence content checks for the directory
	for persona, expect_companies in (("hr_fenced", {COMPANY_A}), ("hr_user", None), ("emp", None)):
		out = call(persona, f, "get_all_employees[content]", api.get_all_employees, rows, "OK")
		if out:
			companies = {r.get("company") for r in out}
			fields = set(out[0].keys())
			leak = expect_companies and not companies <= expect_companies
			rows.append(
				(
					persona,
					"  -> directory",
					f"companies={sorted(c for c in companies if c)[:4]}...",
					None,
					f"{'LEAK ' if leak else ''}fields={sorted(fields)}",
				)
			)


# --------------------------------------------------------------------------- (c) missing params

REQUIRED_PARAM_ENDPOINTS = [
	"get_ot_claim_summary",
	"get_replacement_leave_bank_summary",
	"get_shift_request_approvers",
	"get_holidays_for_employee",
	"get_leave_approval_details",
	"get_leave_types",
	"get_expense_approval_details",
	"get_company_cost_center_and_expense_account",
	"get_expense_cost_tags",
	"get_doctype_fields",
	"get_doctype_states",
	"get_attachments",
	"upload_base64_file",
	"delete_attachment",
	"get_workflow",
	"get_permitted_fields_for_write",
	"withdraw_request",
	"mark_notification_as_read",
	"get_reports_to_employee_name",
	"get_attendance_calendar_events",
	"geofence.check_geofence",
	"geofence.get_active_shift_location",
	"team.get_team_roster",
	"remote_checkin.submit_remarks",
	"remote_checkin.approve",
	"remote_checkin.reject",
	"remote_checkin.punch",
	"remote_checkin.submit_late_checkout",
	"approval.decide",
	"approval.finalize",
	"approval.get_decision_actions",
	"approval.can_cancel_approved",
	"sop.get_sop",
	"sop.remove_attachment",
	"helpdesk.get_ticket",
	"helpdesk.new_ticket",
	"helpdesk.reply",
	"kpi.get_employee_kpi",
]


def missing_params(f, rows):
	for label in REQUIRED_PARAM_ENDPOINTS:
		call("emp", f, f"{label}[no args]", _resolve(label), rows, None)


# --------------------------------------------------------------------------- (e) guest


def guest_check(rows):
	pwa_calls = [label for label, _ in EMPLOYEE_READS] + [
		"get_current_user_info",
		"get_current_employee_info",
		"get_employee_identity_status",
		"get_all_employees",
		"get_hr_settings",
		"get_unread_notifications_count",
		"mark_notification_as_read",
		"mark_all_notifications_as_read",
		"are_push_notifications_enabled",
		"withdraw_request",
		"get_leave_balance_map",
		"get_expense_claim_types",
		"get_company_currencies",
		"get_currency_symbols",
		"get_company_cost_center_and_expense_account",
		"get_expense_cost_tags",
		"get_doctype_fields",
		"get_doctype_states",
		"get_attachments",
		"upload_base64_file",
		"delete_attachment",
		"get_workflow",
		"get_permitted_fields_for_write",
		"get_reports_to_employee_name",
		"team.has_team",
		"team.is_approver",
		"team.get_managers",
		"team.get_team_status",
		"team.get_team_roster",
		"remote_checkin.list_pending_for_approver",
		"remote_checkin.list_decided_for_approver",
		"remote_checkin.get_pending_count",
		"remote_checkin.get_unresolved_stale_in",
		"remote_checkin.punch",
		"remote_checkin.approve",
		"remote_checkin.reject",
		"remote_checkin.submit_remarks",
		"remote_checkin.submit_late_checkout",
		"approval.decide",
		"approval.finalize",
		"approval.get_decision_actions",
		"approval.can_cancel_approved",
		"sop.get_sops",
		"sop.get_sop",
		"sop.remove_attachment",
		"helpdesk.is_available",
		"helpdesk.list_tickets",
		"helpdesk.get_ticket",
		"helpdesk.new_ticket",
		"helpdesk.reply",
		"helpdesk.get_options",
		"hr_contacts.list_hr_contacts",
		"kpi.can_view_team_kpi",
		"kpi.get_my_kpi_dashboard",
		"kpi.get_employee_kpi",
		"kpi.get_department_kpi",
		"kpi.get_team_kpi",
		"erp_instance.get_my_erp_instance",
	]
	for label in pwa_calls:
		fn = _resolve(label)
		whitelisted = fn in frappe.whitelisted
		guest = fn in frappe.guest_methods
		verbs = sorted(frappe.allowed_http_methods_for_whitelisted_func.get(fn, []))
		outcome = "REFUSED" if whitelisted and not guest else ("GUEST-OPEN" if guest else "NOT-WHITELISTED")
		rows.append(("guest", label, outcome, "REFUSED", ",".join(verbs)))


# --------------------------------------------------------------------------- report


def report(rows):
	out = []
	mismatches = []
	errors = []
	big = []
	for persona, label, outcome, expected, note in rows:
		out.append(f"{persona:10} {label:58} {outcome:14} {note}")
		if expected and outcome != expected:
			mismatches.append(f"{persona:10} {label:58} got {outcome:10} expected {expected}  {note}")
		if outcome.startswith("ERR") and "[no args]" not in label:
			errors.append(f"{persona:10} {label:58} {outcome:14} {note}")
		if note.endswith(" rows") and int(note.split()[0]) > 50:
			big.append(f"{persona:10} {label:58} {note}")
	print("\n".join(out))
	print(f"\n=== MISMATCHES ({len(mismatches)}) ===")
	print("\n".join(mismatches) or "none")
	print(f"\n=== 500s outside the no-args pass ({len(errors)}) ===")
	print("\n".join(errors) or "none")
	print("\n=== no-args pass ===")
	print("\n".join(f"{label:58} {outcome}" for _, label, outcome, _, _ in rows if "[no args]" in label))
	print("\n=== lists over 50 rows ===")
	print("\n".join(big) or "none")
	print(f"\nMATRIX DONE rows={len(rows)}")


main()
