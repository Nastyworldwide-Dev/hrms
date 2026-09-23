# Nadi 2.0 — what each page is for, and what belongs on it

23 September 2026. Written from two sources, read screen by screen:

- **P** = the prototype, `Nadi PWA UI UX 2.0/nadi-prototype.html` (36 screens, plus its own flow map)
- **M4** = mockup 4, `Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html` (11 screens, 5 sheets)

Home is covered separately. This file covers every other page.

Tags on each change:

- ✅ **have the data**: frontend work only
- 🔧 **small backend**: an endpoint or field on data that already exists
- 🆕 **new data**: needs a doctype or a source that does not exist yet

---

## The rules every page follows

These come from the owner's brief and from the flow map in P. They apply to every page below.

1. **One page, one job.** A number lives on ONE page. M4 says it plainly: *"A second copy of a number does not inform, it asks which copy is right."*
2. **Requests owns everything about requests,** including what the person HAS: balances, money owed, drafts.
3. **Every number is a door.** Tapping it opens the thing it counts, already filtered.
4. **One primary action per card or sheet,** chosen by what that item needs right now (M4's day sheet rule).
5. **Fits one phone screen (390×844) where possible.** The rest sits one tap away: a segment, a sheet or a row.
6. **No explaining paragraphs on the page.** Empty states are ONE line, never a dashed box (P's flow map). Rules like OT rounding sit behind an ⓘ tap.
7. **Fixed status words everywhere:** Draft · Waiting · Approved · Not approved · Withdrawn.

### Duplicates that exist today and must go

| Number | Today it sits on | It belongs on |
|---|---|---|
| Overtime to claim | Calendar card **and** Requests strip | **Calendar → Extra hours** (it is day evidence; M4) |
| Days with no attendance | Calendar dots **and** Requests strip | **Calendar** (it is a day problem) |
| Leave balances | Requests strip **and** Leaves dashboard | **Requests**; tapping a card opens the breakdown |
| Team requests | Requests tab **and** Remote Approvals | **Approvals** (its own screen) |

---

## CALENDAR — the most important page

**Job:** *"What happened on each of my days, and what do I need to fix or claim?"*

### Today

OT card at the top → month grid with dots → 5-state legend → 4-number strip (Present / Half / Absent / Leave) → 3 request rows → 2 link rows. **It scrolls.** The day sheet shows 4 fact cells and a timeline of taps, and **always** shows "Request a fix" even on a good day.

### What P and M4 say

- **M4:** three segments at the top: **Month · Extra hours · Roster**.
- **M4 day sheet:** status word, shift line, tap timeline, hours counted, and **exactly one action**, chosen by the day: *Tell us when you left* / *Claim 1h* / *Paid in last payroll* / *Nothing to do*.
- **P:** the calendar is the month at a glance; requests are NOT listed here.

### Changes

| # | Change | Why | Tag |
|---|---|---|---|
| C1 | Add segments **Month · Extra hours · Roster** | Three jobs, one screen, zero scroll | ✅ |
| C2 | **Month** = grid + legend only. Plus one line when needed: *"2 days need a fix ›"* | Only the actionable number | ✅ |
| C3 | **Cut** the 4-number strip (Present 13…) | Counting good days leads to no action | ✅ |
| C4 | **Cut** the 3 request rows | They live on the day sheet (pre-filled) and on Requests | ✅ |
| C5 | **Cut** the 2 link rows; check-in history moves behind the day sheet | One tap away already | ✅ |
| C6 | Legend shows **only the states that occur this month** | M4 draws 8, and 3 of them we have no data for | ✅ |
| C7 | Day sheet: **exactly one action** chosen by the day | M4's core rule; today it always offers "fix" | ✅ |
| C8 | Day sheet: taps as a timeline with the place (*"Clocked in 09:31 · KL office"*) | Evidence before the number | 🔧 place name |
| C9 | **Extra hours** tab: total ready to claim + *Claim all* + two groups: **Ready** / **Not yet** (with reason: no clock-out, already paid) | Moves the OT card here; groups by what you can do | ✅ |
| C10 | OT rounding rule behind ⓘ, not on the page | Rule 6 | ✅ |
| C11 | **Roster** tab: your next 7 shifts + *Ask to change a shift* | M4 | ✅ |
| C12 | Roster tab, managers only: *who is on this week*, gaps flagged (*"No closer Sunday ›"*) | M4; server decides who sees it | 🔧 |

**Where M4 is wrong, and we do better:**

- Its explaining card *"What a day tap shows you"*: text that is useless after the first visit. **Cut.**
- Its 8-state legend lists states with no data behind them. **Show only what occurs.**
- Its Extra hours tab and Home both carry the claim total. **Calendar only.**

---

## REQUESTS

**Job:** *"What have I asked for, where is it, and what do I have left?"*

### Today

Balance strip (4 cards + "show more") → 3 counter rows (OT, unpaid money, unmarked days) → **6 big tiles** "Start a request" → list with My / Team / History tabs, filter chips, Waiting / Finished split. **It scrolls far.** The 6 tiles push the list below the fold.

### What P and M4 say

- **P:** big headline balance *"19 of 22 annual days left"* + small others (*Medical 18 · Hosp 60*); money in progress; assets; issues; trips. **One "＋ New request" button** opens a type sheet. P's flow map: *"One New request sheet routes to the right form with the type preset."*
- **M4:** *Make a request* button → chips → **Waiting on someone** / **Finished** → **Your balances** (given · taken · left).
- **P tap-through:** balance card → breakdown: *Entitlement 20 · Carried 4 · Lapsed −2 · Taken −3 · Available 19* → *Apply for annual leave*.

### Changes

| # | Change | Why | Tag |
|---|---|---|---|
| R1 | **Replace the 6 tiles with one "＋ New request" button** → a sheet listing the types | Both P and M4; gives the list its space back | ✅ |
| R2 | Balances: **one headline** (annual: *7.5 of 12 left*) + a one-line row of the others | P; 4 cards took a third of the screen | ✅ |
| R3 | Tap a balance → **breakdown sheet** (given, carried, lapsed, taken, left) + *Apply* pre-filled | P; the detail one tap away | 🔧 carried/lapsed |
| R4 | **Move out** the OT and unmarked-days rows → Calendar | Rules 1 & 2; they are day facts | ✅ |
| R5 | **Keep** money: *RM 248 approved, not paid* | Nothing else shows it | ✅ |
| R6 | **Move out** the Team and History tabs → Approvals | Requests = mine; deciding is another job | ✅ |
| R7 | Keep chips, the Waiting / Finished split, and *"with Hafiz · 2 days ago"* | Already done; matches M4 | ✅ |
| R8 | Show **Draft / not sent yet** as its own state | M4 | ✅ |
| R9 | *"Not approved"* rows show the reason inline | M4: *"Not approved — kitchen already short"* | ✅ |
| R10 | The Leaves and Expenses dashboards **fold into here** (and leave More) | Rule 2 | ✅ |

**Where M4 is wrong:** it puts balances at the BOTTOM, below the list. The balance is what you check **before** asking, so it goes first (P has it right).

---

## SCORE

**Job:** *"How am I doing this period, and is anything wrong?"*

### Today

Two dropdowns (Year, Cycle) at the top → either the full detail or a banner saying who scores you. CEO and HR get a team tab (fenced by the server).

### What P and M4 say

- **M4:** period + *still open* → one score + last published grade → **What makes it up** (3 weighted parts) → **Your goals** with a verdict word (*Met / Below / Open*) → *A figure here looks wrong* → one line on when grades are published.
- **P:** the same, plus *Report an issue with a figure* and *Open the full dashboard*.

### Changes

| # | Change | Why | Tag |
|---|---|---|---|
| S1 | **Move the dropdowns behind one row**: *"Other periods ›"* | Rarely used; P and M4 have none on the page | ✅ |
| S2 | Head: period + state (*"Jul–Sep · still open"*) + **one** number + last grade | M4 | ✅ |
| S3 | **What makes it up**: 3 rows, weight and score each | M4 / P; exists in the KRA data | ✅ |
| S4 | **Your goals**: each with actual vs target and **one word**: Met / Below / Open | M4; the actionable part | 🔧 goals payload |
| S5 | **"A figure looks wrong"** → opens an Ask-HR ticket pre-filled with the period | P and M4; turns a complaint into an action | ✅ |
| S6 | Publish rule behind ⓘ | Rule 6 | ✅ |
| S7 | Team tab stays **exactly as fenced** | The protected boundary | — |

**Where M4 is wrong:** it shows *4.2 / 5* **and** *84%*, two numbers for one fact. **Show one.**

---

## APPROVALS — a page of its own (today it is not)

**Job:** *"What is waiting for my decision, and can I decide it here?"*

### Today

Only remote check-ins have a screen. Leave, expense, OT and shift approvals hide in a Requests tab. Home's *Needs you* counts them all but opens different places.

### What P and M4 say

- **M4 "Waiting for you":** one list, every type. Each card carries what the decision needs: *7.5 days left after this* · the reason in quotes · **cover conflict** (*"2 others in Service already off Monday"*) · **Approve / Not approve in place**. Bulk: *"Approve the 3 with no conflicts."* Out-of-area clock-ins grouped in one row.
- **P:** the same, plus *Decided by you*.

### Changes

| # | Change | Why | Tag |
|---|---|---|---|
| A1 | One Approvals page: **Waiting (n) · Decided by you** | M4 and P | 🔧 list endpoint (needs_you gives counts, not rows) |
| A2 | Decide **in place** from the card; *Not approve* asks for a reason | M4 | ✅ decide() exists |
| A3 | Each card shows the context the decision needs: days left after, reason, cover conflict | M4 | 🔧 cover |
| A4 | *Approve the n with no conflicts* | M4; safer than P's "approve all" | 🔧 |
| A5 | Remote check-ins become one type in this list | One queue | ✅ |
| A6 | Reached from Home's *Needs you* and from More, **only for approvers** | Server decides | ✅ |

---

## MORE

**Job:** *"Everything I use now and then."*

### Today

Leaves · Expenses · Helpdesk · SOPs · Announcements · (Team if you have one) · Apps.

### What P and M4 say

**M4:** Announcements *(1 new)* · Help *(Ask HR or IT)* · Your team · Payslips · Public holidays · Things you hold · Training · How we work *(2 to read)* · You and settings.

### Changes

| # | Change | Why | Tag |
|---|---|---|---|
| M1 | **Remove** Leaves and Expenses | They are Requests now (R10) | ✅ |
| M2 | Every row carries its count when there is one: *1 new*, *2 to read*, *1 reply* | Rule 3 | ✅ |
| M3 | Add **Public holidays** (next one + long weekends) | P and M4; the holiday list exists | ✅ |
| M4 | Add **Approvals** for approvers | A6 | ✅ |
| M5 | Add **Payslips** | P and M4 both have it | 🔧 Salary Slip is in ERPNext |
| M6 | Add **Things you hold** (assets) | P and M4 | 🆕 check if Asset is used |
| M7 | Add **Training** and certificates | P and M4 | 🆕 |

---

## PROFILE ("You")

**Job:** *"Who am I in the system, and my settings."*

### Today

Four groups: You · Work · App · Account. Details sit behind three sheets.

### What M4 says

Name · department · location · **"Your manager is Hafiz Omar"** · **Your shift pattern** (*Office 09:00–18:00, Mon–Fri · Rest Sat and Sun*) · Settings (notifications, password, sign out).

### Changes

| # | Change | Why | Tag |
|---|---|---|---|
| U1 | Show **manager** and **shift pattern** on the page, no tap | M4; the two facts people come here for | ✅ |
| U2 | Detail sheets stay one tap away | Already done | — |
| U3 | **Move out** Remote Approvals → Approvals | A5 | ✅ |
| U4 | Keep the version line (*About this app*) | Every phone bug starts with "which version" | — |

---

## HELPDESK ("Help")

**Job:** *"Ask HR or report an IT problem, and see the answer."*

### Today

Two pills with your open count. Lists under each.

### What M4 says

Segments **Ask HR · IT support**. Each row: subject + *"HR replied yesterday"* or *"sorted on 5 Sep"* + state. One button per side: *Ask HR something* / *Report a problem*. One line: *IT tickets are seen by the IS team only.*

### Changes

| # | Change | Why | Tag |
|---|---|---|---|
| H1 | Row says **who spoke last and when** (*"HR replied yesterday"*) | M4; *replied* means it is your turn | 🔧 |
| H2 | Sort by **last reply**, not by date opened | The live one on top | ✅ |
| H3 | One primary button per side | M4 | ✅ |
| H4 | *Replied* shows as **Your turn** | Rule 7; says what to do | ✅ |

---

## ANNOUNCEMENTS

**Job:** *"What HR wants me to know."*

| # | Change | Why | Tag |
|---|---|---|---|
| N1 | Row shows a **one-line preview** + *"HR · yesterday"* | M4; a title alone is a headline | 🔧 add preview and author to the list |
| N2 | Policy needing confirmation stays pinned with its button | Already done | — |

---

## NOTIFICATIONS

**Job:** *"The record of what happened."* (M4: *anything you must act on lives on Home*.)

| # | Change | Why | Tag |
|---|---|---|---|
| T1 | Each line says the **result**: *"Hafiz approved your day fix · 8 Sep now counts 9h 23m"* | M4 | 🔧 message text |
| T2 | Tap opens the thing | Already fixed on 7 Sep | — |
| T3 | Grouped by day, *Mark all read* | P | ✅ |

---

## SOPs ("How we work")

| # | Change | Why | Tag |
|---|---|---|---|
| O1 | Chip **Needs reading** first, then by department | P | 🆕 read tracking (can reuse the announcement pattern) |
| O2 | Count on the More row: *2 to read* | M4 | 🆕 same |

---

## TEAM (managers only)

**Job:** *"Who is in, who is off, where are the gaps."*

| # | Change | Why | Tag |
|---|---|---|---|
| E1 | **Today**: in · off · late · not in yet, one line each | P | ✅ |
| E2 | **Roster week**: days short of cover flagged | P and M4 | 🔧 cover rule per outlet |
| E3 | The Calendar Roster tab links here for managers, and does not repeat it | Rule 1 | ✅ |

---

## Suggested order

By **visible change per effort**, and all ✅ first:

1. **Calendar**: C1–C7, C9–C11 (segments, one-action day sheet, OT moves in, cuts)
2. **Requests**: R1, R2, R4, R6, R8–R10 (one button, compact balances, moves)
3. **Score**: S1–S3, S5–S6
4. **More / Profile**: M1–M4, U1, U3
5. Then the 🔧 items: Approvals page (A1–A6), balance breakdown (R3), goals (S4), helpdesk last-reply (H1), announcement preview (N1), payslips (M5)
6. 🆕 items need a ruling first: assets, training, SOP read tracking

---

## Rulings needed from the owner

1. **Overtime claim: Calendar or Requests?** M4 puts it in Calendar (it is day evidence). The brief says request things go in Requests. **Recommendation: Calendar**, because you claim it from the day. Requests still lists the claim once it is filed.
2. **Approvals as its own page, reached from Home and More.** Recommendation: yes. P wanted it as a tab; the bar is full.
3. **Payslips.** Salary Slip exists in ERPNext. Show them in the app?
