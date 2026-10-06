# Reports and approver roles, probe of 6 Oct 2026 (fresh.local, report only)

Scope: Script Reports in hrms/hr/report whose json roles include Employee, Employee Self Service,
Leave Approver, Expense Approver or Shift Supervisor. HR is out of scope (23 Sep ruling).
Five reports qualify. All calls via frappe.desk.query_report.run as the persona. Test rows were made in a
transaction and rolled back (verified: 0 left).

Persona facts: employee = HR-EMP-00009 (Nadi W0 A); manager = HR-EMP-00008, reports HR-EMP-00009 and
HR-EMP-00027; approver = HR-EMP-00007, expense_approver of HR-EMP-00009's claims; foreign = HR-EMP-00012 (Nadi W0 B).

| Report (roles matched) | Persona | Rows | Rows outside scope | Verdict |
|---|---|---|---|---|
| Employee Advance Summary (Employee, Expense Approver) | all four | 0 | none (site has 0 Employee Advance) | NOT RUN, no data; code reads at employee_advance_summary.py:236-290 apply only company fence, no own-employee filter (see note 1) |
| Employee Leave Balance Summary (Leave Approver) | employee, foreign | - | - | OK, report refused (no role) |
| same | manager | 3 (00008, 00009, 00027) | none (self + 2 direct reports) | OK |
| same | approver | 1 (00007) | none | OK |
| same, other-company filters (_Test Company, Nadi W0 B) | manager, approver | 0 | none | OK |
| Appraisal Overview (Employee, ESS) | all four | 0 | none (site has 0 Appraisal) | NOT RUN, no data; code scopes via get_allowed_appraisal_employees (appraisal_overview.py:75-114) |
| Unpaid Expense Claim (Expense Approver) | employee, manager, foreign | - | - | OK, report refused (no role) |
| same | approver | 1 (HR-EXP-2026-00008, emp 00009) | none; claim HR-EXP-2026-00007 (emp HR-EMP-00001, _Test Company, approver Administrator) with an added unpaid ledger row was NOT shown to approver, shown to Administrator | OK (see note 2) |
| Shift Attendance (Employee, ESS) | employee | 1 (00009) | none | OK |
| same | manager, approver, foreign | 0 | none | OK, but see note 3 |

## Notes
1. Employee Advance Summary: no LEAK shown, but unproven. Zero advance rows exist; I did not create one.
   The query at employee_advance_summary.py:236-290 has no per-employee or approver filter, only
   scoped_companies() (HR fence). Whether Frappe narrows it otherwise is unverified. Needs a seeded advance to settle.
2. Unpaid Expense Claim: the script (unpaid_expense_claim.py:164-215) builds a frappe.qb query with no
   employee/approver filter, yet the approver saw only the claim naming them. I did not find the narrowing
   source (cause unverified). Result is real, mechanism is not. Also: running it as the approver with
   no `scrub` patch raised ImportError (frappe.utils.scrub missing in this bench; I patched it in the probe process only; bench-version issue, not a leak).
3. Shift Attendance: manager/approver see 0 although manager supervises HR-EMP-00009 who has attendance
   with shift in Nadi W0 A. Fine for leak purposes; may be an under-show for supervisors (not tested further).
   Code applies build_qb_match_conditions at shift_attendance.py:332.
4. Employee persona saw only own row on Shift Attendance with no company filter; the foreign persona saw nothing from other companies.

## Verdict
No confirmed LEAK in 5 reports. Two NOT RUN for lack of data (Employee Advance Summary, Appraisal Overview);
Employee Advance Summary is the one worth seeding next.

## Employee Advance Summary (re-run by the orchestrator, 6 Oct, rows seeded and rolled back; 0 left)
Seeded one advance for HR-EMP-00009 (the plain employee) and one for HR-EMP-00007 (outside every team).
| persona | sees own | sees the outsider's | verdict |
|---|---|---|---|
| nadi.w0.employee (Employee) | yes | no | OK |
| nadi.w0.manager (Employee; not Expense Approver) | no (has no advance) | no | OK |
Why it holds: execute() calls hrms/utils/report_scope.apply_employee_scope (report_scope.py:129) before the
query: anyone not HR is pinned to their own employee; no Employee record -> empty report. The "company fence
only" read of get_advances (employee_advance_summary.py:236) missed that pin.
Note (not a leak): a manager does not see their team's advances in this report; same rule as "HR, or your own".

## Summary
No leak in any of the 5 approver-role reports. Appraisal Overview not run (no appraisal data on the site).
