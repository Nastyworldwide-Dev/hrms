# HANDOFF
prompt:   Final deployed production closure & reliability certification
status:   done — GO-LIVE READY WITH EXPLICIT ACCEPTANCE REQUIRED
commit:   5902b2e33 on nz-glass
uat-fixes: RMNaN money format (formatters.js, whole class); Expense Claim
          employee flow (dropped Advances/Totals tabs + Currency/Exchange Rate,
          defaulted backend values, guarded totals) — bench-verified insert+submit
geofence: "No check-in area set" = CONFIGURATION state, not a code defect.
          get_active_shift_location returns null when the shift has no
          Shift Location with coordinates. Remote-approval fallback fully
          implemented (outside+lenient -> approver; strict -> block). 25/25
          decision tests pass.
verify:   bench migrate clean+idempotent; ruff clean; 50/50 bench-free;
          offboarding 2/2; D1 2/2; approval guard OK; geofence 25/25;
          both builds OK; frontend 61/63 (2 pre-existing patch tests)
d1-hist:  read-only diagnostic query produced (candidate = Absent day with
          skipped unlinked punches). NEEDS BUSINESS DECISION — auto-repair
          rewrites closed-payroll history; HR reviews per-day.
accept:   (1) deploy runs full stack (bench start: socketio :9000 + schedule +
          worker); (2) HR configures Shift Location coordinates+radius where
          geofencing is wanted; (3) D1 historical review; (4) provisioning +
          approval-confirmation are recorded business decisions; (5) 2 frontend
          failures are the frappe-ui patch test (env)
verdict:  GO-LIVE READY WITH EXPLICIT ACCEPTANCE REQUIRED
