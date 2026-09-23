# Audit — the secondary pages (Score, More, You, Help, SOPs, news, Team)

23 Sep 2026 · branch `nz-glass` at `e6eb026cb` · read-only audit.
Judged against `2026-09-23-basis.md`. Every finding cites a rule ID from it.

**Live app:** `http://localhost:8080/hrms`, served from this worktree (site `fresh.local`), bundle built 23 Sep 01:56.
**Persona:** `nurul.aisyah@nastyworldwide.com`: an employee with no HR role, no team, no approvals and no appraisal.
**Screenshots:** `/tmp/nadi-audit/pages/*.png` (15 routes × 390×844, 360×640, 320 + 200% text, 1280×800), plus sheets and offline. Raw numbers are in `/tmp/nadi-audit/pages/measure.json`.

**Limits (stated, not guessed):**
- HR, CEO and manager personas were **not checked live**. Only one login was available. Their screens are judged from code.
- The IT Helpdesk app is not installed locally, so `?tab=it` falls back to HR. The IT side is judged from code.
- The local site has **no SOPs, no holidays, no appraisal and no HR Announcement table** (see PAGE-2). So SOP detail, the holiday list, a filled Score page and announcement detail were **not checked live**.
- No write was sent (no ticket, reply, password change or SOP save). This audit is read-only.
- Dark theme was not checked.

---

## 1. Coverage

| Screen / sheet / action | Status | Note |
|---|---|---|
| Score: tierless employee, empty path | **live** + code | 4 viewports |
| Score: my appraisal filled (hero, trend, KRAs, feedback) | code | no appraisal on the site |
| Score: year and cycle selects | code | rendered only when `years` is set |
| Score: team tab (manager) / tree (HR, CEO) / person detail | code | no persona |
| KPI fence, server side | **live** + code | tierless: `can_view_team_kpi` → null; `get_team_kpi` 403; `get_department_kpi` 403; `get_employee_kpi(other)` 403; own record 200 |
| KPI fence, frontend | code | no role, designation or "if HR" in `views/kpi/` or `data/kpi.js` |
| More (phone) | **live** + code | 4 viewports |
| SideNav lower section (desktop) | **live** 1280 + code | |
| More: Apps group (Approva, Project Board) | code | persona has neither role |
| More: Team and Remote approvals rows (managers) | code | `hasTeam` false for the persona |
| You/Profile page | **live** + code | 4 viewports |
| Employee details sheet | **live** | opened. Focus moves in. Escape closes it. |
| Company information sheet | code | |
| Contact information sheet | **live** | |
| Back while a sheet is open | not checked | the test started from a fresh tab, so the result was inconclusive |
| About this app row | **live** | a tap does nothing (PAGE-21) |
| Settings (theme, push, change-password link) | **live** + code | theme was not switched |
| Change password | **live** (render only) | nothing submitted |
| Log out | code | not tapped, to keep the session |
| Help hub, HR side, employee list | **live** + code | |
| Help hub, IT side (list, chips, new ticket, detail, reply) | code | app not installed |
| New HR issue form | **live** (render only) | nothing submitted |
| HR issue detail (employee) | **live** | PAGE-8 |
| HR Issue Board + its detail sheet (HR) | code | no HR persona |
| SOP list | **live** (empty state) + code | |
| SOP detail, SOP form sheet (HR) | code | no SOP on the site |
| Announcements list | **live** (error state) + code | PAGE-2 |
| Announcement detail + acknowledge | code | table missing on the site |
| Notifications page | **live** + code | 31 unread |
| Mark all as read, load more | code | not tapped: that would change data |
| Holidays (component inside Leaves) | **live** (empty) + code | the site returns `[]` |
| HR contacts page | **live** (empty) + code | |
| Team page | **live** (non-manager, by URL) + code | |
| Team roster | code | |
| Remote approvals (as a More/Profile destination) | **live** (empty) | content belongs to the flows auditor |
| Offline: navigating between pages | **live** | PAGE-1 |
| Loading states | code | every list has a skeleton or loading state; checked in code |
| Long text | **live** | long Malaysian name at 390 and 320 |

---

## 2. Findings

### Critical (3)

| ID | Location | Problem | Why | Expected | Fix | Seen |
|---|---|---|---|---|---|---|
| PAGE-1 | `frontend/src/main.js:147-153` (router guard) | **Offline, any page change throws you onto the Login page.** It reads "No login methods are available. Please contact your administrator." with three "Could not load / Failed to fetch" toasts. Measured: `/more` → `/sop`, `/profile`, `/announcements` offline each landed on `/hrms/login`. The guard treats ANY failure of `userResource.reload()` as "logged out". | PWA-OFFLINE, H9, H1 | Offline says so and keeps you where you are. Only a real `AuthenticationError` goes to Login. | In the `catch`, set `isLoggedIn = false` only when `error.exc_type === "AuthenticationError"`. Otherwise keep the session and carry on with the cached user. One line. | live |
| PAGE-2 | `views/announcements/List.vue:18,63-67` | **The page says two opposite things at once:** "Could not load announcements. Try again" AND "Nothing on the board. There is nothing live at the moment." The empty state checks `!rows.length` and not the error. This is the same class as `4fa619563` ("a broken read looked exactly like having nothing"), fixed on Home and not here. *Environment note:* the 403 itself is because site `fresh.local` has no `HR Announcement` table (migrate not run); `spoke.localhost` has it and returns `[]`. | H1, H9, OWN rule D6 (four states) | The error OR the empty state, never both. | Add `&& !allAnnouncements.error` to the `GEmptyState` `v-if`. Then run a sweep for the class: every `GEmptyState` rendered beside a `ResourceError`. | live |
| PAGE-3 | `views/issues/HRIssueBoard.vue:58-63`; `views/team/TeamDashboard.vue:101-104` | **HR's issue cards and the Team member rows are `<div @click>`.** No role, no tabindex, no key handler. A keyboard user cannot open an issue, which is HR's main work tool on desktop. | A-2.1.1, A-4.1.2 | Every row is a button or link. | Render each row with the shared `GListRow` (already a button, 44px, focus ring) or `<button type="button">`. | code |

### Important (17)

| ID | Location | Problem | Why | Expected | Fix | Seen |
|---|---|---|---|---|---|---|
| PAGE-4 | `data/navItems.js:36-58` (`MORE_ITEMS`) | **More lists Leaves and Expenses.** Both are requests. The Leaves dashboard also repeats the balances Requests shows. | OWN (requests/leave/expenses → Requests; H2), S-DUP | They are not in More. | Remove both from `NAV_ITEMS`, and remove their routes from the More `routes` list. Their content folds into Requests (flows auditor). | both |
| PAGE-5 | `views/More.vue:75-84`; `views/Profile.vue:259-273` | **Remote approvals sits in More (managers) and in Profile (approvers)**: two doors, and both are places the owner ruled out. SideNav does not show it, so desktop and phone also disagree. | OWN H3 ("approvals only where they can be done, never in More"), S-DUP, A-3.2.3 | Reached only from the Approvals page (and Home's "Waiting on you"). | Delete both blocks. The route stays for notification deep links until the Approvals page takes it in. | both |
| PAGE-6 | `views/AppSettings.vue:84-98`; `views/Profile.vue:276-303` | **Settings is a whole page for two controls, and it repeats Change password,** which Profile already lists one row below. | S-DUP, OWN "one tap away" / "compact", A-3.2.4 | Theme and notifications sit on You. Change password has one door. | Move the theme segmented control and the push row onto You. Delete `AppSettings.vue` and its route (or redirect `/settings` to `/profile`). | both |
| PAGE-7 | `views/Requests.vue:74-83` | **Help has a second door:** a "HR Issues" / "Issue Board" tile under "Start a request" on Requests. Asking HR is not a request. | S-DUP, OWN "nothing brought back that lives elsewhere" | Help is reached from More (and Home's "HR replied" row). | Delete the tile. The flows auditor owns the rest of that tile grid. | code |
| PAGE-8 | `views/issues/IssueForm.vue` via `FormView` | **An employee opening their own HR issue gets the raw doctype form:** title "Employee Issue", an Employee link picker, "Company: _Test Company", a Status dropdown, and a lime **Save** button on a record they cannot change. **There is no way to reply to HR**, so Ask HR is one-way. The new-issue form is titled "New Employee Issue". | OWN L4 (doctype names never shown), H2, OWN "actionable only", H1 | Subject, what you wrote, status in plain words, and HR's answer. No Save. | Read-only view: set `showFormButton=false` when `props.id`. Title "Your HR issue" / "Ask HR". Hide employee, employee_name, company, status fields (the list already shows the status). A reply thread needs a ruling: Employee Issue has no reply channel today. | live |
| PAGE-9 | `views/HRContacts.vue:44-51` | **The empty state tells an employee to "Ask your administrator to assign the HR Manager or HR User role to your HR team."** That is system words, a diagnosis job, and a role name, all put on staff. | NG-EMPTY, W-PLAIN, OWN (never ask employees to diagnose) | "No HR contacts are listed yet." plus a way forward: *Ask HR* (opens Help). | Replace the body text and add the Help link. | live |
| PAGE-10 | `theme/glass-components.css:529` (`.g-eyebrow` `text-transform: uppercase`) and `g-eyebrow-type` | **Block capitals on every page in this area.** More: "MORE" (which also repeats the page title). You: "YOU · WORK · APP · ACCOUNT". Settings: "APPEARANCE", and "LIGHT DARK SYSTEM" in capitals. Remote approvals: "WAITING ON YOU". Team: "SUN MON…", "PRESENT". Tab bar and SideNav labels. Form labels ("WHAT ARE YOU REPORTING?"). Counted: 16 uppercase nodes on Leaves, 12 on Team, 9 on issue detail. | NG-CAPS, W-CASE, W-DYS, S-EYEBROW | Sentence case, bold for weight. | Remove the `text-transform` from the two classes (one root). Delete the More eyebrow (it repeats the title). Keep group labels only where a page has more than one group. | both |
| PAGE-11 | strings in `Profile.vue`, `AppSettings.vue`, `ChangePassword.vue`, `Holidays.vue`, `Notifications.vue`, `RemoteApprovals.vue`, `kpi/*`, `sop/*`, `issues/*`, `helpdesk/*`, `navItems.js` | **Title Case, and one thing with two names:** "Change password" (You) vs "Change Password" (Settings, page title); "Log Out"; "Remote Approvals"; "Upcoming Holidays"; "View All"; "New HR Issue"; "New IT Ticket"; "Enable Push Notifications"; "31 Unread"; "Update Password"; "All Appraisal Cycles"; "My KPI". 33 distinct strings in this area. | W-CASE, M3-CASE, W-ONE, A-3.2.4, OWN L1 | Sentence case, one name per thing. | One `chore:` string sweep across these files. | both |
| PAGE-12 | `views/team/TeamDashboard.vue` (GCalendar), `views/RemoteApprovals.vue:23`, `views/AppSettings.vue:31-46` | **At 320 px with text at 200%:** Team scrolls sideways (content 486 px wide in a 320 px view). The weekday row runs off-screen. Remote approvals is 345 px wide (the segmented control overflows). The theme control clips to "SYSTE". | A-1.4.10, A-1.4.4 | No sideways scroll. Labels wrap. | Calendar: weekday labels to one letter below a width breakpoint, as GCalendar on the Calendar tab should. Segmented: allow wrap (`white-space: normal`), which also comes free with PAGE-10. | live |
| PAGE-13 | `views/kpi/KpiDetail.vue:43-68, 187-212` | **Score shows one fact twice and counts things that lead nowhere:** the hero "84 / 100" and a ring showing the same 84. "Feedback received this cycle: n" is a number with no action. The line "You can only see your own scores" explains the page. (Mockup 4 makes the same error with "4.2 / 5" plus "84%".) | S-DUP, S-STAT, S-EXPLAIN, H8 | One number (the score), the grade, and the change since last time. | Drop the ring from the hero (keep `GProgressRing` for the team average only if that is still wanted). Delete the feedback row and the lock line from the self view. | code |
| PAGE-14 | `views/kpi/Dashboard.vue:17-47` | **Two dropdowns (Year, Appraisal cycle) sit above the score** for a choice made once a year. | NG-PD, L-HICK, OWN "compact" | "Other periods ›" opens a sheet holding both selects. | Move the two selects into a `GActionSheet`. The same resource calls stay (KR1: no new endpoint). | code |
| PAGE-15 | `views/kpi/*` | **There is no way to say "this figure is wrong"** (mockup 4 and the prototype both have it). A person who disagrees has to find Help by themselves. | H9, H3 | A row "A figure here looks wrong ›" that opens a new HR issue, type Other HR issue, with the cycle named. | A link to `EmployeeIssueFormView`. The form must read `?issue_type=&details=` (the same pre-fill class as calendar C12). No new endpoint. | code |
| PAGE-16 | `views/issues/HRIssueBoard.vue:16-25, 47-53` | **The HR board shows each status count twice:** a stat panel (Open / In progress / Completed / High) and the status segmented control right under it with the same numbers in its labels. | S-DUP, S-STAT | Counts once, on the segments. High urgency as a filter chip. | Delete the `GStatPanel` block. Keep the high-urgency count as a chip. | code |
| PAGE-17 | `views/Notifications.vue:62-95` + server notification text | **Each line reads "Your Leave Application HR-LAP-2026-00043 has been Rejected by Administrator".** It shows the doctype name and a record ID, and "Rejected" where the app says "Not approved". Every avatar is a "?" (from `Administrator`), so the icon carries nothing. | OWN L4, W-PLAIN, W-ONE, S-ICON, A-1.1.1 | "Your leave for 3–4 Sep was not approved." with no "?" well. | Hide the avatar when there is no employee behind `from_user`. Rewrite the subject in the hrms notification templates (a server string change). The glossary word for Rejected is "Not approved". | live |
| PAGE-18 | `data/appLinks.js:34,41` | **The Apps group in More is gated on role names written in the frontend** ("Accounts Manager", "HR User", "Projects User"…). | OWN "no role literals in the frontend", OWN S3 (KR2 spirit) | The server says which apps this user is offered. | Add `apps: [...]` to the existing `get_current_user_info` payload (no new endpoint). Delete the `roles` arrays. | code |
| PAGE-19 | `views/sop/SopList.vue:14-44, 95-103` | **An edit button sits inside the SOP link** (`<button>` nested in `<a>`), so one row is two controls stacked. Pinned "Essentials" are drawn as a 2-column grid of lime tiles, so the colour kept for the ONE primary action is on up to N cards. | A-4.1.2, S-TILE, OWN D8 (one primary per screen), S-DECO | Rows. Edit is in the detail header (it already is) and not on the row. | Delete the row-level and tile-level edit buttons (HR edits from `SopDetail`). Render pinned SOPs as the first `GListRow` group, not accent tiles. | code |
| PAGE-20 | `components/Holidays.vue`, used only in `views/leave/Dashboard.vue:61` | **Public holidays are reachable only inside the Leaves dashboard** ("Leaves & Holidays"). Cutting Leaves from More (PAGE-4) would leave them with no door. The list is the year ahead, so it is a planning fact, not a day fact. | H6, OWN "one tap away", H10 | One More row, "Public holidays ›", opens the list in a sheet. | Reuse the component's existing modal list inside a `GActionSheet` opened from More. Delete the "Upcoming holidays" block from Leaves when Leaves folds into Requests. | both |

### Polish (11)

| ID | Location | Problem | Why | Expected | Fix | Seen |
|---|---|---|---|---|---|---|
| PAGE-21 | `views/Profile.vue:303-312` | "About this app" is a button with a chevron, and a tap does nothing (`go: () => {}`). | S-ARROW, H4, A-4.1.2 | A plain text line: version · build. | `tappable: false`, no chevron. It then carries the version (recollection §3). | live |
| PAGE-22 | `views/Profile.vue:30-33`; `SideNav.vue:142` | The name is cut: "Nurul Aisyah binti Abdul Ra…" at 390 and on desktop. | HIG-TYPE, A-1.4.4 | The name wraps to two lines. | Drop `truncate`, add `break-words`. | live |
| PAGE-23 | `components/ContactInfoSheet.vue:30-37` + Company information sheet (`reports_to`) | The manager appears in TWO sheets on the same page. Each sheet header repeats itself: "CONTACT" over "Contact Information". | S-DUP, S-EYEBROW | The manager is once on the You page itself (see §4). One title per sheet. | Remove "Reporting manager" from the Contact sheet and `reports_to` from Company. Show "Your manager is …" on You. Delete the sheet eyebrows. | live |
| PAGE-24 | `views/AppSettings.vue:60-71, 142-146` | When the site cannot push, the row stays as a disabled switch with "Push notifications have been disabled on your site". | OWN "actionable only", W-PLAIN | No row when nothing can be done. | `v-if` the row on push availability. | live |
| PAGE-25 | `views/team/TeamDashboard.vue`; `router/index.js:84-93` | A non-manager reaching `/team` by URL gets a full calendar and four "0" tiles, then "You do not have a team here" at the bottom. The route has no guard. | NG-EMPTY, S-STAT | The empty message alone. | Render the empty state instead of (not after) the calendar when `members` is empty and `teamManagers` is empty. | live |
| PAGE-26 | `views/helpdesk/HelpdeskList.vue:66-80` | A permanent footer sentence ("IT & admin tickets are handled by…Tap a ticket to read replies.") and a three-clause empty body. | S-EXPLAIN, H8 | Once, in the empty state only. | Delete the footer. Shorten the body. | code |
| PAGE-27 | `views/kpi/Dashboard.vue:427-436`; `KpiDetail.vue:137` | The tab says **Score**, the page says "My KPI / Team KPI / All KPI", "Whose KPI", "My KRAs". | W-ONE, H2 | "Mine / My team / Everyone"; "What makes it up". | String change only (the tier keys stay server-owned). | code |
| PAGE-28 | `components/glass/GScorePanel.vue`, `GKraPanel.vue`, `GGoalsPanel.vue` | Used only by `DesignSpecimen.vue`. `KpiDetail` hand-rolls its own hero and KRA bars. So there are two implementations of one pattern. | DRY-ONE | One. | Either `KpiDetail` renders `GKraPanel`, or delete the three. Deletion is preferred until a goals payload exists (KR1). | code |
| PAGE-29 | `Profile.vue:95`, `HRIssueBoard.vue:93`, `SopFormSheet.vue:2` | Raw `<ion-modal>` (recollection E6/E7: stuck sheets). | ION-MODAL, DRY-ONE, M3-BACK | The one fixed sheet component. | Part of the foundation step (`00-sheets-and-transitions.md`). Listed so these three are not missed. | code |
| PAGE-30 | `views/issues/IssueList.vue:79-83` | Help rows lead with the record ID: "HR-ISS-26-08-00002 · 21 Aug, 07:51 · My July payslip…". The first issue's label is just "Issue". | W-PLAIN, H2 | "What you wrote" first, then "Opened 21 Aug · Open". | Put the `details` first line as the label and date + status as the sublabel. Drop the ID. | live |
| PAGE-31 | `views/Profile.vue:384-386` | The log-out error text is not wrapped in `__()`, and it ends in "!". | OWN L3, W-PLAIN | "Could not log out. Try again." | Wrap it and rewrite it. | code |

**Counts:** 3 Critical · 17 Important · 11 Polish = **31**.

### Where mockup 4 / the prototype break a rule (do not copy)

| Where | What | Rule |
|---|---|---|
| M4 s-score | `4.2 / 5` **and** `84%` for one score | S-DUP |
| M4 s-score | "When grades are published…" paragraph on the page | S-EXPLAIN (put it behind ⓘ or cut it) |
| M4 s-more | "You and your settings" row: the header avatar is already that door | S-DUP |
| M4 s-more | Payslips | OWN (no payslips yet) |
| M4 s-more / P | Things you hold, Training: no data exists | S-FAKE |
| M4 s-more | "1 new" on Announcements: Home already owns unread | S-DUP |
| M4 s-notifs | "Anything you must act on lives on Home…" line | S-EXPLAIN |
| M4 s-help | "IT tickets are seen by the IS team only." as a permanent line | S-EXPLAIN (keep it once, in the empty state) |
| P s-more | "Viewing as Approver · Switch": a role switch in the frontend | OWN (no role literals / frontend never decides) |
| P s-kpi | "Figures come from the group dashboards. If a number looks wrong…" paragraph | S-EXPLAIN (the action row is enough) |
| P s-profile | Scorecard row on Profile: Score is a tab | S-DUP |

---

## 3. Keep list (right today, do not touch)

- **The KPI fence.** One `_scope()` decides every tier (HR by role via `is_hr_operator`; CEO by designation; manager by chain seeded from identity). `get_my_kpi_dashboard` takes no employee argument. `get_employee_kpi` runs `_require_kpi_read` before any read. `get_department_kpi` refuses managers. Verified live for the tierless persona (403 on team, tree and another person). Guard tests are in `hrms/api/test_kpi.py`. **Frontend holds no role literal in `views/kpi/` or `data/kpi.js`.** The tab label comes from the server tier.
- The Score empty path is one populated banner that says who scores you (KR3: only the reader's own cycle).
- The team detail is gated on WHO the payload is about (`openedDetail`), not on truthiness.
- Focus handling on the KPI drill-down and breadcrumb (heading focus, `aria-current`, live summary region).
- The Help hub: one page, two segments, the count in the label (read aloud), the URL states the segment, the IT segment is removed only on an answered "no".
- `IssuesTab` picks board or list from the server's `is_hr`, not a role list.
- `safeHtml` on every rich-text render (announcement, SOP, ticket, notification).
- Announcements: two groups ("Needs your confirmation" / the rest), a real acknowledgement sentence, opening = read, a personal cache key.
- Personal cache keys on every personal resource (SEC-STORE).
- The Notifications three states each have their own condition. Mark all as read shows only when there is unread.
- The Profile employee sheet: focus moves in, Escape closes it (live).
- Error states have "Try again" everywhere (U9).
- SideNav lower section = More flattened (§20.2). It follows `MORE_ITEMS` automatically, so fixing `navItems.js` fixes both shells.

---

## 4. Page contents: the definitive lists

Tags: **keep** · **change** · **move → X** · **cut** · **add**. "Lives on X" means it already exists there, so it is not brought back.

### Score (tab 4)
**Job:** how am I doing this period, and is anything wrong?

| Item | Verdict | Rule |
|---|---|---|
| Head: period + state ("Jul–Sep · open") | change: one line, replaces the eyebrow | NG-PD |
| One score + grade + "+2.1 since last time" | keep (drop the ring, PAGE-13) | S-DUP |
| Year / cycle selects | move → "Other periods ›" sheet | NG-PD, L-HICK |
| Score trend chart | keep, only when there are ≥ 2 cycles (already so) | H1 |
| KRA rows (weight, bar, target / actual) = "What makes it up" | keep; rename the heading | W-ONE |
| "Your goals" with Met / Below / Open | not now: needs goal data the existing payload does not carry (KR1). Revisit if `kras` target/actual is enough to derive the word | OWN S2 |
| Feedback count row | cut | S-STAT |
| "You can only see your own scores" line | cut | S-EXPLAIN |
| "A figure here looks wrong ›" | add → new HR issue, pre-filled | H9 |
| Mine / My team / Everyone segments | keep, server tier only; rename (PAGE-27) | OWN S3 |
| Team: filters, breadcrumb tree, people table, read-only note | keep as is. HR and CEO see the tree, a manager sees the chain, and the server fences all of it. The read-only note stays on the team view only | OWN S1–S6 |

Fits one 390×844 screen for the self view with 3–4 KRAs.

### More (tab 5; the same list is the SideNav lower section)
**Job:** everything used now and then that no tab owns.

| Row today | Verdict | Rule |
|---|---|---|
| "More" eyebrow | cut (repeats the title) | S-EYEBROW, S-DUP |
| Leaves | cut: lives on Requests | OWN H2, S-DUP |
| Expenses | cut: lives on Requests | OWN H2, S-DUP |
| Helpdesk | keep, rename **Help** | W-PLAIN |
| SOPs | keep | — |
| Announcements | keep, no count (Home owns "new") | S-DUP |
| Team (managers, server `hasTeam`) | keep | — |
| Remote approvals (managers) | cut: moves into the Approvals page | OWN H3 |
| Apps: Approva, Project Board | keep (they leave the PWA; no other door). Gate them from the server (PAGE-18) | OWN no role literals |
| Row icons | keep only while rows ≥ 5; otherwise cut | S-ICON |
| **Public holidays** | add → sheet (PAGE-20) | H6 |
| Payslips, Things you hold, Training, "You and settings", Approvals | do not add | OWN, S-FAKE, S-DUP |

**Final More:** Help · Announcements · SOPs · Public holidays · Team (managers) · Apps group (if offered). At most 5 + 2 rows. No scroll at 360×640.

### You (reached ONLY from the header avatar / SideNav footer)
**Job:** who I am in the system, and how the app behaves for me.

| Item today | Verdict | Rule |
|---|---|---|
| Page title "Profile" | change → **You** (the tab of the avatar; M4) | W-ONE |
| Avatar + name + designation | keep; name wraps (PAGE-22); add department · branch on the same line | HIG-TYPE |
| "Your manager is …" | add on the page (moved out of two sheets, PAGE-23) | H6, S-DUP |
| Your shift pattern | add **only on a ruling**. `Employee.default_shift` exists, but it is new content | OWN compact |
| Employee details / Company information / Contact information (3 rows, 3 sheets) | change → ONE row "Your details ›", one sheet, three short groups | L-HICK, H8 |
| HR contacts | move → Help ("Who to ask") | one job per page |
| Remote approvals | cut: lives on Approvals | OWN H3 |
| Settings row + Settings page | cut the page; its two controls come here: | S-DUP |
| · Theme: System / Light / Dark | add inline (segmented) | OWN P1 |
| · Notifications on/off | add inline, only when the site can push | actionable only |
| Change password | keep, the only door (removed from Settings) | S-DUP |
| About this app | change → plain line "Version 2.0.0-alpha.N · 23 Sep 14:02", not a button | S-ARROW |
| Log out | keep, rename **Log out**, neutral style | W-CASE |
| Group eyebrows You/Work/App/Account | cut; two plain groups at most (details / app) | S-EYEBROW |

### Help
**Job:** ask HR or report an IT problem, and see the answer.

| Item | Verdict | Rule |
|---|---|---|
| Title "Helpdesk" | change → **Help** | W-PLAIN |
| Segments "Ask HR (n)" / "IT support (n)" | keep; rename | W-PLAIN |
| Primary per side: "Ask HR something" / "Report a problem" | keep (rename from "New HR Issue" / "New IT Ticket") | W-CASE |
| HR row: ID · date · text | change → what you wrote, then "Opened 21 Aug · Open" (PAGE-30) | W-PLAIN |
| "Reported by you" eyebrow | cut (the page only holds yours) | S-EYEBROW |
| IT chips All / Open / Awaiting you / Resolved | keep; "Awaiting you" becomes "Your turn" | H2 |
| IT footer sentence | cut (PAGE-26) | S-EXPLAIN |
| HR issue detail | change → read-only summary, no Save (PAGE-8); reply thread = ruling | OWN L4 |
| **Who to ask** (HR contacts) | add as the last row → sheet (moved from You) | one job |
| HR board (HR role, server `is_hr`) | keep; drop the stat panel (PAGE-16); rows keyboard-reachable (PAGE-3) | S-DUP, A-2.1.1 |
| Door on Requests | cut (PAGE-7) | S-DUP |

### SOPs
**Job:** find the procedure I half remember.

| Item | Verdict | Rule |
|---|---|---|
| Search first | keep | L-HICK |
| Essentials as lime tiles | change → first list group "Essentials" | S-TILE, D8 |
| Department sections | keep; "My department: X" in sentence case | W-CASE |
| "HR" badge | cut (says who you are, not what to do) | S-STAT |
| Edit pens on rows and tiles | cut; edit in the detail header only (PAGE-19) | A-4.1.2 |
| New SOP floating button (HR, server `is_hr`) | keep | — |
| "Needs reading" chip, "2 to read" on More | not now: needs read tracking (new data) | OWN no new data without ruling |
| Detail: badge, updated date, body, attachment, edit (HR) | keep | — |

### Announcements
**Job:** what HR wants me to know.

| Item | Verdict | Rule |
|---|---|---|
| "Needs your confirmation" group first | keep | NG-PD |
| Rows: category icon (tells the type apart) + title + "yesterday" | keep; add a one-line preview + author when the list payload carries them (backend field) | S-ICON ok |
| "Everything else" eyebrow | keep only when both groups show (already so) | — |
| Error + empty at once | fix (PAGE-2) | H1 |
| Detail: category, title, date, body, "I've read and understood this" | keep | OWN AN2 |
| Doors | More row + Home block (Home only unread/to-confirm, max 2) | OWN AN4 |

### Notifications
**Job:** the record of what happened. Its only door is the bell.

| Item | Verdict | Rule |
|---|---|---|
| "31 Unread" headline | change → "31 unread", small, next to Mark all as read | W-CASE, S-STAT |
| Mark all as read | keep | — |
| Rows: dot + text + time | keep; plain result wording (PAGE-17) | OWN L4, W-ONE |
| "?" avatar | cut when there is no person | S-ICON |
| Group by day | add (prototype) | H6 |
| Load more | keep | — |

### Holidays
**Job:** which days off are coming, so I can plan.
**Decision:** not a page. **One More row → sheet** (PAGE-20). The Calendar day sheet names a holiday on its day. That is the day fact, and the list is the plan, so there is no duplicate.

| Item | Verdict | Rule |
|---|---|---|
| Upcoming list (name + date) | keep, inside the sheet | — |
| "Upcoming Holidays" / "View All" / second "Holiday List" modal | cut: one list, the sheet itself | S-DUP, W-CASE |
| Block inside the Leaves dashboard | cut with Leaves | OWN H2 |
| "Long weekend" tag (P) | add only if computed from dates already sent (no new data) | H6 |

### Team (managers; server `hasTeam` / HR selector)
**Job:** who is in, who is off, where the gaps are.

| Item | Verdict | Rule |
|---|---|---|
| HR "Team of" selector | keep (server list) | — |
| Month grid for picking a day | keep; must fit 320 / 200% (PAGE-12) | A-1.4.10 |
| 4-tile day strip | change → one line "4 of 6 in · 1 on leave · 1 not in yet". **Conflict:** the approved Calendar plan (`01-calendar.md` §manager lines) puts the same line on Calendar. Recommend Calendar keeps the line **as the door only** and Team owns the numbers. Needs an owner nod | S-DUP, PAGE-n |
| Member rows by department, tap to expand | keep; make them buttons (PAGE-3) | A-2.1.1 |
| "Open team roster" | keep → Team roster (assign shift) | — |
| Non-manager by URL | empty state only (PAGE-25) | NG-EMPTY |

### Sub-page decisions

| Sub-page | Decision | Why |
|---|---|---|
| Holidays | **fold** → More row → sheet | no own job big enough for a page; one tap |
| HR contacts | **fold** → Help ("Who to ask" sheet) | one job: getting help |
| Apps | **keep** as a More group | leaves the PWA; no other door |
| Team (+ roster) | **keep** as its own page | a distinct job for managers |
| SOPs | **keep** as its own page (+ detail) | a lookup library |
| Announcements | **keep** as its own page (+ detail) | the full board behind Home's 2 |
| Help | **keep** as its own page | two queues, replies |
| Settings | **cut** → controls onto You | two controls do not justify a page |
| Remote approvals | **move** → Approvals page | OWN H3 |
| Leaves / Expenses dashboards | **cut** → Requests | OWN H2 |

---

## Flags

- `fresh.local` (the live test site) lacks the `HR Announcement` table. Run migrate before the a11y/visual gates, or they will photograph an error page.
- A Team vs Calendar manager-line overlap with the approved `01-calendar.md` needs a ruling (see Team).
- An HR issue reply thread needs a ruling (Employee Issue has no employee-facing reply today).
- Goals (M4 "Your goals") cannot be built without goal data; KR1 forbids a new endpoint.
