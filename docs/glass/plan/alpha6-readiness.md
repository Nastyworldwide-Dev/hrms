# Nadi Request Readiness: Gap Analysis

## Existing Readiness Checks in HRMS

| Check Name | File:Line | What It Checks | Who Sees It | How Often | Notes |
|---|---|---|---|---|---|
| **Request Access Health** | hrms/hr/report/request_access_health/request_access_health.py:28 | Permissions for each doctype (role, hook, User Permission gates via diagnose.py) for 10 PWA request types per employee | HR Manager / System Manager in Desk report | Daily job: `heal_known_shapes()` runs nightly; report callable on-demand | Uses `hrms.api.diagnose` gate walk. Catches gaps #6 (approver for row-scope hook), #9 (no user_id resolved to employee) |
| **Staff Without A Shift** | hrms/hr/report/staff_without_a_shift/staff_without_a_shift.py:32 | Gap #8: Employee has no default_shift AND no active Shift Assignment | HR Manager / System Manager in Desk report | On-demand report (no scheduler job) | Checks `default_shift` field and active Shift Assignments |
| **System Readiness** | hrms/utils/readiness.py:476 | Site-wide config gaps: scheduler, checkin, auto_attendance, leaves, holiday calendar, push, locations, orphan requests, series, ESS permissions | HR Manager / System Manager via whitelisted `/api/method/hrms.utils.readiness.system_readiness` GET | Daily job: `report_readiness()` creates Error Log when failing; also callable on-demand | Gap #1 (no holiday list) via `_holiday_calendar_facts()` / `get_holiday_list_for_employee()`. Gap #7 (no leave allocation) via count of employees without Leave Allocation. No per-employee approver check. |
| **Attendance Health** | hrms/utils/attendance_health.py:10 | Yesterday's attendance integrity: wrong assignments, shiftless punches, skipped stamps, mirrored rows, late checkouts, overwritten punches + Request Access summary | HR User / HR Manager / System Manager (Desk Error Log + alert) + log line in daily health summary | Daily job: `run_daily_health_check()` | Includes Request Access summary (top 3 refusal gates, user count) but NOT per-employee detailed breakdown. Reads request_access.summary_lines() |

## Nadi Request Setup Gaps (9 Causes of User Failure)

| Gap # | Brief | Already Checked By | Where HR Sees It | Missing / How to Surface |
|---|---|---|---|---|
| **1** | No holiday list for employee/company | readiness.py: `_holiday_calendar_facts()` line 436 | System Readiness report (`holiday_calendar` finding) | ✓ COVERED — per-employee list in report if > 0 |
| **2** | Expense Claim Type has no default_account for company | NOT CHECKED | NONE | ✗ MISSING — not scanned anywhere |
| **3** | Company has no default_expense_claim_payable_account / cost_center | NOT CHECKED | NONE | ✗ MISSING — not scanned anywhere |
| **4** | Shift Type enable_overtime off or no overtime_rates | readiness.py checks `auto_attendance` but NOT overtime config | readiness.py (`auto_attendance` finding) | ✗ PARTIAL — only auto_attendance flag, not overtime_rates table |
| **5** | No active Leave Period for company | NOT CHECKED | NONE | ✗ MISSING — not scanned anywhere |
| **6** | Employee has no approver in leave/shift/expense/reports_to chain | Request Access Health (via diagnose.py row-scope hooks + identity gate) | Request Access Health report + daily health log (top reasons) | ✓ PARTIAL — caught via permission gate walk, NOT a per-employee checklist; identity gate catches if `user_id` → Employee fails; row-scope hook catches if no own employee resolvable. No explicit check for leave_approver / expense_approver / shift_request_approver / reports_to fields. |
| **7** | No leave allocation for leave types | readiness.py: `collect_facts()` line 365 | System Readiness report (`leave_allocation` finding) | ✓ COVERED — count of employees without allocation; list of types not shown |
| **8** | No default_shift + no Shift Assignment | Staff Without A Shift report line 32 | HR Manager / System Manager on-demand report | ✓ COVERED — but report must be RUN manually; not in readiness checks |
| **9** | Employee has no user_id | Request Access Health (diagnose.py identity gate catches it) + readiness checks ess_users_without_permission | Request Access Health report (identity gate refusal) + System Readiness (ESS without permission) | ✓ PARTIAL — caught via permission gate walk, not a standalone health check |

---

## Coverage Summary

**Fully Covered (3 gaps):**
- Gap #1 (no holiday list) — readiness report
- Gap #7 (no leave allocation) — readiness report
- Gap #8 (no shift) — Staff Without A Shift report

**Partially Covered (3 gaps):**
- Gap #4 (overtime config) — only auto_attendance, not overtime_rates
- Gap #6 (no approver) — caught via permission gate when user tries to file, NOT proactively listed
- Gap #9 (no user_id) — caught via permission gate, NOT a standalone proactive check

**Not Covered (3 gaps):**
- Gap #2 (Expense Claim Type default account)
- Gap #3 (Company expense/cost_center defaults)
- Gap #5 (no active Leave Period)

---

## Current Check Visibility & How They Run

### Scheduled (Runs Without HR Action)

1. **Daily Health Log** (attendance_health.run_daily_health_check)
   - File: hrms/utils/attendance_health.py:10
   - When: Daily scheduler
   - Output: Error Log (for HR Manager) + system log line
   - Contains: Attendance integrity issues + request_access summary (top 3 gates, user count)
   - Limitation: Summary-level only, not per-employee

2. **Readiness Report** (readiness.report_readiness)
   - File: hrms/utils/readiness.py:492
   - When: Daily scheduler + whitelisted on-demand
   - Output: Error Log with 14 potential findings (scheduler, checkin, auto_attendance, leave_allocation, holiday_calendar, etc.)
   - Shows: Site-wide config gaps; includes **gaps #1 and #7** per-employee lists
   - Limitation: No expense, Leave Period, overtime rates, or approver chain checks

3. **Request Access Healing** (request_access.heal_known_shapes)
   - File: hrms/utils/request_access.py:227
   - When: Nightly scheduler
   - Output: Log entry (silent auto-repair)
   - Fixes: Role flag strips, user_id drift, self User Permission

### On-Demand (HR Must Navigate to Report)

1. **Request Access Health Report**
   - File: hrms/hr/report/request_access_health/request_access_health.py:28
   - Callable: HR Manager / System Manager, filtered by company
   - Output: List of (user, employee, request_type, refused_by gate, why) rows
   - Shows: Permission refusals per doctype; catches identity and row-scope gate issues
   - Limitation: Must be opened manually; no notifications unless scheduled as a check

2. **Staff Without A Shift Report**
   - File: hrms/hr/report/staff_without_a_shift/staff_without_a_shift.py:32
   - Callable: HR Manager / System Manager, filtered by company
   - Output: List of (employee, name, company, department, why) rows
   - Shows: Employees missing shift assignment; **covers gap #8**
   - Limitation: Must be opened manually; not in system readiness findings

---

## Recommendation: Missing Proactive Checks

To close coverage gaps before users hit them in Nadi:

1. **Add to readiness.py collect_facts():**
   - Count employees without Leave Period active for their company (gap #5)
   - Count Expense Claim Types missing default_account for each company (gap #2)
   - Count companies missing default_expense_claim_payable_account or cost_center (gap #3)
   - Per-Shift-Type: if enable_overtime=1, check if overtime_rates table is populated (gap #4)
   - Per-employee: check leave_approver / expense_approver / shift_request_approver / reports_to fields (gap #6, more explicit)

2. **Surface in Daily Health Log:**
   - Add a "Config" section to attendance_health.summary_lines() showing top failing gaps
   - Or: Schedule a separate daily "setup readiness" check

3. **Create a Nadi-specific Report (Optional but Recommended):**
   - "Nadi Readiness per Employee" — one row per employee, columns for [user_id, approver, leave allocation, shift, holiday calendar, expense capability]
   - Callable on-demand, HR-visible in Desk

---

## Query Locations for Missing Checks

To implement the missing checks, these modules would need updates:

- **hrms/utils/readiness.py** — add facts to collect_facts(); add evaluate() logic
- **hrms/utils/attendance_health.py** — add config health to daily summary
- **New module or hrms/utils/nadi_readiness.py** — if a separate per-employee Nadi readiness report is desired

