"""Manager team view — who is present / on leave / not in / absent on a day.

Fencing: every query below is hard-filtered to the session user's DIRECT
reports (Employee.reports_to). That fence is the security boundary, so the
reads run ignore_permissions — staff roles can't read colleague checkin times
(permlevel 1) or leave rows, but a manager may see their own reports' day
status. Users without reports get an empty payload, never an error.
"""

import logging

import frappe
from frappe import _
from frappe.utils import get_time, getdate

from hrms.hr.utils import HR_SEE_ALL_ROLES
from hrms.overrides.company_scope import allowed_companies
from hrms.utils.identity import get_employee
from hrms.utils.team_status import derive_member_status
from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)


def _my_employee() -> str | None:
	return get_employee()


def _is_hr() -> bool:
	# HR User / HR Manager only — System Manager cannot browse other teams
	user = frappe.session.user
	return user == "Administrator" or bool(HR_SEE_ALL_ROLES & set(frappe.get_roles(user)))


@frappe.whitelist()
def has_team() -> bool:
	"""Nav gate: direct reports, or HR (who browse teams via the selector)."""
	if _is_hr():
		return True
	employee = _my_employee()
	if not employee:
		logger.debug("[team] has_team: no employee for %s", frappe.session.user)
		return False
	return bool(frappe.db.exists("Employee", {"reports_to": employee, "status": "Active"}))


@frappe.whitelist()
def get_managers() -> list[dict]:
	"""HR-only selector data: active employees with ≥1 active direct report.
	Non-HR callers get [] — their view is always their own team."""
	if not _is_hr():
		return []
	# The reads below run ignore_permissions (the manager fence IS the security
	# boundary for staff), so the company fence has to be restated here: an
	# "HR (Company)" user holds HR Manager and passed _is_hr, and without this
	# the selector handed them every company's managers.
	fence = allowed_companies()
	member_filters = {"status": "Active", "reports_to": ("is", "set")}
	if fence:
		member_filters["company"] = ("in", fence)
	manager_ids = frappe.get_all(
		"Employee",
		filters=member_filters,
		pluck="reports_to",
		distinct=True,
		ignore_permissions=True,
	)
	if not manager_ids:
		return []
	manager_filters = {"name": ("in", manager_ids), "status": "Active"}
	if fence:
		# a manager may sit in a holding company outside the fence while their
		# reports are inside it; fencing the MEMBERS (above) is the data
		# boundary, fencing the manager list keeps the selector coherent
		manager_filters["company"] = ("in", fence)
	managers = frappe.get_all(
		"Employee",
		filters=manager_filters,
		fields=["name", "employee_name"],
		order_by="employee_name asc",
		ignore_permissions=True,
	)
	logger.info("[team] managers list for %s: %d", frappe.session.user, len(managers))
	return managers


@frappe.whitelist()
def get_team_status(date: str | None = None, manager: str | None = None) -> dict:
	# getdate returns None (not an exception) for some malformed strings —
	# fail closed to today instead of sending "None 00:00:00" into a filter
	day = getdate(date) or getdate()
	employee = _my_employee()
	# HR may browse any manager's team; everyone else is pinned to their own
	if manager and manager != employee and not _is_hr():
		logger.warning("[team] %s denied manager override %s", frappe.session.user, manager)
		frappe.throw(_("Only HR can view another manager's team."), frappe.PermissionError)
	team_of = manager or employee
	empty = {"date": str(day), "manager": team_of, "members": [], "summary": {}}
	if not team_of:
		return empty

	# Everything below runs ignore_permissions, so the company fence must be
	# restated at the member read — role checks alone let an "HR (Company)"
	# user browse another company's punches and leave through the override.
	# A manager browsing their OWN team is never fenced: their reports are
	# their reports whichever company employs them.
	fence = allowed_companies() if team_of != employee else []
	member_filters = {"reports_to": team_of, "status": "Active"}
	if fence:
		member_filters["company"] = ("in", fence)
	members = frappe.get_all(
		"Employee",
		filters=member_filters,
		fields=["name", "employee_name", "designation", "default_shift", "holiday_list"],
		order_by="employee_name asc",
		ignore_permissions=True,
	)
	if not members:
		return empty
	ids = [m.name for m in members]

	attendance = {
		row.employee: row
		for row in frappe.get_all(
			"Attendance",
			filters={"employee": ("in", ids), "attendance_date": day, "docstatus": ("<", 2)},
			fields=["employee", "status", "shift"],
			ignore_permissions=True,
		)
	}
	leaves = {
		row.employee: row
		for row in frappe.get_all(
			"Leave Application",
			filters={
				"employee": ("in", ids),
				"status": "Approved",
				"docstatus": 1,
				"from_date": ("<=", day),
				"to_date": (">=", day),
			},
			fields=["employee", "leave_type", "to_date", "half_day"],
			ignore_permissions=True,
		)
	}
	punches = {}
	for row in frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": ("in", ids),
			"time": ("between", [f"{day} 00:00:00", f"{day} 23:59:59"]),
		},
		fields=["employee", "log_type", "time"],
		order_by="time asc",
		ignore_permissions=True,
	):
		slot = punches.setdefault(row.employee, {"first_in": None, "last_out": None})
		if row.log_type == "IN" and not slot["first_in"]:
			slot["first_in"] = row.time
		elif row.log_type == "OUT":
			slot["last_out"] = row.time

	shift_bounds = {}

	def bounds(shift):
		if not shift:
			return (None, None)
		if shift not in shift_bounds:
			row = frappe.db.get_value("Shift Type", shift, ["start_time", "end_time"], as_dict=True)
			shift_bounds[shift] = (get_time(row.start_time), get_time(row.end_time)) if row else (None, None)
		return shift_bounds[shift]

	out = []
	summary = {"Present": 0, "On Leave": 0, "Not In Yet": 0, "Absent": 0, "Off": 0, "Scheduled": 0}
	for member in members:
		att = attendance.get(member.name)
		leave = leaves.get(member.name)
		punch = punches.get(member.name) or {}
		shift = (att and att.shift) or member.default_shift
		shift_start, shift_end = bounds(shift)
		is_holiday = bool(
			member.holiday_list
			and frappe.db.exists("Holiday", {"parent": member.holiday_list, "holiday_date": day})
		)
		# The MEMBER's wall clock, not the site's. "Has the shift ended" and
		# "is this day still today" are questions about where the member works:
		# on a Dubai site a Malaysian member's 17:00 shift end read as 13:00
		# server time, so the team view said "Not In Yet" for four hours after
		# an absence was already real — the exact skew hrms.utils.timezone
		# exists to remove. employee_now memoizes per request, so a team of N
		# costs the resolution once per member, not once per row.
		member_now = employee_now(member.name)
		member_status = derive_member_status(
			day=day,
			today=member_now.date(),
			now_time=member_now.time(),
			on_leave={"leave_type": leave.leave_type} if leave else None,
			is_holiday=is_holiday,
			attendance_status=att and att.status,
			has_checkin=bool(punch.get("first_in") or punch.get("last_out")),
			shift_start=shift_start,
			shift_end=shift_end,
		)
		summary[member_status] += 1
		out.append(
			{
				"employee": member.name,
				"employee_name": member.employee_name,
				"designation": member.designation,
				"status": member_status,
				"shift": shift,
				"shift_start": str(shift_start) if shift_start else None,
				"shift_end": str(shift_end) if shift_end else None,
				"first_in": punch.get("first_in"),
				"last_out": punch.get("last_out"),
				"leave_type": leave and leave.leave_type,
				"leave_until": str(leave.to_date) if leave else None,
				"half_day": bool(leave and leave.half_day),
			}
		)
	logger.info("[team] %s viewed team of %s on %s: %d members", frappe.session.user, team_of, day, len(out))
	return {"date": str(day), "manager": team_of, "members": out, "summary": summary}
