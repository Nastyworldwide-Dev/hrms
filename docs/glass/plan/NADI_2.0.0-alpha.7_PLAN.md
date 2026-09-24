# Nadi 2.0.0-alpha.7 — plan: an app that looks and behaves like Apple built it

**Status:** proposal for the owner's go. Nothing is coded.
**Owner's ask (25 Sep 2026):** exact 1:1 with iOS 26/27 Liquid Glass, smallest to biggest detail, UI and UX;
a Home overhaul; announcements with preview and required acknowledgement (research first, no hand-rolling);
fix the live defects in the new screenshots; a deep dive per page; a better-calculated score.

## 0. Where Nadi stands — the honest number

| Measure | Result |
|---|---|
| My first estimate (25 Sep) | "about 60%" — **too generous** |
| Review A: 19 tab roots and list screens, each scored vs iOS 26 | **48 / 100** |
| Review B: every form, detail screen and sheet, plus the owner's 7 live shots | **48 / 100** |
| Method | Every screen photographed at iPhone size (402 pt, both personas); iOS 26 numbers measured from the owner's own Settings + App Store screenshots; Apple's HIG/WWDC25 for rules; each difference scored P1 (visible at a glance) / P2 (on inspection) / P3 (pixel) |

**Target for alpha.7: ≥ 90 / 100 on the same scoring, re-measured by the same reviewers' checklist.**

## 1. Evidence (all committed in `docs/glass/plan/`)

| File | What it holds |
|---|---|
| `alpha7-review-A.md` | 19 screens: difference tables, SwiftUI "how Apple would build it", scores |
| `alpha7-review-B.md` | 9 details, 7 forms, profile/settings, sheets, the owner's live shots; top 25 fixes |
| `alpha7-home.md` | What Home shows today (code-traced), Apple's Wallet/Fitness/Live Activity/Widget rules, 6 workforce apps' clock-in screens, proposed Home |
| `alpha7-announcements.md` | Current announcement model (code-traced), what Frappe already provides, how Connecteam/Deputy/Staffbase/Workvivo/Viva do "read and acknowledge", accessibility of scroll-gated buttons |
| `alpha7-ot-bug.md` | The live Overtime failure: CSS cause measured; server call probed |
| `alpha7-ios26-spec.md` | Apple's exact numbers (colours, type, tracking, springs) and what Apple does NOT publish |
| `alpha7-web-native.md` | What an iPhone Home Screen web app can do, per Safari version (MDN compat data, WebKit blog to Safari 27) |
| `alpha7-handrolled.md` | Code sweep: frappe-ui leftovers (53 toasts), fonts, hand-built lists |

---

## 2. Live defects from the owner's screenshots (fix first — phase 0)

| # | Defect | Cause (evidence) | Fix |
|---|---|---|---|
| 0.1 | Overtime: the red "Could not check overtime…" / "Checking…" text wraps one word per line **inside** the Hours row (row grows 43 → 87 pt) | CSS: `.g-form-row > :not(…):not(…)` (specificity 0,3,0) beats `.g-form-row--error .g-field-error` (0,2,0), so the error gets `flex-basis: 0` and a 22 px column (measured, `alpha7-ot-bug.md`) | Error moves UNDER the row, full width: `.g-form-row.g-form-row--error > .g-field-error { flex: 0 0 100% }`. Affects every form row with an error. |
| 0.2 | Overtime: "Could not check overtime" on a day the list offered | **Not reproducible locally**: every employee × claimable day passes, server and browser. The app throws the real server error away (no `onError`) | Record and show the real reason (`exc_type` + message) — the next report names the cause. No blind backend change. |
| 0.3 | Overtime: "Checking…" shows as red error text | loading and error share one channel | Loading = a spinner in the row (iOS `ProgressView`), not red text |
| 0.4 | Overtime: the picked day is shown twice ("Wed, 23 Sep" and "Day you worked 23 Sep 2026") | the date field stays visible after a pick | Hide "Day you worked" once a day is picked (show it only for a day not in the list) |
| 0.5 | "Paid as overtime", the hint line and "Try again" float between groups at different indents | free text outside any group | They become a row or a group footer |
| 0.6 | Filters sheet: labels above empty boxed selects; a black footer band with two mismatched buttons | ListFiltersActionSheet predates the grouped form | Filters = grouped rows with menu pickers ("All" default); Reset leading / Done trailing in the sheet bar; apply live |
| 0.7 | Appearance menu: opaque, a blank slot above "Light", covers the row labels | custom menu | iOS pull-down menu (glass, anchored to the value, no blank slot) — see D2 |
| 0.8 | Check-ins list: time as a bold title, In/Out as chips, filter as a boxed square | list row predates alpha.6 | Rows "In / Out" + time trailing, grouped by day (Today / Yesterday / Mon 22 Sep); filter = a glass bar button |
| 0.9 | Staff see **"₹ 50"** on expenses; the approver sees "RM 12.50" | a claim can carry the employee's salary currency; the list formats with it | **Withdrawn 25 Sep (checked, not a defect):** the staff test user is in "_Test Company", whose currency IS INR; the approver's company is MYR. Each claim shows its own currency correctly. No change. |

## 3. Home overhaul (owner's request; research: `alpha7-home.md`)

**Rule that shapes it:** Apple HIG Materials — glass is for controls and navigation, **not content**. So the
check-in card is a solid, raised content card (like a Wallet pass or the Fitness summary card), and only its
button is the prominent glass button. That delivers the owner's "a card that clearly holds the clock-in" without
breaking Apple's rule.

**What the research says to do (sources in the file):** every workforce app studied (Deputy, Teams Shifts,
Connecteam, When I Work, Homebase, Workday) leads with **the shift + one big clock button**; once in, the
**running time becomes the headline**; a disabled button must **say why**. None puts routine news above the clock;
NN/g: people skip banner-like blocks at the top ("banner blindness").

**Proposed Home, top to bottom (staff):**
1. **Large title** "Today" with the date under it (34 pt bold; collapses on scroll).
2. **Required announcement** — only one, and only if it must be read or is urgent (compact row with a preview line).
   Routine news goes lower. *(This adjusts the owner's "announcement on top": it follows the research above.)*
3. **Today card** (solid content card, 26 pt corners):
   - top: shift line "Day shift · 9:00–18:00"
   - middle, the headline: "Not checked in" / "Checked in · 3h 12m" (live) / "Done · 8h 41m" / "Rest day" / "On leave"
   - a hairline, then details: location "HQ · in range" or "1.2 km away — needs approval", last punch "In 9:02"
   - bottom: **one** prominent button, "Check in" / "Check out"; when it can't be used, it says why
   - the forgotten check-out becomes a state of this card, not a separate banner
4. **Announcements** — 2 rows, each title + one-line preview + unread dot; "See all".
5. **This week** — "3 of 5 days · 1h 00m overtime to claim", next leave or holiday.
6. **No quick-action grid** (the Requests tab does that; HIG Widgets: avoid app-like grids on glanceable screens).

**Approver:** the same, plus **"Needs you"** (counts by kind, e.g. "Time off 2 · Overtime 1") right after the
Today card when anything waits; one quiet line at the bottom when nothing does.

**Removed:** the separate Now bar, the separate open-check-in banner, the logo in the title position, "No news."

## 4. Announcements with preview and required acknowledgement (research: `alpha7-announcements.md`)

**Finding: most of it already exists** — HR writes in Desk with the rich-text editor, audience targeting,
publish dates, pinning; every open and "I've read and understood" is recorded per employee with a time; HR sees
"Read by X of Y · Z confirmed". **Add nothing new as a library**: Frappe's editor for HR, the app's own HTML
sanitiser for staff, the browser's IntersectionObserver for "reached the end", Ionic's non-dismissible modal.

| # | Gap | Change | Evidence |
|---|---|---|---|
| 4.1 | **Images HR pastes do not show for staff** (Frappe stores them private) | set the doctype's `make_attachments_public` + a guarded patch (a site Property Setter can override the JSON) | Frappe file permissions; our memory note "Property Setter shadows doctype JSON" |
| 4.2 | HR has no true preview | "Preview as staff" button in Desk → opens the real app screen, marked "Preview — not published", records no read | owner's ask |
| 4.3 | Editing does not ask for re-acknowledgement | `version` on the announcement, raised when a published required notice's title/body changes; "Minor fix" skips it; the read record stores the version acknowledged | Deputy / Read-and-Understood re-ack on change |
| 4.4 | The "I've read this" button is always active | Required notices open **full-screen** on app open, oldest first; the confirm button enables when the end is reached; before that it stays focusable, says "Read to the end to confirm", and a tap scrolls to the end (VoiceOver users can confirm) | HIG Modality (full-screen for long required tasks); NN/g (a disabled button must say why); WCAG 2.1.1 |
| 4.5 | No escape hatch | "Remind me later" on non-urgent required notices (not on urgent ones) | Connecteam pattern; HIG (always an obvious way out) |
| 4.6 | HR cannot chase | "Remind those who haven't confirmed" (existing push path) + a who-has/hasn't list with export | Connecteam/Staffbase/Workvivo |
| 4.7 | Two taps could record twice | unique (announcement, employee) | race seen in code review |

**Needs the owner:** (a) the confirmation report is a new Desk report (you deferred report work on 13 Sep —
is this one OK?); (b) public images are reachable by anyone with the link — fine for normal notices; say if some
notices are sensitive.

## 5. Every page — the full alpha.7 list

Numbers = fixes from the two reviews (`A#` = review A's top-20, `B#` = review B's top-25). The per-screen tables
with every P1/P2/P3 difference are in the review files.

### 5.1 The frame (every screen)
- **Large titles** on the 5 tab roots, collapsing to a centred 17 pt inline title (A1). Home gets a title (it has none).
- **Pushed screens**: back chevron + centred inline title + contextual actions only; **bell and avatar only on tab roots** (B24).
- **Bar buttons** are 44 pt round glass buttons with a monochrome symbol; "New" = a `+` button, not a lime capsule (A8, A9); filter = `line.3.horizontal.decrease.circle` (B20).
- **Avatar**: a circle, gradient initials (A10).
- **Tab bar**: selected-tab lens, height 61, inset 20, minimise on scroll (A5).
- **Search**: a search button at the end of the tab bar → searches requests, people (names), SOPs, days (owner: yes).

### 5.2 Colour and surface
- Page #000 dark / #F2F2F7 light; content cells **flat** #1C1C1E / #FFFFFF — no gradient, rim or border on content (A2, A7).
- Status as **coloured text** in Apple's iOS 26 colours (orange #FF9230, green #30D158, red #FF4245), not pills (A3).
- One currency, from the company (0.9).

### 5.3 Lists
- Everything is an inset grouped list; rows never sit loose on the page (A6).
- Group radius 26, gap 35, rows 54 with an icon / 44 without (A11).
- Icon tiles: **coloured tile + white symbol** (owner: yes) — see §7 for the example set (A12).
- Row title 17 regular, subtitle 15 secondary, SF tracking (A13).
- Section headers attached to their group (A14); "See all" as the last row of the group (A15).
- Dates the iOS way: Today / Yesterday / Wed 23 Sep; durations "Half day" / "3 days", never "0d" (A16, B4).
- Tabular digits for times, money, counts (A17).
- **Empty states** = centred icon + title + one line (ContentUnavailableView); no dashed boxes, no top-left grey sentence (A4, B25).
- Calendar legend moves to an info sheet; one dot style on the grid (A19).

### 5.4 Forms
- Errors under the row, loading in the row (0.1, 0.3; B2, B3).
- No red asterisks — the Send button stays disabled until the form is complete (B14).
- No section header over a single row (B13); guidance in group footers (B11).
- Dates and times as **compact pills** ("23 Sep 2026"), nothing before a value is set (B15).
- Menu picker glyph = up/down chevron, value in secondary colour (B16).
- A **sheet's** primary action sits in the sheet bar: Cancel left, Add/Done right (B21); no card inside a sheet (B22).

### 5.5 Detail screens (a sent request)
- Read-only rows as label/value (`LabeledContent`), no chevrons, pickers or switches (B1).
- Status shown once (B7); person by name (B5).
- Cancel a request = red text row at the end + confirmation, not a salmon capsule (B6).

### 5.6 Controls
- **Switch = Safari's native switch** (`<input type=checkbox switch>`): Apple's look, VoiceOver role, and the only haptic a web app gets (Safari 18) (B17).
- **Menus** (Appearance, "⋯" on a request): iOS pull-down, glass, anchored to the button (0.7, B18).
- **Notification banners** replace all 53 frappe-ui toasts (top glass capsule, VoiceOver live region).
- **Alerts** (Delete / Discard?): one centred glass alert, Cancel always "Cancel".

### 5.7 Type, motion, native feel
- Dynamic Type: the app follows the iPhone's Text Size setting (`-apple-system-body`, rem).
- Apple's default spring for push, sheets and the tab lens (response 0.5, damping 0.825).
- Stop downloading Inter / Inter Tight / JetBrains Mono on Apple devices.
- **App icon badge** = approvals waiting / unread (Home Screen apps, iOS 16.4+).
- **Tapping a notification opens that exact request** (Declarative Web Push). Approve/Reject buttons *on* the notification are impossible on iPhone.
- ~~**Check-in without signal**~~ **Not built (25 Sep):** the owner's standing rule is "never ever offline checks in"; the app says "You need signal to check in" at the button instead.
- **Screen stays on** during the selfie (Wake Lock, iOS 18.4+).
- **Share** (iOS share sheet) on a request or an announcement.
- Face ID sign-in: **later** (owner, 25 Sep).

## 6. How alpha.7 is proven
1. **Parity check**: a script measures Nadi at 402 pt against fixed numbers from the owner's iOS screenshots (group radius 26, gap 35, row 54/44, separator at the text, title 34, colours) — fails on > 1 pt or > 2 RGB units.
2. **The two reviews re-run** with the same checklist → the score must reach ≥ 90.
3. alpha.6's gates stay: audit (205 views), journeys (87 server + 10 screens), sheet crawler, a11y, coherence, visual.
4. **Real Safari**: once `sudo npx playwright install-deps webkit` is run (owner will do it after this plan) — the
   WebKit-only checks (date pills, switch, menus, safe areas, Dynamic Type) run in the real engine.

## 7. Recommendation for Q2 (coloured icon tiles) — example

Like iOS Settings: a small rounded tile in one colour with a white symbol. One colour per *kind*, reused
everywhere that kind appears (More, New request sheet, notifications, Needs you):

| Kind | Tile colour (iOS system) | Symbol |
|---|---|---|
| Time off | green #30D158 | palm tree / sun |
| Overtime | orange #FF9230 | clock |
| Expense | blue #0091FF | receipt |
| Shift change | indigo #6D7CFF | calendar with clock |
| Fix a day | teal #40C8E0 | calendar with check |
| Help | blue #0091FF | lifebuoy |
| SOPs | brown #B78A66 | book |
| Announcements | red #FF4245 | megaphone |
| Public holidays | red #FF4245 | calendar |

Evidence: Settings uses exactly this (owner's screenshot: orange Airplane, blue Wi-Fi, green Mobile Service);
colour carries the kind, the word carries the meaning (never colour alone — HIG Accessibility).

## 8. Order and size

| Phase | What | Steps |
|---|---|---|
| 0 | Live defects (§2) | 9 |
| 1 | The frame + colour (5.1, 5.2) | 10 |
| 2 | Home overhaul (§3) | 6 |
| 3 | Lists, forms, details (5.3–5.5) | 16 |
| 4 | Controls (5.6) | 4 |
| 5 | Announcements (§4) | 7 |
| 6 | Type, motion, native features (5.7) | 8 |
| 7 | Prove (§6) + release | 4 |
| | **Total** | **64** |

## 9. Owner decisions (from 25 Sep, and what is still open)

| Q | Answer / status |
|---|---|
| Q1 accent | **Yes** — keep lime as the one tint; only on the primary action, switches ON, the tab lens |
| Q2 coloured icon tiles | **Yes** (25 Sep) — set in §7 |
| Q3 Face ID sign-in | **Later** |
| Q4 real Safari | Owner will run `! sudo npx playwright install-deps webkit` after this plan |
| Q5 search | **Yes** — requests, people's names, SOPs, days |
| Q6 new | Announcement confirmation report in Desk — OK despite the 13 Sep report deferral? |
| Q7 new | Announcement images public-by-link — OK, or are some notices sensitive? |
| Q8 new | Home: required/urgent announcement above the Today card, routine news below it (research) — OK vs "announcement on top"? |

## 10. Owner answers, 25 Sep (second round) — and the calls made on them

**Q6 confirmation report: yes. Q7 public images: yes. Q8: yes, with the senior's ask folded in (below).**

### 10.1 Announcement fields in Desk (owner: "separate what shows in the preview and in the notification")
One field per job, so HR controls each place the notice appears:

| Field | Shown where | Rule |
|---|---|---|
| Title | Home card, list, notification title, full view | short; required |
| **Summary** (new) | the Home preview line **and** the push notification body | plain text, max 140 characters, required when published; no formatting (a notification cannot show any) |
| Body | only the full view | rich text + images (existing editor) |
| Cover image (new, optional) | small thumbnail on the Home card | one image |
| Must read | full-screen + "I have read this" | existing |
| Urgent (new) | sits above the Today card; no "Remind me later" | off by default |
| Notify on publish (new) | sends the push once when published | on by default |

Today the Home preview and the push are cut from the body HTML, so a picture or a heading can become the
preview. The Summary field removes that guesswork. HR sees all three places in "Preview as staff".

### 10.2 Carousel — decision: no
NN/g's carousel studies: people mostly see only the first slide, and auto-rotating carousels annoy users and hurt
accessibility (nngroup.com/articles/auto-forwarding, nngroup.com/articles/designing-effective-carousels).
Apple uses horizontal scrolling rows (App Store) for browsing catalogues, not for things people must read.
So: a **short vertical list** (up to 3, each title + summary + thumbnail) and "See all". Every notice is visible
without swiping.

### 10.3 Home order with the senior's goal ("make sure people read announcements")
Taken seriously, not blindly:
- **What actually makes people read is the must-read flow (§4.4), not the position.** A notice at the top of a
  page can still be skipped (NN/g banner blindness). Must-read notices open full screen and need "I have read
  this"; that is the guarantee.
- **The senior's placement is adopted where it does not slow the daily task:** the Announcements section sits
  **first, always in the same place** (consistent = same spot every day; persistent = the slot is there even
  on a quiet day, so people learn to glance at it).
- **The check-in card goes directly under it, still on the first screen with no scrolling.** Measured budget
  at iPhone height (874 pt): title about 100, announcements about 130 to 230, Today card about 220. This fits.
  Putting check-in at the very bottom of the page was rejected: it is the one daily action, done at a door,
  often in a hurry. Every workforce app studied keeps it on the first screen. Apple's iOS 26 guidance also
  rejects the other "bottom" option, a check-in bar docked above the tab bar: "Do not put screen-specific
  actions (like a checkout button) in the tab bar accessory" (WWDC25 356).
- **Quiet day:** the slot shrinks to one line, "No new announcements · See all". It is not an empty card.
  An empty card would take the top of the screen every day to say nothing.
- **Separation:** the Announcements group and the Today card are separate groups with the standard 35 pt gap
  and their own headers. That keeps them visually apart without extra lines or borders.

## 11. Safari engine results (WebKit 26.5, 25 Sep)

WebKit now runs locally without admin rights (`~/.local/webkit-deps/README.txt`); the audit and sheet crawler
accept `ENGINE=webkit` and present an iPhone user agent, so iOS-only code runs.

**Whole-app audit, 205 views, WebKit vs Chromium: identical on every measure** (sideways scroll 0, glass on content
0, text under 11 pt 0, tap targets under 44 pt 0, field looks, button heights, empty sections, jargon). The 5
"page errors" are the local site's live-update socket (port 9000 not running on the test bench), not the app.
**Sheets: 10/10 open and close in WebKit.** Time off: page 393 wide, no sideways scroll.

**Found only in Safari (added to phase 0):**

| # | Defect | Evidence | Fix |
|---|---|---|---|
| 0.10 | The iOS "Install Nadi" banner covers the bottom of every page for anyone using Nadi in Safari (not installed). White text on lime: **contrast 1.18** (WCAG needs 4.5) | `components/InstallPrompt.vue` (a frappe-ui Popover with Tailwind accent colours); measured on the WebKit screenshot | Replace with one small dismissible row at the top of Home only ("Add Nadi to your Home Screen" + Share symbol), our own tokens, shown once per 30 days; never over forms |
| 0.11 | **Body text and buttons render in Inter, not Apple's system font** on iPhone | frappe-ui's Tailwind plugin sets `html { font-family: InterVar, … }` ahead of our `-apple-system` stack (`node_modules/frappe-ui/src/tailwind/plugin.js:18`); measured in WebKit: html/body/tab labels = InterVar first | Override the html font family with our stack (system font first); stop shipping InterVar/Inter Tight/JetBrains Mono to Apple devices (plan 5.7) |

## 12. What alpha.7 shipped from §5.7, and what moved (25 Sep)

Shipped: Home Screen badge (unread count), screen stays on for the selfie, the
large title folding into the bar, system font on iPhone (0.11).

Moved, with the reason:
- **Dynamic Type** (follow the iPhone's Text Size): every font size is in px
  (34+ rules and the tokens). Following Text Size means moving them to rem, which
  changes every screen's baseline. It is its own release, measured screen by
  screen, not a tail item. → alpha.8.
- **Search** (owner Q5: yes): needs a ruling before it is built. Who may find
  whom by name? HR sees everyone (ruling, 23 Sep); should staff find people
  outside their team? A search box is a way round every fence if that is not
  decided first. → question for the owner, then alpha.8.
- **Tapping a notification opens that exact request**: already true for request
  notifications (the push carries the link); Declarative Web Push would need the
  push relay to change, which is not this app's code.
- **Apple's spring on push, sheets, tab lens**: a motion tuning pass; the current
  motion tokens are unchanged. → alpha.8.
- **Offline check-in**: not built, by the owner's rule ("never ever offline
  checks in").
