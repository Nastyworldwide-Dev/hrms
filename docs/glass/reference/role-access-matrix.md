# Who sees what in Nadi — measured, 26 August 2026

Read off a live database, not off the doctype JSON. That distinction matters
here: **this site carries `Custom DocPerm` rows, and where they exist they
replace the JSON permissions entirely.** A matrix built from the repo would be
wrong for exactly the doctypes that matter most.

## First: "team lead" is not a role

There is no Team Lead role in HRMS. `Projects Team Lead` belongs to Project
Board. Approver authority comes from two places instead:

* **`Leave Approver` / `Expense Approver`** — Frappe roles, granted per person;
* **row scope** — `Employee.reports_to`, and the approver link field on each
  request (`leave_approver`, `expense_approver`, `shift_request_approver`).

So an approver is an ordinary employee who happens to be named on a row or sits
above someone in `reports_to`. That is why `hrms/overrides/*_row_scope.py`
exists, and why granting somebody "approver access" is a data change, not a role
change.

## The matrix

`r` read · `w` write · `c` create · `s` submit · `*` own rows only
Row-scoped means a `permission_query_conditions` hook narrows what the role can
see to their own rows plus, where relevant, their reports'.

| Doctype | Employee | Leave Appr. | Expense Appr. | HR User | HR Manager | Row-scoped |
|---|---|---|---|---|---|---|
| **Salary Slip** | — | — | — | rwcs | rwcs | no |
| **Salary Structure** | — | — | — | rwcs | rwcs | no |
| **HR Settings** | — | — | — | r | rw | no |
| **Employee Separation** | — | — | — | rwc | rwc | no |
| **Employee Onboarding** | — | — | — | rwc | rwcs | no |
| **Job Applicant** | — | — | — | rwc | rwc | no |
| **Interview** | — | — | — | rwcs | rwcs | no |
| Employee | r | — | — | rwc | rwc | yes |
| Attendance | r | — | — | rwcs | rwcs | yes |
| Employee Checkin | r | — | — | rwc | rwc | yes |
| Employee Promotion | r | — | — | rwcs | rwcs | yes |
| Appraisal | rwc | — | — | rwcs | rwcs | yes |
| Performance Improvement Plan | rc | — | — | rwcs | rwcs | yes |
| Leave Application | rwc | rws | — | rwcs | rwcs | yes |
| Expense Claim | rwc | — | rwcs | rwcs | rwcs | yes |
| OT Request | rwc | — | — | rwcs | rwcs | yes |
| Employee Grievance | rwc | — | — | rwc | rwcs | yes |
| Employee Issue | rc* | — | — | rwc | rwc | yes |

**The seven bold rows are HR-only and have no Employee permission at all** —
not restricted, absent. Their lack of row scoping is therefore harmless: the
only roles that can read them are the ones meant to see everything, and HR
seeing every company is the recorded R1 decision.

Everything an employee can reach IS row-scoped. Verified functionally rather
than by reading the hook list — acting as a plain Employee-role user:

```
Employee            sees  1 of 6
Employee Checkin    sees  2 of 2   both their own
Leave Application   sees 40 of 43  all 40 their own, 0 belonging to anyone else
Salary Slip         DENIED (PermissionError)
```

## Appraisal deserves its own note

It looks alarming in the table — an employee has `rwc` on their own appraisal —
and it is correct. The protection is at FIELD level, not doctype level:

* every computed score is `read_only=1` at permlevel 0: `total_score`,
  `final_score`, `pms_total_score`, `a1_score`, `a2_score`, the section scores,
  `overall_grade`, `employee_band`, `has_serious_misconduct`,
  `has_written_warning`, `total_demerit_pct`. They are calculated in `validate`,
  never typed;
* the sign-off chain is a graduated permlevel ladder —

  | level | fields | who it is for |
  |---|---|---|
  | 1 | `appraisee_comments`, `appraisee_agreement`, `appraisee_sign_date` | the employee |
  | 2 | `appraiser_comments`, `appraiser_decision`, `appraiser_sign_date` | the manager |
  | 3 | `demerits`, `reviewer_comments`, `reviewer_sign_date` | the reviewer |
  | 4 | `second_validator_approved`, and its comments/date | the second validator |

**The Employee role holds levels 1–4 as READ only and can write none of them.**
Measured: `permlevels this Employee-role user may WRITE: [0]`. So an employee
writes their self-ratings and reflections, sees everything about their own
appraisal, and cannot sign as their own manager, clear their own demerits, or
approve the second-validator gate that a score above 90% requires.

That is a well-built model and it was checked rather than assumed — the ladder
existing is not the same as the ladder being enforced.

## Open questions for HR

Not defects. Places where the code has made a choice nobody has ruled on.

1. **An employee cannot write `appraisee_agreement`** (permlevel 1, read-only to
   them). The field offers "I agree and accept the reviews and feedback" versus
   requesting a review — so the disagreement path exists in the schema and the
   employee cannot use it. Deliberate, or an oversight?
2. **An employee can read their own demerits, misconduct flags and the
   appraiser's decision.** Reasonable — it is their appraisal — but it is the
   same sensitivity class as salary, which HR has ruled out of Verifica.
3. **Employee has `create` on Performance Improvement Plan.** Reading their own
   is clearly right; raising one for themselves is odd. Harmless, but unlikely
   to be intended.

## How to re-run this

The matrix is a snapshot; Custom DocPerm rows change it without any code change.
Rebuild by reading `Custom DocPerm` where it exists and `DocPerm` otherwise,
filtered to `permlevel = 0`, and cross-checking
`hooks.permission_query_conditions` for row scope.
