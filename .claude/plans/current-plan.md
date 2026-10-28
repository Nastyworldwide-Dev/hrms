# Plan: Cost Tag/Center from an Excel upload in Data Import (owner, 28 Oct 2026)

Owner: "the excel will contain staff name, ID, year/month, cost tag/center, old cost tag/center, percentage and will
auto show on each staff profile under overview" — upload in Desk → Data Import. Rule (owner): "just follow the file
upload: if have same existing can replace, if new then new row; the name and staff id is for you to read where to put".

## GOAL
HR uploads one Excel in Data Import; each row lands in that employee's Cost Tag/Center Allocation table (Employee →
Overview). Same employee + Year/Month + Cost Tag/Center (or Old Cost Tag/Center) already there → that row's percentage
is replaced. Otherwise → a new row is added. Other rows are untouched.

## FLOW
Data Import, Document Type "Cost Tag/Center Upload", Insert New Records → one Cost Tag/Center Upload record per Excel
row (employee, employee_name, allocation_month, cost_center, territory, percentage) → its after_insert puts the row
on the Employee (match on month + tag; replace % or append) and saves the Employee, so the existing check runs
(each month totals 100%). If it fails, the import row fails with that reason and nothing is half-written.
Employee ID is what places the row; Staff Name is read for the template and checked loosely, not used to place.

DESIGN SKILLS: NONE (Desk doctype + Data Import only; no PWA screen)

## MOCKUP: NOT NEEDED (Desk Data Import is Frappe's own screen; no new UI)

## EXPECTED OUTPUT
- Template download in Data Import shows: Employee ID, Staff Name, Year/Month, Cost Tag/Center, Old Cost Tag/Center,
  Percentage.
- Upload 2 rows for one employee for Oct (60/40) → profile shows both; upload again with 70/30 → same two rows now
  70/30, no duplicates; a Nov row → added, Oct kept.
- A month that would not total 100% → that row fails in the import log with the month named.
- Bench-free tests red first, then green. Needs bench migrate (new doctype).

## RISK
New standalone doctype (log of uploaded rows, HR-only). Writes through Employee.save, so all Employee validation and
permission checks still apply. Rollback: revert; uploaded rows already on Employees stay as normal table rows.

## Pipeline Summary
owner ask → plan (this) approved → TDD → commit → review → push → owner deploys with migrate.
