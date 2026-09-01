# HANDOFF
prompt:   Full product sweep & live-readiness audit
status:   partial (12 fixes shipped; 1 known blocker documented, not fixed)
commit:   0013dc02a on nz-glass (a8f657ff2..0013dc02a, 12 commits)
files:    hrms/utils/ot_calculation.py (rejected OT not paid)
          hrms/hr/{leave_rules,utils,offboarding}.py + 4 doctypes (mirror + relieving guards)
          hrms/api/__init__.py, approval.py (fail-closed employee + fence-bounded approval)
          hrms/utils/{__init__,company_fence}.py (get_country, reconcile savepoint)
          frontend FormView/RemoteApprovals.vue, roster MonthViewTable.vue, www/roster.py
verify:   ruff check hrms; python3 hrms/tests/test_offboarding.py (+ 48 more bench-free)
flags:    6 audit tracks + live bench E2E; all fixes bench- or source-verified;
          2 security fixes routed through adversarial verifier (1 caught a regression, fixed)
blocker:  D1 auto-attendance marks a worked day Absent when punches arrive after
          last_sync and won't self-repair (shift_type.py mark_absent_*). Payroll-
          affecting, silent, manual HR override only. NOT fixed — needs attendance-
          flow redesign + regression, too risky to rush.
next:     fix D1; then the recorded MEDIUMs (offboarding vs encashment/RL top-ups,
          error-as-empty PWA states, geofence-log rollback, OT double-pay engines)
