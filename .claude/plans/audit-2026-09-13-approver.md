# AUDIT — approver logic and row scope, 13 Sep 2026

Read-only. Probes savepointed on fresh.local and rolled back; nothing edited.
Anchors re-verified independently by this session — see "Re-verified" and "REFUTED" at the bottom.

## (a) Verdict against the 8 Sep ledger

| Ledger row | Verdict |
|---|---|
| Settled remote decisions (bf2126a7d) | FIXED |
| PWA/Desk approval capability, stale actions (6384996d6) | FIXED AS SCOPED, OVER-CLAIMED. approval.py:290-303 get_decision_actions is action-specific and revision-bound (_check_review_revision:277-286), but it reports what `_decision_access` allows, which is WIDER than the row scope — see (c)B |
| Concurrent OT decisions / RL grants (6be841a6e) | OT FIXED (approval.py:215-229 takes the Employee lock before the request lock, ordered to match OTRequest.check_if_latest). RL grant concurrency genuinely OPEN — ledger is honest |
| Private issue notification recipients (981c1cbe7) | FIXED — employee_issue.py:100-105 gates on company_visible AND frappe.has_permission |
| "Still open: N02 cross-company issue recipients" | **NOT OPEN — stale ledger.** Closed by the same commit. The get_all at hrms/mixins/pwa_notifications.py:120-126 is a SORTING TIEBREAKER inside _get_ot_approver, not a broadcast; the send passes _ot_approver_can_receive:131-146 |
| "Still open: N03 OT approver policy" | **NOT OPEN AS WRITTEN — stale ledger.** Closed by d479e4c05 (8 Sep 14:01, BEFORE ledger commit 4915632e5 at 17:56) and 686e4aa0d (9 Sep, after it) — only the second landed after the row; (f)3 states this correctly. hrms/mixins/pwa_notifications.py:131-146 now calls the same _is_routed_approver + ot_row_scope.has_permission the decision uses. The real open question under that label is (c)B |
| "Script Report family hunt not yet done" | **OPEN, and far larger than implied** — 26 of 32 unfenced, 4 wrong claims in the fixed list, 4 reports actively bypass an existing hook |
| Today's filing-guard fix (not on the ledger) | FIXED, committed 6c1f71efb, tested |

## (b) The approver model — there isn't one

Sight and action are decided by different code that does not agree.
  SIGHT  = the row-scope hooks in hrms/overrides/ (hooks.py:167-236 wires permission_query_conditions; :238-285 wires has_permission)
  ACTION = hrms/api/approval.py::_decision_access, which runs its own gate then sets ignore_permissions=True

**Action is bounded by row-scope READ. It is NOT bounded by row-scope WRITE.**

| Doctype | Who can SEE | Who can APPROVE | Which code decides |
|---|---|---|---|
| Leave Application, Expense Claim, Shift Request | HR/Admin (NO company fence); the employee; the named approver; the reports_to manager (READ-ONLY); DocShare | HR (company-fenced); the named approver; AND the reports_to manager (elevated) | sight approval_row_scope.py:65-130; action approval.py:136-166 + _is_routed_approver:35-87 |
| OT Request, Replacement Leave Claim | HR/Admin; the employee; direct reports (NO Active filter, NO company fence); DocShare | HR (company-fenced); reports_to manager | sight ot_row_scope.py:34-88 |
| Attendance Request | own + DocShare + HR (fenced) + direct reports read-only | HR; reports_to manager | employee_owned_row_scope.py:132 TEAM_REVIEWED_DOCTYPES |
| Employee Issue | HR operator (fenced); the employee only — NO manager | HR only (READ_PTYPES:78 blocks every staff mutation) | employee_issue_row_scope.py:45-115 |
| 29 employee-owned doctypes (pay, benefits, PIP, attendance, checkins) | own + DocShare + HR (fenced). No manager visibility | HR | employee_owned_row_scope.py — **the one built correctly**: canonical identity, company fence, both hooks, integrity test |
| Appraisal | own + the TRANSITIVE reports_to chain + HR (fenced) + DocShare | same | appraisal.py:920-941 |
| Script Reports (26 of 32) | whoever holds the report role, FOR ANY COMPANY THEY TYPE INTO THE FILTER | n/a | no fence at all |

## (c) Where two mechanisms disagree

### A. Seven derivations of "my team"
Canonical: hr/utils.py:1108-1135 get_direct_report_employees — Active-only, company-fenced. Its own
docstring: "One definition of 'my team', shared by every row scope... duplicating it would let the
fences drift apart." Six others ignore it.

| # | Location | Active filter | Company fence | Depth |
|---|---|---|---|---|
| 1 | hr/utils.py:1119 CANONICAL | yes | yes | direct |
| 2 | ot_row_scope.py:38 | **no** | **no** | direct |
| 3 | approval.py:85 _is_routed_approver | **YES — see REFUTED** | no | direct |
| 4 | team.py:158,299 | yes | deliberately not, for own team | direct |
| 5 | api/__init__.py:320 _may_read_employee | no | no | direct |
| 6 | roster.py:54 | no | yes | direct |
| 7 | appraisal.py:939 | no | no | **transitive** |

#4 and #6 assert OPPOSITE company rules for the same manager, each in a comment claiming to be right.

### B. _is_routed_approver overrides the row scope's write rule
approval_row_scope.py:15-18 promises "the employee's direct manager, READ ONLY... write/submit/cancel/
delete/share/amend stay with the named approver." FALSE. A reports_to manager can approve or reject a
Leave Application named to somebody else. _is_routed_approver's own docstring (:39-51) says reports_to
routes "OT, Attendance Request and Replacement Leave Claim" — the code applies it to all six.
finalize:410-416 additionally elevates on routing alone for CANCEL, a right the row scope never grants.

### C. System Manager
hr/utils.py:52-63 splits HR_ROLES (includes SM, write-side only) from HR_SEE_ALL_ROLES (excludes SM),
citing a 2026-08-19 ruling that SM must not see staff data. approval.py:58 puts SM straight back in.
It fails closed only because _request_read_allowed happens to run first inside _decision_access — an
ORDERING ACCIDENT, not a boundary.

### D. Company fencing missing from two of four row scopes
ot_row_scope.py contains the word "company" ZERO times (verified). approval_row_scope.py once, in a
comment. approval.py:133 fences by company. That split is the cause of open item 8.

### E. Identity re-derived instead of resolved — the known class, four more instances
1. **employee_issue_row_scope.py:106** — the file's own canonical _own_employees() (line 28) builds the
   query; thirteen lines later has_permission uses a raw get_value(..., "user_id") == user. **FAILS OPEN.**
2. appraisal.py:887-888 _get_own_employees — raw, status-agnostic, every claimant. Its docstring at
   :918-931 ADMITS this and says identity callers should pass own_employees as the seed. kpi.py does;
   the Desk get_permission_query_conditions hook does not.
3. employee_one_on_one.py:19-20 — same raw pattern; fails CLOSED (blocks a legitimate manager).
4. employee_ctc_break_up.py:359-364 — raw compare, ROLES_ALLOWED_TO_VIEW_ANY_EMPLOYEE includes System
   Manager, no company fence.
5. company_fence.py:237-239 — raw {"user_id","status":"Active"} while deciding a user's own fence.

### F. Can a designated approver always act on what the PWA shows them? NO — refuted twice
- applicable_for gap: hrms/utils/company_scope.py:86-91 deliberately ignores applicable_for ("it can only ever
  fence more, never less"). True for the ACTION gate, false for the LIST, because the framework's list
  filtering honours it. A hand-made Company UP scoped to applicable_for = Employee leaves the request
  list unfiltered while company_visible still refuses the decision.
- Structural: ot_row_scope/approval_row_scope carry no company predicate, approval.py:133 does. Reaches
  every company-fenced approver on all five request doctypes. The auto-provisioned fence
  (employee_hrms_scope.py:186, apply_to_all_doctypes=1) is consistent; hand-made and legacy UPs are not.

CORRECTED AFTER REVIEW — the replaced-approver DocShare case is NOT dead code. The earlier wording
claimed approval_row_scope "grants the named approver submit", so the share is never created. **A
has_permission hook cannot GRANT a ptype in Frappe — the role DocPerm is evaluated first and the hook
can only SUBTRACT.** Verified from the doctype JSON: the Employee role carries submit=0 on Leave
Application, Expense Claim and Shift Request (only Leave Approver / Expense Approver / HR Manager /
HR User carry submit=1). hr/utils.py:986 shares exactly when has_permission(submit) is False. So for
the very persona approval.py:39-51 was written for — "a team lead holding only the Employee role" —
**the DocShare IS created**, by live callers at leave_application.py:116, expense_claim.py:160 and
shift_request.py:29. The share is a no-op only for approvers whose ROLE already carries submit.
DO NOT delete share_doc_with_approver or the DocShare branch of approval_row_scope.has_permission as
dead: every Employee-role-only named approver would instantly lose sight of the requests routed to
them.

### G. ignore_permissions=True in approval.py — NO BYPASS FOUND
All three entry points are gated before elevation (decide:230 -> _decision_access:136 ->
_request_read_allowed:147; finalize:398 direct; get_decision_actions:300/can_decide via
_decision_access). Elevation at :236 and :406 is reachable only on access == "routed". But the checks
are not strictly NARROWER than the row scope — the true invariant is
`elevated submit = row-scope READ ∩ routing`, and routing carries no company fence.

## (d) Open list, ranked by impact on pay

### Tier 1 — reaches salary, banking or tax data
1. **26 of 32 Script Reports unfenced.** Payroll reports take a caller-supplied `company` with NO
   validation; salary_payments_via_ecs.py:77 makes it OPTIONAL (verified), so omitting it returns every
   company. income_tax_deductions.py:72 pulls every PAN site-wide. The helper report_scope.py:108
   fenced_companies exists and is unused by 27 of them.
2. **Four reports bypass a fence that already exists** — worse than one never written, because the
   boundary was designed, wired into hooks.py and tested, and the report reads past it via
   get_all/frappe.qb (neither applies permission_query_conditions):
     unpaid_expense_claim.py:165-166            bypasses approval_row_scope on Expense Claim (hooks.py:188)
     income_tax_computation.py:62               bypasses company_scope.employee_query_conditions (hooks.py:197)
     attendance_day_audit.py -> utils/attendance_day_audit.py:253,277   bypasses employee_owned_row_scope
     checkin_provenance_audit.py -> sync/checkin_recovery.py:236        same
3. **Non-HR roles reach pay and claim data** (roles read from the report .json):
     project_profitability              -> Accounts User, Projects User, Manufacturing User (SalarySlip.base_gross_pay)
     intercompany_salary_cost_allocation -> Accounts Manager, Accounts User (gross pay + employer contributions)
     unpaid_expense_claim               -> **Expense Approver** — should see only claims routed to them; via #2 sees everyone's
     employee_leave_balance_summary     -> **Leave Approver** — whole-company balances, not their team
4. employee_ctc_break_up.py:359 — System Manager reads anyone's full CTC, any company.

### Tier 2 — leaks confidential HR data, not pay
5. **employee_issue_row_scope.py:106 FAILS OPEN** — offboarded and duplicate-claimed logins can read HR
   tickets, including another person's, via the document API.
6. appraisal.py:887-888 — phantom reporting chain on the Desk list; transitive, unfenced. Fixed in kpi.py,
   not at the source.
7. ot_row_scope.py:38 — OT and RL rows of INACTIVE and CROSS-COMPANY reports visible to a manager.

### Tier 3 — blocks someone doing their job
8. (c)F — a designated approver sees the request and cannot decide it; the message gives no hint it is
   a company fence.
9. RL grant concurrency — no lock equivalent to the OT path.

### Tier 4 — unreviewed authority, needs a RULING not a patch
10. (c)B — reports_to managers can approve AND CANCEL requests routed to a named approver. This is the
    real content of what the ledger filed as "N03 OT approver policy".

## (e) Smallest check that goes red today

ALREADY RUN by the auditor, savepointed and rolled back:

| Item | Check | Actual |
|---|---|---|
| 5 | offboard an Employee, keep the User enabled, call employee_issue_row_scope.has_permission on their own ticket | own_employees: [] / LIST query: 1=0 / **has_permission(read): True** |
| 5 | two Active Employees claiming one login | list 1=0, **has_permission: True on BOTH employees' rows** |
| 7 | manager with one inactive and one cross-company report | ot_row_scope._reporting_employees -> BOTH; get_direct_report_employees -> [] |
| 10 | Leave Application named to a different approver, ask about the reports_to manager | read=True write=False submit=False but **_is_routed_approver: True** |
| (c)C | same, as System Manager | row-scope read=False but **_is_routed_approver: True** |
| 8 | hand-made Company UP with applicable_for='Employee' | framework fences OT Request: False (list shows); company_visible(other co): False (decide refuses) |

PROPOSED, not yet run:
  1,3  call execute() on salary_payments_via_ecs with filters={} as a user holding a Company UP; assert
       every returned row's company is in allowed_companies(). RED today: the filter is optional.
  2    as an Expense Approver with no claims routed to them, run unpaid_expense_claim.execute(); assert
       the row count equals frappe.get_list("Expense Claim") for them. RED today: the report uses frappe.qb.
  4    as System Manager, employee_ctc_break_up.validate_employee_access(<someone else>) must raise
       PermissionError. RED today: the role is in the allow-list.
  6    a user with an Active Employee plus a leftover inactive one with subordinates; assert
       get_allowed_appraisal_employees() excludes the phantom chain. RED today: the default seed is raw.
  9    two concurrent RL grants against one allocation; assert one waits. RED today: no lock.

## (f) Where the ledger over-claims

1. **Four wrong entries in the "reports fenced" set.** Only SIX are fenced: Salary Register (:301),
   Monthly Attendance Sheet (:73-74), Employee Analytics (:23) via fenced_companies; Employee Advance
   Summary (:20,273) and Shift Attendance (:19,293) via a SECOND helper, report_scope.py:105
   apply_employee_scope + :53 scoped_companies; Appraisal Overview (:78-109) via
   get_allowed_appraisal_employees. **Employee Leave Balance is listed as fixed and was NEVER TOUCHED**
   — employee_leave_balance.py:147-165 is a raw frappe.qb Employee query with optional, unvalidated
   company/department/employee filters that does not even default to status="Active" (verified).
2. "PWA and Desk approval capability" is not settled. The endpoint is correct about STATE; it is wrong
   about AUTHORITY, because it reports what _decision_access allows and that is wider than the row
   scope claims — (c)B.
3. N02 and N03 are listed as OPEN and are CLOSED in code, both by commits made the same day, one of
   them AFTER the ledger row was written. Pure bookkeeping rot.
4. "Family hunt not yet done" understates the size. It reads as a tidy-up. It is 26 unfenced reports,
   4 active fence bypasses, and 4 non-HR roles with a path to pay data.

EFFICIENCY NOTE: provident_fund_deductions.py:60-77 get_conditions is imported by
professional_tax_deductions.py and salary_payments_based_on_payment_mode.py — one fix closes three.

## Re-verified independently in this session

  employee_issue_row_scope.py:106   owner_user = frappe.db.get_value("Employee", doc.employee, "user_id");
                                    allowed = owner_user == user   -> E1 CONFIRMED, and the canonical
                                    _own_employees() sits at line 28 OF THE SAME FILE
  ot_row_scope.py                   grep -c -i company -> 0        -> D CONFIRMED
  ot_row_scope.py:34-38             _reporting_employees does use canonical own_employees for IDENTITY,
                                    but the reports query carries NO status and NO company filter
                                                                    -> A#2 CONFIRMED as stated
  salary_payments_via_ecs.py:77     `if filters.get("company")`     -> Tier-1 #1 CONFIRMED, optional
  employee_leave_balance.py:147-165 raw qb, optional company/department, no Active default
                                                                    -> (f)1 CONFIRMED, ledger is wrong

## REFUTED — correction to the auditor's own table

(c)A row #3 claims approval.py:85 _is_routed_approver has "no Active filter". **FALSE.** approval.py:80-85
reads:

    from hrms.utils.identity import own_employees
    mine = own_employees(user)
    if not mine: return False
    routed = frappe.db.get_value("Employee", employee, "reports_to") == mine[0]

CORRECTED AGAIN AFTER REVIEW: this refutation was graded on the wrong axis. `own_employees` IS the
canonical primitive — normalized, Active-only, fail-closed on ambiguity
(identity.py docstring). So routing resolves the CALLER correctly. Its real gap is narrower than
claimed: no company fence on the REPORT, i.e. a manager may be routed a subordinate in another company.
Do not quote row #3's Active column as it was written. But the column itself was measuring the wrong
thing: rows #5 (api/__init__.py:320) and #6 (roster.py:54) ALSO resolve their CALLER canonically and
are graded "Active: no" on the SUBORDINATE. Split the column into `caller Active / report Active`. On
that axis approval.py:85 reads caller=yes / report=NO — an INACTIVE employee's pending request still
routes to the manager for elevated submit. So the remaining gap is "no status filter AND no company
fence on the report", not the company fence alone. Anyone fixing the company side must not assume the
status side is handled.
