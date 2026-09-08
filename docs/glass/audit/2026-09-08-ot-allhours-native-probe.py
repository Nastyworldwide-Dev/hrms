"""Native rollback-only all-hours and scheduler/query/link regression.

Run from /home/nabil/verify-bench/sites with its env/bin/python.
All fixtures use random synthetic names. No schema changes, commits or
FrappeTestCase class setup. Actual scheduler query, mark helper, Attendance
controller and checkin linking execute against the local database.
"""
import ast
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import frappe

frappe.init(site="fresh.local", sites_path="/home/nabil/verify-bench/sites")
frappe.connect()
frappe.set_user("Administrator")
try:
    from hrms.utils import test_ot_calculation as existing

    original_create = existing.create_shift_type
    with patch.object(existing, "create_shift_type", side_effect=lambda name, **args: original_create(name + uuid4().hex[:10], **args)):
        case = existing.TestOTCalculation()
        for method in ("test_ot_rest_day_rate", "test_ot_off_day_tiered_bands", "test_ot_above_minimum_uses_threshold_semantics", "test_ot_below_minimum_is_zero"):
            getattr(case, method)()
        shift_name = existing.ot_shift("SYNTHETIC-ALLHOURS-", holiday_list=existing.ot_holiday_calendar(), determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin", working_hours_calculation_based_on="First Check-in and Last Check-out")
    shift = frappe.get_doc("Shift Type", shift_name)
    if "--old-fetch" in sys.argv:
        # Reproduce the reviewed scheduler defect with the pre-correction
        # actual query body; keep the current holiday calculation identical.
        source = subprocess.check_output(["git", "show", "090091e06:hrms/hr/doctype/shift_type/shift_type.py"], cwd=Path(__file__).resolve().parents[3], text=True)
        method = next(node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) and node.name == "get_employee_checkins")
        scope = {"frappe": frappe}
        exec(compile(ast.Module(body=[method], type_ignores=[]), "old-native-fetch", "exec"), scope)
        shift.get_employee_checkins = scope["get_employee_checkins"].__get__(shift)

    shift.process_attendance_after = "2026-07-26"
    shift.last_sync_of_checkin = "2026-07-27 23:59:59"
    shift.working_hours_threshold_for_absent = 4
    shift.working_hours_threshold_for_half_day = 8
    employee = "SYNTHETIC-EMP-" + uuid4().hex[:10]
    company = "SYNTHETIC-COMPANY-" + uuid4().hex[:10]
    frappe.db.sql("INSERT INTO `tabCompany` (name,abbr,country,default_currency) VALUES (%s,%s,%s,%s)", (company, "SYN", "Malaysia", "MYR"))
    frappe.db.sql("INSERT INTO `tabEmployee` (name,employee_name,company,status,date_of_joining) VALUES (%s,%s,%s,%s,%s)", (employee, "Synthetic", company, "Active", "2026-01-01"))

    def row(value, kind):
        return frappe._dict(employee=employee, shift=shift_name, time=datetime.fromisoformat("2026-07-26 " + value), log_type=kind, shift_start=datetime(2026, 7, 26, 9), shift_end=datetime(2026, 7, 26, 18), shift_actual_start=datetime(2026, 7, 26, 8), shift_actual_end=datetime(2026, 7, 26, 23), remote_approval_status="Approved", skip_auto_attendance=0, requires_remote_approval=0, offshift=0)

    logs = [row("10:08", "IN"), row("13:22", "OUT")]
    result = shift.get_attendance(logs, 4, 8)
    assert result[:4] == ("Present", 194 / 60, False, False), result
    attendance = frappe.new_doc("Attendance")
    attendance.update(dict(employee=employee, shift=shift_name, attendance_date="2026-07-26", status="Present", in_time=logs[0].time, out_time=logs[-1].time))
    attendance.set_overtime()
    assert attendance.ot_hours == 194 / 60
    assert attendance.ot_rate_bands[0].hours == 194 / 60

    def insert_punch(value, kind, **invalid):
        doc = frappe.get_doc({"doctype": "Employee Checkin", "name": "SYNTHETIC-PUNCH-" + uuid4().hex[:12], **row(value, kind), **invalid})
        doc.db_insert()  # fixed evidence fixture; deliberately no shift-fetch hooks
        return doc.name

    for invalid in ({"skip_auto_attendance": 1}, {"remote_approval_status": "Pending"}, {"remote_approval_status": "Rejected"}, {"requires_remote_approval": 1}, {"offshift": 1}):
        frappe.db.savepoint("scheduler_case")
        names = [insert_punch("09:00", "IN"), insert_punch("10:00", "OUT", **invalid), insert_punch("12:00", "OUT")]
        fetched = shift.get_employee_checkins()
        assert len(fetched) == 3, ("boundary was filtered", invalid, len(fetched))
        assert shift.mark_attendance_for_shift_logs(employee, "2026-07-26", fetched) is None
        assert not frappe.db.exists("Attendance", {"employee": employee})
        names.extend([insert_punch("13:00", "IN"), insert_punch("14:00", "OUT")])
        attendance = shift.mark_attendance_for_shift_logs(employee, "2026-07-26", shift.get_employee_checkins())
        assert attendance is not None, ("attendance not created", invalid)
        attendance.reload()
        assert attendance.status == "Present" and attendance.working_hours == 1, (attendance.status, attendance.working_hours)
        assert attendance.ot_hours == 1 and not attendance.late_entry and not attendance.early_exit
        linked = {item.name: item.attendance for item in frappe.get_all("Employee Checkin", filters={"employee": employee}, fields=["name", "attendance"])}
        assert not linked[names[1]], "ineligible boundary was linked"
        assert linked[names[-1]] == attendance.name and linked[names[-2]] == attendance.name
        frappe.db.rollback(save_point="scheduler_case")
    print("PASS: four existing native OT methods, exact 194-minute ShiftType/Attendance calculation, five real scheduler-query/mark/submit/link boundary scenarios; all synthetic local fixtures rolled back.")
finally:
    frappe.db.rollback()
    frappe.destroy()
