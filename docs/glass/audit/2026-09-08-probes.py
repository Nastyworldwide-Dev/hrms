"""Read-only synthetic probes of current production functions; no site or DB writes.

Run from repository root: python3 docs/glass/audit/2026-09-08-probes.py
Exit 1 means the listed acceptance properties are still violated, NOT that
the audit failed. AST extraction runs the actual methods with explicit seams;
it does not exercise a full Frappe document transaction or browser lifecycle.
"""

import ast
import logging
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "hrms/tests")]
import _frappe_stub

_frappe_stub.install()
import frappe

from hrms.utils import ot_calculation as ot
from hrms.utils.filing_window import earliest_filable_date
from hrms.utils.geofence import evaluate_geofence

logging.disable(logging.CRITICAL)
failures = []


def check(label, actual, expected):
    passed = actual == expected
    print(f"{'PASS' if passed else 'FAIL'} {label}: actual={actual!r}; expected={expected!r}")
    if not passed:
        failures.append(label)


def method(path, name, env):
    tree = ast.parse((ROOT / path).read_text())
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, "exec"), env)
    return env[name]


gate = method("hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py", "before_save", {
    "frappe": frappe, "_": lambda s: s, "HR_MANAGER_ROLE": "HR Manager",
    "logger": logging.getLogger("probe"),
})
request = NS(status="Approved", approver="approver@example.invalid", name="AUDIT-OUT",
             parent_request="AUDIT-IN", has_value_changed=lambda _: True)
with patch.object(frappe.session, "user", "employee@example.invalid"), patch.object(frappe, "get_roles", return_value=["Employee"]):
    try:
        gate(request)
        outcome = "allowed"
    except frappe.ValidationError:
        outcome = "refused"
check("inherited Approved OUT by employee (before_save seam)", outcome, "allowed")

config = dict(start_time="09:00:00", end_time="18:00:00", min_minutes=60,
              days_per_month=26, hours_per_day=8, daily_cap=0, monthly_cap=104,
              bands={"normal": [(0, 24, 1.5)], "rest": [(0, 24, 2)],
                     "public_holiday": [(0, 8, 2), (8, 24, 3)]})
with patch.object(ot, "_get_shift_ot_config", return_value=config), patch.object(ot, "get_time", side_effect=time.fromisoformat):
    with patch.object(ot, "_classify_day", return_value="rest"):
        rest = ot.get_shift_ot_breakdown("AUDIT", "SHIFT", "2026-09-06", "2026-09-06 13:22:00", "2026-09-06 10:08:00")
    check("rest day 10:08-13:22 raw OT", rest["ot_hours"], round(194 / 60, 2))
    with patch.object(ot, "_classify_day", return_value="public_holiday"):
        holiday = ot.get_shift_ot_breakdown("AUDIT", "SHIFT", "2026-09-07", "2026-09-07 18:00:00", "2026-09-07 09:00:00")
    check("public holiday 9h band hours", [(b["hours"], b["rate"]) for b in holiday["bands"]], [(8, 2), (1, 3)])

    logs = [dict(name=f"AUDIT-{i}", time=f"2026-09-03 {t}:00", log_type=kind, shift="SHIFT",
                 shift_actual_start="2026-09-03 08:00:00", shift_actual_end="2026-09-03 20:00:00",
                 remote_approval_status="Approved")
            for i, (t, kind) in enumerate([("09:00", "IN"), ("12:00", "OUT"), ("13:00", "IN"), ("19:30", "OUT")])]
    with patch.object(ot, "_classify_day", return_value="normal"), patch.object(frappe, "get_all", return_value=logs):
        attendance = ot.get_shift_ot_breakdown("AUDIT", "SHIFT", "2026-09-03", "2026-09-03 19:30:00", "2026-09-03 09:00:00")
        scanned = ot.get_day_ot_breakdown("AUDIT", "2026-09-03")
        check("split-session Attendance OT versus punch scan", (attendance["ot_hours"], scanned["ot_hours"]), (1.5, 1.5))
        weekday = ot.get_shift_ot_breakdown("AUDIT", "SHIFT", "2026-09-03", "2026-09-03 18:59:00", "2026-09-03 09:00:00")
        check("weekday below 60-minute minimum", weekday["ot_hours"], 0)

start, end = datetime(2026, 9, 6, 10, 8), datetime(2026, 9, 6, 13, 22)
get_attendance = method("hrms/hr/doctype/shift_type/shift_type.py", "get_attendance", {
    "calculate_working_hours": lambda *args: (194 / 60, start, end),
    "_company_of_logs": lambda logs: "AUDIT", "cint": int, "timedelta": timedelta,
})
shift = NS(determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
           working_hours_calculation_based_on="First Check-in and Last Check-out",
           _deduct_unpaid_breaks=lambda hours, *args, **kwargs: hours,
           enable_late_entry_marking=1, enable_early_exit_marking=1,
           late_entry_grace_period=0, early_exit_grace_period=0)
result = get_attendance(shift, [NS(shift_start=start.replace(hour=9, minute=0), shift_end=start.replace(hour=18, minute=0))], 2, 4)
check("non-working-day short session status and flags", (result[0], result[2], result[3]), ("Present", False, False))

decision = evaluate_geofence(False, True, 1000, 1300, 1500)
check("coarse 1.3km reading: server reason", decision[1]["reason"], "imprecise_location")
decision = evaluate_geofence(False, True, 100, 120, 40)
check("120m point with 40m accuracy and 100m radius: server allows", decision, None)
print("INFO 194 minutes =", round(194 / 60, 2), "decimal hours; existing OT-pay rounding =", ot.round_ot_pay_hours(194 / 60))
print("INFO earliest claim date on 2026-09-08 =", earliest_filable_date(date(2026, 9, 8)))
print(f"RESULT {len(failures)} unmet acceptance properties in synthetic probes")
sys.exit(bool(failures))
