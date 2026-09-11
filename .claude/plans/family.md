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



## AMENDMENT 2 — re-review of 4c181eeb3

Verdict DEPLOY. Three corrections, one of them to a claim I made in a commit
message.

**I said "moved", and I had copied.** The false "invisible to every user"
warning was added to the `gaps` loop without being removed from the `writeless`
loop, so a repaired write flag logged it twice — once accurately, once saying a
field had been invisible when it had rendered fine all along. The reviewer
proved it by parsing the committed file with `ast` and counting `logger` calls
per enclosing `for` node; reading the diff cannot show that the old call site
survived. Verified the same way after the fix: one warning per loop.

**The one silent write in the file was the irreversible one.**
`setup_custom_perms` moves a doctype off its shipped JSON permissions
permanently — after it, no app update to that doctype's permissions ever lands
on the site again. It was logged at `logger.info` while every reversible write
was at `warning` + `log_error`. Now the loudest. The conversion is NOT gated
off: the lockdown patch skips such doctypes, but Employee is exactly that case
and is the live defect, so the guard has to do it — loudly.

**Three discovery sources collapsed to one, for correctness not tidiness.**
`Meta.process()` merges Custom Fields and THEN applies Property Setters, so
`get_meta(dt).fields` already covers both — and it is the only source that sees
a permlevel being LOWERED back to 0. Reading `Custom Field` / `Property Setter`
rows directly sees raises only, so those two sources kept asking for a row the
site no longer needed. Deleting them also removed two unfiltered full-table
scans per migrate.

Also pinned: the Employee role's level-1 row on Employee Checkin is READ-ONLY by
design (staff_perm_lockdown.py:168-175) and must never be granted write. That
held only because "Employee" is absent from HR_ROLES — a coincidence of one
constant, not a rule. Now a rule.

EVIDENCE: 2 — 26/26 green. 3 — bench: discovery still reports all four guarded
doctypes after the source collapse, `ensure_permlevel_rows()` still a no-op, and
an AST count confirms one warning per loop.

---

## AMENDMENT — re-review of 861d9be54

Verdict DEPLOY: the Critical is fixed and was proven the right way — red on the
real broken state (rows forced to write=0, a real HR Manager save read back 0),
green after (read back 1), silent on the run after that.

Two further defects closed here.

**Latent privilege escalation.** `_needed_permlevels` queried Custom Field with
no doctype filter, and `rows_needing_write` has no level-0-holder gate — so its
effect is to grant WRITE on a row somebody deliberately left read-only, on any
doctype. One permlevel-1 Custom Field on Appraisal — an ordinary HR
customisation — and the next migrate would have granted HR write at Appraisal
level 1, where `appraisee_comments`, `appraisee_agreement` and
`appraisee_sign_date` are read-only for HR BY DESIGN so HR cannot sign on the
employee's behalf. Not live (no such field exists), closed anyway: the
precondition is one form edit away and nothing would have reported it.
The boundary is now `GUARDED_DOCTYPES`, pinned equal to the lockdown patch's own
`L1_HR_DOCTYPES` by test.

**Coverage gap closed in the same move.** Discovery read Custom Field and
Property Setter only, so of the patch's four doctypes just Employee was seen —
the other three declare their restricted fields in their own JSON. A third
source reads `frappe.get_meta(doctype).fields`, scoped to GUARDED_DOCTYPES.
Measured on the bench: needed went from `{("Employee", 1)}` to all four, and the
run stayed a no-op because the other three are already healthy.

**Log defect.** The per-row "restored ... invisible to every user" warning had
been absorbed into the write-grant loop, where it was false — the row existed
and the field rendered. Moved back to the create loop; the write path keeps its
own accurate line.

Still open, recorded for the user's decision, NOT fixed here:
the inverse leak — `lock_employee_sensitive_fields` is patch-only and
`install_app` stamps patches done without running them, so `bank_ac_no`, `iban`,
`passport_number` and `salary_mode` sit at permlevel 0 on a fresh site, readable
by anyone who can open that Employee. Confirmed live on the verify bench.
Locking them REMOVES access from staff and needs the user's explicit word.

EVIDENCE: 2 — three defects each proved red first (ImportError on
GUARDED_DOCTYPES, then the two filter assertions); 16/16 green. 3 — bench:
discovery `{Employee}` -> all four guarded doctypes, run still a no-op.

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
