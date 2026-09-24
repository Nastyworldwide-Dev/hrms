# Review B — forms, details, profile, sheets vs iOS 26 (alpha.6 build + owner's live screenshots)

Reviewer: iOS 26 visual-design pass, read-only. Measured with PIL.
Nadi pages: 804×1748 = 402×874 pt @2x. Owner live shots and iOS refs: 1206×2622 @3x. alpha6 sheets: 390×844 @1x (light).
"Apple" = published in HIG/SwiftUI docs (via `alpha7-ios26-spec.md`). "Measured" = from the owner's iOS 26 Settings screenshot. Anything else is marked as an observation of iOS behaviour, not a number.

## Overall native-look score: **48 / 100**

The screens use the right pieces: inset groups, label-left/value-right rows, a sheet grabber, Close on the left.
Two things give it away straight away:
1. **Detail screens are edit forms.** Read-only records show pickers, chevrons, red asterisks, switches, raw IDs and US dates.
2. **The OT form's states are broken on a real device.** An error is wrapped one word per line inside the Hours value column. Hint text floats between groups at the wrong inset.

---

## The 25 highest-impact fixes (biggest first)

| # | Fix | Screens | Sev |
|---|---|---|---|
| 1 | **Read-only detail = `LabeledContent` rows.** No chevrons, no `*`, no switch tracks, no pickers. Only fields the viewer can change stay controls. Today every row has a ▾ chevron and 8–10 rows show a red `*`. | all 9 *-detail | P1 |
| 2 | **Inline error goes UNDER the row as a footer line, never inside the value column.** Owner shot: the "Could not check overtime. Try again before saving." error wraps into a ~40 pt column, 7 lines, one word per line. The Hours row grows from 43 pt to **87.3 pt** (measured @3x). | ot-requests-new (live) | P1 |
| 3 | **Loading = `ProgressView` in the row's trailing slot** (spinner plus secondary "Checking…"), not red text. The owner shot shows "Checking overtime for this date…" in red, wrapped 5 lines inside the Hours row. It also appears a second time as grey text between groups. | ot-requests-new (live) | P1 |
| 4 | **One date format everywhere: "Wed 23 Sep" / "23 Sep 2026".** Today one OT flow shows "Wed, 23 Sep", "23 Sep 2026", "09/16/2026" and the `mm/dd/yyyy` placeholder. Details show "06/10/2026", "08/21/2026". Standard W7 bans this. | all forms + details | P1 |
| 5 | **Picker values show names, never IDs.** "Who: HR-EMP-00009" on approver details. The next row, "Name: W0 employee", repeats the same person. Merge them into one "Employee" row that shows the name. | ot/leave/shift/expense detail (approver) | P1 |
| 6 | **Cancel request is a destructive action, not a filled salmon capsule.** Today it is a 358×47 pt bar filled with (248,113,113). Make it a red-text row "Cancel Request" in its own group at the end of the page (or in the ••• menu), confirmed with `.confirmationDialog`. | leave/ot/expense detail | P1 |
| 7 | **Status is shown once**, as secondary text in a "Status" row (or a subtitle under the title). Today it appears three times: a chip in the nav bar, a "Status" picker row, and a Status row in the approval group. The nav-bar chip also squeezes the title ("Approved, not paid yet" chip is ~190 pt wide). | all details | P1 |
| 8 | **Filters = a sheet of grouped rows with checkmarks, or a toolbar `Menu`.** Not labels above empty boxed selects. Owner shot: selects are 46 pt tall, (57,58,62) fill, about 200 pt wide, hanging off the right half of the row. The labels sit above them. The selects are **empty**, with no "All" value. | employee-checkins filters (live) | P1 |
| 9 | **Remove the sheet footer band.** Owner shot: a near-black band (8,6,11), 86 pt tall, sits at 717–803 pt. Under it is another 70 pt band of (33,32,37). It holds a dark outlined "Clear all" and a lime "Apply filters" (both 47 pt) side by side. iOS: "Reset" leading, "Done/Apply" trailing in the sheet's nav bar. Apply live, or put one button at the bottom. | filters (live) | P1 |
| 10 | **Drop "Day you worked" when a day is already picked.** Owner shot: "Wed, 23 Sep 1h 00m ✓" in the "Pick a day" group, then "Day you worked * 23 Sep 2026" 3 groups later. The same fact is shown twice in two formats. | ot-requests-new | P1 |
| 11 | **Guidance text belongs in a group footer (Footnote, secondary, 16 pt + row inset).** Owner shot: "HR will sort these out…" sits at x≈33 pt, but "Checking overtime…", "Could not check…" and the lime "Try again" sit at x≈16 pt. They float between groups, attached to none. | ot-requests-new | P1 |
| 12 | **"Paid as overtime" must be a row, not a floating label.** It is plain 15 pt text at x≈33 with no cell behind it. Make it `LabeledContent("Paid as", "Overtime")` in the first group, or a footer. | ot-requests-new | P2 |
| 13 | **No section header over a single row.** "Claim" over Hours alone, "Reason" over Note alone, "Approval" over Goes to alone, "Totals" over Paid back alone, "Issue"/"Details" over one row each. iOS uses a header only when it labels a group. Merge these rows into the neighbouring group. | ot/leave/issue new, expense detail | P2 |
| 14 | **Drop red asterisks on required fields.** iOS marks nothing and disables the confirm button until the form is valid (the Calendar "Add" button greys out). Nadi already disables Send, so the `*` adds nothing. A "Required" placeholder is acceptable. | all forms | P2 |
| 15 | **Date = compact date pill (`DatePicker(.compact)`), not a `mm/dd/yyyy` + calendar-glyph text input.** Show the value as a grey capsule, for example "23 Sep 2026". Show nothing until a date is set, not a placeholder mask. The same goes for time: "--:-- --" becomes an empty pill or "Not set". | leave/attendance/shift/ot new | P1 |
| 16 | **Menu picker glyph = chevron.up.chevron.down, value in secondary.** Today it is a chevron-down ▾. That reads as a web `<select>`. | all pickers | P2 |
| 17 | **Switch: white knob, green or tint track, native `<input type=checkbox switch>`.** Today the ON state is a lime track with a BLACK knob, about 52×31 pt. The OFF state is a dark track with a black knob, which is almost invisible on (21,23,29). | leave-new, attendance, profile | P1 |
| 18 | **Appearance menu = iOS pull-down.** Items are tight (about 44 pt pitch). There must be no empty first slot. Today about 45 pt of blank space sits above "Light". The menu anchors to the value's trailing edge. It must not cover the row labels: today the menu's left edge at x≈140 pt cuts "Notifications"/"Shift reminders" to "Shift reminder". Keep the checkmark leading — that part already matches. Use glass (not the opaque (26,28,34) fill), with the page dimmed or with a lensing blur. | profile/settings (live) | P1 |
| 19 | **Check-in list row = a plain list row.** Title "In" / "Out" (17 pt regular). Time right, in secondary or monospaced digits. Section headers by day ("Today", "Yesterday", "22 Sep"). Today each row shows the time as a 20 pt bold title, the day repeated as a subtitle, and an In/Out chip (Out filled lime-tint (69,82,45)). Rows are 64 pt apart. | employee-checkins (live) | P1 |
| 20 | **Filter button = a plain toolbar glyph in the glass nav group.** Not a boxed 42×42 pt rounded square with its own outline. Use `line.3.horizontal.decrease.circle` inside a `Menu`. | employee-checkins (live) | P2 |
| 21 | **Primary action of a SHEET goes in the nav bar (`.confirmationAction`, trailing).** New expense item: "Add expense" is a grey capsule at the bottom of an inner card, with only an X in the header. It needs "Cancel" leading and "Add" trailing. Pushed full-page forms may keep a bottom button, but the button must not sit in a separate 80 pt band with a hairline. | expense item sheet, filters, approval | P1 |
| 22 | **No card inside a sheet.** The Approval and New expense item sheets have an outer grey sheet (215,216,218) and an inner card (237,239,243) inset 16 pt. The rows sit inside the card, and the buttons sit inside the card too. iOS: the sheet background is the grouped background, with inset groups directly on it. | approval sheets ×5, expense item | P1 |
| 23 | **Currency: one symbol from the company.** The staff expense screens show **"₹ 50", "₹ 0"**. The approver sees "RM 12.50". A Malaysian user must never see a rupee sign. This is a data/locale defect, not styling. | expense-claims new/detail (staff) | P1 |
| 24 | **Sub-pages drop the bell + avatar.** Every pushed page (Time off, You, Change password, all details) carries the bell and a 36 pt rounded-square "N". iOS pushed pages show back + title + contextual actions only. The account button lives on tab roots. | all pushed pages | P2 |
| 25 | **Empty states = `ContentUnavailableView`.** Centred icon + title + one line. Today: "Nothing is waiting on you." sits top-left in grey; "No public holidays ahead are listed yet." is 13 pt grey; "No manager is set for you." is a footnote. | remote-approvals, hr-contacts, holidays sheet | P2 |

---

## Shared form findings (all "*-new" screens)

Measured on `staff-leave-applications-new.png`:
- Page background (7,7,10). iOS: #000.
- Cell (21,23,29). iOS: (28,28,30) (measured, Settings).
- Row pitch 43–44 pt. That is fine for a plain row (iOS 18 44; iOS 26 stock cell measured at 52, non-Apple).
- Gap between groups 50 pt when there is a header, 40 pt without one.
- Group corner radius ≈ 16 pt (edge inset reaches 17.5 pt at 9 pt down). iOS measured ≈ 26.
- Send button: 46 pt tall, lime (200,255,0), in a bottom band that starts at 794 pt with a hairline. The band is 80 pt.

---

## 1. Overtime — New (`ot-requests-new`, plus the owner's 4 live shots)

**Purpose:** claim paid hours for a worked day. It should feel like **Calendar "New Event"**: one sheet, rows, and Add enabled only when the form is valid.

| Element | Nadi now | iOS 26 | Rule / source | Sev |
|---|---|---|---|---|
| Check glyph on picked day | tiny lime ✓ (~8 pt) trailing, after "1h 00m" | selection checkmark in tint, trailing, 17 pt symbol; or no check (a single choice is shown by the value) | MENU anatomy "selection indicator" | P3 |
| Hint text inset | "HR will sort…" x≈33; "Checking…/Could not…/Try again" x≈16 | all footers aligned to the row text (16 + 16 pt) | R4 (alpha6-standard) | P2 |
| "Paid as overtime" | floating 15 pt label, no cell | `LabeledContent` row or a footer | R4 | P2 |
| Section headers "Claim", "Reason" | a header over 1 row each | none; merge the rows | LIST | P2 |
| Required `*` | red on Day, Hours, Note | none; disable Add | observed iOS forms | P2 |
| Hours field | "Required" placeholder right, value "1" | `TextField` with `.keyboardType(.decimalPad)`, or a `Stepper`/menu of 0.5 h steps; value "1h" | W7 "1h 30m" | P2 |
| Note | 140 pt box with "Note *" label on top, "Required" under it | `TextField("Note", axis: .vertical)`, `lineLimit(3...)`, no inner label | PICK/LIST | P2 |
| Day shown twice | "Wed, 23 Sep" (picker group) + "Day you worked * 23 Sep 2026" | one row "Day" → compact date pill or the picked list | K-rules, W7 | P1 |
| Loading | red "Checking overtime for this date…" wrapped 5 lines **inside** the Hours value; also grey text between groups | `ProgressView()` trailing in the Hours row, Add disabled | PICK / states | P1 |
| Error | red text wrapped **one word per line** in a ~40 pt column; row grows 43 → 87.3 pt; a second copy floats above with a lime "Try again" | one footer under the group: "Couldn't check overtime." plus an inline "Try Again" button in tint; the row keeps its height | W5 "next to the field" | P1 |
| Empty state (fresh) | "No overtime recorded in this period, so there is nothing to claim yet." + "Choose a work date…" as floating text | `ContentUnavailableView("No overtime to claim", systemImage: "clock")` when nothing is claimable; otherwise a footer | — | P2 |
| Primary action | "Send", full-width bottom 46 pt, grey when disabled | pushed form: bottom `.borderedProminent` allowed; presented as a sheet: "Send" in `.confirmationAction` | SHEET (Cancel leading / Done trailing) | P2 |
| Nav bar | back + 20 pt title + bell + avatar tile | back + inline title "Overtime" (17 pt semibold) | TOOL | P2 |

**Apple build:** `Form { Section { Picker("Day", selection:$day) { … } .pickerStyle(.navigationLink); LabeledContent("Paid as","Overtime") } Section { LabeledContent("Hours") { if loading { ProgressView() } else { TextField("0", value:$h, format:.number).multilineTextAlignment(.trailing) } } } footer: { if let err { Text(err) + Button("Try Again") } }; Section { TextField("Note", text:$note, axis:.vertical) } }.toolbar { ToolbarItem(placement:.confirmationAction) { Button("Send").disabled(!valid) } }`

**Score: 30** (the live states are the worst item in this review).

## 2. Time off — New (`leave-applications-new`)
**Feel:** Calendar "New Event".

| Element | Nadi now | iOS 26 | Source | Sev |
|---|---|---|---|---|
| Picker glyph | ▾ chevron-down | chevron.up.chevron.down | PICK | P2 |
| Half day switch | OFF: black knob on (40,40,46) track, ≈52×31 pt | white knob, grey track (native switch) | D1 plan / TOG | P1 |
| From/To | `mm/dd/yyyy` + calendar glyph (raw Chromium input) | compact date pills; "All-day"-style Half day under them | PICK | P1 |
| Group order | "Kind of leave" alone; "Dates & reason" holds From/To/Half/Reason; "Approval" holds Goes to alone; "Add a file" alone | Section 1: Kind + balance footer ("19 days left"); Section 2: From, To, Half day; Section 3: Reason (multiline); Section 4: Goes to; Section 5: "Add Attachment" as a tint-colour button row | LIST, R4 | P2 |
| "Reason / Optional" | label above a 113 pt box | `TextField("Reason (optional)", axis:.vertical)` | — | P3 |
| Add a file | text + upload glyph, white | tint-coloured button row "Add Attachment" (paperclip) | BTN | P3 |
| Send | bottom lime 46 pt | pushed: OK; sheet: nav trailing | SHEET | P2 |

**Score: 55**

## 3. Fix a day — New (`attendance-requests-new`)
**Feel:** Calendar "New Event" (From/To/All-day + time pickers).
- "In"/"Out" show "--:-- --" plus a clock glyph (P1). Use compact time pills ("9:00 AM"). Hide them when the Reason is "On Duty" all day.
- Two switches, Half day and Include holidays, have black knobs (P1).
- Shift is a picker with no value, showing only ▾ (P2). Show "None" in secondary.
- The "Reason *" picker and the "Note / Optional" box share a group; that part is correct.
- Header "Reason" over the group that contains a "Reason" row — the header repeats the row label (P2).

**Score: 52**

## 4. Shift change — New (`shift-requests-new`)
- The cleanest form: one group, 4 rows, no header.
- Issues: ▾ glyphs (P2); `mm/dd/yyyy` (P1); "To" has no `*` while "From" has one — inconsistent (P3). Remove both.
- "Goes to" should be the approver's name, with the default preselected (K3).

**Score: 60**

## 5. Expense — New (`expense-claims-new`)
**Feel:** Wallet / Reminders "New List" with a line-item section.

| Element | Nadi now | iOS 26 | Sev |
|---|---|---|---|
| Currency | "Expenses ₹ 0" (staff) | "RM 0.00" | P1 |
| Line items | header row "Expenses ₹0 +" (bare + glyph, 13 pt header), then a dashed-border empty box "No expenses added / Add each item … with the + above" | Section "Items" with a tint button row "Add Item" (plus.circle.fill); empty = just that row; total in the footer | P1 |
| Dashed empty box | 1 pt dashed outline, 110 pt tall | iOS never uses dashed outlines in lists | P2 |
| Goes to first | the approver is the first thing asked | items first, approver last | P2 |

**Score: 45**

## 6. Issue — New (`issues-new`, staff and approver)
- "What are you reporting? *" wraps to 2 lines in the label column while the value is empty (P2). Use a short label ("Topic") or a navigationLink picker.
- The Urgency "Medium" menu is fine apart from ▾.
- The "Issue" and "Details" headers each head one group (P2).
- "Send to HR" bottom button is fine (a clear verb).

**Score: 55**

---

## 7. Detail screens (`*-detail`: leave, attendance, expense, issue, ot, shift, shift-assignment)

**Purpose:** a read-only record with, at most, Cancel (owner) or Approve/Reject (approver).
**Feel:** **Wallet transaction detail** / **Mail "Event" detail**: a title block, `LabeledContent` rows, a destructive row at the end.

| Element | Nadi now | iOS 26 | Source | Sev |
|---|---|---|---|---|
| Name clipping | "Nurul Aisyah binti Abdul Rahmar" cut at the right edge, no ellipsis; the "Who" row above truncates "…Abdul R…" | wrap to 2 lines, or one ellipsis; never a hard clip | TYP | P2 |
| Label wraps | "Hours from check-ins", "Balance shown (days)", "Strict shift location check-in", "Both shifts on purpose (HR)" wrap to 2 lines at about 145 pt of label width | LabeledContent lets the label take the width; the value goes under it if needed | LIST | P3 |
| ••• button | three bare dots, 20 pt, no glass | `Menu { … } label: { Image(systemName:"ellipsis") }` inside the glass toolbar group | TOOL | P2 |
| Status | nav chip (outlined orange / filled red / filled green) + "Status" picker row + "Status *" in Approval | one row "Status: Waiting" in system orange text, or a subtitle | B3 plan | P1 |
| Pickers in read-only | every row ends with ▾; `*` on 6–9 rows | plain `LabeledContent`, value in secondary, no glyph | LIST | P1 |
| Switches in read-only | Half day, Include holidays, Strict location, Both shifts, Created by shift rule — dark tracks | show "Yes/No" as a value, or drop a row that is false | LIST | P1 |
| Empty values | In/Out "--:-- --", "Goes to" empty with ▾ (expense detail) | drop empty rows | — | P2 |
| IDs | "Who HR-EMP-00009" + "Name W0 employee" | one "Employee: W0 employee" row | K3 | P1 |
| Dates | "06/10/2026", "09/16/2026", "08/21/2026" | "Wed 10 Jun 2026" | W7 | P1 |
| Company row | "Company * _Test Company ▾" | hide it (one-company users); show it only to HR | W1 | P3 |
| Destructive | salmon filled full-width "Cancel", 47 pt, in a bottom band | red text row "Cancel Request" at the end + `.confirmationDialog` | ASH/S7 | P1 |
| Issue detail "Save" | lime Save bar on a record that shows "Open" | editable only if the owner may edit; then "Edit" in the toolbar, not a permanent Save | — | P2 |
| Expense line card | an outlined card (lighter border) inside a list; "Approved: ₹50 · 8 Sep" | a plain row inside the "Items" section | G1 | P2 |

**Apple build:** `List { Section { LabeledContent("Employee", value: name); LabeledContent("Leave", value:"Casual"); LabeledContent("Dates", value: range.formatted(.interval.day().month().year())); LabeledContent("Days", value:"1") } Section("Reason") { Text(reason) } Section { LabeledContent("Status") { Text("Waiting").foregroundStyle(.orange) }; LabeledContent("Approver", value:"W0 approver") } Section { Button("Cancel Request", role:.destructive) { confirm = true } } }.confirmationDialog(...)`

**Scores:** leave 35 · attendance 35 · expense 38 · issue 40 · ot 38 · shift 40 · shift-assignment 35.

---

## 8. You / Settings (`profile`, `settings`) + live Appearance menu

**Feel:** **Settings root**: the account row, then groups.
`settings` renders the same page as `profile`: two routes, one page (N4).

| Element | Nadi now | iOS 26 (measured, Settings) | Sev |
|---|---|---|---|
| Account header | rounded-square "N" tile ≈60 pt (estimated from the capture; plan §1 says 72), name 22 pt bold wrapping 2 lines, subtitle "_Test Department 1 - _TC" | the account row IS a cell: 44 pt circle avatar, name 20 pt semibold, subtitle secondary, chevron → "Your details" | P1 |
| Details group | a lighter top stroke (28,30,36) — a glass/outline on a list group | no stroke; the cell is flat (28,28,30) | P2 |
| Icon tiles | 32 pt grey tile, grey outline glyph | 29×28 filled colour tile, white glyph (measured) | P2 |
| Appearance menu (live) | opaque (26,28,34) panel ~246 pt wide from x≈140; a blank ~45 pt slot above "Light"; items ~46 pt pitch; it covers row labels; the lime toggles bleed through at the right edge | glass menu anchored to the value, opening over it, no blank slot, leading ✓ (matches) | P1 |
| Toggle | lime track, black knob | green (#30D158) or tint, white knob | P1 |
| Footer | "Shift reminders nudge you…" as a footer | ✓ matches R4 | — |
| Log out | red centred text in its own group | ✓ matches "Sign Out" | — |
| Version line | centred footnote | ✓ OK | — |
| Approver extra | "Your shift: Nadi W0 Day" as a floating 15 pt line | a row in the account section, or the subtitle | P2 |

**Score: 62** (the closest screen to iOS in this set).

## 9. Change password (`change-password`)
**Feel:** Settings › Apple Account › Change Password.
- The labels "Current/New/Confirm" with "Required" placeholders are fine (P3). iOS uses placeholders "Required" in exactly this layout.
- The rules are missing: there should be a footer ("At least 8 characters…") (P2).
- "Current" should be in its own section, apart from New and Confirm (P3).
- "Update password" lime bottom bar (P2). iOS: "Change" in `.confirmationAction`, top right, disabled until valid.
- Bell + avatar on a sub-page (P2).

**Score: 60**

## 10. Who to ask (`hr-contacts` page + sheet 06)
- Page: headers "Your manager"/"HR" with grey empty text and nothing under them. The ↻ refresh button in the nav bar should be pull-to-refresh (P2).
- Sheet: "W0 manager" sits in a white capsule of ~24 pt radius. That is a pill, not a list row (P2).
- The row has no action (P1). iOS Contacts: the row pushes a contact card, or has a trailing phone/message button (`Link("tel:")`).
- Empty HR = a footer "HR hasn't added contacts yet."

**Score: 45**

## 11. Remote approvals (`remote-approvals`)
- "Nothing is waiting on you." sits 17 pt, secondary, top-left at y≈63 pt (P2).
- iOS: `ContentUnavailableView("No Approvals", systemImage:"checkmark.circle", description: Text("Requests that need you appear here."))`, centred.
- There is also a large title "Approvals" (this is a destination) and bell/avatar in the header.

**Score: 50**

## 12. Invalid employee (`invalid-employee`)
- Both personas render the **normal Home** (logo, "Not checked in", Check in button, tab bar). No "not linked to an employee" state is shown (P1, and possibly functional).
- iOS: a full-screen `ContentUnavailableView("Account not linked", systemImage:"person.crop.circle.badge.exclamationmark", description:…)` with a "Log Out" button. No Check in.

**Score: n/a — the state is not visible (flag it to the owner).**

---

## 13. Sheets (alpha6, light, 390 pt)

| Sheet | Feel like | Main differences | Score |
|---|---|---|---|
| **New request** | Mail compose chooser / Reminders "New" menu | Close leading ✓, centred title ✓, rows with subtitle ✓. Icons are grey outline tiles; iOS: colour tiles (C2). The white card sits on a grey sheet: OK as a grouped list. Rows have chevrons, but they open a new screen, so a chevron is right. The ~24 pt top gap under the header is fine. | 70 |
| **All balances** | Health › Data summary | One card, "Nadi W0 Annual / 19 of 20 left" as a 2-line row. Use `LabeledContent("Annual", value:"19 of 20 left")`. Add a medium detent (the sheet is ~140 pt of content in a tall sheet). | 62 |
| **Check in** | Wallet pass / Camera prompt | "04:49 am" at ~40 pt with a leading zero and lowercase am (iOS 12-hour clock: "4:49 AM"). "24 Sep, 2026" puts a stray comma before the year. The camera-error text is inside a black 360×270 box; use `ContentUnavailableView` with a "Try Again" button. "Confirm Check in" is a lime button with a trailing ✓ glyph (P3); make it just "Check In". | 50 |
| **Public holidays** | Calendar › Holidays list | Empty = 13 pt grey text left. Use `ContentUnavailableView`. | 50 |
| **Your details** | Settings › General › About | Labels are **13 pt grey** and values 13 pt; iOS About uses 17 pt label + secondary value. The rows are not in an inset group (plain separators on the sheet background). Dates "1 Jan 2025" ✓. | 55 |
| **Who to ask** | Contacts | see §10 | 45 |
| **New expense item** | Wallet "Add Card" details / Calendar New Event | **Boxed white inputs** (194×43 pt) to the right of labels inside a grey card inside the sheet. "Date 09/24/2026" in a box. A raw `<select>` with an empty value. "Accounting dimensions" (ERP words, W1). "Amount (MYR) *". The action is an "Add expense" capsule at the bottom inside the card; iOS: "Cancel" leading and "Add" trailing in the nav bar, rows = `LabeledContent` with a trailing-aligned TextField, a compact DatePicker and Picker(.menu). Hide cost center/department (default them). | 30 |
| **Approval** (light) | Mail message sheet with actions / Screen Time "Ask to Buy" approval | No nav title (the title "Time off" is 22 pt bold in the body under a "Request" caption). An inner card (237,239,243) sits inset 16 pt on the grey (215,216,218) sheet. Labels are **13 pt grey**. The Reason is a boxed field with **right-aligned** text "sheet crawl". Status is an outlined chip. Reject/Approve are 46 pt capsules inside the card (salmon fill + lime). iOS: nav title "Time Off", Close leading; LabeledContent rows; the reason as a plain Text under a "Reason" header; bottom toolbar with `Button("Decline", role:.destructive)` + `Button("Approve").buttonStyle(.borderedProminent)`. Screen Time "Ask to Buy" has these two actions at the bottom. | 40 |
| **Answered** (All your requests) | Mail filter / Reminders list with segmented control | The segmented control selected state is a **black filled** pill (iOS: a raised light thumb on a grey track). Filter chips wrap to 2 rows ("Not approved 2" on line 2). iOS: `Picker(.segmented)` + a toolbar filter `Menu`, or one scrolling row. The status chips are fully filled red/green; iOS: coloured secondary text. | 45 |

### Approver sheets (dark, `journey/13,15,17,19,21`)
- Same structure as Approval.
- The sheet is (21,23,29) from y=144, with an inner darker card (the page (7,7,10)-like block at x 16–378).
- The "Paid as" value is a grey chip "Overtime Pay". "Reason" in fix-a-day is a chip "On Duty"; iOS shows values as plain text, never chips.
- The expense sheet puts "Travel RM 12.50" in bold 17/20 pt inside a separate row block. That is OK as an Items section.
- The open-external icon (↗) top-right of the title block: in iOS it is a toolbar button ("Open") or the whole title row pushes.

**Score: 42**

### Live Filters sheet (owner `mufa669m`)
- The sheet top is at 466.7 pt: a ~407 pt custom detent. The grabber is ✓. X leading ✓. Title "Filters" centred ✓.
- Body: "Check-in type" and "Shift" labels (13 pt) sit **above** empty boxed selects (46 pt, (57,58,62), right half).
- Footer band: 86 pt, near-black, with two 47 pt buttons in mismatched styles (outlined dark vs filled lime).
- iOS (Mail filter / Photos filter): `Form { Picker("Type", selection:$type) { Text("All"); Text("In"); Text("Out") }.pickerStyle(.inline) ; Picker("Shift", …).pickerStyle(.menu) }`, `.toolbar { .cancellationAction: "Reset"; .confirmationAction: "Done" }`, `.presentationDetents([.medium])`.
- For just two filters, a toolbar `Menu` with sections of checkmarked items (no sheet) is even closer to iOS 26 (Mail's filter button).

**Score: 25**

### Live check-ins list (owner `mufa62pa`)
- Rows are 64 pt apart. The time is a 20 pt bold title (x≈17 pt, inset 20 inside a group that starts at x=16). The day is repeated in the subtitle on every row.
- The In/Out chips are ~32×22 pt. "Out" is lime-tinted, "In" is grey.
- The filter button is a 42 pt outlined square.
- iOS (Phone › Recents / Wallet transactions): sections per day. Row: SF symbol arrow.down.right / arrow.up.right in green/orange, label "In"/"Out" 17 pt, trailing time in secondary ("9:09 AM"). Row ≈44–52 pt.

**Score: 40**

---

## Score table

| Screen | Score |
|---|---|
| ot-requests-new (live states) | 30 |
| leave-applications-new | 55 |
| attendance-requests-new | 52 |
| shift-requests-new | 60 |
| expense-claims-new | 45 |
| issues-new | 55 |
| details (avg of 7) | 37 |
| profile / settings | 62 |
| change-password | 60 |
| hr-contacts | 45 |
| remote-approvals | 50 |
| invalid-employee | n/a (state not rendered) |
| sheets: new request 70 · balances 62 · check-in 50 · holidays 50 · your details 55 · who to ask 45 · expense item 30 · approval 40 · answered 45 | avg 50 |
| approver sheets | 42 |
| live filters | 25 |
| live check-ins | 40 |
| **Overall** | **48** |

## Not measured / caveats
- The alpha6 sheet captures are 1× light mode, so their numbers are pt directly. Their colours are the light theme, not the dark theme the owner uses.
- The Nadi page captures are Chromium. The `mm/dd/yyyy` and `--:-- --` masks are Chromium's native date/time inputs. iOS Safari renders `<input type=date>` as a native compact pill ("23 Sep 2026"), so on the device fix #15 is partly a capture artefact. The live OT shot (iOS) shows "23 Sep 2026", confirming that. The fix still stands for the empty state and for the grey capsule styling.
- Apple does not publish menu row height, sheet radius or switch size (ios26-spec §6/§8/§9). The menu and switch numbers above are Nadi measurements, not Apple targets.
