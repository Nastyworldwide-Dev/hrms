"""Live proof of multi-site check-in (HR, 28 Sep 2026). Synthetic, rolled back.

    bench --site <site> execute hrms.tests.probes.multi_site_probe.run
"""

import frappe
from frappe.utils import add_to_date, now_datetime

A = (3.1500, 101.6200)
B = (3.1500, 101.6700)


def _site(name, point):
	doc = frappe.get_doc(
		{
			"doctype": "Shift Location",
			"location_name": name,
			"latitude": point[0],
			"longitude": point[1],
			"checkin_radius": 100,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _punch(employee, point, minutes, log_type="IN"):
	doc = frappe.new_doc("Employee Checkin")
	doc.update(
		{
			"employee": employee,
			"log_type": log_type,
			"time": add_to_date(now_datetime(), minutes=minutes),
			"latitude": point[0],
			"longitude": point[1],
		}
	)
	doc.flags.ignore_permissions = True
	doc.flags.location_accuracy_m = 10
	doc.insert()
	return frappe.db.get_value(
		"Employee Checkin",
		doc.name,
		["checked_in_at", "geofence_outcome", "requires_remote_approval", "geofence_distance_m"],
		as_dict=True,
	)


def run():
	from unittest.mock import patch

	frappe.db.savepoint("multi_site_probe")
	results = {}
	try:
		shift = frappe.db.get_value("Shift Type", {}, "name")
		company = frappe.db.get_value("Company", {}, "name")
		site_a, site_b = _site("ProbeSite A", A), _site("ProbeSite B", B)
		emp = frappe.new_doc("Employee")
		emp.update(
			{
				"first_name": "MultiSiteProbe",
				"company": company,
				"gender": frappe.db.get_value("Gender", {}, "name"),
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
				"shift_location": site_a,
				"default_shift": shift,
			}
		)
		emp.flags.ignore_permissions = emp.flags.ignore_mandatory = True
		emp.insert()
		employee = emp.name
		with patch("hrms.overrides.employee_checkin_override.is_setting_enabled_for_employee", return_value=True):
			frappe.flags.probe_shift = shift
			with patch(
				"hrms.overrides.employee_checkin_override.CustomEmployeeCheckin.fetch_shift",
				lambda self: setattr(self, "shift", shift),
				create=True,
			):
				results["not ticked, at B"] = _punch(employee, B, -300)
				frappe.db.set_value("Employee", employee, "multi_site_checkin", 1)
				emp.reload()
				emp.append("other_checkin_sites", {"shift_location": site_b})
				emp.flags.ignore_permissions = emp.flags.ignore_mandatory = True
				emp.save()
				results["ticked, at A"] = _punch(employee, A, -240, "OUT")
				results["ticked, at B"] = _punch(employee, B, -180)
				results["ticked, far"] = _punch(employee, (3.30, 101.90), -120, "OUT")
		for label, row in results.items():
			print(label, "->", dict(row))
		return {k: dict(v) for k, v in results.items()}
	finally:
		frappe.db.rollback(save_point="multi_site_probe")
