# FAMILY LEDGER — a restored permission row that cannot write

CLASS: a capability restored in halves. `frappe.permissions.add_permission(dt,
role, permlevel=N)` grants READ only. A restricted field whose row carries no
write flag RENDERS, accepts the edit in the form, and is silently reverted on
save by `Document.reset_values_if_no_permlevel_access`. No error, no message.

DEFECT (mine, in 33d286691): the guard called `add_permission` and stopped. The
patch it replaces did not — `staff_perm_lockdown.py:166` follows every
`add_permission` with `update_permission_property(..., "write", 1)`. Dropping
that line made the situation WORSE than the bug being fixed: before, the
checkbox was absent and HR knew something was wrong; after, it rendered, HR
ticked it, HR believed eligibility was granted, and the employee stayed on
Replacement Leave.

SECOND DEFECT, found while fixing the first: the guard keyed only on whether a
row EXISTS. A row created read-only therefore stayed read-only for ever — the
create path saw it and called the doctype healthy. That is the state the guard's
own first run left the verify bench in, measured: `write: 0` on both rows.

FIX: two jobs, not one. Create the row that is missing, and grant write on the
row that has none. Both go through `update_permission_property`.

## Call sites the machine listed

| file:line | verdict |
|---|---|
| hrms/utils/permlevel_guard.py:~141 (`add_permission`) | same-root — fixed here, write granted immediately after |
| hrms/utils/permlevel_guard.py (`_permission_source`) | same-root — now reads the `write` flag too and reports write-less rows |
| hrms/patches/v15_99_0/staff_perm_lockdown.py:166 | not-affected — it already did this correctly; it is the reference the fix copies |
| hrms/hooks.py:109 (`after_migrate`) | not-affected — same entry, corrected behaviour |

## Locking the class

- source contract: `TestTheRestoredRowCanWrite` — `add_permission` must be
  followed by a `write` grant on the same (dt, role, lvl), in that order. The
  pure set-difference tests cannot see which flags a created row carries, which
  is exactly why the defect got through.
- pure invariant: `TestARowThatExistsButCannotWrite` — an existing row without
  write is reported; a level-0 read-only row is not (that is a deliberate
  grant); a role outside the operator set is never granted write.

EVIDENCE: 2 — both defects proved red first (ValueError on the missing
`update_permission_property`, then ImportError on `rows_needing_write`); 13/13
green after. 3 — measured on the verify bench: rows read
`{HR Manager write:0, HR User write:0}` before and `{write:1, write:1}` after,
and a third run printed nothing at all. The bench was in the broken state the
first version of this guard created, which is how the fix was verified against
the real failure rather than a constructed one.

---

# FAMILY LEDGER — a select value the field does not declare

CLASS: a string literal compared against a Select field, where the literal is
not one of that field's options. Python raises nothing; the comparison is
simply always false. A branch that never runs is indistinguishable from a
branch that was not meant to run, which is why both instances survived.

## Instances found and fixed

| file:line | literal | field declares | what it did |
|---|---|---|---|
| hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py:164 | `assignment_based_on == "Leave Policy"` | `""`, `"Leave Period"`, `"Joining Date"` | always false, so EVERY Leave Allocation a policy created was written with `leave_period = ""` — including the period-based ones it was meant to stamp. `leave_encashment.py:346` reads `allocation.leave_period` and carried the blank forward. |
| hrms/hr/doctype/employee_referral/employee_referral.py:54 | `status in ["Pending", "In process"]` | `Pending`, `In Process`, … | lower-case `p`. A referral already in progress never mapped to Job Applicant `Open`; it copied `"In Process"` into `Job Applicant.status`, which does not declare that option. |

## Call sites the machine listed

| file:line | verdict |
|---|---|
| hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py:164 | same-root — fixed here |
| hrms/hr/doctype/employee_referral/employee_referral.py:54 | same-root — fixed here |
| hrms/hr/doctype/leave_encashment/leave_encashment.py:346 (`leave_period=allocation.leave_period`) | not-affected — it copies whatever the allocation holds. Correct once the allocation is correct; no change needed. |
| hrms/hr/doctype/leave_allocation/leave_allocation.py:57 (`get_leave_period`) | not-affected — resolves the period from dates, independent of the stamped field |
| hrms/hr/doctype/compensatory_leave_request/…:93 and replacement_leave_claim.py:135 | not-affected — both pass a leave_period they resolved themselves |

Historical rows: allocations already created with a blank `leave_period` are
NOT repaired here. Not proposed either — it is a mass write over submitted
leave records and needs Nabil's word for the exact range.

## Locking the class

`hrms/tests/test_select_literals_are_declared.py` — a gate, not a regression
test for two lines. It builds {doctype -> {select field -> declared values}}
from every doctype JSON, then scans every non-test module in the app for
`x.field == "literal"`, `!=`, and `in [...]`, resolving `x` through `self` (the
controller's own doctype) and through `x = frappe.get_doc("Doctype", ...)`.

Verified as a gate: red on HEAD~ with exactly these two findings and no false
positives across the whole app; green after the two fixes. Options that name a
doctype or carry a jinja expression are skipped — they are filled at runtime
and there is nothing static to check.

EVIDENCE: 2 — the gate was written first and failed on both instances by name.
3 — bench-free suite diffed against the 174-failure baseline: no new failures.
ruff clean, ruff format applied.
