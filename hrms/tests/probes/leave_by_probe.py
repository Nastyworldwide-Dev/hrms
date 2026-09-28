"""Live: the Today card for a person in at 9:45 on a 09:00-18:00 shift. Rolled back.

    bench --site <site> execute hrms.tests.probes.leave_by_probe.run
"""

import frappe
from frappe.utils import add_to_date, now_datetime


def run(employee="HR-EMP-00009", came_in="09:45"):
	from unittest.mock import patch

	from hrms.api import now as now_api

	frappe.db.savepoint("leave_by_probe")
	try:
		today = now_datetime().date()
		h, m = map(int, came_in.split(":"))
		in_time = now_datetime().replace(year=today.year, month=today.month, day=today.day, hour=h, minute=m, second=0, microsecond=0)
		for row in frappe.get_all("Employee Checkin", filters={"employee": employee, "time": (">=", f"{today} 00:00:00")}, pluck="name"):
			frappe.db.delete("Employee Checkin", row)
		frappe.db.sql(
			"""insert into `tabEmployee Checkin` (name, employee, log_type, time, shift, shift_start, shift_end,
			shift_actual_end, creation, modified, owner) values (%s,%s,'IN',%s,'Nadi W0 Day',%s,%s,%s,now(),now(),'Administrator')""",
			("LEAVEBY-PROBE", employee, in_time, f"{today} 09:00:00", f"{today} 18:00:00", f"{today} 19:00:00"),
		)
		fake_now = in_time.replace(hour=18, minute=7)
		with patch("hrms.utils.timezone.employee_now", return_value=fake_now), patch("hrms.api.get_current_employee", return_value=employee, create=True):
			payload = now_api.get_now()
		s = payload.get("session") or {}
		print("state", payload["state"]["key"], "| time", payload["time"], "| first_in", s.get("first_in"), "| leave_by", s.get("leave_by"))
		return s
	finally:
		frappe.db.rollback(save_point="leave_by_probe")
