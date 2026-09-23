# Page 1 of 11 — Calendar

Status: **APPROVED 23 Sep 2026, not yet built.**
Date: 23 Sep 2026.
This file replaces rows C1–C12 in `../NADI_2.0_PAGES_2026-09-23.md`.

Owner rulings this applies (23 Sep):
- Claims **belong to Requests**. The Calendar **shows** which days hold claimable overtime, and the claim can be sent **from inside the day**.
- Approvals appear **only where they can be done**, never in More.
- No payslips yet.
- No repeated action. No repeated information. No text that adds load.

---

## 1. The job of this page

> **"What happened on my days, and which day needs me?"**

The page does three things:
- **Look:** the month, at a glance.
- **Spot:** which days need a fix, and which days hold overtime to claim.
- **Act:** tap the day and do the one thing it needs.

Anything else lives somewhere else.

---

## 2. What ships today, and what is wrong with it

These were checked in the code, not guessed.

| # | Problem | Where | Kind |
|---|---|---|---|
| D1 | **Absent days look like blank days.** The legend has an "Absent" swatch, but no day style exists for it. | `glass-components.css`: no `.g-cal__day--absent` | **Defect** |
| D2 | **"Pre-filled with the date" is false.** The day sheet sends `?date=`, but neither form reads it. People re-pick the date. | `DaySheet.vue` `fixDay()` / `claimOt()`; no `route.query.date` in any form | **Defect** |
| D3 | **The dots have no legend.** Leave, holiday, event and needs-you dots are drawn, but the legend explains only the fills. You can't read what a dot means. | `GCalendar.vue` legend only lists `state` | **Defect** (WCAG 1.4.1) |
| D4 | **Leave and holiday are drawn twice:** once as the fill, again as a dot. | `calendar.py` `FLAG_ORDER` + `STATE` map | Repeat |
| D5 | **One orange dot means three things:** worked but not counted, overtime not claimed, and waiting on someone. You can't tell which. | `_needs_you_days()` | Unclear |
| D6 | **Today is not marked.** | `AttendanceCalendar.vue` | Missing |
| D7 | **The 4-number strip** (Present 13 · Half 1 …) counts what the grid already shows. It leads to no action. | `GStatPanel` | Repeat |
| D8 | **The overtime card** repeats the Requests strip. | `Dashboard.vue` | Repeat |
| D9 | **3 "start a request" rows** repeat Requests' "New request". | `Dashboard.vue` | Repeat |
| D10 | **The day sheet always offers "Request a fix"**, even on a perfect day. | `DaySheet.vue` | Wrong action |
| D11 | **Hours shown as "8.03 h".** People read time as 8h 02m. | `DaySheet.vue` `toFixed(2)` | Hard to read |
| D12 | **Tap rows say the raw "IN" / "OUT"** from the database. | `punchTime()` | Jargon |
| D13 | **Overtime claim needs a written reason** (HR asked for it). So "claim in one tap" must still ask for the reason. | `OTRequestForm.vue:279` | Constraint |

---

## 3. The page (390 × 844 phone)

```
┌──────────────────────────────────────┐
│ Calendar                             │  header
├──────────────────────────────────────┤
│ ┌──────────────────────────────────┐ │
│ │ September 2026          ‹   ›    │ │  month + steppers
│ │  S   M   T   W   T   F   S       │ │
│ │          1   2   3   4   5       │ │  fill = what the day WAS
│ │  6   7  (8)  9  10  11  12       │ │  (8) = today ring
│ │ 13  14  15  16  17  18  19       │ │  •  = something to do
│ │ ...                              │ │
│ │ ■ Worked  ■ Leave  ■ Rest day    │ │  legend: only what occurs
│ │ ■ Absent  ● Overtime  ● Fix      │ │  this month
│ └──────────────────────────────────┘ │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ ● 2 days need a fix           ›  │ │  only when > 0
│ │ ● 3h 30m overtime to claim    ›  │ │  only when > 0
│ └──────────────────────────────────┘ │
│                                      │
│   All check-ins ›      Your shifts › │  two quiet links, one row
└──────────────────────────────────────┘
│  Home  Calendar  Requests  Score  More│  tab bar
```

**Height budget:**

| | Space available | Page height | Fits? |
|---|---|---|---|
| 390×844 | ~640px | ~500px | ✅ fits, no scroll |
| 360×640 | ~440px | ~470px | ❌ scrolls ~30px on 6-week months |

At 360×640 the grid (the job) stays fully visible. Only the links row falls below.

### Each element: why it is there, and its source

| Element | Why it stays | Basis |
|---|---|---|
| Month grid, fill per day | The job itself | P flow map: *"Calendar shows the month at a glance"* |
| Today ring | Where am I? | Nielsen heuristic 1, *visibility of system status* |
| **Two** dot kinds only: **Overtime** (brand) and **Fix** (warn) | They mark the only days you can act on. Every other state is already the fill. | Owner: *"tell people that day they have claimable OT"*; fixes D4, D5 |
| Legend shows only what occurs this month | 8 keys when 3 apply is load with no use | Hick's law (more choices, slower decisions); Nielsen 8, *minimalist design* |
| Action rows, only when > 0, **tapping one opens the first such day** | The number is a door (rule 3). It leads to the day, not to a list. | M4 openDay; Nielsen 7, *efficiency* |
| "All check-ins" · "Your shifts" as one quiet text row | Rarely used, still one tap away. They carry no count, so they stay quiet. | NN/g progressive disclosure |

### Removed, and where each thing goes now

| Removed | Where it went |
|---|---|
| Overtime card at the top | The dot + the action row + the day sheet. The claim list lives in **Requests**. |
| Present / Half / Absent / Leave count strip | Nowhere. The grid already shows it (D7). |
| Request Attendance / Claim Overtime / Request a Shift | The day sheet (with the date filled in), and Requests "＋ New request" |
| "Your shifts" as a big row | The quiet link |

### The legend: final words

Each word was checked to fit at 12px in 262px (the card's inside width at 320px). The legend wraps; nothing gets cut off.

| Mark | Word | Meaning |
|---|---|---|
| solid brand fill | **Worked** | Present, or work from home |
| half fill + outline | **Half day** | Half day |
| leave tint | **Leave** | Approved leave |
| quiet fill | **Rest day** | Weekly off **or** public holiday. The sheet names the holiday. |
| danger tint *(new, D1)* | **Absent** | Marked absent |
| brand dot | **Overtime** | Overtime you can still claim |
| warn dot | **Fix** | Worked but not counted, or no clock-out |
| ring | *(no key)* | Today. Understood without one (iOS and Google Calendar do the same). |

Two dots can show on one tile. The order is fixed: **Fix, then Overtime**. A person learns the position.

Every tile's spoken label names the fill and the dots. For example: *"2 September, worked, overtime to claim"*.

Company events no longer get a dot. They are announcements, and they show inside the day sheet. **One place.**

---

## 4. The day sheet: tap a day

This is the owner's open question, answered in full.

### Rules

1. **Heading = date + one status word.** Example: `Wednesday 2 September · Worked`.
2. **One line of shift:** `Office · 09:00–18:00`, or `Rest day`, or `Public holiday · Merdeka`.
3. **The taps, as a timeline:** `In 09:31` → `Out 20:04`. The words are *In* / *Out*, never *IN* / *OUT*.
4. **Hours in time, not decimals:** `8h 02m worked · 1h 30m overtime`.
5. **Exactly ONE main button, chosen by the day.** Or none, with one line saying there is nothing to do.
6. **Manager lines at the bottom**, only if the server sends them.
7. **Nothing else.** No explaining paragraph.

Basis: M4 `openDay()` (*"exactly one action, chosen by what the day needs"*). Apple HIG, *Sheets*: a sheet serves one focused task. The main button sits at the bottom, where the thumb rests (Hoober's thumb-zone research).

### Every kind of day, and what its sheet shows

| # | Kind of day | Status word | Main action | The line under it |
|---|---|---|---|---|
| 1 | Worked, no overtime | **Worked** | none | *Nothing to do.* |
| 2 | Worked, overtime **not yet claimed** | **Worked** | **Claim 1h 30m** | *Paid as overtime* or *Taken as time off*, from the employee's setting |
| 3 | Overtime **claimed, waiting** | **Worked** | none | *Claim waiting with Hafiz* ›, which opens that request in Requests |
| 4 | Overtime **claim approved** | **Worked** | none | *Claim approved* › |
| 5 | Overtime **claim not approved** | **Worked** | none | *Claim not approved: {reason}* › |
| 6 | Clocked in, **no clock-out** | **Needs a fix** | **Tell us when you left** | *Without it we can't count this day.* |
| 7 | Worked, **not counted yet** (today or tonight's run) | **Today** / **Not counted yet** | none | *Counted overnight.* |
| 8 | Work day, **no taps**, marked absent | **Absent** | **Fix this day** | none |
| 9 | Leave, approved | **Leave** | none | *Annual leave · approved by Hafiz* |
| 10 | Leave, **waiting** | **Leave, waiting** | none | *With Hafiz since Monday* › |
| 11 | Rest day or holiday, **not worked** | **Rest day** | none | holiday name, if there is one |
| 12 | Rest day or holiday, **worked** | **Worked a rest day** | **Claim …**, same as #2 | as #2 |
| 13 | **Future** work day | **Coming up** | **Ask for this day off** | the shift line |
| 14 | A tap **set aside by HR** | *(as the day)* | *(as the day)* | that tap row says *Set aside by HR* |

**Just one quiet text link, only on past work days that have no main action (rows 1, 3–5, 9):**
*"Something wrong with this day?"* opens the same fix form, with the date filled in.

**Why:** a day can look right and still be wrong (a mistimed tap). This keeps the way out without competing with a main button. Nielsen 3, *user control and freedom*.

### Claiming inside the day (#2, #12)

The owner asked for it. HR's rule that a reason is required (D13) stays.

```
┌──────────────────────────────────────┐
│ Wednesday 2 September · Worked       │
│ Office · 09:00–18:00                 │
│  ● In 09:31                          │
│  ● Out 20:04                         │
│ 8h 02m worked · 1h 30m overtime      │
│ ──────────────────────────────────── │
│ Why did you stay?                    │  one field, required
│ [ Stock count after close          ] │
│                                      │
│ [        Claim 1h 30m              ] │  main button
│ Paid as overtime · goes to Hafiz     │
└──────────────────────────────────────┘
```

- The hours come from the **same capacity engine** the form and the save use (`get_ot_claim_capacity`). The sheet can never offer more than the form accepts.
- Sending **creates the same OT Request.** It shows up in **Requests** as *Waiting · with Hafiz*. The claim belongs to Requests; the Calendar is only the door.
- The day sheet then changes to row #3. **No page change.**
- The full form (to claim fewer hours, or to add a file) stays one tap away: *Change hours* ›.

Basis: owner ruling 1; NN/g *inline editing* (short, single-field tasks are completed faster in place). The **claim-all list** is not here. It is in Requests.

### Team line (managers and team leads; AMENDED 23 Sep: see AUDIT-PLAN.md "Team line")

Superseded by the owner's ruling 1: one compressed line for **direct reports**, per past / today / future day. Tap → Team page for that date. The text below is the old version, kept for history.

#### (old) Manager lines

```
Your team: 4 of 6 in · 1 on leave · 1 not marked   ›
```

- One line, not a 4-cell grid.
- Tapping opens the names: name + **leave type**, **never the reason** (owner ruling, kept).

---

## 5. Words: one check for cut-off text

Every string on the page and in the sheet was measured at **320px width, text at 200%** (WCAG 1.4.4 and 1.4.10). Long strings **wrap**, they never **truncate** (no `…` on any label).

| String | Longest case | Fits at 320px, 100% |
|---|---|---|
| Sheet heading | `Wednesday 30 September · Worked a rest day` | wraps to 2 lines, allowed |
| Main button | `Tell us when you left` | ✅ one line |
| Action row | `3h 30m overtime to claim` | ✅ |
| Legend words | `Rest day` (longest) | ✅ |
| Tab label | `CALENDAR` (from earlier work) | ✅ 50.7px in 57.6px |

A test will lock this: no `text-overflow: ellipsis` and no `truncate` class on any Calendar string.

---

## 6. Backend needed (small; all on data that already exists)

| # | Change | File | Size |
|---|---|---|---|
| B1 | Split `needs_you` into **`fix`** and **`overtime`** flags. Drop the `leave` and `holiday` dots. | `hrms/api/calendar.py` | small |
| B2 | Day sheet returns **`claim`**: `{state: none/claimable/waiting/approved/rejected, hours, compensation, approver_name, reason, request}` | `hrms/api/calendar.py` `_my_day` | small |
| B3 | Day sheet returns the **holiday name**, **pending leave**, **lone clock-in** and the **day kind** (#1–#14), so the screen does not decide | `hrms/api/calendar.py` | medium |
| B4 | Inline claim: reuse the **existing** OT Request save path. No new endpoint unless the existing one can't take `{date, hours, explanation}`. | `hrms/api/__init__.py` | small |
| B5 | Both forms **read `?date=`** (fixes D2) | `OTRequestForm.vue`, `AttendanceRequestForm.vue` | small |

The **day kind is decided by the server** (the same pattern as the Now bar). The screen holds no attendance rules.

**Not doing:**
- The **place name** on a tap: the check-in stores coordinates, not a place. *Add when a site name is stored on the check-in.*
- Showing **"Paid"**: no reliable field says an OT Request was paid in payroll. *Add when payroll marks it.* Saying "paid" without that would be a guess.

---

## 7. How it will be proven

| Check | Evidence |
|---|---|
| Each of the 14 day kinds | Python test per kind on `get_day` (real doctype, stubbed DB), plus a probe on `spoke.localhost` with synthetic rows that are deleted afterwards |
| One main button per kind | Component test: every kind renders **≤ 1** main button |
| Legend = only states that occur | Unit test |
| Absent is styled (D1) | Contrast gate: new token pair measured ≥ 4.5:1 text, ≥ 3:1 dot |
| Date filled in (D2) | Form test: `?date=2026-09-02` → field set |
| No cut-off text | Gate: no ellipsis in Calendar; 320px + 200% Playwright shot |
| No scroll at 390×844 | Playwright: `scrollHeight ≤ clientHeight` |
| Inline claim = same OT Request as the form | Test: sheet and form produce identical docs for the same day |

Slices (one commit each, tests with their code):
1. D1 + today ring
2. B1 flags + legend
3. B2/B3 day kinds (server)
4. Day sheet rebuilt on day kinds
5. Inline claim (B4)
6. Date fill-in (B5)
7. Page cuts (D7–D9) + action rows

---

## 8. Questions for the owner

1. **Word for overtime.** The app and forms say **"Overtime"**; mockup 4 says **"Extra hours"**. The plan uses **Overtime** everywhere, because HR, payroll and the forms already say it. OK?
2. **Rest day and public holiday: one colour** (the sheet names the holiday), or two? The plan says **one**, which means one fewer legend key.
