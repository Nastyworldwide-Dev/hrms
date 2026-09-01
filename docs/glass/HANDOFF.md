# HANDOFF
prompt:   Nadi final live acceptance & production gate
status:   done (ran the real app as all 3 roles; 1 runtime defect found + fixed)
commit:   190a70560 on nz-glass
files:    hrms/hr/doctype/leave_application/leave_application.py (leave-details guard)
          hrms/tests/test_leave_details_guard.py
verify:   drove the live PWA (localhost:8080) via Playwright as Employee / Manager
          / HR; bench console + regression test confirm the fix
runtime:  Employee 36/36 screens clean; Manager/Approver 33/33 clean;
          HR 32/33 — the one issue is the defect below, now fixed
defect:   HR opening an employee's leave application got 403 on get_leave_types
          (blank leave-types dropdown). _ensure_leave_details_permitted used
          frappe.has_permission("Employee"), which fails CLOSED for an HR user
          carrying the auto-created allow=Employee self UP. Repointed at the
          canonical _may_read_employee (role-based) + the leave-approver case.
          Bench-verified: HR / reports-to manager / self allowed, stranger denied.
realtime: socket.io (:9000) not running in the preview env — the app degrades
          gracefully (every screen clean without it). Needs the socketio process
          in the deployed environment for live updates.
caveat:   the HR fix is code+bench+test verified; the :8000 web workers hold old
          code in memory (no hot-reload), so the browser reflects it only after
          a normal worker reload/deploy.
regress:  ruff clean; 50/50 bench-free suites; both builds green; frontend tests
          61/63 (2 pre-existing frappe-ui call-error-handling patch failures)
next:     deploy (reloads workers) then re-shoot the one HR screen
