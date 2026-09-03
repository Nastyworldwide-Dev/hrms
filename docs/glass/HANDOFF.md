# HANDOFF
prompt:   PWA↔backend flow audit — eliminate employee identity/permission anomalies
status:   done
commit:   e73d68d0b on nz-glass (4: 53327bd feat, 470ca32 fix, 60d6451 fix, e73d68d refactor)
files:    hrms/utils/identity.py (+ hrms/tests/test_identity.py)
          hrms/overrides/{employee_owned,approval,ot,employee_issue,sop_document}_row_scope.py
          hrms/api/approval.py, hrms/hr/utils.py (own-employee resolvers)
          hrms/overrides/test_row_scope_identity_parity.py
          frontend/src/utils/identity.js (+ __tests__), frontend/src/main.js guard
verify:   bench --site test.local run-tests --module hrms.overrides.test_row_scope_identity_parity
          (run-tests env-broken here: installed_apps orjson/py3.14 — verified via console)
          yarn --cwd frontend test  (identity.test.js 3 pass)
flags:    A1 fence fail-open on ambiguous + A2 inactive self-read + A3 frontend case-drift
          stranding — all fixed by one seam: identity.own_employees. Fence now agrees a
          login = at most one Active Employee (multi-company-per-user branch removed,
          was already unreachable via PWA). A4 (attendance queue) was a MISDIAGNOSIS —
          Attendance Request is team-reviewed, managers do see/action reports. Not deployed.
next:     deploy to a staging site and re-run the parity module where run-tests works
