# Payroll and salary stay out of Nadi / Verifica

**Status:** DECIDED. Ruled by HR, relayed by Nabil, 26 August 2026.

## The ruling

Salary and anything on that path is **not** coming to Verifica. It is sensitive
and it lives in a separate application. This is a deliberate boundary, not a gap
waiting to be filled.

## What it settles

An audit on 26 August found no payslip screen anywhere in the PWA — 49 routes
and not one reaching Salary Slip — and flagged it as a basic-tier gap on the
grounds that "an employee can see their payslip" is close to the definition of
an HRMS.

That reading was wrong for this company. The absence is the design.

Worth recording that neither `as-hr_kpi` (v15, live) nor upstream
`origin/version-16` has such a screen either, so nothing was ever removed. The
fork has never carried payroll to the employee.

## What follows

**Parked, not deleted** — per the standing rule that everything on ERP/Verifica
either works or is explicitly parked. These stay in
`parity.UNMIRRORED_CANDIDATES` and should be ruled **Not needed on hub** on each
ERP Instance, which is a signed record carrying `ruled_by` and `ruled_on`:

    Salary Structure · Salary Structure Assignment · Salary Slip
    Payroll Entry · Payroll Period · Income Tax Slab
    Additional Salary · Employee Benefit Application · Gratuity
    Leave Encashment

The **Payroll** and **Tax & Benefits** workspaces stay in Desk. They ship with
the app, they are fully built (Payroll carries 37 links), and removing them
would breach the same rule. They simply stay unpopulated.

No PWA work follows. The payslip screen is dropped from the plan rather than
deferred.

## Still open, and it is not this decision's job to answer

The separate payroll application needs attendance and leave data, and staff now
record both in Nadi. Nothing currently carries that across — the shadow sync is
`ALLOWED_HTTP_METHOD = "GET"` by assertion and never pushes anywhere.

That is an interface question for whoever owns the payroll app, and it is now a
**defined boundary** rather than an accidental gap. Recorded here so it is not
rediscovered as a surprise at cutover.

## Not covered by this ruling

**Expense Claim and Travel Request** are reimbursement rather than salary, and
the PWA already carries expense claims end to end. Assumed to stay in Nadi. If
HR means them under the same sensitivity rule, that is a separate decision and
this file should be amended.

**Employee Advance is already settled and is NOT covered by this file.** It was
removed from the PWA deliberately in v15.112.0 under a different policy — staff
may not request an advance and the company does not issue them — and
`patches/v15_112_0/lock_employee_advance_readonly.py` enforces it by revoking
create/write/submit/cancel/amend/delete for every role. Nothing to decide and
nothing to restore.
