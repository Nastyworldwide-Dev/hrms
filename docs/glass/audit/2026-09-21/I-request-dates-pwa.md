# Audit — date-only values, PWA/Desk → API → DB → screen (read-only, 21 Sep 2026)

Repo: /home/nabil/nz-version-16 · PWA: frontend/ (Vue 3, frappe-ui 0.1.105, dayjs 1.11.13)
Invariant under test: a request for 24 Aug must never become 23/25 Aug in any browser tz.

## Ground truth verified by running node

| Expression | TZ=America/Los_Angeles | TZ=Pacific/Auckland |
|---|---|---|
| `dayjs("2026-08-24")` | 24 Aug 00:00 local (safe) | 24 Aug (safe) |
| `dayjs("2026-08-24 07:56:00")` | 24 Aug 07:56 local (safe) | safe |
| `new Date("2026-08-24")` | **23 Aug 17:00** (UTC midnight) | 24 Aug 12:00 |
| `dayjs(new Date("2026-08-24")).format("YYYY-MM-DD")` (= frappe-ui `getDateValue(getDate(str))`) | **2026-08-23** | 2026-08-24 |
| `new Date("2026-08-24T07:56:00")` | 24 Aug 07:56 local (safe) | safe |
| `new Date("2026-08-24 07:56:00")` (space) | V8 local ok; **Safari/iOS = Invalid Date** | same |

App dayjs (frontend/src/utils/dayjs.js:1-16) loads NO utc/timezone plugin → every `dayjs(str)` is local wall-clock. frappe-ui's own `dayjsLocal/dayjsSystem` (node_modules/frappe-ui/src/utils/dayjs.js:25-43) only convert when `setConfig("systemTimezone")` is set; the PWA never sets it (only `resourceFetcher`, src/resourceConfig.js:77) → they degrade to plain `dayjs`. No PWA code appends `Z`/`T00:00`, calls `toISOString()` on a business date (only pushPrompt.js:11 for a localStorage stamp), or uses `Date.UTC` except src/utils/team.js:57 (pure days-in-month arithmetic, tz-free).

## §1 Send path (PWA → server)

| Screen | Field(s) | How the value is built | Safe? |
|---|---|---|---|
| Leave form `views/leave/Form.vue` | from_date, to_date, half_day_date | FormView → FormField `fieldtype==='Date'` (FormField.vue:147) → GDatePicker (glass/GDatePicker.vue:31) → frappe-ui DatePicker. **Cell tap**: `selectDate(date)` with a local `Date` from `getDatesAfter` → `getDateValue` → local `YYYY-MM-DD` (DatePicker/utils.ts:9-18). **Typed text** (DatePicker.vue:53) and **"Today"** (:60): `getDate(text)` = `new Date("YYYY-MM-DD")` = UTC midnight → local re-format | Tap: safe. Typed: **UNSAFE west of UTC** (24→23). Today: safe (`dayjsLocal(getDate())` is now-based) |
| Leave form | posting_date | `dayjs().format("YYYY-MM-DD")` (Form.vue:30,72) | safe (browser-local "today") |
| Leave form | to_date auto-fill, half-day range, validation | string copy / lexical `<` `>` compare (Form.vue:158-159,215-237,288-298) | safe |
| Attendance request `views/attendance/AttendanceRequestForm.vue` | from_date, to_date, half_day_date | same GDatePicker path; lexical compare (:66-110) | as above |
| Shift request `ShiftRequestForm.vue:93-111`, Shift assignment `ShiftAssignmentForm.vue:67-84` | from/to, start/end | same GDatePicker path | as above |
| Expense claim `views/expense_claim/Form.vue` | posting_date | `dayjs().format("YYYY-MM-DD")` (:57,88) | safe |
| Expense claim rows `ExpenseItems.vue` | expense_date | FormField Date → GDatePicker | as above |
| OT request `views/ot/OTRequestForm.vue` | ot_date | picked from a server-listed day chip: `otRequest.value.ot_date = d.date` (:200) — server string copied verbatim | safe |
| Replacement leave claim `ReplacementLeaveClaimForm.vue` | (no date built client-side) | — | safe |
| Comp leave | not a PWA form (no Datetime fieldtype reaches FormField in any live form; grep `Datetime` hits only FormField.vue:185) | — | n/a |
| Punch `CheckInPanel.vue:1181-1189` | (no `time`) | payload has no time; server stamps the clock | safe by design |
| Late check-out `LateCheckoutDialog.vue` | checkout_datetime | native `<input type="datetime-local">` (:30) gives `YYYY-MM-DDTHH:mm` in the **browser's** wall clock; sent as `replace("T"," ")+":00"` (:155). Server `get_datetime()` (hrms/api/remote_checkin.py:1122) reads it naive = **system tz (MYT)**. Min/max/default (:105-146) compare the IN's naive MYT string parsed as browser-local (`new Date(s.replace(" ","T"))`) against browser `new Date()` | Safe for a MYT browser. For a browser in another tz the typed wall-clock is silently re-labelled MYT, and "Cannot be in the future" uses the browser's now — Medium, see F5 |
| Attendance calendar `AttendanceCalendar.vue:81,140-156` | from_date/to_date per month | `dayjs().date(1).startOf("D")` + `.format("YYYY-MM-DD")`, `endOf("M")` | safe (local dayjs) |
| Team roster `TeamRoster.vue:158-211` | start_date/end_date week window | local dayjs format; native `<input type="date">` (:104,112) yields local `YYYY-MM-DD` | safe |
| Team dashboard `TeamDashboard.vue:182-234` | date | local dayjs; day cells from team.js (string arithmetic) | safe |
| ListView filters (`ListView.vue`, `ListFiltersActionSheet.vue:58-63`; FILTER_CONFIG Date fields in leave/List.vue:61-62, AttendanceRequestList.vue:27-28, OTRequestList.vue:28, expense_claim/List.vue:65, ShiftRequestList.vue:62-63, ShiftAssignmentList.vue:27-28) | from/to/ot_date/posting_date | FormField Date → GDatePicker → same frappe-ui path | tap safe / typed unsafe west of UTC |

## §2 Display path (server string → screen)

| Component | Field | Parse | Safe? |
|---|---|---|---|
| `data/leaves.js:16-17` (LeaveRequestItem.vue:13, Home rows via RequestPanel) | from_date/to_date | `dayjs(str).format("D MMM")` | safe |
| `data/attendance.js:7-30` (AttendanceRequestItem:13, ShiftRequestItem:13, ShiftAssignmentItem:9) | from/to, start/end | `dayjs(str)` local; `.diff(...,"d")+1` on local midnights | safe (DST-safe: diff floors, both midnights local) |
| `data/overtime.js:14,26` (OTRequestItem:13) | ot_date, bank_month | `dayjs(str)` | safe |
| `ExpenseClaimItem.vue:73-82`, `ExpenseItems.vue:27`, `ExpensesTable.vue:49` | posting/from/to/expense_date | `dayjs(str)` | safe |
| `FormattedField.vue:12-13` (FormView / RequestActionSheet summaries) | any `Date` fieldtype | `dayjs(value).format("D MMM YYYY")` | safe |
| `AttendanceCalendar.vue:104-119` | event map keys | `firstOfMonth.date(day).format("YYYY-MM-DD")` lookup into server dict | safe |
| `Holidays.vue:81-91` | holiday_date | `dayjs(str)`; `isAfter(dayjs())` → today's holiday shows as past (not tz — semantic) | safe (Low) |
| `views/attendance/Dashboard.vue:220` | end_date | `dayjs(end_date).isAfter(dayjs())` → an assignment ending today is "not upcoming" after 00:00 | safe (Low, tz-free) |
| `HRIssueBoard.vue:285` | affected_date | `dayjs(str)` | safe |
| `Notifications.vue:97`, IssueList:85, HelpdeskList:107, TicketDetail:131, SopList:94, SopDetail:43 | creation/modified (Datetime) | `dayjs(str)` local | safe |
| `RequestPanel.vue:139-140` | creation (sort) | **`new Date("YYYY-MM-DD HH:mm:ss.ffffff")`** — V8 local OK; **Safari → Invalid Date → comparator NaN → Home request order undefined** | Medium (iOS), not a tz issue |
| `frappe-ui DatePicker.vue:176` `selectCurrentMonthYear` | modelValue | `getDate("YYYY-MM-DD")` → UTC midnight → `getMonth()` local | west of UTC, a value on the 1st opens the picker on the PREVIOUS month (cosmetic) |

## §3 Datetimes vs dates

- Employee Checkin `time`, Attendance `in_time/out_time`, `creation` arrive as naive `str(datetime)` (`frappe/utils/response.py:224-226`, verify-bench copy): `"YYYY-MM-DD HH:MM:SS[.ffffff]"`, Date as `"YYYY-MM-DD"`. Nothing in the PWA re-labels them.
- PWA punch display: `formatters.js:61-70 formatTimestamp`, `EmployeeCheckinItem.vue:36-44`, `ListView.vue:403`, `CheckInPanel.vue:118-119`, `TeamDashboard.vue:260-262 formatPunch` — all `dayjs(str)` = browser-local wall clock, **no tz applied** → a MYT-stamped 19:56 reads "07:56 pm" everywhere. Correct for the MYT workforce; a travelling user sees MYT clock times unlabelled (documented behaviour, not a defect).
- Staleness check `CheckInPanel.vue:496-507`: `new Date(str.replace(" ","T"))` = local parse, compared with `Date.now()`. A browser N hours off MYT skews the 16-h stale window by N hours (Low; server `is_abandoned` is authoritative, :503).
- `ListView.vue:403` formats `"HH:mm a"` → "19:56 pm" (24-h with am/pm; cosmetic, Low).
- Note: the earlier audit's reference "formatters.js:246" is stale — the file is 70 lines; the tz-converted display is in **Frappe Desk**, not the PWA.
- **Desk** (verify-bench/apps/frappe/frappe/public/js/frappe/utils/datetime.js:157-181, form/formatters.js:248, form/controls/datetime.js:55): `Datetime` values are converted system-tz → `frappe.boot.time_zone.user`; `Date` values (`str_to_user` branch :168-170) are not. So in Desk `attendance_date` = 24 Aug stays 24 Aug while `in_time` shifts for a user whose User.time_zone ≠ system — the memory note is confirmed, with the exact lines.
- `hrms/public/js/fix_day.bundle.js:42-45 fd_clock` regex-extracts `HH:mm` from the raw string (no tz); `shift_attendance.js` renders in/out as fieldtype `Time` from python `format_in_out_time` (shift_attendance.py:369-373) — tz-free. `attendance_list.js:79,98` builds Date defaults with `frappe.datetime.obj_to_str(moment())` — Desk-local, fine.

## §4 Findings

### F1 — HIGH · typed date in any GDatePicker field shifts one day west of UTC
- Problem: typing `2026-08-24` into the picker's text box (or pasting) emits `2026-08-23` when the browser tz is west of UTC.
- Location: node_modules/frappe-ui/src/components/DatePicker/DatePicker.vue:53 (`selectDate(getDate($event.target.value))`) → utils.ts:5-7 (`new Date(str)`) → utils.ts:12-17 (`dayjs(Date).format`). Reached from FormField.vue:147 (every Date field: leave from/to/half-day, attendance request, shift request/assignment, expense_date, list filters).
- Root cause: `new Date("YYYY-MM-DD")` is UTC midnight per ECMA-262; re-formatting in local tz crosses the day boundary.
- User impact: a request lands on the wrong day; validations (`from_date > to_date`) then mis-fire; approver sees 23 Aug.
- Reproduces: `TZ=America/Los_Angeles` (any UTC−); NOT in MYT (UTC+8) or Auckland. Calendar-cell taps are unaffected in every tz.
- Recommended: in GDatePicker.vue, pass a `formatter`-independent guard — intercept `update:modelValue` and re-normalise? No: the wrong value is already emitted. Fix at the source instead: patch/override `getDate` for date-only strings (`/^\d{4}-\d{2}-\d{2}$/` → `new Date(y, m-1, d)`), or wrap the picker so the text `@change` goes through `dayjs(text, "YYYY-MM-DD")`. Add a node test that asserts `getDateValue(getDate("2026-08-24")) === "2026-08-24"` under `TZ=America/Los_Angeles`.
- When: separately (frappe-ui upstream/patch-package); not a MYT production bug today.

### F2 — MEDIUM · picker opens on the wrong month west of UTC when the value is the 1st
- Location: DatePicker.vue:175-182 / DateTimePicker.vue:280-289 (`getDate(dateValue.value)`).
- Root cause: same UTC-midnight parse; `.getMonth()` on 31 Jul 17:00 local.
- Impact: cosmetic; the emitted value is unchanged. Reproduces `TZ=America/Los_Angeles`, value `2026-08-01`.
- Recommended: same source fix as F1. Separately.

### F3 — MEDIUM · Home "recent requests" ordering undefined on iOS
- Location: frontend/src/components/RequestPanel.vue:139-140 `new Date(b.creation) - new Date(a.creation)`.
- Root cause: Safari cannot parse `"YYYY-MM-DD HH:mm:ss.ffffff"` (space, microseconds) → `NaN` comparator; V8 parses it as local. The repo already learned this at CheckInPanel.vue:491-496 and fixed only that call site.
- Impact: iOS PWA Home shows the 10 "latest" requests in arbitrary order; may hide the newest. tz-independent; reproduces on Safari/iOS (any TZ).
- Recommended: `dayjs(b.creation).valueOf() - dayjs(a.creation).valueOf()` (dayjs parses the format in all engines; verified `.SSS` precision). Now (one line, Low risk).

### F4 — MEDIUM · Late check-out: browser wall-clock sent as system-tz naive datetime
- Location: LateCheckoutDialog.vue:30 (`datetime-local`), :112 (max = browser now), :150-159 (send `YYYY-MM-DD HH:mm:ss`); server hrms/api/remote_checkin.py:1122 `get_datetime()` naive → MYT.
- Root cause: naive datetime contract with no tz label; browser and server may disagree on the wall clock.
- Impact: a user with a browser tz ≠ MYT (travel, wrong phone tz) submits an OUT that is re-labelled MYT; "Cannot be in the future" and the 18:00 default use the browser's clock, so the true MYT "now" may be refused. In MYT no impact.
- Recommended: state the contract in the dialog ("Company time, MYT"), or have the server return `now` and the IN time, and validate max on the server only (it already does at :1090). Separately.

### F5 — LOW · stale-session window and "today" keys use the browser clock
- Location: CheckInPanel.vue:496-507 (`Date.now() - t.getTime()` on a naive MYT string parsed as local), :933 (`checkinTimestamp` = local now shown in the sheet), :986 (`toDateString()` pending-tap day key).
- Impact: window skews by the tz offset; server `is_abandoned` (:503) is authoritative so the button still recovers. Reproduces only with browser tz ≠ MYT. Recommended: none now; note in the punch contract. Separately.

### F6 — LOW · semantic "upcoming" checks compare a date to now instead of to start-of-day
- Location: Holidays.vue:82, views/attendance/Dashboard.vue:220.
- Impact: today's holiday / an assignment ending today is tagged past from 00:01. tz-free. Recommended: `isSameOrAfter(dayjs().startOf("day"))`. Separately.

### F7 — LOW · "HH:mm a" prints 24-h with am/pm
- Location: ListView.vue:403. Cosmetic. Now (one token).

### Confirmed SAFE (no action)
- Every business date display goes through `dayjs("YYYY-MM-DD")` (local midnight) — leaves.js, attendance.js, overtime.js, FormattedField, ExpenseClaimItem, calendar, HRIssueBoard.
- Every client-built send date is `dayjs().format("YYYY-MM-DD")`, a lexical copy of another field, a server-supplied string (OT day chips), or a native `<input type="date">` value.
- No `toISOString().slice(0,10)`, no `T00:00`, no `'Z'`, no `Date.UTC` on a business date in frontend/src.
- Backend serialises Date → `YYYY-MM-DD`, Datetime → naive `YYYY-MM-DD HH:MM:SS[.ffffff]`; PWA never re-labels.

## §5 Tests
- No frontend test exercises date parsing; the only date-related tests are source-grep assertions (CheckInPanel.test.js:40-47 checks the space→T replace). Ran `TZ=America/Los_Angeles` and `TZ=Pacific/Auckland node --experimental-test-module-mocks --test src/components/__tests__/CheckInPanel.test.js src/data/team.test.js` → 6 pass / 0 fail under both; they are not tz-sensitive.
- Gap: add `frontend/src/components/glass/__tests__/GDatePicker.tz.test.js` importing frappe-ui's `DatePicker/utils` (`getDate`, `getDateValue`) and asserting round-trip of `"2026-08-24"` under `process.env.TZ` set to `America/Los_Angeles` before the import; plus a RequestPanel sort test with a Safari-style stub (`new Date` returning Invalid) or simply asserting the code uses dayjs.
