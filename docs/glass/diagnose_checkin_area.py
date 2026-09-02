"""Diagnose "No check-in area set for your shift" for ONE employee, on the LIVE
site. Read-only. Run on the live bench:

    bench --site <your-live-site> console
    >>> exec(
    ...     open("apps/hrms/docs/glass/diagnose_checkin_area.py").read(),
    ...     {"EMAIL": "mirza.hakim@yourcompany.com"},
    ... )

Set EMAIL to the person's login email (the MS365 SSO email). It prints exactly
which link in the chain is broken and what the resolver returns.
"""

import frappe

EMAIL = globals().get("EMAIL") or "PUT_THE_LOGIN_EMAIL_HERE"
print("\n==== CHECK-IN AREA DIAGNOSIS for", EMAIL, "====\n")

# 1) User -> Employee (SSO email must match Employee.user_id)
emp = frappe.db.get_value(
	"Employee",
	{"user_id": EMAIL},
	["name", "employee_name", "status", "company", "department", "shift_location"],
	as_dict=True,
)
if not emp:
	print("FAIL 1) No Employee has user_id =", EMAIL)
	print("      -> The SSO login email does not match any Employee.user_id.")
	print("      -> HR fix: set that email as user_id on the Employee record.")
	raise SystemExit
print("OK   1) Employee:", emp.name, "|", emp.employee_name, "| status:", emp.status)
print("        company:", emp.company, "| department:", emp.department)
print("        Employee.shift_location:", emp.shift_location or "(NOT SET)")

from frappe.utils import nowdate

# 2) Active Shift Assignment today
rows = frappe.get_all(
	"Shift Assignment",
	filters={"employee": emp.name, "docstatus": 1, "status": "Active", "start_date": ["<=", nowdate()]},
	or_filters=[["end_date", ">=", nowdate()], ["end_date", "is", "not set"]],
	fields=["name", "shift_type", "shift_location", "enable_strict_geofence", "start_date", "end_date"],
	order_by="start_date desc",
)
if not rows:
	print("FAIL 2) NO active Shift Assignment for today.")
	print("      -> Even with Employee.shift_location set, the current resolver")
	print("         needs an active assignment. HR fix: assign a shift (Shift")
	print("         Assignment or a Shift Location rule that materialises one).")
	raise SystemExit
sa = rows[0]
print("OK   2) Active Shift Assignment:", sa.name, "| shift_type:", sa.shift_type)
print("        assignment.shift_location:", sa.shift_location or "(NOT SET)")
print("        strict_geofence:", bool(sa.enable_strict_geofence))

# 3) Effective shift location (assignment's, else Employee's) — the deployed fix
loc_name = sa.shift_location or emp.shift_location
if not loc_name:
	print("FAIL 3) Neither the assignment NOR the Employee has a Shift Location.")
	print("      -> HR fix: set Employee.shift_location = Damansara (or put the")
	print("         Shift Location on the Shift Assignment).")
	raise SystemExit
print("OK   3) Effective Shift Location:", loc_name)

# 4) Shift Location coordinates
loc = frappe.db.get_value(
	"Shift Location",
	loc_name,
	["name", "location_name", "latitude", "longitude", "checkin_radius"],
	as_dict=True,
)
if not loc or loc.latitude is None or loc.longitude is None:
	print("FAIL 4) Shift Location", loc_name, "has NO latitude/longitude saved.")
	print("      -> HR fix: open the Shift Location, set the map pin / coordinates + radius.")
	raise SystemExit
print("OK   4) Coordinates:", loc.latitude, loc.longitude, "| radius:", loc.checkin_radius, "m")

# 5) Geolocation enabled for the company?
from hrms.utils.company_settings import is_setting_enabled_for_employee

geo_on = is_setting_enabled_for_employee(emp.name, "allow_geolocation_tracking")
print(("OK   5)" if geo_on else "WARN 5)"), "allow_geolocation_tracking:", bool(geo_on))

# 6) What the PWA actually receives
try:
	from hrms.api.geofence import get_active_shift_location

	frappe.set_user(EMAIL)
	res = get_active_shift_location(emp.name)
	frappe.set_user("Administrator")
	print("\n==== RESOLVER RESULT (what Nadi shows) ====")
	print(res if res else "None  -> Nadi shows 'No check-in area set'")
	if res:
		print("\n=> With the latest build deployed, this employee WILL see the geofence.")
	else:
		print("\n=> Still None. If this is the OLD build, deploy the fix. If it's the")
		print("   NEW build and you got here, the missing link is printed above.")
except Exception as e:
	frappe.set_user("Administrator")
	print("resolver call error (are you on the latest build?):", str(e)[:200])
