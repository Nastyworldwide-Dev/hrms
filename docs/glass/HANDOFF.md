# HANDOFF
prompt:   13 Sep 2026 — clock in/out, overtime, approver audit + fixes
status:   done
commit:   5ef3877d7 on nz-glass (pushed; 42 commits since 84b057733)
files:    hrms/api/remote_checkin.py · hrms/utils/ot_calculation.py
          hrms/hr/shift_rules.py · hrms/hr/doctype/attendance/attendance.py
          hrms/api/approval.py · hrms/utils/filing_window.py
          hrms/sync/checkin_recovery.py · hrms/overrides/employee_issue_row_scope.py
          hrms/utils/checkin_damage_enumeration.py (new) · hrms/hr/utils.py
verify:   PYTHONPATH=. python3 hrms/tests/test_ot_calculation_rules.py  (and the test_ot_* set)
flags:    BEFORE DEPLOY run the dry run in backfill_ot_after_rounding_rule's docstring —
          the wider filing window widened that deploy-time repair 92 -> 153 days.
          Reports project DEFERRED by Nabil. Historical repair still needs his word.
          Two open decisions: cancel-right on 3 doctypes, duplicate OT filing at 5 months.
next:     fix the raw 5.669444444h shown in the PWA, then run the damage count (shape S6).
