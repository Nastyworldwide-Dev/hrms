"""Synthetic manager + six reports on today, for capturing the Calendar day
sheet's team list. `make` returns the login; `drop` deletes every row it made.

    bench --site <site> execute hrms.tests.probes.day_sheet_team_fixture.make --kwargs '{"password": "..."}'
    bench --site <site> execute hrms.tests.probes.day_sheet_team_fixture.drop
"""

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, nowdate

TAG = "DaySheetProbe"
BOSS = "daysheet.probe.boss@example.invalid"


def make(password):
	drop()
	company = frappe.db.get_value("Company", {}, "name")
	gender = frappe.db.get_value("Gender", {}, "name")
	shift = frappe.db.get_value("Shift Type", {}, "name")
	u = frappe.get_doc(
		{
			"doctype": "User",
			"email": BOSS,
			"first_name": f"{TAG} Senior",
			"send_welcome_email": 0,
			"new_password": password,
		}
	)
	u.append("roles", {"role": "Employee"})
	u.flags.ignore_permissions = True
	u.insert()

	def employee(first, reports_to=None, user=None):
		doc = frappe.new_doc("Employee")
		doc.update(
			{
				"first_name": first,
				"last_name": TAG,
				"company": company,
				"gender": gender,
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
				"reports_to": reports_to,
				"default_shift": shift,
				"designation": None,
			}
		)
		doc.flags.ignore_permissions = doc.flags.ignore_mandatory = True
		doc.insert()
		if user:
			frappe.db.set_value("Employee", doc.name, "user_id", user, update_modified=False)
		return doc.name

	boss = employee("Senior", user=BOSS)
	now = now_datetime()
	people = ["Harith", "Azza", "Nabil", "Arif", "Diyana", "Syauqina"]
	reports = [employee(p, boss) for p in people]
	for i, name in enumerate(reports[:4]):
		frappe.db.sql(
			"""insert into `tabEmployee Checkin` (name, employee, log_type, time, creation, modified, owner)
			values (%s, %s, 'IN', %s, now(), now(), 'Administrator')""",
			(f"{TAG}-{i}", name, add_to_date(now, minutes=-40 - i * 7)),
		)
	leave_type = frappe.db.get_value("Leave Type", {}, "name")
	frappe.db.sql(
		"""insert into `tabLeave Application` (name, employee, employee_name, leave_type, from_date, to_date,
		status, docstatus, company, posting_date, creation, modified, owner)
		values (%s, %s, 'Diyana', %s, %s, %s, 'Approved', 1, %s, %s, now(), now(), 'Administrator')""",
		(f"{TAG}-LEAVE", reports[4], leave_type, nowdate(), add_days(nowdate(), 1), company, nowdate()),
	)
	frappe.db.commit()
	print("MADE", boss, len(reports))
	return BOSS


def drop():
	names = frappe.get_all("Employee", filters={"last_name": TAG}, pluck="name")
	if names:
		frappe.db.delete("Employee Checkin", {"employee": ("in", names)})
		frappe.db.delete("Leave Application", {"employee": ("in", names)})
		frappe.db.delete("Employee", {"name": ("in", names)})
	if frappe.db.exists("User", BOSS):
		frappe.delete_doc("User", BOSS, ignore_permissions=True, force=True)
	frappe.db.commit()
	print("DROPPED", len(names))
