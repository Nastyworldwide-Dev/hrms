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
