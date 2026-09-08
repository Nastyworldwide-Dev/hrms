# Read-only diagnostics to run on verifica-live (bench console)

I was blocked from querying live, so these are for Nabil. All read-only.
`bench --site <site> console`, then paste one block at a time.

## D1. CANDIDATE sessions hit by the inherited-approval check-out bug (30 days)
Result = candidates, not proof: an IN with no OUT can also be a forgotten
check-out. HR confirms with the employee before repair.
```python
import frappe
from frappe.utils import add_days, nowdate
since = add_days(nowdate(), -30)
reqs = frappe.get_all("Remote Checkin Request",
    filters={"log_type": "IN", "status": "Approved", "checkin_time": [">=", since]},
    fields=["employee", "employee_name", "checkin_time", "checkin", "name"], order_by="checkin_time asc")
cands = []
for r in reqs:
    # session order, not calendar day: the next punch after this IN decides
    nxt = frappe.get_all("Employee Checkin",
        filters=[["employee", "=", r.employee], ["time", ">", r.checkin_time],
                 ["remote_approval_status", "!=", "Rejected"]],
        fields=["log_type", "time"], order_by="time asc", limit_page_length=1)
    if not nxt or nxt[0].log_type != "OUT":
        cands.append((r.employee, r.employee_name, str(r.checkin_time)[:16], r.name,
                      "next punch: " + (nxt[0].log_type + " " + str(nxt[0].time)[:16] if nxt else "none")))
print(len(reqs), "approved INs;", len(cands), "candidate open sessions")
for c in cands: print(*c)
```

## D2. Geofence: is it the pin, or the phones?
```python
import frappe, collections
from frappe.utils import add_days, nowdate
from hrms.hr.utils import get_distance_between_coordinates as dist
for loc in frappe.get_all("Shift Location", fields=["name","location_name","latitude","longitude","checkin_radius"]):
    print("PIN", loc.name, loc.latitude, loc.longitude, "radius", loc.checkin_radius)
since = add_days(nowdate(), -14)
rows = frappe.get_all("Remote Checkin Request", filters={"checkin_time": [">=", since]},
    fields=["name","employee","checkin","checkin_time","distance_m","nearest_shift_location","status"])
pts = collections.Counter(); per_emp = collections.defaultdict(list)
for r in rows:
    ck = frappe.db.get_value("Employee Checkin", r.checkin, ["latitude","longitude"], as_dict=True)
    if not ck or ck.latitude is None: continue
    key = (round(float(ck.latitude), 4), round(float(ck.longitude), 4))
    pts[key] += 1; per_emp[r.employee].append((str(r.checkin_time)[:16], key, round(float(r.distance_m or 0))))
print(len(rows), "remote requests;", len(pts), "distinct rounded points")
print("TOP POINTS (same point many times = coarse/network fix, not a person):")
for k, n in pts.most_common(8): print("  ", k, "x", n)
for e, lst in list(per_emp.items())[:15]: print(e, lst[-3:])
```
Reading it (clues, not proof): many punches on ONE identical coordinate
1-2 km from the pin SUGGESTS an approximate (network/IP) position — fixed
terminals and cached fixes repeat coordinates too. Points scattered around
the pin at a roughly constant offset SUGGESTS the pin is off. Compare the
pin against Google Maps for the actual building.

## D3. Accuracy values the server saw (Frappe Cloud log search)
Search the site logs (worker + web) for the last 7 days:
`Remote check-in flagged` and `geofence] route to remote approval` — each line
carries `accuracy=<m>`. Values of 1000-3000 m confirm approximate location.

## D4. Why 7 Sep has no attendance on the calendar (employee "S")
```python
import frappe
emp = "<EMPLOYEE ID>"
for s in frappe.get_all("Shift Type", fields=["name","enable_auto_attendance","auto_update_last_sync","last_sync_of_checkin","process_attendance_after","mark_auto_attendance_on_holidays","working_hours_threshold_for_absent","working_hours_threshold_for_half_day"]): print(s)
for c in frappe.get_all("Employee Checkin", filters={"employee": emp, "time": [">=", "2026-09-01"]},
    fields=["name","time","log_type","shift","shift_actual_start","shift_actual_end","offshift","skip_auto_attendance","attendance","remote_approval_status","requires_remote_approval"], order_by="time asc"): print(c)
print(frappe.get_all("Attendance", filters={"employee": emp, "attendance_date": [">=", "2026-09-01"], "docstatus": ["<", 2]},
    fields=["attendance_date","status","docstatus","shift","in_time","out_time","working_hours","ot_hours","late_entry","early_exit"]))
```
Reading it: a punch with `shift` empty or `offshift=1` is never processed;
`last_sync_of_checkin` older than the shift end means the hourly job is not
advancing; a day with only an IN (no OUT) is EITHER the check-out bug (D1) or a
forgotten check-out — confirm with the employee.

## D5. Why the OT form says 0 h for 3 Sep while the list says 1.5 h
```python
import frappe
from hrms.utils.ot_calculation import get_day_ot_breakdown, get_shift_ot_breakdown
emp = "<EMPLOYEE ID>"; day = "2026-09-03"
att = frappe.db.get_value("Attendance", {"employee": emp, "attendance_date": day, "docstatus": ["<", 2]}, ["shift","in_time","out_time","ot_hours","status"], as_dict=True)
print("attendance", att)
print("checkin scan ", get_day_ot_breakdown(emp, day))
if att: print("attendance path", get_shift_ot_breakdown(emp, att.shift, day, att.out_time, in_time=att.in_time))
for c in frappe.get_all("Employee Checkin", filters={"employee": emp, "time": ["between", [day+" 00:00:00", day+" 23:59:59"]]}  # widen to day-1..day+1 for overnight shifts,
    fields=["time","log_type","shift","shift_actual_start","shift_actual_end","remote_approval_status"], order_by="time asc"): print(c)
```
