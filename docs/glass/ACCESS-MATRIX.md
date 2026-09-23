# Nadi access matrix: who sees and does what (draft, 23 Sep 2026)

Status: **DRAFT, describes the code as it is.** Owner ruling R4: docs now;
no access change without a yes on that exact line. Every cell cites the rule
in code that grants it.

Principles we measure against: least privilege and separation of duties
(NIST SP 800-53 AC-6, AC-5), role-based plus relationship rules (NIST RBAC;
NIST SP 800-162), need-to-know (ISO/IEC 27001:2022 A.5.15), deny by default
(OWASP Top 10 A01), personal data minimisation (Malaysia PDPA 2010).

## The people

| Who | How the system knows |
|---|---|
| Employee | has an Employee record linked to their login |
| Team lead / manager | someone's `reports_to` points at their Employee |
| Named approver | named as `leave_approver` / `shift_request_approver` on someone's Employee, or as the approver on a request |
| Chain approver | above a named approver or manager, any number of levels up (owner ruling 21 Sep: "the chain goes until they don't have") |
| HR User / HR Manager | holds the role (`HR_SEE_ALL_ROLES`, hrms/hr/utils.py:65), inside their company fence when they have one |
| System Manager | admin role; **not** HR, sees no one's HR data (hrms/hr/utils.py:68-97) |

## Requests: see and decide

| Record | Employee | Manager (direct) | Named approver | Chain approver | HR | System Manager |
|---|---|---|---|---|---|---|
| Leave, Expense, Shift request | own | see (read) | see + decide | not routed | see + decide | no |
| Overtime, Replacement Leave | own | see + decide | see + decide | see + decide | see + decide | no |
| On Duty (Attendance Request) | own | see + decide | see + decide | see + decide | see + decide | no |
| Comp leave | own | see + decide | see + decide | see + decide | see + decide | no |
| Check-in outside the area | own | see + decide | see + decide | see + decide | see + decide | no |

Rules in code: `approval_row_scope` (hrms/overrides/approval_row_scope.py:62,
direct reports only); `ot_row_scope` (hrms/overrides/ot_row_scope.py:52,90) and
`employee_owned_row_scope` (hrms/overrides/employee_owned_row_scope.py:233,284),
both via `get_employees_routed_to` (hrms/hr/utils.py:1312, the whole chain);
decide gate `_is_routed_approver` (hrms/api/approval.py:83); check-ins outside
the area `_pending_for_approver_query` (hrms/api/remote_checkin.py:257).

**Open line A1.** Chain approvers see and decide at every depth below them
for five request types. The Approvals page (alpha.4) now separates **Yours**
from **Other teams**, so this is visible rather than confusing. Keep, or
narrow to direct + named? Owner said "this looks correct" (23 Sep); recorded
here for a formal yes.

## Other records

| Record | Employee | Manager | HR | System Manager | Rule |
|---|---|---|---|---|---|
| Who is off today + leave TYPE | own | own team | all in fence | no | hrms/api/team.py:224,279 (type only) |
| Leave REASON | own | **never** | yes | no | owner rule; team.py sends leave_type only |
| Score (KPI) | own | own team (tier) | all in fence | no | hrms/api/kpi.py:494 `_scope` / `_require_kpi_read`; "protected at any cost" |
| Pay, salary, benefits, tax | own | no | in fence | no | employee_owned_row_scope (hooks.py:207-240) |
| Attendance, check-ins | own | own team (read) | in fence | no | employee_owned_row_scope |
| Colleague directory | name, job, department, photo | same | full | no | STAFF_DIRECTORY_FIELDS, hrms/api/__init__.py:161 |
| IC / passport / bank | own | no | in fence | no | not in STAFF_DIRECTORY_FIELDS |
| HR issue board, SOP authoring, 1-on-1 | no | no | yes | no | `is_hr_operator` hrms/hr/utils.py:68 |
| Announcements | read (audience) | read | publish in Desk | no | hrms/api/announcements.py |

## Known risks (need a yes per line before any change)

| # | Risk | Evidence | Proposal |
|---|---|---|---|
| A1 | Chain approvers reach every level below them | table above | keep, now shown as "Other teams" |
| A2 | The "HR" role profile bundles approver roles **with** HR User/Manager, so making someone an approver makes them HR (see-all) | hrms/setup.py DEFAULT_ROLE_PROFILES; seen live 3 Sep (Hafiz) | add an "Approver" role profile without HR roles |
| A3 | HR with no Company permission sees every company | company_scope `company_visible` is True for an unfenced user | keep for group HR; fence per-company HR |
| A4 | Desk script reports not fenced | owner deferred 13 Sep | stays deferred |

## Checks

Automatic tests guard the enforced lines: hrms/api/test_approval.py,
hrms/api/test_approvals_list.py, hrms/overrides/test_approval_row_scope.py,
hrms/overrides/test_row_scope_identity_parity.py. Any new
approved line gets its own test in the same commit.
