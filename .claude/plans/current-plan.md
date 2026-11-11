# Plan: Employee Status options (HR, 10 Nov 2026)

## Decisions (user)
- Options: Active, Resigned, Terminated, Deceased, Suspended (all selectable).
- Everyone now Left or Inactive -> Resigned. Missing relieving dates stay blank; HR fills later.
- Resigned works everywhere "Left" works today.
- Terminated, Deceased, Suspended: selectable only, no new rules now (HR decides later).
  Login still disabled for any non-Active status (ERPNext core, unchanged).
- Customize Form is not touched by hand: options set by a patch (Property Setter).

## Steps
1. `hrms/utils/employee_status.py` — STATUS_OPTIONS, LEAVER_STATUS = "Resigned",
   `is_leaver()`, `to_current()` (Left/Inactive -> Resigned). Pure, unit-tested.
2. Patch `v16_0.employee_status_options` — Property Setter on Employee.status options;
   `UPDATE Employee SET status='Resigned' WHERE status IN ('Left','Inactive')`; logs counts
   (moved, with no relieving date). Idempotent.
3. `EmployeeMaster.validate` (overrides/employee_master.py) — accept the 5 options instead of
   ERPNext's hard-coded list; Resigned gets ERPNext's Left checks (relieving date, no Active
   reports), only when status changes to Resigned, so old records still save.
4. "Left" -> Resigned: salary_slip.py:679, hr/utils.py:649 (accrual), sync/checkin_import.py:147,
   api/manpower.py:118, hr/offboarding.py:344, employee_transfer.py:42.
5. "Inactive" guards (hr/utils.py:1666 validate_active_employee, attendance.py:334,
   payroll_entry.py:1365, shift_type.py:1077, additional_salary.js:16) are NOT moved to Resigned:
   they never applied to Left, and Resigned must work like Left (final payslip, last expense claim,
   leave encashment after the relieving date). With nobody Inactive they simply never fire.
6. Sync (sync/runner.py `_mirror_payload`): incoming Employee status Left/Inactive -> Resigned.
7. Leave report status filters (3 .js), Employee list colours, manpower "Left" label kept as wording.
8. ERPNext `deactivate_sales_person` only fires on "Left": hrms wrapper for Resigned.
9. Update existing tests that set Left/Inactive on Employee to Resigned.

Out of scope: Shift Assignment Active/Inactive (different field).

## EXPECTED OUTPUT:
- UI result: Employee Status dropdown (Desk) shows Active, Resigned, Terminated, Deceased,
  Suspended. Every employee who was Left or Inactive shows Resigned. Employee list shows
  Resigned in grey; leave report status filters list the five options.
- Behaviour: Resigned does everything Left did (no login, leave accrual stops, final payslip,
  check-ins after relieving date ignored, offboarding/transfer set Resigned, sync maps Left/Inactive
  to Resigned). Terminated / Deceased / Suspended: selectable, login disabled, no other rules yet.
- Code changed: hrms/utils/employee_status.py (new), patch v16_0.employee_status_options (new),
  overrides/employee_master.py, payroll/salary_slip.py, hr/utils.py, sync/checkin_import.py,
  sync/runner.py, api/manpower.py, hr/offboarding.py, employee_transfer.py, 3 leave report .js,
  Employee list colours; tests for each.
- How it ships: alpha release on nz-glass -> Frappe Cloud deploy; needs `bench migrate`
  (the patch moves the statuses and sets the dropdown).

## MOCKUP: NOT NEEDED (no new screen or layout: the existing Status dropdown gets different options, and the list colour of an existing field changes)

## FLOW
- patch v16_0.employee_status_options -> Property Setter (Employee.status options) + Employee rows Left/Inactive -> Resigned
- hrms/utils/employee_status.py -> employee_master.validate, salary_slip, hr/utils (accrual), checkin_import, api/manpower, offboarding, employee_transfer, sync/runner
- source ERP sync -> sync/runner._mirror_payload (Left/Inactive -> Resigned) -> Employee row -> _reconcile_user_status (login off)
- offboarding sweep / Employee Transfer -> Employee.status = Resigned -> ERPNext update_user_status (login off)

## Pipeline Summary
TDD per area (red -> green) -> one commit per cause -> code review -> version bump + /deploy
(Frappe Cloud, needs `bench migrate` for the patch) -> HANDOFF.md commit + push.
