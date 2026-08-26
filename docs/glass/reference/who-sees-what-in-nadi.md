# What each person sees in Nadi — verified 26 August 2026

The functional answer, not the permission table. Every row below was checked by
acting as that persona on a running site.

Companion to `role-access-matrix.md`, which covers what the DATA layer allows.
This covers what the APP actually puts in front of somebody.

## There are three personas and only one of them is a role

| Persona | How the app recognises them |
|---|---|
| **Normal employee** | everybody. No role needed beyond `Employee` |
| **Approver / team lead** | `hrms.api.team.is_approver` — computed, not a role |
| **HR** | the `HR User` / `HR Manager` role |

**"Team lead" is not a role and cannot be granted like one.** `Projects Team
Lead` belongs to Project Board. In HRMS the app asks `is_approver()`, which
returns true when ANY approval work can route to that person:

1. they hold an HR role; or
2. an active Employee has them as `reports_to`; or
3. an active Employee names them in `leave_approver`, `expense_approver` or
   `shift_request_approver`; or
4. they appear in a Department Approver table.

So making somebody an approver is **a data change** — set `reports_to`, or name
them on the employee record. Adding a role does nothing.

### Measured, four cases, one person

```
plain employee (no reports)        is_approver=False  has_team=False
same person, now has a report      is_approver=True   has_team=True
named leave_approver, no reports    is_approver=True   has_team=False
HR                                 is_approver=True   has_team=True
```

The third line is the one worth understanding. **`is_approver` and `has_team`
are deliberately different gates.** An assigned approver who manages nobody has
a real queue and no team roster; a manager can exist without ever being named on
a request. Gating the queue on `has_team` would have hidden work from the person
it was routed to.

## What is on screen

Navigation is **identical for everyone** — `NAV_ITEMS` has no role gating. Home,
Attendance, Leaves, Expenses, My KPI, Issues, SOPs. The distinction happens
INSIDE screens, not in the menu.

| Surface | Normal employee | Approver | HR |
|---|---|---|---|
| Bottom tabs / side nav | same 7 items | same 7 items | same 7 items |
| Request panels | **"My Requests" only** | + **Team Requests** + **History** | + Team Requests + History |
| Profile → Remote Approvals | hidden | **shown** | shown |
| More → Team | hidden | shown **only with direct reports** | shown |
| Check in / out | yes | yes | yes |
| Own leave, expense, OT, shift, issue | yes | yes | yes |

The gates, so they can be found:

* `RequestPanel.vue` — `isApprover.data ? ["My Requests","Team Requests","History"] : ["My Requests"]`
* `Profile.vue` — `v-if="isApprover.data"` on Remote Approvals
* `More.vue` — `if (hasTeam.data)` on the Team entry

Two design notes worth keeping, both recorded in the source:

* **The Team tab used to render for everybody** and was permanently empty for
  anyone approval work could not reach. The gate exists because of that.
* **Remote Approvals is gated on being an approver, never on the pending
  COUNT.** Count-gating made the entry vanish the moment a queue emptied,
  stranding an approver away from their own decision history.

## What HR gets that nobody else does

Not in the PWA — in Desk. HR's surface is the nine Nadi workspaces (HR Setup,
Leaves, Shift & Attendance, Expenses, Performance, Recruitment, Payroll, Tax &
Benefits, Tenure), plus the seven doctypes no employee can read at all: Salary
Slip, Salary Structure, HR Settings, Employee Separation, Employee Onboarding,
Job Applicant, Interview.

An employee's Nadi is self-service. HR's Nadi is the PWA plus Desk.

## The one thing that is presentation only

`is_approver` decides what is DRAWN. It does not decide what can be READ — the
queue endpoints enforce their own scope, and `hrms/overrides/*_row_scope.py`
narrows every list independently. A user who forced the Team tab open would
still see only rows routed to them.

That separation is correct and worth preserving: a presentation gate that is
also the security gate fails open the moment somebody edits the client.
