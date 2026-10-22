# Cost Tag/Center allocation with Year/Month, 22 Oct 2026

Owner: "rename that to cost tag/center allocation. adjust the doctype, field. the table must have
new collumn, its called year/month". Answers: 3 columns; a month with no rows carries the latest
earlier month's split forward; labels only (internal names stay).

APPROVED: owner, 22 Oct 2026 — "3 columns (Recommended)", "Carry forward (Recommended)", "Labels only (Recommended)"

FLOW
1. Child doctype Employee Interco Allocation: new first column `allocation_month` (Date, label
   "Year/Month", required); `territory` label -> "Cost Tag/Center".
2. Employee section + table labels -> "Cost Tag/Center Allocation" (setup.py; sync patch line bumped).
3. Validate (Employee.validate): month saved as the 1st; per month rows total 100%; a cost tag
   once per month; percentage > 0; empty table allowed.
4. Report "Intercompany Salary Cost Allocation": each slip uses the split of the latest month
   on or before the slip's month (end_date); none -> one unallocated row. Labels renamed.
5. Patch stamps existing rows with the employee's joining month (fallback: row creation), so
   today's report output is unchanged.
No push, no deploy. Needs migrate.

MOCKUP: NOT NEEDED (Desk form: one new grid column and renamed labels; no new screen)

EXPECTED OUTPUT
- Employee > Overview: section "Cost Tag/Center Allocation"; grid Year/Month | Cost Tag/Center | Percentage.
- Saving Oct 60/40 + Jan 100 works; Oct 60/30 refuses "must total 100% for Oct 2026".
- Report for Nov slip uses the Oct split; a Sep slip before any month shows unallocated.
