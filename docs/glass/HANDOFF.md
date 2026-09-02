# HANDOFF
prompt:   Verifica Desktop Pass 2 — HR module operational closure
status:   custom HR lifecycle features runtime-verified; data integrity clean
commit:   d545028d6 on nz-glass (operational-verification pass — no code defect)
shift/attendance: geofence config (Shift Location) + resolution proven (f3860e3f3);
          check-in/attendance/OT/remote-checkin admin present + HR-accessible.
attendance-allowance: 13/13 tests incl the negatives — absent/on-leave never
          count, zero eligible days books NOTHING, rerun is a no-op (idempotent),
          employees cannot configure it, books one Additional Salary w/ reference,
          monthly job registered. Invalid/missing attendance -> no allowance.
leaves:   Leave Type/Policy/Allocation/Application via stock HRMS; entitlement->
          allocation->usage->balance renders in Nadi (3 allocations proven prior).
offboarding: RUNTIME integration tests pass — test_relieving_date_prorates_ledger
          _and_restores (proration incl already-taken floor + restore on change)
          and test_status_sweep_marks_left_and_is_rerun_safe. Unit suite 33/33:
          Active->Left after N working days, holidays/weekends handled, leaver
          with active reports HELD not errored, relieving-date-moved recheck,
          configurable threshold, rerun-safe.
expenses: HR config paths (Expense Claim Type R/W/C, Company payable-account via
          HR Manager) accessible; control renders when data exists.
perf/recruit: stock HRMS modules; active pieces reuse native contracts; unused
          upstream functionality classified, not treated as broken.
tenure/integrity: employee-integrity sweep CLEAN (6 active) — no duplicate
          user_id, no self-reports, no active->inactive-manager routing, no
          company/department mismatch. Nadi cannot resolve a wrong employee/mgr/
          company from bad data.
reports:  exception reports exist (unpaid claims, exits, out_of_radius, holiday
          workers) + HR-only report_half_transitioned; no consolidated month-end
          view (usability opportunity, not a blocker).
ledger:   Attendance Allowance / offboarding proration / Active->Left / D1 self-
          repair / leave approval finalization / OT / approver routing = ALL
          OPERATIONALLY VERIFIED. Geofence = verified + LIVE TEST for live employee.
          Expense = verified + CONFIGURATION (company payable account).
verdict:  HR DESKTOP OPERATIONS CLOSED
