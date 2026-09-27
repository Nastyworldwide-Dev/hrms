# PWA Calendar & Team Screen Data Analysis

## 1. get_day(date) — Sections Returned & Who Sees Them

### Employee's own day (me):
- `date`: The requested date
- `status`: Attendance status (Present, On Leave, Half Day, Absent, Work From Home)
- `leave_type`: Leave type if on leave (e.g., "Casual Leave")
- `worked_hours`: Hours worked (float)
- `ot_hours`: Overtime hours (float)
- `shift`: Object with shift name, start_time, end_time
- `punches`: List of check-ins/check-outs (IN/OUT time, skipped status, next_day flag)
- `counted_elsewhere`: Check-outs after midnight that count on previous work day
- `claim`: OT claim status for the day (status, approver_name) or null

**Who sees this:** Employee (always); Approver viewing another day via team (not applicable)
**Privacy rule:** No leave reason/description read — manager sees type, never why (line 613)

### Team summary (team_off):
- Array of team members off that day
- Per member: `employee`, `name`, `leave_type`, `half_day` (true/false)
- NO reason/description field is read

**Who sees this:** Approver/manager only (via get_day); their direct team only
**Privacy rule:** Manager sees who is off and leave TYPE, never the reason (line 613-614)
**Source:** _who_is_off() line 586 — filters to direct report employees passed from get_direct_report_employees()

### Coverage (coverage):
- `headcount`: Total team member count
- `present`: Count present + half day
- `on_leave`: Count on approved leave
- `absent`: Count marked absent
- `unmarked`: Count with no attendance row marked yet

**Who sees this:** Approver/manager (direct team on the day)
**Source:** _coverage() line 620 — same employee list as team_off

**File references:**
- `get_day()` line 654
- `_my_day()` line 514
- `_who_is_off()` line 586
- `_coverage()` line 620

---

## 2. get_month_flags() — "Open" Dot Computation & Team Signals

### "Open" (request waiting on approver):
- Computed by `_open_days()` line 188
- Lists requests from the caller's **YOURS** section of the Approvals page only
- Reads dates from request records matching `OPEN_DATE_FIELDS` (line 50-56):
  - Leave Application: `from_date`, `to_date`
  - OT Request: `ot_date`
  - Attendance Request: `from_date`, `to_date`
  - Shift Request: `from_date`, `to_date`
  - Compensatory Leave Request: `work_from_date`, `work_end_date`
- Gate: only approvers see dots (checked via `is_approver()`)
- Privacy: reads dates only, never reasons (line 193)
- **Non-approvers get no open dots at all**

**File reference:** line 188-217

### Per-day team signals on month grid:
- **NO team-level signals on the month grid today**
- The grid shows the EMPLOYEE's own calendar only
- Team data is on a separate "Team" screen with its own month picker

**Month grid flags returned (FLAG_ORDER, line 45):**
1. leave
2. travel
3. training
4. holiday
5. event
6. open (approvers only)
7. needs_you

Max 3 dots per tile (MAX_DOTS, line 37)

**File reference:** line 328-413

---

## 3. Team Screen (TeamDashboard.vue + get_team_status)

### What it shows per team member per day:
- `status`: Present / On Leave / Not In Yet / Absent / Off / Scheduled
  - Derived from _attendance_, leave approval, holiday list, and shift state
- `shift`: Shift type name + shift start/end times
- `first_in`: First check-in time (IN punch)
- `last_out`: Last check-out time (OUT punch)
- `out_next_day`: Boolean — whether the OUT was after midnight
- `counted_on`: Date the taps count on if worked past midnight
- `leave_type`: Leave type if on leave
- `leave_until`: End date of leave
- `half_day`: Boolean
- `employee`, `employee_name`, `designation`, `department`
- `shift_start`, `shift_end`: Actual shift window times

### Multi-date capability:
- Month picker: selects a date on the calendar
- Calendar shows: today (dot) and selected date (filled highlight)
- Same day can be browsed repeatedly by tapping different dates
- HR users can browse any manager's team via a dropdown selector

**Who sees what:** Approver/manager sees direct reports only; HR sees any manager's team (if allowed by company scope)

**File references:**
- TeamDashboard.vue line 1-175
- get_team_status() line 138-331
- derive_member_status() — imported, computes final status

---

## 4. Team Data Existing Server-Side But NOT Shown to Approver on Calendar/Team Screens

### Employee Checkin fields (not shown on calendar/team):
- **Location data:**
  - `latitude`, `longitude`: Raw coordinates
  - `location_source`: "GPS" or "Network"
  - `location_accuracy_m`: Accuracy in meters
  - `location_fix_age_s`: Age of location fix in seconds
  - `geofence_distance_m`: Distance from geofence center
  - `geofence_radius_m`: Radius of the geofence
  - `geofence_outcome`: Outcome (inside/outside/imprecise)
  
- **Remote context:**
  - `selfie_image`: Captured selfie (BLOB)
  - `capture_selfie`: Boolean (was selfie required)
  
- **Shift details:**
  - `shift_start`: Shift start time (datetime)
  - `shift_end`: Shift end time (datetime)
  - `shift_actual_start`: Actual shift start (computed)
  - `shift_actual_end`: Actual shift end (computed)
  - `offshift`: Boolean
  
- **Other:**
  - `overtime_type`: Type of overtime
  - `skip_auto_attendance`: Boolean (was punch skipped as noise)
  - `device_id`: Device that made the punch
  - `client_tap_id`: Client-side tap identifier

**Doctype:** Employee Checkin (hrms/hr/doctype/employee_checkin/employee_checkin.json)
**Note:** These are read at ignore_permissions in calendar.py (lines 447-456)

### Attendance fields (not shown):
- `late_entry`: Boolean — employee checked in late
- `early_exit`: Boolean — employee checked out early
- `in_time`: Check-in time
- `out_time`: Check-out time
- `actual_overtime_duration`: Computed overtime
- `overtime_type`: Type of overtime
- `standard_working_hours`: Hours expected

**Doctype:** Attendance (hrms/hr/doctype/attendance/attendance.json)

### Pending approval requests NOT shown on calendar grid:
The "open" dot only shows requests the approver must decide. But these exist server-side:
- Shift Requests (pending, approved, rejected) — awaiting a decision or approved
- Compensation Leave Requests — pending or approved
- Remote Check-in Requests — pending approver review with location/selfie data
  - Includes: `distance_m`, `latitude`, `longitude`, `employee_remarks`, `nearest_shift_location`

**These live in:** ApprovalsList (get_waiting_for_me), Remote Checkin Request, not the calendar grid

### Team member data NOT shown on team screen for a date:
- **Branch**: Member's branch (read in get_team_roster but not get_team_status)
- **Work-from-home / Remote status:** Attendance can mark "Work From Home" (seen on calendar grid state, not team screen member detail)
- **Public holidays per member's holiday list:** Holiday list is read, but only to check if a day is a holiday; the holiday name is NOT returned
- **Birthdays:** Not available on any calendar
- **Pending requests per member/date:** Remote check-in requests, pending shift changes, pending attendance fixes — not listed under each team member on the team screen
- **Last attendance status change reason:** Not tracked or shown

### Doctype fence references for team:
- **own_employees()** (hrms/utils/identity.py:257) — used in permission hooks to scope Employee reads
- **get_direct_report_employees()** (not read yet, used in calendar.py line 661, get_day) — derives the team from Employee.reports_to

---

## 5. Privacy Rules in Code (Must Stay)

| Rule | Location | Meaning |
|------|----------|---------|
| **Leave reason never shown to managers** | calendar.py:613-614 | Manager sees `leave_type` (e.g., "Casual Leave"), never `description` or leave application reason. Owner ruling Q3, 22 Sep 2026. |
| **Open dates only, never reasons** | calendar.py:193 | _open_days() reads date fields only from approval requests, never reason/remarks. Manager sees which dates a request covers, never why. |
| **Direct team only** | calendar.py:675 | Approver sees `get_direct_report_employees()` (reporting line), not all employees routed to them for approval. Team screen rule: same list. |
| **No description read on _who_is_off** | calendar.py:613 | Explicit comment: `description` deliberately NOT read. |
| **Manager sees type, never why** | calendar.py:431 | Day sheet comment: LEAVE TYPE YES, LEAVE REASON NEVER (owner's ruling Q3, 22 Sep 2026). |
| **HR may browse any manager, others see own team** | team.py:147 | Only HR can override manager parameter; everyone else pinned to their own team. |
| **Company scope on HR team browser** | team.py:99-100, 174-177 | HR users with company scope cannot see teams outside their fence. |
| **Entitled vs. empty distinction** | team.py:151-164, 186-201 | Server returns `entitled` flag: false = "you don't manage anybody", true = "your team has nobody on this day". Never same message for both. |

**Files:**
- hrms/api/calendar.py
- hrms/api/team.py
- hrms/utils/identity.py (fencing machinery, not privacy rules per se)

---

## Summary

**Approver sees on calendar today:**
- Their own day: full detail (punches, hours, shift, OT claim status)
- Their direct team on the selected date: names, who's off (with leave type), and coverage summary
- Pending requests waiting on their decision: marked as "open" dots on the month grid
- Each team member on the team screen: in/out times, shift, presence status, leave type (not reason)

**Missing (exists server-side, not shown):**
- Remote check-in requests (separate screen, not calendar)
- Shift change requests (separate request approval, not calendar)
- Late arrivals (field exists, not displayed)
- Absence with no leave (marked as "Absent" status, no detail)
- Public holiday names (only dates, marked "Holiday")
- Branch information (read for roster, not team status display)
- Location / geofence / selfie data (captured for remote, not shown on calendar)
- Team member list for other dates without picking them on the calendar one-by-one

**Privacy gates enforced in code (per memory docs & code rules):**
- Leave reasons blocked by design (never read, db.get_value asks for fields only)
- Request reasons blocked by design (reads date fields only)
- Direct team only (from reports_to graph, not all routings)
