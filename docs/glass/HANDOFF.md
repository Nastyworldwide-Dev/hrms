# HANDOFF
prompt:   D1 — auto-attendance self-repair on late check-ins
status:   done
commit:   aaa56fe04 on nz-glass
files:    hrms/hr/doctype/employee_checkin/employee_checkin.py (repair path + marker)
          hrms/hr/doctype/attendance/attendance.{py,json} (auto_attendance field)
          hrms/hr/doctype/shift_type/shift_type.py (stamp provisional absent)
          hrms/hr/doctype/shift_type/test_shift_type.py (2 regression tests)
verify:   bench --site test.local run-tests --app hrms --module \
          hrms.hr.doctype.shift_type.test_shift_type --test \
          test_late_punches_repair_auto_marked_absent
flags:    schema add (auto_attendance) applied by migrate, no patch. Bench
          test.local has pre-existing pollution (mid-test commits leave _Test
          Shift / employees) — clean before module-wide runs; 3 unrelated
          checkin tests fail identically on the pre-D1 baseline.
remain:   punches skipped BEFORE this fix stay skipped (historical); a one-off
          backfill clearing skip_auto_attendance on days with a provisional
          Absent would remediate them. Not payroll-blocking going forward.
next:     optional backfill patch for pre-fix skipped punches
