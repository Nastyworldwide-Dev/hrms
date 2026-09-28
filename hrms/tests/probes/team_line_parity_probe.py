"""Live parity probe: Calendar day-sheet coverage == Team page summary, per manager.

bench --site <site> execute hrms.tests.probes.team_line_parity_probe.run
"""

import frappe
from frappe.utils import nowdate


def run(day=None, limit=5):
	from hrms.api import calendar, team

	day = day or nowdate()
	managers = frappe.db.sql(
		"""select reports_to, count(*) c from tabEmployee
		where status='Active' and ifnull(reports_to,'')!='' group by reports_to order by c desc limit %s""",
		(int(limit),),
		as_dict=True,
	)
	results = []
	for row in managers:
		user = frappe.db.get_value("Employee", row.reports_to, "user_id")
		if not user:
			continue
		frappe.set_user(user)
		try:
			cov = calendar.get_day(day).get("coverage", {})
			page = team.get_team_status(day)
		finally:
			frappe.set_user("Administrator")
		summary = page["summary"]
		ok = (
			cov.get("headcount", 0) == len(page["members"])
			and cov.get("present", 0) == summary.get("Present", 0)
			and cov.get("unmarked", 0) == summary.get("Not In Yet", 0)
			and cov.get("on_leave", 0) == summary.get("On Leave", 0)
			and cov.get("absent", 0) == summary.get("Absent", 0)
		)
		results.append(
			{
				"ok": ok,
				"manager": row.reports_to,
				"sheet": cov,
				"page": {k: v for k, v in summary.items() if v},
			}
		)
	print(frappe.as_json(results))
	return results


def scenario():
	"""The owner's 28 Sep morning, on synthetic rows, rolled back: a manager
	with three reports, two punched in, no Attendance yet. Before the fix the
	sheet said "3 not in yet"; now it must match the Team page."""
	from frappe.utils import add_to_date, now_datetime

	from hrms.api import calendar, team

	frappe.db.savepoint("team_line_parity")
	try:
		company = frappe.db.get_value("Company", {}, "name")
		shift = frappe.db.get_value("Shift Type", {}, "name")

		def employee(tag, reports_to=None):
			doc = frappe.new_doc("Employee")
			doc.update(
				{
					"first_name": f"ParityProbe {tag}",
					"company": company,
					"gender": frappe.db.get_value("Gender", {}, "name"),
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2020-01-01",
					"status": "Active",
					"reports_to": reports_to,
					"default_shift": shift,
				}
			)
			doc.flags.ignore_permissions = doc.flags.ignore_mandatory = True
			doc.insert()
			return doc.name

		user = "parity.probe.boss@example.invalid"
		if not frappe.db.exists("User", user):
			u = frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Parity", "send_welcome_email": 0}
			)
			u.flags.ignore_permissions = True
			u.insert()
		boss = employee("Boss")
		frappe.db.set_value("Employee", boss, "user_id", user, update_modified=False)
		reports = [employee(t, boss) for t in ("A", "B", "C")]
		now = now_datetime()
		for name in reports[:2]:
			frappe.db.sql(
				"""insert into `tabEmployee Checkin` (name, employee, log_type, time, creation, modified)
				values (%s, %s, 'IN', %s, now(), now())""",
				(frappe.generate_hash(length=10), name, add_to_date(now, minutes=-30)),
			)
		day = str(now.date())
		frappe.set_user(user)
		try:
			cov = calendar.get_day(day).get("coverage", {})
			summary = team.get_team_status(day)["summary"]
		finally:
			frappe.set_user("Administrator")
		ok = cov.get("present") == summary.get("Present") == 2 and cov.get("headcount") == 3
		print(("PASS" if ok else "FAIL"), "sheet", cov, "page", {k: v for k, v in summary.items() if v})
		return ok
	finally:
		frappe.db.rollback(save_point="team_line_parity")


def hr_fence():
	"""HR browsing another manager's team stays company-fenced after the
	member_statuses / own_team_members extraction: a report in a company
	outside the fence must not appear. Synthetic, rolled back."""
	from unittest.mock import patch

	from hrms.api import team

	frappe.db.savepoint("team_hr_fence")
	try:
		companies = frappe.get_all("Company", pluck="name", limit=2)
		if len(companies) < 2:
			print("SKIP need two companies")
			return None
		inside, outside = companies
		gender = frappe.db.get_value("Gender", {}, "name")

		def employee(tag, company, reports_to=None):
			doc = frappe.new_doc("Employee")
			doc.update(
				{
					"first_name": f"FenceProbe {tag}",
					"company": company,
					"gender": gender,
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2020-01-01",
					"status": "Active",
					"reports_to": reports_to,
				}
			)
			doc.flags.ignore_permissions = doc.flags.ignore_mandatory = True
			doc.insert()
			return doc.name

		boss = employee("Boss", inside)
		kept = employee("Inside", inside, boss)
		fenced = employee("Outside", outside, boss)
		with (
			patch.object(team, "_is_hr", return_value=True),
			patch.object(team, "_my_employee", return_value=None),
			patch.object(team, "allowed_companies", return_value=[inside]),
		):
			names = {m["employee"] for m in team.get_team_status(nowdate(), manager=boss)["members"]}
		ok = kept in names and fenced not in names
		print(("PASS" if ok else "FAIL"), "members", sorted(names), "kept", kept, "fenced", fenced)
		return ok
	finally:
		frappe.db.rollback(save_point="team_hr_fence")
