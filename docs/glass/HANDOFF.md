# HANDOFF
prompt:   Nadi/Verifica full access & live-readiness audit
status:   done (critical finding = cosmetic, remediated; backend authoritative)
commit:   1051ad655 on nz-glass (865bfa3cc..1051ad655)
files:    9 hrms/**/workspace/*.json (+HR roles), 2 payroll report json (+roles)
          hrms/patches/v16_0/gate_hr_workspaces_to_hr_roles.py (+patches.txt)
          hrms/tests/test_workspace_access_gating.py
verify:   bench --site test.local execute \
          hrms.patches.v16_0.gate_hr_workspaces_to_hr_roles.execute
finding:  employee reaching Desk saw 9 HR/Payroll workspace cards — verified on
          bench to be COSMETIC: every doctype/report/page behind them 403s an
          employee; get_doc of another's Salary Slip/Employee/Attendance denied;
          get_list self-scoped. Gated the 9 workspaces + 2 open payroll reports
          to HR roles. Employee now sees 0 HR workspaces; HR sees all 9.
residual: ESS User Type user can get_list Salary Structure NAMES (no data) — a
          Frappe framework quirk (doctype perms are HR-only); ESS type is not
          the live provisioning model (employees are System Users, unaffected).
          LOW; documented, not masked with a speculative hook.
next:     decide whether to move employees to ESS User Type / Website User (the
          cleaner no-Desk model readiness.py already recommends)
