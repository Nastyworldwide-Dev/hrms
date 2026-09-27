# ROSTER Feature Map

## 1. Where It Lives

**Roster App (Vue SPA at /hr/roster):**
- roster/src/views/MonthView.vue — Desk-style calendar grid view with company selector
- roster/src/views/Home.vue — app home/launcher
- roster/src/router.ts:12 — route base path `/hr/roster`
- roster/src/components/ShiftAssignmentDialog.vue — UI to create assignments
- roster/src/components/MonthViewTable.vue — shift grid renderer
- roster/src/components/MonthViewHeader.vue — filters (status, company, dept, branch, designation)

**PWA Team Roster (native mobile-first):**
- frontend/src/views/team/TeamRoster.vue — week view of direct reports' shifts
  - Line 14: "Team of" HR-only manager selector
  - Line 56: "Assign" button per team member
  - Line 95: shift_type + shift_location Link fields
  - Line 223: calls hrms.api.roster.insert_shift to submit
- frontend/src/data/team.js:35-37 — teamRoster resource calls hrms.api.team.get_team_roster
- frontend/src/data/team.js:42-44 — assignShift resource calls hrms.api.roster.insert_shift

**Backend APIs:**
- hrms/api/roster.py — all whitelisted write methods (create_shift_schedule_assignment, delete_shift_schedule_assignment, swap_shift, break_shift, insert_shift)
- hrms/api/team.py — read methods (get_team_roster, get_team_status, has_team, is_approver, get_managers)
- hrms/www/roster.py — web page shell; sets no_cache=1, injects CSRF token

**Desk (Frappe UI):**
- hrms/hr/doctype/shift_assignment/shift_assignment.json — doctype with permlevel 1 "both_shifts_on_purpose" HR field
- hrms/hr/doctype/shift_assignment/shift_assignment.js — no custom form logic
- hrms/hr/doctype/shift_assignment/shift_assignment_list.js — calls hrms.add_shift_tools_button_to_list
- hrms/hr/doctype/shift_schedule_assignment/shift_schedule_assignment.py — creates Shift Assignments on a schedule

---

## 2. Who May Use It (Roles, Predicates, Scope)

**Write Fence (_ensure_can_roster):**
- hrms/api/roster.py:23-62 — every write (insert/swap/break) gates on _ensure_can_roster(employee)
  - Line 47-48: HR who sees_all_employee_data AND company_visible → allowed
  - Line 50-56: Shift Supervisor with employee in direct reports (reports_to == caller) AND company_visible → allowed
  - Line 62: All others → PermissionError

**Role Definition:**
- hrms/api/roster.py:20 — ROSTER_SUPERVISOR_ROLE = "Shift Supervisor"
- hrms/patches/v16_0/add_shift_supervisor_role.py — creates the role at install time

**Read Fence (get_team_roster):**
- hrms/api/team.py:335-407 — get_team_roster endpoint
  - Line 345-348: Non-HR caller denied manager override; only HR may browse another manager's team
  - Line 356-359: Team of own-employee is never fenced; team of other is company-fenced (allowed_companies)
  - Line 357: members read with reports_to=team_of AND status=Active
  - Line 363: returns branch (+ company, designation, dept)

**HR-Only Scope:**
- hrms/api/team.py:30-32 — _is_hr() = sees_all_employee_data(user)
- hrms/api/team.py:91-99 — get_managers() returns [] if not HR; HR gets all active managers with reports
- hrms/api/team.py:100 — applies allowed_companies() fence even for HR

**Scope Mechanism (branch/dept/team):**
- hrms/api/roster.py:65-72 — ALLOWED_EMPLOYEE_FILTERS = {status, company, department, branch, designation, employee_name}
- hrms/api/roster.py:104-116 — filters applied as equality or ["in", [...]] for multi-company callers
- frontend/src/views/team/TeamRoster.vue:50 — shows member.branch or departmentLabel(member.department)
- hrms/api/team.py:363 — roster query returns both branch AND department per member

**Company Scoping:**
- hrms/utils/company_scope.py (imported) — get_permitted_companies, company_visible, scope_employee_filters
- hrms/api/roster.py:46-56 — every write checks company_visible(employee.company)
- hrms/api/team.py:356-359 — get_team_roster applies allowed_companies() fence to non-own-team reads

---

## 3. What a Leader Can Do

**From PWA Team Roster:**
- frontend/src/views/team/TeamRoster.vue:176-182 — load() fetches roster with start_date, end_date, manager (HR only)
- frontend/src/views/team/TeamRoster.vue:23-30 — week navigation (prev/next)
- frontend/src/views/team/TeamRoster.vue:56-59 — click "Assign" to open assignment sheet
- frontend/src/views/team/TeamRoster.vue:212-219 — form pre-fills shift_type, shift_location, start_date (week start), end_date (week end)
- frontend/src/views/team/TeamRoster.vue:220 — canSubmit checks shift_type AND start_date (end_date optional)
- frontend/src/views/team/TeamRoster.vue:223-242 — submitAssign calls insert_shift with employee, company, shift_type, dates, status="Active", location

**From Roster App (Desk):**
- roster/src/components/ShiftAssignmentDialog.vue — create Shift Assignment (calls same API)
- hrms/api/roster.py:332-373 — insert_shift(employee, company, shift_type, start_date, end_date, status, location)
  - Merges adjacent shifts of same type/location/status (line 353-370)
  - Creates or updates Shift Assignment in database

**Shift Schedule Feature (repeating):**
- hrms/api/roster.py:182-225 — create_shift_schedule_assignment
  - Takes frequency (Every Week/2/3/4 weeks), repeat_on_days, status, location
  - Calls get_or_insert_shift_schedule (caches by type+frequency+days)
  - Creates Shift Assignments for 90 days or enqueues for longer spans (line 220-225)
- hrms/hr/doctype/shift_schedule_assignment/shift_schedule_assignment.py:64-118 — creates individual Shift Assignments on schedule days

**Edit Actions:**
- hrms/api/roster.py:247-294 — swap_shift(src_shift, src_date, tgt_employee, tgt_date, tgt_shift)
- hrms/api/roster.py:298-328 — break_shift(assignment, date) — splits an assignment at a date
  - Line 306-308: validates date is within assignment range
  - Line 318-323: deletes if on start_date; else sets end_date to date-1
  - Line 325-328: creates new assignment from date+1 onward if needed
- hrms/api/roster.py:228-243 — delete_shift_schedule_assignment — cancels all related Shift Assignments

**Aware Of:**
- hrms/api/roster.py:157-159, 376-395 — get_events reads holidays + leaves + shifts; leaves aware (approved, docstatus=1)
- hrms/api/roster.py:398-426 — get_leaves filters on status="Approved", from_date<=month_end, to_date>=month_start
- hrms/api/team.py:281-283 — TeamStatus aware of holidays via holiday_list

---

## 4. Gaps & Defects Provable from Code

**Permission Gaps Found:**
- hrms/api/roster.py:231 — delete_shift_schedule_assignment checks shift_schedule_assignment perms but does NOT call _ensure_can_roster on the employee BEFORE deleting shifts
  - RISK: HR holding Shift Schedule Assignment delete could delete all shifts from a cascade without roster fence
  - MITIGATED: Line 237-238 per-shift check is present (inside the loop)

**Missing Edge Cases:**
- hrms/api/roster.py:306-309 — break_shift does not check if date falls on a holiday or approved leave
  - No validation that the split point is a workday
  - A leader can split a shift mid-leave unaware

**State Handling:**
- frontend/src/views/team/TeamRoster.vue:32 — ResourceError shown; no loading/empty state between requests
  - Weekly navigation does not debounce; rapid clicks may overlap requests

**Leave/Holiday Gaps (observable):**
- hrms/api/roster.py:159, 429-475 — get_events calls get_holidays/get_leaves separately
  - Shifts assigned on holidays are read but not rejected or warned
  - No validation in insert_shift/break_shift against holidays

**Past/Locked Period Editing:**
- hrms/api/roster.py:332-373 — insert_shift has no date validation (no "today" check, no lock period check)
  - A leader may assign shifts retroactively with no guard
  - break_shift allows splitting any date in range, including past (line 306-309 allows all dates)

**Doctype Permission Model:**
- hrms/hr/doctype/shift_assignment/shift_assignment.json:187-241 — standard role-based perms (Employee, HR Manager, HR User)
  - Shift Supervisor role NOT in doctype perms list
  - UI roster write works via API fence, not doctype perms (API fence is stronger)
  - DESK roster (Frappe form) would NOT work for Shift Supervisor (no create/write perm)

**Unprotected Swap:**
- hrms/api/roster.py:247-294 — swap_shift allows swapping shifts from BOTH employees
  - Line 250: rejects src==tgt but not timing/holiday conflicts
  - No atomic rollback if the second insert fails; manual cleanup required

---

## 5. Data on Test Site

**Not reached.** Database query failed (table does not exist on fresh.local). Test site is clean/minimal.
- Expected counts: unknown
- Recent activity: none observable

---

## Summary of Breadth

**Swept:**
- roster/ app structure ✓
- hrms/www/roster.py ✓
- hrms/api/roster.py and team.py ✓
- PWA frontend/src/views/team/TeamRoster.vue ✓
- frontend/src/data/team.js ✓
- Shift Assignment doctype + scripts ✓
- Shift Schedule Assignment ✓
- Permission tests (test_roster.py) ✓
- Router, navbar integration, "Team of" selector ✓

**Not reached:**
- hrms/hr/workspace/shift_&_attendance (list configuration)
- hrms/hr/dashboard_chart/shift_assignment_breakup (reporting)
- roster list/form scripts beyond ShiftAssignmentDialog ✓
- Desk shift-assignment list buttons (add_shift_tools_button_to_list implementation)
- Shift Type, Shift Location doctypes (data types only, no permission logic)

