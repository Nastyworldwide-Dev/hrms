# Page 2 of 11 — Home

Status: **APPROVED 23 Sep 2026, not yet built.** Q1 → date as header title (recommended, accepted). Q2 → "Not approved" stays in Requests only; the Home row for it is REMOVED below.
Date: 23 Sep 2026.

Owner rulings this applies:
- Each page has its own purpose. **Requests and balances belong to Requests.**
- **No money or claim row on Home** (rejected 23 Sep).
- Approvals appear **only where they can be done**. Home points to them; More does not.
- Compact, no scrolling if possible, one tap away, nothing decorative.

---

## 1. The job of this page

> **"What is true right now, and what is waiting on me?"**

The page answers three questions:
- **Now:** am I on shift, and for how long?
- **Do:** check in or out.
- **Waiting on me:** only things **I** must act on, each one tap from done.

Everything else lives on its own page.

---

## 2. What ships today, and what is wrong with it

These were checked in the code, not guessed.

| # | Problem | Where | Kind |
|---|---|---|---|
| H1 | **The whole Requests panel sits on Home**: tabs, chips, lists. It repeats the Requests tab and pushes everything below the fold. | `Home.vue` renders `<RequestPanel />` | Repeat |
| H2 | **The date appears up to three times:** the header kicker, the eyebrow `WEDNESDAY, 23 SEPTEMBER 2026`, and the fallback date line. | `GAppHeader`, `CheckInPanel.vue` | Repeat |
| H3 | **The date is in ALL CAPS, with the year.** Capitals are harder to read, and dyslexia guidance says to avoid them. The year adds nothing. | `CheckInPanel.vue` eyebrow | Hard to read |
| H4 | **"Hey, Nabil 👋" at display size** takes ~50px, and it can't be acted on. | `CheckInPanel.vue` | Decoration |
| H5 | **The missing check-out shows in two places:** a big banner in the check-in block, and a row in Needs you. | `CheckInPanel` stale banner + `NeedsYou` | Repeat |
| H6 | **The check-in history link sits on Home**, and also on Calendar and Profile. | `CheckInPanel.vue` | Repeat |
| H7 | **The notification permission sheet opens by itself** a few seconds after Home loads. It interrupts the first thing people came to do. | `PushNotificationPrompt.vue`, `onMounted` + `setTimeout` | Interruption |
| H8 | **Mixed capitals on buttons:** "Check In", "Confirm Check In", but "Make a request" elsewhere | `CheckInPanel.vue:517-519` | Inconsistent |
| H9 | **Home says "check in"; mockup 4 says "clock in".** The Calendar sheet will show taps. One word must be picked. | several | Inconsistent |

---

## 3. The page (390 × 844 phone)

```
┌──────────────────────────────────────┐
│ Wed 23 Sep                  🔔  (NA) │  header: date is the title
├──────────────────────────────────────┤
│ ● Working · 3h 12m                   │  Now bar (kept)
│   Office · 09:00–18:00               │
│                                      │
│ [          Check out            →  ] │  the one big button
│                                      │
│ WAITING ON YOU                       │  only if something is
│ ┌──────────────────────────────────┐ │
│ │ ⚠ Mon 8 Sep: no check-out     ›  │ │  → that day in Calendar
│ │ ✓ 3 leave requests to decide  ›  │ │  → Approvals (approvers only)
│ │ 📄 Confirm: new leave policy   ›  │ │  → the announcement
│ └──────────────────────────────────┘ │
│   Show 2 more                        │  only if > 3
│                                      │
│ ANNOUNCEMENTS                        │  only if something is new
│ ┌──────────────────────────────────┐ │
│ │ Raya holiday dates confirmed New │ │
│ │ Offices close 20–22 Mar · HR     │ │  one-line preview
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
│  Home  Calendar  Requests  Score  More│
```

**Height budget** (all blocks at their maximum: 3 waiting rows + 2 announcements):

| | Space available | Page height | Fits? |
|---|---|---|---|
| 390×844 | ~640px | ~520px | ✅ fits, no scroll |
| 360×640 | ~440px | ~520px max, ~300px on a normal day | ✅ on a normal day. On a busy day the announcements fall below the fold. |

On a quiet day the page is just the Now bar + one button. **That is correct:** nothing is waiting.

### Each element: why it is there, and its source

| Element | Why | Basis |
|---|---|---|
| **Date as the header title** (`Wed 23 Sep`) | Said once, in the place the eye starts. It replaces the brand word "Nadi", which tells you nothing. | Fixes H2/H3; Nielsen 8, *minimalist design* |
| **Now bar** | *Am I on shift, and for how long?* Always visible, so the button below is a decision, not a guess. | M4 `On shift · 7h 12m today · shift ends 18:00`; Nielsen 1, *visibility of system status* |
| **One big button** (Check in / Check out) | The action people open the app for, within thumb reach | M4 + P both lead with it; Fitts's law (big and near is fast) |
| **Waiting on you**, max 3 + "Show n more" | Only things **the reader** must do. Each row opens **the place where it gets done**, already filtered. | M4 *"Home keeps one line: what is waiting on the reader"*; P flow map *"Needs you rows → Approve request"* |
| **Announcements**, only unread / to confirm, max 2 | Something HR wants read *now*. Once read, it lives on the Announcements page, not here. | M4 home block; 23 Sep owner ruling on announcements |

### What counts as "waiting on you" (the full list)

Every row is **an action only the reader can take**.

| Row | Who sees it | Opens | Source |
|---|---|---|---|
| `Mon 8 Sep: no check-out` | anyone with a lone check-in | the **Calendar day sheet** for 8 Sep ("Tell us when you left") | M4 *"Waiting on you: Monday 8 September, clocked in, never clocked out"* |
| `3 leave requests to decide` (one row per type) | approvers only, **decided by the server** | **Approvals**, filtered to that type | M4 "Waiting for you"; owner ruling 2 |
| `2 check-ins outside the area` | approvers only | Approvals, filtered | M4 |
| `Confirm: {policy title}` | people in the audience who haven't confirmed | the announcement | owner ruling (acknowledgements) |
| `HR replied: {ticket subject}` | ticket owner, when the reply is the last word | the ticket | M4 Help *"HR replied yesterday"* |

**Not on Home (by ruling or by rule):**
- Overtime to claim → the Calendar dot + Requests (owner, 23 Sep)
- Balances, money owed → Requests
- Your own requests that are waiting on *someone else* → Requests. **You can't act on them.**
- "Coming up at work" (both designs have it) → cut. Nothing to do. Events are announcements and show on their calendar day.
- Greeting → cut (H4)

---

## 4. Check-in sheet (opened by the big button)

The sheet is needed: the selfie and the location check must be seen before sending.

```
┌──────────────────────────────────────┐
│ Check out                            │  title = the action
│ 06:12 pm                             │  time that will be recorded
│ ✓ Inside the KL office area          │  location verdict (kept)
│ ┌──────────────────────────────────┐ │
│ │          camera preview          │ │
│ └──────────────────────────────────┘ │
│ [        Confirm check out       ✓ ] │
└──────────────────────────────────────┘
```

| Change | Why |
|---|---|
| **Cut the date line** in the sheet. It is today; the header says so. | Repeat |
| **Sentence case**: `Check in`, `Check out`, `Confirm check out` | One style app-wide (H8). Material 3 and GOV.UK use sentence case. It is easier to read for dyslexic readers (BDA style guide). |
| Kept: the time, the location verdict, the camera, **one** button | Each is needed to decide. None is decoration. |
| The sheet follows the **new sheet rule** (`00-sheets-and-transitions.md`): leaving the page closes it, and back closes it first | Fixes the stuck-sheet class here too |

---

## 5. Notification permission (H7)

- **Never on load.** Ask **once**, in context: right after the **first successful check-in**, as a small inline card, not a sheet:
  > `Get told when your requests are decided?  [Turn on]  [Not now]`
- "Not now" is remembered. The same choice lives in You → Settings.

**Basis:** web.dev *Permission UX* (ask in context, after a user gesture) and Chrome's quiet-prompt policy. Browsers now **block** prompts that are requested on load and denied often.

---

## 6. Words (sentence case; cut-off checked at 320px, text at 200%)

| String | Worst case | Fits |
|---|---|---|
| Header title | `Wed 30 Sep` | ✅ fixed length, no name. That is why it replaces the greeting (a long name would cut off beside the bell and avatar). |
| Now bar | `Working · 11h 59m` / `Office · 09:00–18:00` | ✅. The shift name wraps, never cuts. |
| Waiting row | `Confirm: {a long policy title}` | wraps to 2 lines, allowed; never "…" |
| Button | `Confirm check out` | ✅ |

**One word everywhere: "check in / check out".** It is what ERPNext, HR and the current app say. Mockup 4's "clock in" is changed to match. The Calendar sheet shows `In 09:31` / `Out 20:04`.

---

## 7. Backend needed

| # | Change | File | Size |
|---|---|---|---|
| B1 | `needs_you` adds: **lone check-in day**, **policy to confirm**, **HR replied**. Each row carries its route and filter. | `hrms/api/home.py` (the existing `needs_you`) | small–medium |
| B2 | Announcements on Home: **unread or to-confirm only**, max 2, with a one-line preview | `hrms/api/announcements.py` | small |

Both are **decided by the server** (the existing pattern). The screen holds no role logic.

---

## 8. Proof

| Check | Test |
|---|---|
| Home has no RequestPanel, no greeting, date once | Component test |
| Each waiting kind appears only for the right person | Python test per kind, on `needs_you` |
| Each row opens the right place, pre-filtered | Component test on the routes |
| Push prompt never on load; shown after first check-in; "Not now" remembered | Component test |
| Fits 390×844 with 3 rows + 2 announcements | Playwright: no scroll |
| No "…" on any Home string at 320px / 200% | Playwright shot + ellipsis gate |

Slices (one commit each, tests with their code):
1. Cuts: RequestPanel, greeting, date repeats, history link
2. Header date + sentence case
3. `needs_you` kinds (server) + rows (lone check-in, policy to confirm, HR replied)
4. Home announcements (unread only, preview)
5. Push prompt in context

---

## 9. Questions for the owner

1. **Date as the header title instead of "Nadi" + greeting.** OK? The avatar already says who you are.
2. **"Not approved" on Home for 7 days, until opened.** OK, or leave it only in Requests?
