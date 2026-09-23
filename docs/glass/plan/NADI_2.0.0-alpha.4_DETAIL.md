# Nadi 2.0.0-alpha.4 — detailed spec, page by page, element by element

Companion to `NADI_2.0.0-alpha.4_PLAN.md` (priorities, rulings, order of work).
This file is the **what exactly**: for every page, component and element,
**Today** (measured in code and on fresh.local, 23 Sep) → **Rule** (research)
→ **Change**. Priority tags match the plan: P0 broken · P1 redesign · P2
polish · P3 needs a yes.

Sources are listed once at the end and cited by short key:
`NNG-EMPTY` empty states · `NNG-SHEET` bottom sheets · `NNG-SKEL` skeletons ·
`NNG-PUSH` notifications · `NNG-PD` progressive disclosure · `M3-SHEET`
Material 3 bottom sheets · `M3-MOTION` Material 3 easing/duration · `HIG-SHEET`
Apple sheets · `HIG-44` Apple 44 pt targets · `W-258` WCAG 2.5.8 target size ·
`W-243` WCAG 2.4.3 focus order · `W-H102` modal dialog technique · `W-141` use of
colour · `W-143` contrast · `W-1411` non-text contrast · `CWV-CLS` layout shift ·
`OWASP-A01` · `ISO-5.15` · `NIST-AC6` · `PDPA` · basis rules (W-PLAIN, W-CASE,
S-ONE, S-DUP, H8) from `docs/glass/audit/2026-09-23-basis.md`.

---

## 0. Global standards (apply to every element below)

| Standard | Value | Rule |
|---|---|---|
| Touch target | ≥ 44×44 px for every tappable thing; icons may be small inside a 44 px box | HIG-44, W-258 (24 px floor) |
| Text contrast | ≥ 4.5:1 body, ≥ 3:1 large text and UI indicators, both themes | W-143, W-1411 |
| Colour | never the only signal; every colour has a word | W-141 |
| Words | sentence case; plain words; no "(s)", no doctype names, no record IDs in running text | W-PLAIN, W-CASE |
| Numbers | money "RM 50.00"; hours "1h 30m"; dates "Tue 22 Sep" (list) / "22 Sep" (compact) | basis, owner |
| Loading | a skeleton the size of what's coming, for whole-page loads; a small inline indicator for one block | NNG-SKEL |
| Empty | never a blank area: say what's missing and what to do next | NNG-EMPTY |
| Error | one plain line + a way to retry; never a raw error | basis H9 |
| Motion | enter 250–300 ms decelerate, exit 200 ms accelerate; reduced-motion = no slide | M3-MOTION |
| Layout jump | ≤ 0.1 per page | CWV-CLS |
| Sheets | see §1.1: Close (X), Back closes, tap-outside closes, everything behind blocked | NNG-SHEET, M3-SHEET, W-243 |
| Access | the server decides who sees what; the app never reads role names | OWASP-A01, ISO-5.15 |

---

## 1. Shared components (fix once, every page benefits)

### 1.1 Sheet (`GModal`) — P0
| Element | Today | Rule | Change |
|---|---|---|---|
| Close button | none; only pull-down closes | NNG-SHEET: visible Close at the top | **X button**, top right, 44 px, label "Close" |
| Tap outside | dim layer is inside the page; tab bar and header still take taps | M3-SHEET: scrim blocks and closes; W-243: outside is inert | dim + block **the whole app** behind the sheet; tap on dim closes |
| Back | closes via router guard, not always | NNG-SHEET: Back closes the sheet | Back closes the top sheet only, never leaves the page |
| Drag | pull-down closes (Ionic) | HIG-SHEET: drag to dismiss | keep, but not the only way |
| Motion | Ionic default spring | M3-MOTION | 280 ms in, 200 ms out, no slide under reduced motion |
| Focus | moves in, returns to opener (done alpha.2) | W-243 | keep; add a test |
| Title | optional prop, inconsistent sizes | S-ONE | every sheet has a title in one style |
| Width, padding | varies per sheet (Approvals narrower) | consistency | one width and padding token |
| Stacked sheets | confirm-inside-sheet (reject reason) opens a second sheet | NNG-SHEET: avoid stacking | reason field inside the same sheet (step), no second sheet |
| Desktop | centred (done), side menu not dimmed | M3-SHEET | dim covers side menu (from 1.1 blocking) |

### 1.2 Pull to refresh (`GPullRefresh`) — P0
| Today | Rule | Change |
|---|---|---|
| "Refreshing…" stays after the pull (waits for an event Ionic never sends) | Ionic refresher docs | reset on the pull's end; the text only shows while pulling |
| Text line under the header | — | a slim bar, no text once released |

### 1.3 Page header (`GAppHeader` / `BaseLayout`) — P1 (owner, 23 Sep)
**Owner:** "the date on top nav is not good. It should be inside, not replacing
Nadi. Use the Nadi logo we already use instead of the word."

| Element | Today | Change |
|---|---|---|
| Brand | Home's title **is** the date ("Wed 23 Sep"); other tabs show the page name; the word "Nadi" only as a fallback | the **Nadi mark** (lime rounded square with "n", already drawn in `SideNav.vue` from brand tokens) at the left of every tab-page header, 32 px, labelled "Nadi" for screen readers. One shared `GLogo` component, used by both the header and the side menu (one source). |
| Page title | date on Home, page name elsewhere | Home: the mark only, no text title (Home is the brand page); other tabs: the mark, then the page name ("Calendar", "Requests") |
| Date | **replaces** the title on Home | moves **inside the page**: first line of Home's **Today** card ("Wednesday, 23 September"), not in the header |
| Bell | unread dot | keep, 44 px |
| Avatar | letter, goes to You | keep; photo when set |
| Dead code | date "kicker" branch unused | removed |
| Pages without tab bar (You, Notifications, Approvals, HR contacts, forms) | back arrow + title, markup differs per page | one shared back-header: ‹ + title, same height; no mark (the back arrow is the way out) |
Rules: brand recognition and one consistent place for it (HIG, M3 top app bar:
brand or page title, actions right); date is content, so it belongs with
today's content (S-DUP, NNG-PD).
Done when: every tab page shows the mark in the same place, size and colour
in both themes; Home's date appears once, inside the Today card.

### 1.4 Tab bar (`BottomTabs`) / side menu (`SideNav`) — P2
| Today | Change |
|---|---|
| Team highlights "More" | Team belongs to More (it is reached from More), keep, but add "Team" to the page title so the reader knows where they are |
| Tab labels fit at 200 % text (measured) | keep a test |
| Side menu: grayscale photo | full colour |

### 1.5 Rows and lists (`GListPanel`, `GListRow`) — P1
| Today | Change |
|---|---|
| Rows 52 px, one surface per panel (good) | keep |
| "Show N more" styles differ per page | one style: centred text button, 44 px |
| Empty lists sometimes render nothing | every list has an empty line (NNG-EMPTY) |

### 1.6 Loading and errors (`GSkeleton`, `ResourceError`, `GBanner`) — P1
| Today | Change |
|---|---|
| Mix of skeletons, spinners ("Loading your KPIs…"), pulsing boxes | skeleton for page/block loads, spinner only inside a button (NNG-SKEL) |
| Error lines vary ("could not be loaded", "Something didn't load") | one pattern: "{Thing} didn't load. Pull down to try again." |

### 1.7 Status chips (`GStatusChip`, `GBadge`) — P1
| Today | Change |
|---|---|
| Words from the system: "Open", "Approved & Unpaid" | one vocabulary: **Waiting · Approved · Not approved · Paid · Cancelled**; colour + word |
| "Waiting" chip is orange outline; "Approved" is green fill | keep colours, check contrast in both themes |

### 1.8 Buttons (`GButton`, `GGhostButton`, `GIconButton`) — P2
| Today | Change |
|---|---|
| Frappe `Button` still used in Notifications ("Mark all as read", "Load more") | use the glass buttons |
| "Log out" plain outline | outline in danger ink (it ends the session) |

---

## 2. Home — P0 + P1 (one screen, never empty)

**Job:** "What do I need to do today?" Rule: NNG-EMPTY, NNG-PD, S-ONE.
**Measured today:** header 74 px, status 41 px, button 63 px, then **553 px empty**.

| # | Element | Today | Change |
|---|---|---|---|
| 2.1 | Header | title is the date "Wed 23 Sep" | **Nadi mark** in the header (1.3); the date moves into the Today card |
| 2.2 | Pull to refresh | reloads 4 things; text sticks (P0) | fixed by 1.2 |
| 2.3 | **Today card** (was NowBar + CheckInPanel) | two separate pieces: status line, then the button | one card: state + hours on one line, shift under it, the button inside the card |
| 2.3· | Date line (new, top of card) | — | "Wednesday, 23 September" |
| 2.3a | State line | "Working · 7h 20m", "Not checked in", "No shift today" | keep words; "No shift today. Enjoy your day off." when off |
| 2.3b | Shift line | "Audit Morning Shift 09:00–18:00" | "Day shift · 9:00–18:00" (short name, no seconds) |
| 2.3c | Check in / out button | shown even with no shift (P0) | shown only when a check-in is possible; offline: disabled + "You need signal to check in." (kept) |
| 2.3d | Forgot-to-check-out banner | yellow tappable banner above the card | keep, inside the card top, one line + "Resolve ›" |
| 2.4 | **Check-in sheet** | clock, date, location verdict, selfie box, Confirm | keep flow; fix: Close (X) (1.1), no **white camera box** in dark (P1-5); location line one sentence; Confirm button label "Check in" / "Check out" (not "Confirm Check in") |
| 2.4a | After a punch | toast "{IN} successful!" | "Checked in at 9:02." / "Checked out at 18:04." |
| 2.4b | Remote / strict / late dialogs | three separate dialogs | each is one sheet with a title and Close; words reviewed (W-PLAIN) |
| 2.5 | **This week** (new) | — | "4 days worked · 1h 30m overtime to claim ›" or "Nothing to claim this week." Tap → Calendar |
| 2.6 | **Coming up** (new) | — | next leave / travel / training / public holiday; else "Nothing booked. Next public holiday: Deepavali · Tue 20 Oct." |
| 2.7 | **Waiting on you** | eyebrow "Needs you", rows "1 leave request(s) to approve", hidden when zero | always for approvers: "2 requests · 1 check-in waiting ›", or "Nothing waiting on you."; proper plurals |
| 2.8 | **Latest announcement** | up to 2 rows + "See N more", hidden when none | always one: title + "Needs your confirmation" or date; "See all ›"; else "No news." |
| 2.9 | Push prompt | appears after first check-in | keep, one line under the card, dismissible |
| 2.10 | Update bar | fixed in alpha.3 | keep |

**Done when:** fits 390×844 for an employee without scrolling; no block hides;
loading shows 4 skeleton blocks of the final size; CLS ≤ 0.1; zero console errors.

---

## 3. Calendar — P0 + P1

**Job:** "What happened on my days, and what do I need to fix?"

| # | Element | Today | Change |
|---|---|---|---|
| 3.1 | Title / month / arrows | "September 2026", ‹ › | keep; arrows 44 px |
| 3.2 | Weekday row | "Sun Mon Tue…" (no capitals now) | keep |
| 3.3 | **Day tiles** | states: worked, half, leave, rest, absent, none; dots for flags | add kinds (R1): **Travel**, **Training**, **Open request** (approvers/managers); past-no-record looks different from future (P1) |
| 3.4 | Today | ring, readable on every fill (alpha.2) | keep |
| 3.5 | **Key** | only kinds in the month (R1 says always) | always every kind, each swatch **with its word** (W-141); wraps to 2 rows max at 390 |
| 3.6 | Tap a day → **day sheet** | see 3.7 | Close (X) (1.1) |
| 3.7a | Sheet title | "Tuesday, 22 September" | keep |
| 3.7b | Shift line | "No shift" on a worked day (P0); "9:00:–18:00" stray colon (P0) | read attendance → check-ins → roster; "Day shift · 9:00–18:00" |
| 3.7c | Punches | "In 09:19", "Out 20:17" rows | keep; skipped: "Set aside by HR" (kept) |
| 3.7d | Hours | "9h 58m worked · 1h 58m overtime" | keep |
| 3.7e | Kind of day | not shown | one line when it's leave/travel/training: "Annual leave", "Travel: Penang", "Training: First aid" |
| 3.7f | Team line (managers) | "Your team · 1 absent ›" | keep |
| 3.7g | Action | "Claim 1h 58m" / "Tell us what happened" / note | keep one action; absent past day: "Tell us what happened" (was text only) |
| 3.8 | Links under grid | underlined text "All check-ins", "Your shifts" | two quiet rows in one panel |
| 3.9 | Empty space | ~270 px under the grid | a "This month" summary line: "18 worked · 1 leave · 2 to fix ›" |

**Server:** `get_month_flags` / `day_sheet` return the new kinds; each source
checked first (Travel Request, Training Event on this site) — reported before coding.

---

## 4. Requests — P1 redesign (compact, no scroll)

**Job:** "Ask for something, and see where my asks are." Measured: scrolls 426 px.

| # | Element | Today | Change |
|---|---|---|---|
| 4.1 | Title | "Requests" | keep |
| 4.2 | **New request** | lime button, below balances | **top**, full width |
| 4.2a | Type sheet | Time off, Claim overtime, Claim an expense, Change a shift, Fix a day | keep; add Close (1.1) |
| 4.3 | **Balances** | 4 big cards in a 2×2 grid (+ "Show 3 more leave types") | one line: **"Annual 6 · Medical 13 · All balances ›"** (R2) |
| 4.3a | All balances sheet | — | compact rows, same style: "Annual leave · 6 of 14 · expires 31 Dec" |
| 4.4 | **Needs attention** | rows: overtime to claim, **"INR 50.00"** unpaid (P0), days with no attendance | one line each, only when non-zero: "1 day of overtime to claim ›", "RM 50.00 approved, not yet paid ›", "1 day with no attendance ›" |
| 4.5 | Tabs | "My requests / Answered by you" (approvers) | keep for approvers; hide for everyone else (done) |
| 4.6 | Filter chips | All / Waiting / Approved / Not approved, wrap to 2 lines | move into **See all**; main page shows no chips |
| 4.7 | **List** | two piles, 10 rows, "Show 5 more"; "Waiting 42" but only 4 (P0) | **last 5, one line each**: "Compassionate leave · 28 Aug · Waiting"; "See all ›" |
| 4.7a | Row detail | leave type bold, dates grey, "with Hafiz · 2 days ago" | one line + chip; the "with whom, since when" goes in the request's sheet |
| 4.8 | **See all** (new page) | — | filters + full list, paged; counts match the chips |
| 4.9 | Request sheet | system words ("ID", "Leave Application", Status "Open"), right-aligned reason | plain words; "Waiting with Hafiz since Mon"; reason left-aligned; "Not approved: <reason>" shown when rejected |

**Done when:** fits one screen at 390×844 for an employee with ≤ 5 recent requests; no chip wraps; CLS ≤ 0.1.

---

## 5. Approvals — P1 + P2

| # | Element | Today | Change |
|---|---|---|---|
| 5.1 | Summary | "1 waiting · oldest since 14 Sep" | keep |
| 5.2 | Rows | "Time off · Aisyah" / "Tue 15 Sep · Annual Leave · 1 day" | keep |
| 5.3 | Empty | "Nothing is waiting on you." (then ~470 px empty) | keep line; the two "answered" rows sit right under it |
| 5.4 | Request sheet | system words, "Reject" / "Approve", reason right-aligned | plain words; "Not approve" / "Approve"; reason step inside the same sheet (no stacking, 1.1) |
| 5.5 | Check-in sheet | photo, reason, Not approve / Approve | Close (1.1); photo 16:9 box, dark-safe placeholder |
| 5.6 | Answered check-ins sheet | list, "Nothing answered yet." | keep |
| 5.7 | Tab bar | none on this page | shared back-header (1.3) |

---

## 6. Team — P2

| # | Element | Today | Change |
|---|---|---|---|
| 6.1 | Team of (HR) | autocomplete | keep |
| 6.2 | Calendar | a date picker only | add marks: days with someone on leave (dot), matches R1 kinds |
| 6.3 | Day label + roster link | "Tue 22 Sep · Open team roster" | keep |
| 6.4 | Groups | "Nadi W0 A - NW0A (1)" raw code | department name only: "Nadi W0 A · 1" |
| 6.5 | Member rows | name, designation, chip, summary; tap expands | keep; chip words = §1.7 vocabulary |
| 6.6 | Footer caption | "You see your direct reports…" | keep |
| 6.7 | Page scrolls 34 px for nothing | — | fix bottom padding |

---

## 7. Score — P1 redesign

| # | Element | Today | Change |
|---|---|---|---|
| 7.1 | Tabs (managers, HR, CEO) | "My KPI / Team KPI / All KPI" | "Mine / My team / Everyone" (plain words) |
| 7.2 | **No review** | big banner "No review scheduled yet" + long body naming the appraiser + a second card "Scored by …" (repeat) | one line: "No review yet. Hafiz scores you when HR opens one." + "Last review: Q2 · 82% ›" if any (R3) |
| 7.3 | Filters | year + cycle selects | only when a review exists; default latest |
| 7.4 | Score | big number + ring + badges | keep; ring and number never both "82" twice — number inside the ring only |
| 7.5 | Trend | SVG line | keep when ≥ 2 cycles |
| 7.6 | KRAs | rows with bar, target/actual/weighted | keep; one line per KRA + tap for detail |
| 7.7 | Feedback count | row | keep |
| 7.8 | "A figure looks wrong ›" (new) | — | opens a new HR issue, pre-filled (PAGE-15) |
| 7.9 | Team / Everyone | table, department tree for HR/CEO | keep; server-scoped (protected rule unchanged) |
| 7.10 | Loading | spinner "Loading your KPIs…" | skeleton (1.6) |

---

## 8. More — P2

| # | Element | Today | Change |
|---|---|---|---|
| 8.1 | Rows | Help, SOPs, Announcements, Public holidays, Team (managers) | keep; icons 44 px wells |
| 8.2 | Apps | heading + rows when offered | keep |
| 8.3 | Empty space | ~475 px | acceptable (a menu); no filler |
| 8.4 | Public holidays sheet | list, "No public holidays ahead…" | keep; Close (1.1) |

## 9. You — P0 + P2

| # | Element | Today | Change |
|---|---|---|---|
| 9.1 | Identity | avatar, name, role · department · branch | keep |
| 9.2 | Manager / shift lines | shown when set | keep |
| 9.3 | Your details | **5 blank labels** (P0) | every field labelled; empty values hidden, not "-" |
| 9.4 | Approvals row | with count | keep |
| 9.5 | Change password | own page; hard-coded white background | theme-safe |
| 9.6 | Theme | Light / Dark / System | keep |
| 9.7 | Notifications switch | when the site can push | keep |
| 9.8 | Log out | neutral outline | danger outline (1.8) |
| 9.9 | Version | "Version 2.0.0-alpha.x · build" | keep |

## 10. Help — P0 + P2

| # | Element | Today | Change |
|---|---|---|---|
| 10.1 | Page | **error on every open** (P0) | fix `.catch` on undefined |
| 10.2 | HR / IT pills | IT when installed | keep |
| 10.3 | Who to ask | row → HR contacts | keep |
| 10.4 | HR contacts empty | "Ask your administrator to assign the HR Manager role…" (asks staff to diagnose) | "No HR contacts are listed yet." + "Ask HR ›" (opens a new issue) |
| 10.5 | Issue list | "Reported by you", an issue titled "Issue" | a title is required when raising an issue |
| 10.6 | IT footer | "IT & admin tickets are handled by…" permanent | move into the empty state only |

## 11. Notifications — P1

| # | Element | Today | Change |
|---|---|---|---|
| 11.1 | Header | back + "Notifications" | shared back-header (1.3) |
| 11.2 | Unread | "31 Unread" + "Mark all as read" (Frappe button) | "31 unread" + glass ghost button |
| 11.3 | Avatar | "?" for Administrator | the app mark for system messages; person's initial otherwise |
| 11.4 | Message | raw: "Leave Application HR-LAP-2026-00043 has been Rejected by Administrator", IDs break mid-word | plain: "Your leave on 22 Sep wasn't approved. See why ›" (NNG-PUSH: short, one action) |
| 11.5 | Time | "2 hours ago" | keep |
| 11.6 | Load more | right-aligned Frappe button | centred glass button |
| 11.7 | Empty | "You are all caught up" | keep |

## 12. Announcements — P2

| # | Element | Today | Change |
|---|---|---|---|
| 12.1 | List groups | "Needs your confirmation" / "Everything else" | keep |
| 12.2 | Category icons | keyed by English names | keyed by value; unknown → megaphone |
| 12.3 | Detail | title, date, body, "I've read and understood this" | keep |
| 12.4 | Desk | HR finds it only by search | add to the HR workspace |
| 12.5 | Images | not tested on S3 | test on the live site |

## 13. SOPs — P2
| Today | Change |
|---|---|
| no empty line when a search finds nothing | "No SOP matches '{text}'." |
| essentials 2-column cards | keep |

## 14. Forms (leave, overtime, expense, shift, fix a day) — P2
| Today | Change |
|---|---|
| each form its own header | shared back-header (1.3) |
| field labels from the system ("Leave Type", "Half Day Date") | plain labels; required marked once |
| submit button labels vary | "Send request" everywhere |

---

## 15. Server work (backs the pages above)

| # | Change | For |
|---|---|---|
| S1 | `day_sheet` shift from attendance → check-ins → roster | 3.7b |
| S2 | Day kinds: travel, training, open request in `get_month_flags` / calendar | 3.3 |
| S3 | Home "this week" + "coming up" in one call | 2.5, 2.6 |
| S4 | Currency from the company, not the claim default | 4.4 |
| S5 | Plain notification text at creation | 11.4 |
| S6 | Requests "See all" paged list with the same counts | 4.8 |

## 16. Tests added this release

- **Sheet gate:** every sheet opens, takes a tap inside, closes by X, by tap
  outside and by Back; nothing behind takes a tap (phone + desktop).
- **One-screen gate:** Home, Requests, Calendar fit 390×844 without scroll for
  the seeded employee.
- **No-blank gate:** every Home block renders in its empty state.
- **Words gate:** no "(s)", no "INR", no doctype names or record IDs in rendered text.
- **Both themes:** each page captured in dark and light; contrast pairs checked.

## Sources

- NN/g empty states: https://www.nngroup.com/videos/empty-states-in-application-design-guidelines/
- NN/g bottom sheets: https://www.nngroup.com/articles/bottom-sheet/
- NN/g skeleton screens: https://www.nngroup.com/articles/skeleton-screens/
- NN/g push notifications: https://www.nngroup.com/articles/push-notification/
- Carbon empty states: https://carbondesignsystem.com/patterns/empty-states-pattern/
- Material 3 bottom sheets: https://m3.material.io/components/bottom-sheets/guidelines
- Material 3 easing and duration: https://m3.material.io/styles/motion/easing-and-duration
- Apple HIG sheets: https://developer.apple.com/design/human-interface-guidelines/sheets
- WCAG 2.2 focus order: https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html
- WCAG H102 modal dialogs: https://www.w3.org/WAI/WCAG22/Techniques/html/H102.html
- WCAG 2.5.8 target size: https://accessibility.build/wcag/2-5-8
- Ionic refresher: https://ionicframework.com/docs/api/refresher
- OWASP A01: https://owasp.org/Top10/2021/A01_2021-Broken_Access_Control/
- ISO 27001 A.5.15: https://www.isms.online/iso-27001/annex-a-2022/5-15-access-control-2022/
- NIST RBAC / AC-6: https://csrc.nist.gov/csrc/media/projects/role-based-access-control/documents/rbac-std-draft.pdf
- Malaysia PDPA 2010: https://malaysia.incorp.asia/guides/malaysia-pdpa-2010-guide/
