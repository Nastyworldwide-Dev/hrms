"""Which shift does each punch land on? One row per edge case, from the real resolver.

Run:  cd ~/verify-bench/sites && ../env/bin/python <this file>

Every scenario is inserted through the real Employee Checkin insert (so
fetch_shift, the geofence override and every hook run) inside one savepoint,
then rolled back. Nothing is committed.
"""

import datetime
import sys

import frappe

DAY = datetime.date(2026, 9, 10)


def dt(day_offset, h, m=0):
    return datetime.datetime.combine(DAY + datetime.timedelta(days=day_offset), datetime.time(h, m))


SHIFTS = {
    "P 9-6": ("09:00:00", "18:00:00"),
    "P 7pm-330": ("19:00:00", "03:30:00"),
}

# (name, [(log_type, when)], assignments)
CASES = [
    ("normal day", [("IN", dt(0, 9, 30)), ("OUT", dt(0, 18, 5))], ["P 9-6"]),
    ("OT past the grace window", [("IN", dt(0, 9, 30)), ("OUT", dt(1, 0, 32))], ["P 9-6"]),
    ("OT just inside the grace", [("IN", dt(0, 9, 30)), ("OUT", dt(0, 18, 55))], ["P 9-6"]),
    ("early in, before the grace", [("IN", dt(0, 7, 30)), ("OUT", dt(0, 18, 5))], ["P 9-6"]),
    ("forgot to check out", [("IN", dt(0, 9, 30))], ["P 9-6"]),
    ("out next morning", [("IN", dt(0, 9, 30)), ("OUT", dt(1, 8, 0))], ["P 9-6"]),
    ("out two days later", [("IN", dt(0, 9, 30)), ("OUT", dt(2, 10, 0))], ["P 9-6"]),
    ("two sessions in a day", [("IN", dt(0, 9, 0)), ("OUT", dt(0, 13, 0)), ("IN", dt(0, 14, 0)), ("OUT", dt(0, 18, 0))], ["P 9-6"]),
    ("out with no in", [("OUT", dt(0, 18, 5))], ["P 9-6"]),
    ("night shift, out after midnight", [("IN", dt(0, 19, 5)), ("OUT", dt(1, 3, 25))], ["P 7pm-330"]),
    ("night shift, OT past its grace", [("IN", dt(0, 19, 5)), ("OUT", dt(1, 6, 10))], ["P 7pm-330"]),
    ("no assignment at all", [("IN", dt(0, 9, 30)), ("OUT", dt(0, 18, 5))], []),
]

#: Cases the ordinary punch path cannot create — a forgotten check-out is
#: submitted through submit_late_checkout, which names the IN's shift.
LATE_CHECKOUT_CASES = [
    ("late checkout, next morning", dt(0, 9, 30), dt(1, 8, 0), ["P 9-6"]),
    ("late checkout, two days later", dt(0, 9, 30), dt(2, 10, 0), ["P 9-6"]),
]


def setup(emp, company, shift_names):
    made = []
    for name in shift_names:
        start, end = SHIFTS[name]
        if not frappe.db.exists("Shift Type", name):
            frappe.get_doc(
                {
                    "doctype": "Shift Type",
                    "name": name,
                    "start_time": start,
                    "end_time": end,
                    "enable_auto_attendance": 1,
                    "process_attendance_after": "2026-09-01",
                    "last_sync_of_checkin": "2026-09-15 00:00:00",
                    "determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
                    "working_hours_calculation_based_on": "First Check-in and Last Check-out",
                }
            ).insert(ignore_permissions=True)
        a = frappe.get_doc(
            {
                "doctype": "Shift Assignment",
                "employee": emp,
                "shift_type": name,
                "start_date": "2026-09-01",
                "status": "Active",
                "company": company,
            }
        )
        a.flags.ignore_permissions = True
        a.insert()
        a.submit()
        made.append(a.name)
    return made


def main():
    frappe.init("fresh.local")
    frappe.connect()
    frappe.set_user("Administrator")
    emp = frappe.db.get_value("Employee", {"status": "Active"}, "name")
    company = frappe.db.get_value("Employee", emp, "company")
    frappe.db.set_single_value("HR Settings", "allow_multiple_shift_assignments", 1)

    print(f"{'case':<32} {'punch':<16} {'shift':<12} off  shift_start")
    print("-" * 88)
    for label, punches, shifts in CASES:
        frappe.db.savepoint("edgeprobe")
        try:
            setup(emp, company, shifts)
            for log_type, when in punches:
                d = frappe.new_doc("Employee Checkin")
                d.update({"employee": emp, "log_type": log_type, "time": when})
                d.flags.ignore_permissions = True
                try:
                    d.insert()
                    shift = (d.shift or "-")[:12]
                    start = str(d.shift_start or "-")[:16]
                    print(f"{label:<32} {log_type} {when.strftime('%d %H:%M'):<12} {shift:<12} {d.offshift}    {start}")
                except Exception as e:
                    print(f"{label:<32} {log_type} {when.strftime('%d %H:%M'):<12} REFUSED: {type(e).__name__}: {str(e)[:40]}")
            label = ""
        except Exception as e:
            print(f"{label:<32} SETUP FAILED: {type(e).__name__}: {str(e)[:60]}")
        frappe.db.rollback(save_point="edgeprobe")

    print()
    print("late check-out (the designed path for a forgotten one)")
    print("-" * 88)
    for label, in_at, out_at, shifts in LATE_CHECKOUT_CASES:
        frappe.db.savepoint("edgeprobe")
        try:
            setup(emp, company, shifts)
            d = frappe.new_doc("Employee Checkin")
            d.update({"employee": emp, "log_type": "IN", "time": in_at})
            d.flags.ignore_permissions = True
            d.insert()
            out = frappe.new_doc("Employee Checkin")
            out.update({"employee": emp, "log_type": "OUT", "time": out_at, "shift": d.shift})
            out.flags.is_late_checkout = True
            out.flags.ignore_permissions = True
            out.insert()
            print(f"{label:<32} OUT {out_at.strftime('%d %H:%M'):<12} {(out.shift or '-')[:12]:<12} {out.offshift}    {str(out.shift_start or '-')[:16]}")
        except Exception as e:
            print(f"{label:<32} FAILED: {type(e).__name__}: {str(e)[:60]}")
        frappe.db.rollback(save_point="edgeprobe")

    frappe.destroy()


if __name__ == "__main__":
    sys.exit(main())
