# Nadi PWA — audit result and next-update plan (23 Sep 2026)

**Read this file first.** It merges the three audits and the recollection into one ranked list.

| File | What it holds |
|---|---|
| `2026-09-23-basis.md` | Every standard, with its source and a rule ID. Each finding below cites one. |
| `2026-09-23-audit-app.md` | Findings APP-1…32: shell, sheets, platform, design, words |
| `2026-09-23-audit-flows.md` | Findings FLOW-1…29: Home, Calendar, Requests, forms, approving |
| `2026-09-23-audit-pages.md` | Findings PAGE-1…31: Score, More, You, Help, SOPs, news, Team |
| `2026-09-23-recollection.md` | What exists today; the version decision |

**How it was checked:**
- **Live:** on the seeded test site at 390×844, 360×640, 320 wide with 200% text, and 1280×800, in light and dark.
- **Two logins:** an employee, and an approver.
- **Critical findings:** every one was re-read in the code by the lead reviewer before it was listed here.

**Not checked live** (it would write real records, or it needs a real device): a real check-in, approve, withdraw, iOS edge swipe, Android back, push permission, the install prompt.

**Test-site note:** `fresh.local` lacks the `HR Announcement` table (not migrated). The 403s behind APP-6 come from that site, not from the app. The app defect is that the **raw server text** reaches employees.

**Totals:** 92 findings in the three audits (15 Critical, 50 Important, 27 Polish). Several report the same root cause from different angles, so they merge into **13 P0 rows**, **15 foundation items + 10 page plans (P1)**, and the P2 polish list.

---

## Priorities

| P | Meaning | Ships as |
|---|---|---|
| **P0** | Broken now, blocks a task, leaks data, or fails WCAG AA on a main task | **2.0.0-alpha.2**, all together |
| **P1** | Broken rule people meet daily; owner rulings not yet built | **alpha.3** (foundation), then one alpha per page |
| **P2** | Polish: wording, spacing, rare states | folded into the page it sits on |

---

## P0: fix first, one release (2.0.0-alpha.2)

Each item below is **confirmed in code by the lead reviewer**. Most are also reproduced live.

| # | What is broken | Where | Rule | Fix | Found as |
|---|---|---|---|---|---|
| P0-1 | **Nobody can file an expense claim.** The form shows no fields. | `views/expense_claim/Form.vue:77` (`lastField:"taxes"`) + the field allowlist added 22 Sep (`94a9e278a`) | H5, A-3.3.2 | Point the tab at a field that **is** in the allowlist, and add a test that the new form shows the expense rows | FLOW-1 |
| P0-2 | **The tab bar covers the last row of every tab page.** One comment in the CSS ends early, so the browser drops the rule. | `theme/glass-components.css:117` (`pad-*/`) | A-2.4.11, A-2.5.8 | Change one word. The test must read the **built** CSS, not the source. | APP-1 |
| P0-3 | **A sheet gets stuck after Back or when the app goes to the background.** It floats on the next page, and the tab bar stops working. | `glass/GModal.vue`; no route guard | ION-MODAL, M3-BACK, H3 | Back closes the sheet first; leaving a page closes it; the dim layer follows the sheet; **all 8 raw sheets + 2 old ones move to GModal**, and a gate blocks new ones | APP-2, APP-13, PAGE-29 |
| P0-4 | **Focus escapes an open sheet** after two Tab presses | `GModal.vue` | A-2.4.3, A-4.1.2 | `aria-modal` + the page behind is made inert while a sheet is open | APP-3 |
| P0-5 | **Personal data stays on the phone after logout.** The full Employee record, with date of birth, is still there. | `utils/personalCache.js` (clean-up misses `[doctype, name]` keys) | SEC-STORE | The clean-up also clears those keys; one test | APP-4 |
| P0-6 | **Going offline sends you to Login** ("No login methods are available") | `main.js` router guard: any failure counts as "logged out" | PWA-OFFLINE, H9 | Only a real authentication error goes to Login | PAGE-1 |
| P0-7 | **Check in still works offline.** The owner ruled it must be blocked, with the reason. | `CheckInPanel.vue` | OWN (no offline check-in), PWA-OFFLINE | Disabled offline, with one line: *"You need signal to check in."* | APP-5, FLOW-5 |
| P0-8 | **Filter counts only see the newest 10 requests.** "Not approved" can look empty while 20 are rejected. | `RequestPanel.vue` + `data/*.js limit:10` | H1, S-FAKE | Counts come from the server; the filter asks the server | FLOW-2 |
| P0-9 | **"1 leave request to approve" opens an empty list** (your own leaves) | `hrms/api/needs_you.py` routes | H4, OWN one tap | Open the list already on the team tab. Replaced by the Approvals page in P1. | FLOW-3 |
| P0-10 | **Rejecting asks for no reason**, so the employee never learns why | `RequestActionSheet.vue` reject | H9, A-3.3.2 | A required "Why not?" box; stored; shown to the employee on their request | FLOW-4 |
| P0-11 | **Announcements says "could not load" AND "nothing here" at once** | `views/announcements/List.vue` | H1, H9 | The empty state only when there is no error | PAGE-2 |
| P0-12 | **Keyboard can't open HR issue cards or Team rows** (clickable `div`s) | `HRIssueBoard.vue:58`, `TeamDashboard.vue:100` | A-2.1.1, A-4.1.2 | Make them buttons | PAGE-3 |
| P0-13 | **Calendar and Requests scroll sideways** at 320 wide with 200% text; the numbers get cut | `GCalendar`, balance grid CSS | A-1.4.10, A-1.4.4 | Grid columns that shrink (`minmax(0,1fr)`), no fixed widths | APP-8, PAGE-12 |


---

## P1-A: foundation (alpha.3), before any page work

Every page sits on these. Doing a page first means redoing it after.

| # | What | Rule | Found as |
|---|---|---|---|
| F-1 | **Remove the background blobs.** The full delete list is in `audit-app.md` §3: component, CSS, 13 tokens, gates, tests. **Keep** the solid page ground. | S-DECO, OWN (no blobs, 23 Sep) | APP-19 |
| F-2 | **Version:** `package.json` → `2.0.0-alpha.N`; shown on You as *"Version 2.0.0-alpha.3 · 23 Sep"*; git tag `nadi-v…`; `CHANGELOG.md`; a gate checks they agree | VER-SEMVER, VER-LOG | APP-26 |
| F-3 | **Portrait lock on phones** (manifest), desktop free | PWA-ORIENT, OWN (22 Sep) | APP-15 |
| F-4 | **Right animation per device:** iOS slide on iPhone; a short fade on Android; a 150 ms fade on desktop; **none** for tab and side-nav switches; none after an edge swipe; none with reduced motion. Today it's 540 ms on everything, and the desktop side nav slides. | M3-MOTION, NG-ANIM, HIG-TAB | APP-9, APP-10 |
| F-5 | **Desktop sheets** become centred dialogs, and the side nav dims too | HIG-SHEET, H4 | APP-14 |
| F-6 | **One error pattern:** inline "couldn't load · Try again". A toast only for things **you** did. **Never** raw server text. | DRY-ONE, W-PLAIN, H9 | APP-6, APP-11 |
| F-7 | **One loading pattern:** skeletons only | DRY-ONE | APP-12 |
| F-8 | **Sentence case everywhere** (76 strings in 40 files) + **no ALL CAPS** (eyebrows, status chips, the date) | W-CASE, W-DYS, NG-CAPS | APP-21, APP-22, FLOW-19, PAGE-10, PAGE-11 |
| F-9 | **One word per thing:** check in / check out · Overtime · Help · You · Log out. **No doctype names or record IDs** on screen (sheet titles, notifications, toasts). | W-ONE, OWN L4 | FLOW-9, PAGE-17, PAGE-27, PAGE-30 |
| F-10 | **No emoji, no arrow on buttons that don't navigate, no gradient-and-glow on the main button** | S-EMOJI, S-ARROW, S-DECO | APP-20, APP-23 |
| F-11 | **Fonts:** download Inter once, only the weights used (saves about 770 kB per page) | PERF-BUDGET | APP-27 |
| F-12 | **Layout jumps** on Home (0.32) and Requests (0.51), limit 0.1: reserve space while loading | CWV-CLS | APP-28 |
| F-13 | **Tab labels grow with text size**, and still never cut off. Needs its own test at 200%: label wraps under the icon, or the icon shrinks. | A-1.4.4 | APP-7 |
| F-14 | **The checks must actually run:** the a11y, visual and coherence gates run on every PR against a migrated test site. The visual gate **fails** on a missing baseline instead of writing one. Baselines are refreshed on purpose after F-1. The skip-link false positive is fixed. | H1 (for us) | APP-31, recollection E5 |
| F-15 | **Role names out of the frontend** (the Apps group in More) → decided by the server | OWN (no role literals) | PAGE-18 |

---

## P1-B: pages, one alpha each

Each page has its own plan file with the approved content. The **definitive content lists** are in the audit files named below.

| Order | Page | Job (one line) | Plan / content list | Key changes |
|---|---|---|---|---|
| 1 | **Approvals** (new, `/approvals`) | What waits on my decision; decide it here | `audit-flows.md` §4B | One list for every type + check-ins outside the area; decide on the card; "Why not?" required; cover line (names + leave **type** only); "Decided by you". **Cut** the Requests Team/History tabs, the list-page Team tabs, the Remote approvals page, and its More and Profile rows. |
| 2 | **Requests** | What I asked for, what I have left, what I'm owed | `audit-flows.md` §4A | One "New request" button (not 6 tiles); compact balances + breakdown sheet; money owed; **overtime to claim lives here**; rejected rows show the reason; **cut** the Leaves, Expenses and Overtime-bank pages and the Help tile |
| 3 | **Calendar** | What happened on my days; which day needs me | `plan/pages/01-calendar.md` (approved) + amendments below | as approved |
| 4 | **Home** | What's true now; what's waiting on me | `plan/pages/02-home.md` (approved) + amendments below | as approved |
| 5 | **Score** | How I'm doing this period; is anything wrong | `audit-pages.md` §4 Score | One score (drop the ring); periods behind "Other periods ›"; "A figure looks wrong ›" → Help, pre-filled; **fence unchanged** (verified correct) |
| 6 | **More** | What I use now and then that no tab owns | `audit-pages.md` §4 More | **Help · Announcements · SOPs · Public holidays (sheet) · Team (managers) · Apps.** Cut: Leaves, Expenses, Remote approvals, the "More" eyebrow. |
| 7 | **You** | Who I am in the system; how the app behaves for me | `audit-pages.md` §4 You | Name + department; "Your manager is …"; one "Your details" sheet; theme + notifications **on this page** (the Settings page is cut); Change password; the version line; Log out |
| 8 | **Help** | Ask HR or IT, and see the answer | `audit-pages.md` §4 Help | Rows lead with what you wrote, not the ID; "Your turn"; **Who to ask** (HR contacts moved here); an issue opens as a **read-only summary**, not the raw form |
| 9 | **Announcements · Notifications · SOPs · Team · Holidays** | see each | `audit-pages.md` §4 | Notifications in plain result words, grouped by day; SOP essentials as a list, not tiles; Team day strip → one line; Holidays = a sheet from More |
| 10 | **Forms** (all 26 form routes) | File one thing, correctly, once | to write | The approver is known, so don't ask for it; plain titles; the date filled in from the day |

### Amendments to the two approved plans (both from the audit)

**Calendar (`01-calendar.md`):**
- **Drop** the "3h 30m overtime to claim" row. Claims live on Requests; the Calendar shows the dot and claims inside the day.
- The shift time must read `09:00–18:00`, not `9:00:–18:00` (FLOW-14).
- The no-taps day has no explaining sentence (FLOW-15).

**Home (`02-home.md`):**
- Approval rows open `/approvals` with the type already chosen.
- Check-ins outside the area come from the same server list (FLOW-8).
- Check in is disabled offline (= P0-7).

---

## P2: polish (with its page)

All are listed with their location and fix in the three audit files:
- Title Case leftovers
- the name cut off on You and the side nav
- "About this app" does nothing when tapped
- the HR contacts empty state tells employees to assign roles
- the permanent Help footer sentence
- the "31 Unread" headline
- two doors in one request sheet
- toasts saying "successfully!"
- "Punch in" in the check-in history empty state
- the SOP edit button nested inside its link
- and the rest (IDs APP-24…32, FLOW-23…29, PAGE-21…31)

---

## Keep (good work, do not touch)

Taken from the three audits' keep lists:
- **The KPI visibility fence.** The server decides every tier in one place. It returns **403** for an employee asking for the team, the tree, or another person (tested live). **No role names** in the KPI frontend.
- **Nothing is queued offline.** Personal caches are namespaced per user (27 keys), apart from P0-5.
- **The update prompt:** asks first, and the choice is remembered.
- **Pinch zoom allowed;** dark mode with no flash; contrast gate 44/44.
- **Every list has an error state with "Try again";** 814/814 unit tests pass.
- **The Now bar, the Waiting/Finished split, "with Hafiz · 2 days ago", the filter chips** (once P0-8 makes their counts true).

---

## Owner decisions (answered 23 Sep 2026)

| # | Question | Ruling |
|---|---|---|
| 1 | Team line | **Both, compressed, no repeat.** The Calendar day sheet carries ONE team line for managers and team leads (own team only). The Team page holds the names. See "Team line" below. |
| 2 | Reaching past decisions | **Yes**, with better wording. See "Wording" below. |
| 3 | Shift pattern on You | **Show it.** |
| 4 | Replying to HR in the app | **Later**, as a new feature. |
| 5 | "Your goals" on Score | **Later.** |

### Team line (ruling 1, applied)

**Who sees it:** anyone with **direct reports** (managers and team leads), only for **their own direct team**.
- This is the same test the Team page uses (`has_team`: `reports_to`).
- **Change:** the day sheet today counts "people routed to me for approval" (`get_employees_routed_to`). That is a different group from "my team". It switches to direct reports, so the line and the Team page always count the same people.
- HR sees their own direct team here too. Other teams stay on the Team page's selector.

**What it says:** one line, in the day sheet, under your own day. It changes with the day, and only non-zero parts show:

| Day | Example line |
|---|---|
| Past | `Your team · 5 of 6 worked · 1 on leave ›` |
| Today | `Your team · 4 of 6 in · 1 on leave · 1 not in yet ›` |
| Future | `Your team · 2 on leave · 1 on a rest day ›` |
| Everyone in | `Your team · all 6 in ›` |

**Tap →** the Team page for **that date**, with the names and leave **type**, never the reason.

**No repeat:**
- The line is the **door** (a summary), and the Team page is the **room** (who, and why off).
- The Team page's 4-tile strip (In / On leave / Absent / Not marked) is cut. That page now starts with the names.

**Rules:** NG-PD (summary, then detail one tap away), S-DUP (one owner of the detail), OWN (managers see who and type, never the reason).

### Wording (ruling 2, applied everywhere)

**The rule:** every label says **what the person gets or does**, in their own words. Not what the system calls it.
- A question the person would ask becomes the label.
- A state says what happens next, or who has it.
- An empty page says, in one line, what's missing.

Basis: W-PLAIN, H2, W-ONE.

**Examples** (the full sweep is foundation item F-9):

| Today | Better | Why |
|---|---|---|
| Decided by you | **Requests you've already answered ›** | Says what's behind it |
| Waiting | **With Hafiz since Monday** | Who has it, how long |
| Rejected / Not approved | **Not approved: "kitchen already short"** | The reason, where it's needed |
| Awaiting you | **Your turn to reply** | Says who must act |
| No taps on this day | **You didn't check in this day** | The person's words |
| Request a fix for this day | **Tell us what happened** (or **Tell us when you left**, when the check-out is missing) | Names the actual task |
| Claim Overtime or Leave | **Claim 1h 30m** | The amount, not the category |
| Approved successfully! | **Approved. Aisyah has been told.** | What happened next |
| Could not load announcements | **Announcements didn't load. Pull down to try again.** | What to do |
| Leave Application HR-LAP-2026-00043 has been Rejected by Administrator | **Your leave on 22 Sep wasn't approved. See why ›** | Plain result, a way forward |
| Remote Approvals | **Check-ins outside the work area** | What they are |
| Log Out | **Log out** | Sentence case |

**Where it is enforced:** F-9 builds a glossary (`docs/glass/GLOSSARY.md`, one line per term: word to use, words never to use) and a gate that fails on the banned words (doctype names, "successfully", Title Case in `__()`).

---

## Order of work (by what depends on what)

1. **alpha.2 = P0-1…P0-13.** One commit per root cause, each with the test that failed first. You deploy once.
2. **alpha.3 = F-1…F-15** (the foundation). The visual baselines are refreshed once, after the blobs go.
3. **alpha.4 = Approvals + Requests together.** They split one set of data, so building them apart means building twice.
4. **alpha.5 Calendar → alpha.6 Home → alpha.7 Score → alpha.8 More + You + Help + the rest → alpha.9 Forms.**
5. **2.0.0** when every P0 and P1 row is closed and all 10 gates pass against the test site.
