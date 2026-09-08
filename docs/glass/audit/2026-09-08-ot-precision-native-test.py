"""Approved LOCAL six-column migration and rollback-only financial fixtures.

Run from verify-bench/sites with its env/bin/python. --sync applies only the
three approved DocType files using native model import, then repeats it to
verify idempotence. Without --sync no DDL or commits occur. Synthetic records
always roll back; the approved local schema remains at9dp after --sync.
"""
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE))
import frappe

frappe.init(site="fresh.local", sites_path="/home/nabil/verify-bench/sites")
frappe.connect()
frappe.set_user("Administrator")
try:
    from hrms.patches.v16_0 import check_ot_hour_precision_capacity as preflight
    from hrms.patches.v16_0 import verify_ot_hour_precision as verifier
    from hrms.utils import ot_calculation as ot
    from hrms.utils import test_ot_calculation as fixtures
    from hrms.utils.ot_precision import stored_ot_hours

    if "--sync" in sys.argv:
        scale = frappe.db.sql("SELECT numeric_scale FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='tabOT Request' AND column_name='claimed_hours'")[0][0]
        if scale == 2:
            # A real old-width value would be truncated by ALTER without the
            # pre-model guard. Roll it back BEFORE any native DDL can commit.
            name = "SYNTHETIC-OVERFLOW-" + uuid4().hex[:12]
            frappe.db.sql("INSERT INTO `tabOT Request` (name, claimed_hours) VALUES (%s,%s)", (name, 10**12))
            try:
                preflight.execute()
            except frappe.ValidationError:
                print("PASS: native pre-model guard refused old-width integer overflow")
            else:
                raise AssertionError("overflow must be refused before sync")
            finally:
                frappe.db.rollback()
        from frappe.modules.import_file import import_file_by_path
        for attempt in range(2):
            preflight.execute()
            ddl = []
            original_ddl = frappe.db.sql_ddl
            def trace_ddl(query, *args, **kwargs):
                ddl.append(query)
                return original_ddl(query, *args, **kwargs)
            with patch.object(frappe.db, "sql_ddl", side_effect=trace_ddl):
                for slug in ("attendance_overtime_band", "attendance", "ot_request"):
                    import_file_by_path(str(BASE / f"hrms/hr/doctype/{slug}/{slug}.json"), force=True)
            frappe.db.commit()  # authorized LOCAL schema/metadata sync only; no synthetic rows exist
            verifier.execute()
            if attempt:
                assert not ddl, "repeat native sync unexpectedly emitted DDL"
            print({"native_sync_pass": attempt + 1, "ddl_statements": len(ddl), "ddl": ddl})
    verifier.execute()
    preflight.execute()

    # Native lifecycle fixture: actual source punches/calendar/configuration,
    # actual OT Request insert/reload/submit and actual approved-pay calculation.
    company = "SYNTHETIC-COMPANY-" + uuid4().hex[:10]
    employee = "SYNTHETIC-EMP-" + uuid4().hex[:10]
    frappe.db.sql("INSERT INTO `tabCompany` (name,abbr,country,default_currency) VALUES (%s,%s,%s,%s)", (company, "SYN", "Malaysia", "MYR"))
    frappe.db.sql("INSERT INTO `tabEmployee` (name,employee_name,company,status,date_of_joining,eligible_for_overtime_pay) VALUES (%s,%s,%s,%s,%s,%s)", (employee, "Synthetic", company, "Active", "2026-01-01", 1))
    shift_name = fixtures.ot_shift("SYNTHETIC-PRECISION-" + uuid4().hex[:10], holiday_list=fixtures.ot_holiday_calendar(), determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin")
    day = "2026-07-26"
    for seconds in (60, 194 * 60, 60.125):
        frappe.db.savepoint("precision_duration")
        start = datetime(2026, 7, 26, 10, 8)
        end = start + timedelta(seconds=seconds)
        for timestamp, kind in ((start, "IN"), (end, "OUT")):
            punch = frappe.get_doc(dict(doctype="Employee Checkin", name="SYNTHETIC-PUNCH-" + uuid4().hex[:12], employee=employee, time=timestamp, log_type=kind, shift=shift_name, shift_start=datetime(2026, 7, 26, 9), shift_end=datetime(2026, 7, 26, 18), shift_actual_start=datetime(2026, 7, 26, 8), shift_actual_end=datetime(2026, 7, 26, 23), remote_approval_status="Approved"))
            punch.db_insert()
        raw = ot.get_day_ot_breakdown(employee, day)["ot_hours"]
        expected = stored_ot_hours(Decimal(str(seconds)) / Decimal(3600))
        assert raw == seconds / 3600
        cap = ot.get_ot_claim_capacity(employee, day, "Overtime Pay")["hours"]
        assert Decimal(str(cap)) == expected
        attendance = frappe.new_doc("Attendance")
        attendance.update(dict(employee=employee, company=company, attendance_date=day, status="Present", shift=shift_name, in_time=start, out_time=end, working_hours=raw))
        attendance.insert(ignore_permissions=True)
        attendance.reload()
        assert stored_ot_hours(attendance.working_hours) == expected
        assert stored_ot_hours(attendance.ot_hours) == expected
        assert stored_ot_hours(attendance.ot_rate_bands[0].hours) == expected
        assert stored_ot_hours(attendance.ot_rate_weighted_hours) == stored_ot_hours(raw * 2)
        doc = frappe.new_doc("OT Request")
        doc.update(dict(employee=employee, company=company, employee_name="Synthetic", shift=shift_name, ot_date=day, status="Open", claimed_hours=cap, explanation="Synthetic precision verification"))
        # The historical test day is intentionally outside today's filing
        # window; override only today's clock, never financial verification.
        from hrms.hr.doctype.ot_request import ot_request as controller
        real_getdate = controller.getdate
        with patch.object(controller, "getdate", side_effect=lambda value=None: real_getdate(value or "2026-08-01")), patch.object(doc, "notify_approver"):
            doc.insert(ignore_permissions=True)
        doc.reload()
        assert Decimal(str(doc.claimed_hours)) == expected
        doc.status = "Approved"
        doc.submit()
        doc.reload()
        assert doc.docstatus == 1 and Decimal(str(doc.claimed_hours)) == expected
        expected_pay = round(float(expected) * 10 * 2, 2)
        assert ot.get_ot_pay(employee, day, day, 2080) == expected_pay
        assert stored_ot_hours(doc.punch_ot_hours) == expected
        if seconds == 194 * 60:
            doc.claimed_hours = 3.24
            try:
                doc.validate_claimed_hours()
            except frappe.ValidationError:
                pass
            else:
                raise AssertionError("3.24 must exceed the194-minute capacity")
        print({"seconds": seconds, "stored_hours": str(expected), "native_submitted": True, "pay": expected_pay})
        frappe.db.rollback(save_point="precision_duration")
    print("PASS: metadata/physical scale, idempotent preflight/verifier, actual insert/reload/approve/pay for1min194min and fractional seconds; synthetic fixtures rolled back")
finally:
    frappe.db.rollback()
    frappe.destroy()
