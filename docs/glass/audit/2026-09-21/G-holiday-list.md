# Holiday List audit — "not available / not showing in Verifica (NADI Desk)"

Read-only audit, 21 Sep 2026. Repo `/home/nabil/nz-version-16` (branch `nz-glass`), upstream
apps read from `~/verify-bench/apps/{frappe,erpnext}` (ERPNext 16.32.0). One read-only probe ran on
the local `test.local` site to confirm framework behaviour; nothing on Verifica was touched.

---

## 1. Where it lives and who owns it

### 1.1 The doctype

| Thing | Where | Evidence |
|---|---|---|
| `Holiday List` doctype (+ child `Holiday`) | **ERPNext**, module **Setup** — not in this fork | `~/verify-bench/apps/erpnext/erpnext/setup/doctype/holiday_list/holiday_list.json` (module "Setup"); no `hrms/hr/doctype/holiday_list` exists |
| Shipped permissions (v16) | **HR Manager: full read/write/create**. **HR User: `select` only (no read)**. No Employee/ESS row. | same JSON, `permissions`; confirmed on test.local: `HR User read=0 select=1` |
| `Holiday List Assignment` (HLA) | **this fork**, module HR, submittable, Dynamic Link `assigned_to` -> Employee or Company | `hrms/hr/doctype/holiday_list_assignment/holiday_list_assignment.json`; perms **System Manager + HR Manager only** — HR User has nothing, not even select |
| The resolver | `hrms/utils/holiday_list.py:99-133 get_holiday_list_for_employee` — reads **only submitted HLAs** (employee first, then company, then the newest *ended* one with a warning). It never reads `Employee.holiday_list` or `Company.default_holiday_list`. | `hrms/utils/holiday_list.py:114-120,148-171,174-189` |
| How the resolver is wired | ERPNext's `get_holiday_list_for_employee` hands off to the hook `employee_holiday_list` | `~/verify-bench/apps/erpnext/erpnext/setup/doctype/employee/employee.py:373-377`; `hrms/hooks.py:806` |
| `Employee.holiday_list` field | still exists in ERPNext, but **HRMS v16 hides it on the Employee form** and nothing in the resolver reads it | `hrms/public/js/erpnext/employee.js:29 frm.set_df_property("holiday_list","hidden",1)` (loaded via `hrms/hooks.py:52 doctype_js`) |
| Fork overrides on Holiday List | dashboard links only (`hrms/hooks.py:740`, `hrms/overrides/dashboard_overrides.py:89-94`); cache invalidation `hrms/hooks.py:333-336`. **No** `permission_query_conditions` / `has_permission` for Holiday List (`hrms/hooks.py:169-246`). No fixtures dir, no Property Setters, no custom fields on it. |
| Permission patches touching it | **none**: `staff_perm_lockdown`, `permlevel_guard`, `company_fence`, `add_default_hr_role_permissions`, `gate_hr_*` never mention Holiday List (grep). Only `hrms/setup.py:925` grants `Holiday List: read` inside the **ESS User Type** bundle — which this hub does not use for provisioned users (`hrms/api/__init__.py:1224-1234` comment). |
| Company fence (`allow=Company` User Permission) | does **not** touch Holiday List — it has no Company link field | `hrms/utils/company_fence.py:1-35` |

Migration from the old model: `hrms/patches/v16_0/create_holiday_list_assignments.py` (in `hrms/patches.txt:46`)
derives one HLA per **Active** employee with a resolvable `Employee.holiday_list`, and one per Company
with `default_holiday_list`.

### 1.2 Who owns it in the sync topology

| Question | Answer | Evidence |
|---|---|---|
| Is Holiday List mirrored? | Yes — it is a **MASTER** (create-only, never stamped, never write-blocked, HR-owned on the hub), re-read one document at a time so the `holidays` child rows arrive | `hrms/sync/runner.py:137` (MASTER_DOCTYPES), `:457-460` (CHILD_TABLE_DOCTYPES), `:1468-1469` (get_doc re-read), `:691-697` (children kept) |
| Held back after cutover? | **No.** Only Attendance is held back (`LOCALLY_OWNED_AFTER_CUTOVER = ("Attendance",)`); masters are still pulled, but a row that already exists here is left untouched | `hrms/sync/cutover.py:24,35-73,84-86`; `runner.py:1179-1189` |
| Purged? | Never — purge order is `STAMPED_DOCTYPES` only | `hrms/sync/purge.py:49-63` |
| Is HLA mirrored? | **No — derived**, after every run: `_mirror_company_holiday_defaults` fills an empty `Company.default_holiday_list` from the source, then `_derive_holiday_assignments()` runs the v16 patch | `runner.py:1691-1746, 2053-2070`; the source (v15) has no HLA doctype (`runner.py:305-316`) |
| Does a Verifica clone have Holiday List rows? | Only if a full run pulled them **and** the source API user could read Holiday List there (HR Manager on the source; HR User = select only -> 403 -> doctype fails, run Partial). `check_source_permissions` probes exactly this | `hrms/sync/preflight.py:31-80`; parity audits Holiday List as CONFIG_DOCTYPE `hrms/sync/parity.py:470` |
| `Employee.holiday_list` preserved? | Mirrored verbatim on insert (only `_UNMIRRORED_FIELDS` and `user_id` are dropped) — but after cutover the Employee row is never rewritten, and the field is dead on the hub anyway | `runner.py:423-436, 537-541`; `cutover.py:35-73` |
| `Company.default_holiday_list` preserved? | **Not** in the identity projection (`MIRRORED_FIELDS["Company"]`), set once by `_mirror_company_holiday_defaults`, never overwritten | `runner.py:368-370, 1691-1735` |

**Ownership verdict:** post-cutover the hub (Verifica) owns holiday policy. The authoritative source is
**Holiday List (calendar) + submitted Holiday List Assignment (who it applies to)**. The mirrored
`Employee.holiday_list` is a vestige that only the migration/derivation reads.

---

## 2. Why Verifica does not show it — ranked hypotheses

### H1 (most likely) — HR looks where v15 kept it, and v16 hid it there
On nasty-live (v15) the Holiday List was chosen **on the Employee form** (`.reference/hrms-as-hr_kpi/hrms/public/js/erpnext/employee.js` has no hide). On Verifica (v16) `hrms/public/js/erpnext/employee.js:29` hides `Employee.holiday_list` for **every** user, and the replacement — a "Holiday List Assignment" connection in the Employee dashboard (`hrms/overrides/dashboard_overrides.py:17,70`) — is only rendered when the viewer can read HLA, i.e. **HR Manager / System Manager only** (`holiday_list_assignment.json` perms). An HR User sees no field and no connection: "the Holiday List is not there".
*Check:* open any Employee on Verifica as the reporting HR user; scroll the Attendance & Leaves section — no "Holiday List" field; the Connections panel has no "Holiday List Assignment" tile. As Administrator the tile appears.

### H2 (likely, same root) — the HR user holds HR User, not HR Manager -> no `read` on Holiday List
Frappe 16 builds the Leaves sidebar and Ctrl+K from `boot.user.can_read` (`~/verify-bench/apps/frappe/frappe/desk/desk_views.py:68-86 is_item_allowed`: doctype must be in `can_read` AND `frappe.has_permission`; awesomebar `frappe/public/js/frappe/ui/toolbar/search_utils.js:145,215`). Holiday List gives HR User **select only**, so the sidebar "Setup > Holiday List" link (`hrms/workspace_sidebar/leaves.json:139-150`) and the `/app/holiday-list` search hit disappear; the direct URL 403s. The memory note (workspace roles gate the page; children are perm-filtered) applies exactly: the Leaves Desktop Icon and workspace are gated to HR User/HR Manager/System Manager (`hrms/desktop_icon/leaves.json`, `hrms/hr/workspace/leaves/leaves.json` roles; `gate_hr_desktop_icons_and_payroll_reports.py:31-41`), so the Leaves tile shows but its "Holiday List" child does not.
*Check:* Desk > User > (HR user) > Roles: is "HR Manager" ticked? Then Role Permission Manager > Holiday List: HR User row shows Select only. Or `bench --site verifica console`: `frappe.set_user(u); "Holiday List" in frappe.permissions.get_doctypes_with_read()`.

### H3 (plausible) — Custom DocPerm rows on Verifica differ from the JSON
Verifica is a clone (`hrms/utils/permlevel_guard.py:20-27`) and the ESS User Type writes `Custom DocPerm` rows for Holiday List (`hrms/setup.py:925` -> `frappe/core/doctype/user_type/user_type.py:97-103` -> `add_permission` copies the standard rows first). Once Custom DocPerm rows exist, the JSON rows are inert (`staff_perm_lockdown.py:3-6`). Any hand edit on the source before cloning (e.g. HR Manager read removed, or a "Restore Original Permissions") is carried over and never healed — nothing in the fork re-asserts Holiday List rows.
*Check:* Role Permission Manager > Holiday List on Verifica; or `frappe.get_all("Custom DocPerm", {"parent":"Holiday List"}, ["role","read","select","write"])`.

### H4 (plausible for "list is empty") — the rows never arrived
Holiday List is pulled create-only; if the source API user lacks HR Manager on nasty-live the doctype 403s and the run degrades to Partial (`runner.py:1859-1866`; `preflight.py:31-80`). Then `Employee.holiday_list` on the mirrored employees dangles (inserted with `ignore_links=True`, `runner.py:84-86`), the derivation's inner join skips them (`create_holiday_list_assignments.py:31-44`), and `_mirror_company_holiday_defaults` refuses to set a company default that does not exist (`runner.py:1727-1728`). Every reader then answers "no calendar".
*Check:* Desk > HRMS Sync Run (latest) > results: Holiday List written/failed; `Holiday List` list as Administrator: row count; HRMS ERP Instance form > "Check source permissions" -> `blocked_403` contains Holiday List?

### H5 (low) — Holiday List rows exist but no *submitted* HLA covers today
The resolver ignores the calendar unless an HLA (docstatus 1) names it and the calendar's from/to dates cover the date (`holiday_list.py:136-171`). HLAs are derived only for **Active** employees (`create_holiday_list_assignments.py:43`) and only when `Employee.holiday_list`/`Company.default_holiday_list` were set on the source. A 2026 calendar assigned in 2025 that ended is served as a fallback with a warning only (`holiday_list.py:174-189`, marked `# ceiling`). Symptom: Desk *shows* the list, but employees' Leaves dashboard says "No upcoming holidays" and OT prices as normal.
*Check:* `frappe.db.count("Holiday List Assignment", {"docstatus":1})` vs active employees + companies; the Attendance Health nightly Error Log "Config health ... no holiday list on the shift, the employee or the company" (`hrms/utils/attendance_health.py:155-160`, `attendance_recovery.py:4176-4185`).

### Ruled out (with evidence)
- Workspace/desktop/sidebar JSON omit it: no — `hrms/workspace_sidebar/leaves.json:139-150` and `hrms/hr/workspace/leaves/leaves.json` (link "Holiday List") both carry it. (It is *not* in the Shift & Attendance sidebar; `hr_setup.json` only has the "Employees Working on a Holiday" report.)
- Domain restriction / `restrict_to_domain`: null on Holiday List; module Setup unrestricted.
- Fork permission hooks / query conditions on Holiday List: none (`hrms/hooks.py:169-246`).
- Company fence: Holiday List has no Company field, so `allow=Company` User Permissions cannot hide rows.

---

## 3. Attendance impact table

Resolver contract: `get_holiday_list_for_employee(employee, raise_exception=True, as_on=None)`; `as_on=None` means **today** (`holiday_list.py:113`). ERPNext's `is_holiday(employee, date)` calls it with `raise_exception=True` by default (`employee.py:395-404`).

| Reader | file:line | Behaviour when the employee has NO covering list | Verdict |
|---|---|---|---|
| Auto-attendance absent sweep `get_dates_for_attendance` | `hrms/hr/doctype/shift_type/shift_type.py:838-870`, `get_holiday_list :978-984` | `get_holiday_list(employee)` (no date) -> shift's own list, else resolver `raise_exception=False`, else `None` -> `get_holiday_dates_between(None, …)` -> `[]` -> **every rest day / public holiday becomes an Absent candidate** | **Silent wrong** (loud only if `should_mark_attendance` catches it) |
| `should_mark_attendance` | `shift_type.py:986-1003` | `_classify_day` returns `"normal"` after logging an Error Log; then `is_holiday(None, date)` -> False -> **marks** | **Silent wrong, but leaves an Error Log** ("Overtime priced without a holiday calendar", `ot_calculation.py:339-350`) |
| Half-day holiday check | `shift_type.py:667-671` | False -> treated as full day | Silent |
| OT day-type `_classify_day` | `hrms/utils/ot_calculation.py:299-357` | shift list if it covers the day, else resolver, else `"normal"` + Error Log; a PH (3.0x) / rest day (2.0x) prices at 1.5x | **Underpays, visible in Error Log** (also prior audit A14) |
| Off/rest split | `ot_calculation.py:273-296,351-357` | second concept: `Holiday.weekly_off` row + Company `hr_weekly_rest_day`/`hr_weekly_off_day` decides rest (2.0x) vs off (1.5x); an unlisted weekday can never be rest/off (`test_ot_holiday_classification.py:110,201`) | By design; depends on the list carrying weekly-off rows |
| Attendance Request `should_mark_attendance` | `hrms/hr/doctype/attendance_request/attendance_request.py:314, 476` | `is_holiday(employee, date)` with default `raise_exception=True` -> **throws** "No Holiday List was found … assign through Holiday List Assignment" on submit/approve | **Loud** — but the link points at HLA, which an HR User cannot open |
| Leave Application day count `get_holidays` (PWA + Desk) | `hrms/hr/doctype/leave_application/leave_application.py:1433-1438` -> `holiday_list.py:38-60` | `raise_exception_for_holiday_list=True` -> **throws** | Loud |
| Leave submit ledger / attendance update | `leave_application.py:333, 828, 891, 920` | throws (except in patch) | Loud |
| Compensatory Leave Request | `compensatory_leave_request.py:76` | throws | Loud |
| Salary Slip / Overtime Slip / Payroll Period | `salary_slip.py:695`, `overtime_slip.py:354`, `payroll_period.py:74` | throw | Loud (payroll not on Verifica) |
| Payroll Entry unmarked days | `payroll_entry.py:1145,1190` | reads **dead** `Employee.holiday_list` directly | Divergent reader (upstream) |
| Desk Attendance calendar `add_holidays` | `hrms/hr/doctype/attendance/attendance.py:614-616` | `get_holidays_for_employee` default raise -> Desk calendar view errors | Loud |
| Unmarked-days tool | `attendance.py:758-763` | `raise_exception_for_holiday_list=False` -> holidays count as unmarked working days | Silent |
| Recovery F6 "no attendance row" | `hrms/utils/attendance_recovery.py:3724-3742, 3762-3766` | `raise_exception=False, as_on=win.end` -> no holidays -> a rest day with 2 taps is planned for rebuild (protected by hold rules) | Silent, bounded |
| Recovery config health F16 | `attendance_recovery.py:4111-4200` (`_employees_without_holiday_list :4188-4199`) | lists "no holiday list on the shift, the employee or the company: rest days price as workdays" — **only for employees on shifts whose Shift Type has no own list** | **The existing self-diagnosis**; surfaces nightly via `attendance_health.py:155-176` |
| Nightly health check | `hrms/hooks.py:636-641` `run_daily_health_check` | includes the config block above -> one Error Log | Exists, HR must read Error Log |
| Team status (PWA team view) | `hrms/api/team.py:167, 234-236` | reads **`Employee.holiday_list`** directly — the hidden, dead field | **Divergent reader** |
| Roster holidays | `hrms/api/roster.py:384-392` | `raise_exception=False, as_on=month_end` -> employee skipped -> no holiday shading | Silent |
| PWA "Upcoming Holidays" + calendar | `hrms/api/__init__.py:1219-1247, 405-411` | `raise_exception=False`, `as_on=None` (today) -> `[]` -> "No upcoming holidays"; calendar shows no holiday days | Silent (guarded by `hrms/tests/test_holiday_readers_share_one_rule.py`) |
| Holiday reminders | `hrms/controllers/employee_reminders.py:69-71` | `raise_exception=False` -> nothing sent | Silent |
| Offboarding Active->Left | `hrms/hr/offboarding.py:256-267` | `raise_exception=False` -> every day a working day -> flips to Left sooner | Silent |
| Number card "Holidays this month" | `hrms/utils/custom_method_for_charts.py:12-29` | 0 | Silent |
| Employee boarding | `employee_boarding_controller.py:102-107,128` | resolver default raise -> throws | Loud |
| Daily Work Summary Group | `daily_work_summary_group.py:32` | uses the group's own `holiday_list` field | Separate config |
| Shift Assignment / Employee Checkin / checkin_sweeper | grep: no holiday reads | — | n/a |

**Off-day concept — there are three, not one:**
1. `Holiday.weekly_off` rows in the applicable Holiday List (the only thing that can make a day non-working: `_classify_day`, absent sweep).
2. Company weekend fields `hr_weekly_rest_day` / `hr_weekly_off_day` (`hrms/setup.py:166`, `ot_calculation.py:273-296`) — only *label* a listed weekly-off row as rest vs off.
3. Shift Type's own `holiday_list` (`shift_type.py:978-984`, `ot_calculation.py:311-315`) — wins over the employee's while it covers the date.
Shift Assignment / roster do not define off days.

**Attendance verdict:** a missing (or ended, or unassigned) calendar is **loud** for leave and attendance-request submission (throws), but **silent** for the automatic pipeline: the hourly absent sweep marks rest days and public holidays Absent, `_classify_day` prices holiday OT at 1.5x, F6 plans rebuilds on rest days, and the PWA shows an empty calendar. The only automatic signal is an Error Log line (OT pricing) and the nightly config-health Error Log — neither reaches HR in-app.

---

## 4. Duplicate definitions

| Source | Where | Status |
|---|---|---|
| Holiday List + Holiday List Assignment | ERPNext doctype + `hrms/utils/holiday_list.py` | **Authoritative** |
| `Employee.holiday_list` (hidden, mirrored) | ERPNext field; readers `hrms/api/team.py:167,234`, `payroll_entry.py:1145,1190`; derivation `create_holiday_list_assignments.py:36` | Vestige; two live readers still trust it |
| `Company.default_holiday_list` | set by `runner.py:1691-1735`; read only by derivation | Vestige |
| `Shift Type.holiday_list` | `shift_type.py:978-984`, `ot_calculation.py:311-315` | Legitimate override, second place to configure |
| Company weekend fields | `hrms/setup.py:166`, `ot_calculation.py:273` | Labels only |
| `Daily Work Summary Group.holiday_list` | upstream | Separate, unrelated |
| PWA constants | none — `frontend/src` has no holiday data, only `Holidays.vue:73-74` calling `hrms.api.get_holidays_for_employee` and `AttendanceCalendar.vue:92` mapping "Holiday" -> rest state | No duplicate |
| Roster app | `roster/src/components/MonthViewTable.vue:72-116` reads `roster.get_holidays` events | No duplicate |
| Sync-created copies | Holiday List rows are the source's copies (create-only, HR-owned after that); HLAs derived | Same source, not a second definition |
| Seed/fixtures | `docs/glass/audit/seed.py:35-42` (audit only) | n/a |

---

## 5. Recommendation

**One authoritative source:** Holiday List (calendar) + submitted Holiday List Assignment (scope). Say so in AGENTS/handoff; stop reading `Employee.holiday_list` (`team.py:234`, `payroll_entry.py:1145`) — route both through `get_holiday_list_for_employee(…, as_on=day)`.

**Make it visible in Verifica Desk (HR User, the role HR actually holds):**
1. Grant **HR User** `read` (and `select`) on **Holiday List** and `read/select` on **Holiday List Assignment**, via a patch that uses `add_permission` + `update_permission_property` (the shape of `hrms/setup.py:1152-1179` / `grant_hr_read_on_pwa_notification.py`) so it lands in Custom DocPerm on the clone too. Whether HR User may *create/submit* HLAs is a ruling for the owner (today only HR Manager can; the throw message at `holiday_list.py:123-132` sends HR to a form they cannot open).
2. Add "Holiday List Assignment" next to "Holiday List" in the **Shift & Attendance** sidebar too (it is only in Leaves), since attendance is where the symptom shows.
3. Keep the Employee-form hide (v16 design) but add a form-level indicator: a read-only "Applies today: <list or NONE>" via `frm.dashboard.add_indicator` in `employee.js` — so HR sees the truth where they look.

**Guard attendance when the list is missing (never ask staff):**
1. **Readiness/health finding:** extend `hrms/utils/readiness.py evaluate()` with a FAIL when any Active employee has no covering HLA (employee or company) **today**, and when the newest calendar ends within 60 days (covers the yearly rollover the `# ceiling` at `holiday_list.py:174-177` warns about). Today's F16 check only covers employees on shifts without a shift-level list and reaches HR only through Error Log.
2. **Nightly heal for the known shape:** rerun `_derive_holiday_assignments` logic as an idempotent job for hub-created employees/companies (it currently runs only after a sync, `runner.py:2053-2070`) — and fix its exists-check (`create_holiday_list_assignments.py:20` filters on `to_date`/`company`, columns HLA does not have; `frappe.db.exists` swallows the unknown-column error and returns None — probe confirmed — so every run re-attempts and logs a DuplicateAssignment Error Log per row).
3. **Fail closed in the sweep:** in `shift_type.get_dates_for_attendance` (`:847-848`) skip the employee (and log once) when `get_holiday_list(employee)` is None, instead of marking every day; `_classify_day` already logs — keep it.
4. **Validation at the master:** HLA already validates dates; add a Company-level check (Company form/HR Settings) that a submitted Company HLA exists for the current year, surfaced through the readiness report rather than a throw.
5. **Sync pre-flight:** make "Holiday List blocked at source" a blocking preflight finding before a full pull, not just a report (`preflight.py:31-80`).

---

## 6. Findings

### F1 — Critical: HR cannot reach the authoritative holiday configuration on Verifica
- **Problem:** HR User has `select`-only on Holiday List and **no** permission on Holiday List Assignment; the Employee-form field is hidden. HR has no supported way to see or set an employee's calendar unless they hold HR Manager.
- **Location:** `erpnext/.../holiday_list.json` perms; `hrms/hr/doctype/holiday_list_assignment/holiday_list_assignment.json` perms; `hrms/public/js/erpnext/employee.js:29`.
- **Root cause:** v16 moved the model to HLA and tightened perms; the fork's role model gives HR "HR User" (memory: HR role profile) and never re-granted the new doctypes.
- **User impact:** "Holiday List not available"; throw messages (`holiday_list.py:123-132`) link HR to a form they cannot open.
- **Change:** patch granting HR User read/select on both doctypes (create/submit on HLA per owner ruling); sidebar link in Shift & Attendance.
- **Now.** Evidence: test.local probe `HR User read=0 select=1`; `is_item_allowed` (`desk_views.py:68-86`).

### F2 — High: missing calendar is silent in the automatic attendance pipeline
- **Problem:** absent sweep marks holidays/rest days Absent; OT prices PH at 1.5x; F6 plans rebuilds on rest days; PWA shows empty calendar. Only Error Log lines say why.
- **Location:** `shift_type.py:847-848,986-1003`; `ot_calculation.py:299-350`; `attendance_recovery.py:3724-3766`; `api/__init__.py:1219-1223`.
- **Root cause:** every automatic reader passes `raise_exception=False` and treats `None` as "no holidays".
- **Impact:** wrong Absents and under-priced OT for anyone whose HLA is missing/ended — exactly the population H4/H5 describe.
- **Change:** readiness FAIL + nightly heal (rec. 5.1–5.2); fail-closed skip in the sweep (5.3).
- **Now** (readiness + sweep skip), heal separately. Evidence: prior audit A14 (`docs/glass/audit/2026-09-10-checkin-pipeline-connections.md:177`).

### F3 — High: two readers still trust the dead `Employee.holiday_list`
- **Problem:** `hrms/api/team.py:167,234-236` (team status "is_holiday") and `payroll_entry.py:1145,1190` read the hidden field the resolver ignores.
- **Root cause:** partial migration to HLA upstream; fork added team.py against the old field.
- **Impact:** team view says "Absent/Not In Yet" on a holiday for hub-created employees or once the 2027 calendar is assigned via HLA only.
- **Change:** route through the resolver with `as_on=day`; add an AST guard test like `test_holiday_readers_share_one_rule.py` covering `team.py`.
- **Now** for team.py; payroll separately (payroll is out of Verifica).

### F4 — Medium: HLA derivation is not idempotent by its own check
- **Problem:** `create_holiday_list_assignments.py:20` calls `frappe.db.exists("Holiday List Assignment", entity)` with `to_date` and `company` keys that are not HLA columns; `frappe.db.exists` -> `get_value(ignore=True)` swallows the unknown-column error (`frappe/database/database.py:682-688`) and returns None (probe confirmed), so each post-sync run re-attempts every row and `validate_existing_assignment` (`holiday_list_assignment.py:25-40`) throws DuplicateAssignment into Error Log per employee/company.
- **Impact:** Error Log noise after every sync that buries the real "no calendar" entries; first-run derivation still works.
- **Change:** filter on `assigned_to`, `from_date`, `docstatus=1` (what the validator checks). Separately; upstream-shaped bug.

### F5 — Medium: the yearly rollover has no owner and no alarm
- **Problem:** `_ended_calendar` (`holiday_list.py:174-189`, `# ceiling`) serves last year's list when nothing covers the date; the new year's Holiday List + HLA must be created by hand on the hub (create-only masters, source retired).
- **Impact:** from 1 Jan every day is a working day until someone notices.
- **Change:** readiness WARN 60 days before the newest company calendar ends; FAIL once past. Now (cheap, pure `evaluate()` addition).

### F6 — Medium: resolver date defaults to today for multi-day readers
- **Problem:** `hrms/hr/utils.py:956 get_holidays_for_employee` and `api/__init__.py:1221` call the resolver without `as_on`, so a December leave into January or the PWA "upcoming holidays" list uses today's calendar only.
- **Change:** pass `as_on=start_date` / use `get_holiday_dates_between_range`. Separately.

### F7 — Low: Verifica may hold Custom DocPerm drift on Holiday List from the clone
- **Problem:** ESS User Type setup wrote Custom DocPerm rows for Holiday List (`setup.py:925`); nothing re-asserts them on migrate (unlike `permlevel_guard`).
- **Check/Change:** Role Permission Manager on Verifica; include Holiday List and HLA in the permission patch of F1 so it is re-asserted every migrate.

### F8 — Low: Holiday List absent from Shift & Attendance sidebar and from readiness
- `hrms/workspace_sidebar/shift_&_attendance.json` has no Holiday List/HLA link; `hrms/utils/readiness.py` has no holiday finding. Add both (rec. 5).
