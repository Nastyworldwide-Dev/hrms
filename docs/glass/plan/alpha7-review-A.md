# Review A — Nadi alpha.6 vs real iOS 26 (dark), tab roots + list screens

Reviewer: Apple-iOS-26 visual pass, read-only. Screens: `/tmp/alpha7/pages/{staff,approver}-*.png` (804×1748 = 402×874 pt @2x).
References: owner's iPhone Settings (1206×2622 @3x) and App Store Search (368×800). Numbers from PLAN §1 (measured) and alpha7-ios26-spec; my own Nadi measurements below are in **pt** (px ÷ 2).

**Not captured (cannot review):** `team-roster` and `announcements` have no PNG in `/tmp/alpha7/pages/`. `remote-approvals` renders identically to `approvals` (pixel diff = same layout) and is reviewed with it.

## Nadi measurements used throughout (this pass)

| Thing | Nadi measured | iOS 26 measured / Apple |
|---|---|---|
| Page bg | (7,7,10) #07070A | #000000 (Settings) |
| Grouped cell fill | **vertical gradient** (34,36,42) top → (21,23,29) bottom, plus 1 pt light rim (96,97,100) on top edge and (54,55,60) border | flat #1C1C1E, **no border, no rim** |
| List-screen cell fill (leave list) | (47,49,55) → (43,45,50), bordered | flat #1C1C1E |
| Group radius | ≈18–20 pt (edge curve inset 33 px at top, settles by ~36 px) | 26 pt (measured) |
| More row height | 56 pt (170→284→396→508 px) | 54 pt with icon |
| List row height (Your time off) | **66 pt** (218→350→482→616 px) | 2-line row not published; Mail/Reminders 2-line ≈ 60–64 by eye, not measured |
| Icon tile | 28 pt grey (65,67,71) tile, grey outline glyph (168,174,184) | 29×28 pt **coloured** tile, white glyph |
| Tab-root title | ≈20 pt semibold (cap 14 pt), inline, right of a 32 pt lime logo | Large Title 34 pt bold, x=16/17, own line |
| Avatar (bar) | 34 pt **rounded square**, fill (32,32,34), grey letter | circle, gradient initials (App Store, ~36 pt) |
| Tab bar | 65.5 pt tall, inset 16 pt, fill (26,26,31), selected = bold white label, **no lens** | ~61 pt tall, inset ~20 pt, glass lens pill behind selected, tint colour |
| Primary button | 48 pt lime capsule (200,255,0), full width | App Store: tinted glass capsule "Get"; no full-width filled primary on list screens |
| Status chips | filled salmon **#F87171** (Tailwind red-400) "Rejected", filled teal "Approved", **outlined** orange "Waiting", filled grey "Approved, not paid yet" / "Scheduled" | iOS red dark #FF4245, green #30D158, orange #FF9230 — and as **text**, not pills |
| Empty state | dashed 1 pt border box, centred bold 15 pt + 13 pt text | ContentUnavailableView: no box, SF Symbol 48-ish, title 22 bold, body secondary, centred in the free space |

---

## Overall score: **48 / 100** (average of 19 screen scores below; 912 / 19)

## The 20 highest-impact fixes (across my screens), biggest first

1. **Large titles on the 5 tab roots** (Home, Calendar, Requests, Score, More): 34 pt bold on its own line at x=16 below the status bar, collapsing to a 17 pt semibold centred inline title in the glass bar. Home currently has **no title at all**. Remove the lime "n" logo tile from every bar (P1).
2. **Kill the gradient + rim + border on every grouped cell.** Flat #1C1C1E, no stroke, no top highlight. The rim is what reads as "glass card on web" (G1: no glass in content) (P1).
3. **Replace filled/outlined status pills with iOS status text.** Secondary line or trailing value in system colour: "Waiting" orange #FF9230, "Approved" green #30D158, "Rejected" red #FF4245, 15 pt regular, no background, no stroke. Salmon #F87171 is Tailwind, not Apple (P1).
4. **Delete every dashed empty box.** Use ContentUnavailableView layout: SF-style symbol, 22 pt bold title, 15 pt secondary body, optional borderless tint button, vertically centred in the empty area, no border (P1; 11 screens).
5. **Tab bar selected lens**: a glass pill behind the selected icon+label, selected icon+label in tint; height 61, inset 20 (P1 on every tab root).
6. **Lists are one inset-grouped section, not stacked full-width rows on black.** Requests "Your last 5", Time off "Recent leave", Expense "Recent expenses" draw rows directly on the page with full-bleed hairlines — put them inside a 26 pt-radius #1C1C1E group (P1).
7. **Page background #000000** (currently #07070A) (P2, but everywhere).
8. **Bar buttons**: bell and filter as 44 pt circular glass buttons with a monochrome symbol, no square border. Filter is currently a 34 pt rounded-square with a 1 pt grey stroke (P1 on list screens).
9. **"New" in list bars** is a lime filled capsule with a text label — use a `+` symbol toolbar button (glass, tinted glyph) (P1 on 5 list screens).
10. **Avatar**: circle, 36 pt, gradient initials (App Store). Currently a rounded square with a flat grey letter (P2).
11. **Group radius 26 pt, gap between groups 35 pt, rows 54 pt with icon / 44 pt without** (P2).
12. **Icon tiles**: coloured 29×28 tiles with white glyphs in More/notifications (Help = blue, SOPs = orange, Announcements = red, Public holidays = red/calendar); grey-on-grey is not iOS Settings (P2).
13. **List row type**: title 17 pt regular (currently 17 pt **semibold** with +letter-spacing on leave rows), subtitle 15 pt secondary. Tracking is visibly positive on every Inter-rendered label (T5) (P2).
14. **Section headers**: 13 pt secondary sentence case attached to a group (inset 16 inside the group edge, 6–7 pt above it). "Announcements", "Your week", "Needs you" float with no group under them (P2).
15. **"See all" in lime bold 17 pt** on Time off/Expense section headers → put "See all" as the last row of the group ("Show all" + chevron) or a secondary-coloured 15 pt header button; lime must not decorate (G6) (P2).
16. **Dates the iOS way**: "Today", "Yesterday", "Wed 9 Sep"; the list rows show "10 Jun · 0d" — "0d" is meaningless and should read "Half day" or "1 day"; drop "a month ago" + "with Administrator" (P2).
17. **Numbers tabular** (`font-variant-numeric: tabular-nums`) in calendar grids, balances, money, times (P3).
18. **Currency**: "₹ 50" on a Malaysian site next to "RM 0" — use one locale formatter (en-MY → "RM 50.00") (P1 on Expense; wording/data defect that looks broken).
19. **Calendar legend** of 9–10 coloured dots with outline squares is a web-dashboard pattern; iOS Calendar/Fitness use one dot style + a tap to see detail. Move the legend into a footer or an info sheet (P2).
20. **Score empty state** has a 3 pt lime left stripe on a card — a web "alert" pattern. Use ContentUnavailableView (P1 for that screen).

---

## 1. Home (tab root) — staff + approver

**For:** see today's status and check in. **iOS analogue:** Fitness "Summary" / Health "Summary" (large title, date above title, cards of one object each).

| Element | Nadi now | iOS 26 | Rule/source | Sev |
|---|---|---|---|---|
| Date line tracking | 12–13 pt, letter-spaced | Health: 13 pt secondary uppercase-free, no tracking | T5 | P3 |
| Separator in "Your week" group | none between the 2 rows, rows 56 pt | inset hairline (56,55,59) from text x | R1 | P3 |
| Status dot | 8 pt orange dot left of "Not checked in" | fine; iOS uses colour + word | G8 | P3 |
| Row "Nothing booked." | 17 pt with trailing full stop, same weight as a value | a row label, no full stop | W | P3 |
| Empty sections | "No news." / "Nothing waiting on you." floating 15 pt text under a header | either hide the section or a one-row group "No announcements" in secondary | R7 | P2 |
| Section headers | 15–17 pt (cap 9 pt → ~13 pt? rendered larger with tracking) secondary, far from content (≈26 pt gap) | 13 pt, 6–7 pt above its group | R4 | P2 |
| Group cell | gradient + rim + border | flat #1C1C1E | G1 | P1 |
| Icon tiles in "Your week" | grey 28 pt tile, grey glyph | coloured tile (green calendar) | Settings | P2 |
| Check-in button | 48 pt lime capsule, full width | right place for the one filled action (B1); iOS 26 would use `.glassProminent` capsule 50-ish, not published | B1 | P3 |
| Logo in bar | 32 pt lime "n" tile top-left | none; title owns the header | A2 | P1 |
| Title | **no screen title** | Large Title "Today" or "Home" 34 pt bold | T7, A1 | P1 |
| Avatar | rounded square 34 pt | circle ~36 pt gradient initials | A3 | P2 |
| Tab bar | no lens, 65.5 pt, inset 16 | lens, ~61 pt, inset 20 | A4 | P1 |
| Approver extra | "Needs you" header + one grey sentence | a group with count badge row "Approvals  0 ›" or hidden when 0 | R7 | P2 |

**Apple build:** `NavigationStack { ScrollView { … } .navigationTitle("Today") }` with `.toolbar { ToolbarItem(.topBarTrailing) { bell }; ToolbarItem { avatar .sharedBackgroundVisibility(.hidden) } }`. Under the title: a Fitness-style summary card (one standalone object — R8) holding status word in colour + shift "09:00–18:00" + a `.buttonStyle(.glassProminent)` "Check in". Then `List(.insetGrouped)`-style sections: "This week" with `LabeledContent("Days worked", value: "0")`, "Booked" rows; announcements as a section only when non-empty. `.refreshable` on the scroll view.

**Score: 45** — no title, logo in the header, glassy gradient cards, floating empty lines.

## 2. Requests (tab root)

**For:** start a request, see what's in flight. **iOS analogue:** Reminders list / Mail inbox.

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| "See all ›" | centred 17 pt grey below list | last row "See all" with chevron inside the group, leading-aligned | R6 | P3 |
| Row hairlines | full-bleed from x=16 to 386, on black | inset hairline inside a group, none after last row | R1 | P2 |
| Row text | "Expense · 9 Sep", 17 pt, tracked | title 17 regular + date as trailing secondary or subtitle 15 | R2 | P2 |
| Balance line | "Privilege 16 · Sick 14" loose text row + "All balances ›" | a group row `LabeledContent("Time off left", "16 · 14 days") ›` | R1 | P2 |
| "Needs attention" card | single bordered gradient pill-card, radius ~28, grey icon tile | a one-row group, orange icon tile, row 54 pt | R1 | P2 |
| Status chips | "Approved, not paid yet" filled grey pill 22 pt, "Waiting" orange outline pill | trailing secondary text; colour on the word only | B3, alpha7 B3 | P1 |
| Money | "₹ 50" | "RM 50.00" | W7 | P1 |
| Empty (approver) | dashed box "Nothing here yet" + orphan "See all ›" under it | ContentUnavailableView; no See all when empty | R7 | P1 |
| "New request" | 48 pt lime full-width capsule at top | `+` toolbar button, or tinted glass capsule; full-width filled is OK as the one primary but App Store/Reminders put "New" in toolbar/bottom-trailing | B1, TOOL | P2 |
| Title | ~20 pt inline next to logo | Large Title 34 pt bold | A1 | P1 |

**Apple build:** `List { Section { balance row } ; Section("Needs attention") { row }; Section("Recent") { ForEach(last5) { row } ; NavigationLink("See all") } }.listStyle(.insetGrouped).navigationTitle("Requests").toolbar { Button(systemImage: "plus") }`. Rows use `LabeledContent` with trailing status `Text("Waiting").foregroundStyle(.orange)`. `.swipeActions` for Cancel on waiting items; `.searchable` for "find a request". Empty: `ContentUnavailableView("No requests yet", systemImage: "tray", description: …)`.

**Score: 44** — web pills, rows on black, off-locale currency, no large title.

## 3. Calendar (dash-attendance, tab root)

**For:** see each day's attendance. **iOS analogue:** Calendar month view / Fitness history.

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Day numerals | 15 pt, proportional digits | tabular | T | P3 |
| Weekday header | "Sun Mon…" 12 pt tracked | single-letter "S M T W T F S" 13 pt secondary (Calendar app) | Calendar | P3 |
| Month nav | two 32 pt rounded-square bordered buttons | chevron glyphs in tint, borderless, beside month title (Calendar/DatePicker graphical) | B7 | P2 |
| Today marker | 44 pt rounded-square with 2 pt grey outline | filled circle in accent (red in Calendar, accent in DatePicker) with white numeral | Calendar | P2 |
| Worked days | grey filled rounded squares + tiny dot | a coloured dot under the numeral only | Calendar | P2 |
| Legend | 9 (staff) / 10 (approver) colour chips wrapping over 2–3 lines, mixed filled/outlined squares | none in the grid; a footer line or info button | R4 | P1 |
| Month card | gradient bordered card r≈20 | flat #1C1C1E r 26 | G1 | P1 |
| Links group | "All check-ins", "Your shifts" rows 56 pt, no icons | fine as an inset group; add icon tiles for consistency with More | R2 | P3 |
| Title | inline 20 pt + logo | Large Title | A1 | P1 |

**Apple build:** `DatePicker(selection:, displayedComponents: .date).datePickerStyle(.graphical)` is close, but for status dots Apple would write a `LazyVGrid(7)` month grid with `.monospacedDigit()`, today = filled accent circle 36 pt, status = 5 pt dot under the digit; tap a day → sheet with that day's punches. Below: `Section { NavigationLink("All check-ins"); NavigationLink("Your shifts") }` in `.insetGrouped`. Legend moved into `.toolbar { Button("info.circle") }` sheet.

**Score: 50** — reads like a web date-picker widget; legend is the loudest thing on screen.

## 4. Score (dash-kpi, tab root) — both personas identical

**For:** see performance review status/score. **iOS analogue:** Fitness Activity rings / Health highlights.

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Body text | 15 pt secondary with tracking | 15 pt secondary, no tracking | T5 | P3 |
| Card | gradient bordered card with 3 pt **lime left stripe** | no stripe; no card at all for empty | G6, R7 | P1 |
| Empty layout | card pinned top, 1100 pt of black below | ContentUnavailableView centred vertically | R7 | P1 |
| Title | inline 20 pt | Large Title "Score" | A1 | P1 |

**Apple build:** when a review exists: `Gauge(value:).gaugeStyle(.accessoryCircular)` or a Title-1 28 pt number with `Chart` of past periods, in an inset group. Empty: `ContentUnavailableView("No review yet", systemImage: "chart.line.uptrend.xyaxis", description: Text("HR hasn't opened a review that includes you."))`.

**Score: 40** — a web callout, not an iOS state.

## 5. More (tab root) — identical both personas

**For:** jump to secondary areas. **iOS analogue:** Settings root.

| Element | Nadi now | iOS 26 (Settings) | Rule | Sev |
|---|---|---|---|---|
| Separator start | inset to text (x≈58 pt) | starts at 74 pt from screen edge (after tile) — Nadi's ≈58 pt is right for its tile position, close | R1 | P3 |
| Row height | 56 pt | 54 pt | PLAN §1 | P3 |
| Label size | 17 pt regular (Help cap ~12 px) | 17 pt | ✓ | — |
| Icon tile | 28 pt grey tile, 1.5 pt grey outline glyph | 29×28 coloured, white filled glyph | Settings | P2 |
| Group | gradient + rim + border, r≈20 | flat #1C1C1E, r 26 | G1 | P1 |
| No account row | profile only via top-right avatar | Settings puts the account row first (44 pt circle, name 20 semibold) | Settings | P2 |
| Only 4 rows | one group | Settings groups by kind (Help/SOPs vs Announcements/Holidays) with 35 pt gaps | L5 | P3 |
| Search | none | bottom glass search capsule (Settings) | A5 | P2 |
| Title | inline 20 pt + logo | Large Title "More" 34 pt | A1 | P1 |

**Apple build:** exactly Settings: `List { Section { profile row (circle avatar, name, "Profile, password") } Section { Label("Help", systemImage: "questionmark.circle") … } Section { Announcements, Public holidays } }.listStyle(.insetGrouped).navigationTitle("More").searchable(text:)`. Each `Label` icon in a coloured `RoundedRectangle(cornerRadius: 7)` 29×28 tile.

**Score: 62** — structure is already Settings; the chrome (title, tiles, card rim) gives it away.

## 6. Notifications (pushed)

**For:** read what changed. **iOS analogue:** Mail inbox (unread dot, sender, date).

| Element | Nadi now | iOS 26 (Mail) | Rule | Sev |
|---|---|---|---|---|
| Unread dot | 8 pt lime dot **trailing**, before chevron | 10 pt blue/accent dot **leading** in the margin | Mail | P2 |
| Chevron on every row | yes | Mail shows chevron small next to date; fine | R3 | P3 |
| Time format | "10:36 am", "Wed 9 Sep", "Fri 21 Aug" | "10:36", "Yesterday", "Wednesday", then "21/08/2026" (locale). "am" lowercase with space is not iOS | W7 | P2 |
| Title weight | 17 pt semibold + positive tracking for unread; regular for read | Mail: sender 17 semibold, subject 15 regular | T5 | P2 |
| Subtitle | "Administrator · Wed 9 Sep" | sender is the title; "Administrator" is a system account — hide it (W10) | W1 | P2 |
| 2-line wrap titles | "WO employee asked for shift / change" wraps to 2 lines, 67 pt rows, uneven heights | one-line title truncated with …, date trailing on the title line | Mail | P2 |
| Count line "52 unread" | floating 15 pt secondary text | Mail: in the toolbar bottom status "52 Unread" (subtitle under title) | TOOL | P3 |
| "Mark all read" | lime bold 17 pt text top-right | tint text button or "Edit" → toolbar; lime decoration conflicts with G6 only if not the primary action — acceptable but should be monochrome glass button | G7 | P2 |
| Section header "Today"/"Earlier" | 17 pt secondary, sentence case | 13 pt secondary | T | P3 |
| Group | gradient rim card | flat | G1 | P1 |
| Title | inline 20 pt, left-aligned after back chevron | pushed = inline 17 pt semibold **centred** | N3 | P1 |
| Tab bar | hidden on this screen | tab bar stays on section screens (N2) — pushed from bell, so hidden is defensible | N2 | P3 |

**Apple build:** `List { Section("Today") { ForEach { NotificationRow } } }.listStyle(.insetGrouped).navigationTitle("Notifications").navigationBarTitleDisplayMode(.inline).toolbar { Button("Mark All Read") }` with `.swipeActions { Button("Read") }`, `.badge` on the bell. Row: leading unread `Circle().fill(.tint).frame(10)`, title one line `.lineLimit(1)`, time `.foregroundStyle(.secondary)` trailing.

**Score: 55.**

## 7. Help (pushed) — staff has 2 issues, approver empty

**For:** see open issues, report one. **iOS analogue:** Settings > General subpage / Feedback.

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Status | "Open" orange outlined pill 24 pt | trailing secondary "Open" | B3 | P1 |
| Row title | "Issue" — generic | real subject | W | P2 |
| Section header "Open" | 17 pt secondary | 13 pt | T | P3 |
| Empty (approver) | dashed box with wrapped text | ContentUnavailableView or a single secondary row "No open issues" | R7 | P1 |
| "Who to ask" | its own 1-row card r≈24 (pill-ish) | row inside a group | R1 | P3 |
| "Report an issue" | 48 pt lime capsule mid-page | `+`/compose symbol in the toolbar, or a tint-text row "Report an Issue" in a group (Settings pattern) | B1 | P2 |
| Title | inline, left | centred inline 17 pt | N3 | P1 |

**Apple build:** `List { Section("Open") { ForEach(issues) { LabeledContent(subject) { Text("Open").foregroundStyle(.orange) } } } Section { NavigationLink("Who to ask") } Section { Button("Report an Issue") } }.listStyle(.insetGrouped)`.

**Score: 50.**

## 8. Approvals (pushed) — staff (empty) / approver (+2 history rows); remote-approvals identical

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Empty line | "Nothing is waiting on you." 17 pt **semibold grey** floating top-left | ContentUnavailableView ("All caught up", checkmark symbol), or group row | R7 | P1 |
| Staff sees Approvals at all | page reachable with nothing to do | hide the entry for non-approvers | N4 | P2 |
| History rows | 2-row group, 56 pt rows, long labels "Requests you've already answered" | shorter nouns "Answered requests", "Answered check-ins" (T8, W3) | W | P3 |
| Title | inline left | centred inline | N3 | P1 |
| No tab bar | hidden | stays visible (N2) | N2 | P2 |

**Apple build:** `List { if pending.isEmpty { ContentUnavailableView(…) } else { Section { ForEach … .swipeActions { Approve; Reject } } } Section { NavigationLink("Answered requests") … } }.insetGrouped`.

**Score: 48.**

## 9. Team (pushed) — staff "no team" / approver "nobody today"

**For:** who from my team is in/out on a day. **iOS analogue:** Calendar day list + Contacts.

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Legend | "Selected day / Today" with two hollow squares | no legend | — | P2 |
| Today marker | white 2 pt outlined rounded-square on 24 | filled accent circle | Calendar | P2 |
| "Today · Thu 24 Sep" | 17 pt semibold tracked header | 13 pt section header "Today" or Title 3 day header (Calendar) | T | P2 |
| Empty | dashed box ×2 | ContentUnavailableView | R7 | P1 |
| Staff with no team | full calendar shown above "You do not have a team here" | show only the ContentUnavailableView; the calendar is useless | purpose | P1 |
| Month card | gradient rim | flat | G1 | P1 |
| Title | inline left | centred inline | N3 | P1 |

**Apple build:** `List { Section { MonthGrid } Section("Thu 24 Sep") { ForEach(people) { HStack { circle avatar 32; name 17; Spacer; status text } } } }` — or `ContentUnavailableView("No team", systemImage: "person.2")` alone for staff.

**Score: 45.**

## 10. SOPs (pushed)

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Search field | 40 pt **boxed** field, r 12, 1 pt border, "Search SOPs…" 17 pt | `.searchable`: 36 pt capsule/rounded field fill (118,118,128,0.24), no border, magnifier + mic (App Store screenshot) | K, A5 | P1 |
| Empty | dashed box | ContentUnavailableView.search or "No SOPs" | R7 | P1 |
| Title | inline left | Large Title for a searchable root-like list, or inline centred | T7 | P2 |

**Apple build:** `List(sops) { NavigationLink(sop.title) }.searchable(text:, prompt: "Search")` + `ContentUnavailableView("No SOPs yet", systemImage: "book.closed")`.

**Score: 45.**

## 11. Time off overview (dash-leaves) — staff has balances, approver none

**For:** see balance, ask for time off, see recent. **iOS analogue:** Health "Summary" tiles + Wallet transactions list.

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Balance numbers | 34 pt bold digits "12 / 16 / 14" | Title 1 28 pt bold, tabular (T: one big number is Title 1) | T | P2 |
| Lime underline bars | 3 pt full-width lime bars under each balance (all 100%, no information) | `Gauge`/progress only if it shows used vs allowed; else none | G6 | P1 |
| Balance grid | 2+1 bordered tiles inside a card (card-in-card) | inset group with `LabeledContent("Casual", "12 days")` rows, or Health-style tiles each own card | G2, R8 | P1 |
| "See all" | lime bold 17 pt on the header line ×2 | secondary header button or last row | G6 | P2 |
| "Ask for time off" | lime capsule with **left-aligned** label + → arrow | centred label, no arrow (arrow = web CTA) | B | P2 |
| Recent rows | on black, full-bleed hairlines, 3 lines each (title 20 pt semibold, "5 Jan · 0d", "with Administrator · a month ago") | 2-line row in a group: "Casual" 17, "5 Jan · 1 day" 15 secondary, status text trailing | R2, W10 | P1 |
| Leave names | "Casual Leave", "Sick Leave" | "Casual", "Sick" — W4 says "time off" | W4 | P3 |
| Status | orange outlined "Waiting" pill | text | B3 | P1 |
| Content under tab bar | row text visible through the bar ("Sick Leave" ghosted behind labels) | scroll-edge fade under bar; OK in principle but here the bar is opaque-ish and text collides with labels | G4 | P2 |
| Empty (approver) | dashed box **inside** a bordered card (double frame) + second dashed box | ContentUnavailableView once | R7 | P1 |
| Title | inline left | centred inline | N3 | P1 |

**Apple build:** `List { Section { LabeledContent("Casual", value: "12 days") … } header: { Text("Time off left") } footer: { Button("See all") } Section { Button("Ask for Time Off") } Section("Recent") { ForEach … } }.insetGrouped`. Balances with `.monospacedDigit()`.

**Score: 42.**

## 12. Expense claims overview (dash-expense-claims)

**For:** see how much is claimed/pending, claim one. **iOS analogue:** Wallet (Apple Card balance card + transactions list).

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Currency | "₹ 50" (staff) vs "RM 0" (approver) | single locale "RM 50.00" | W7 | P1 |
| **Lime filled hero card** "Total claimed ₹ 50" | 70 pt-tall lime card, black text | Wallet: dark card, number Title 1 in label colour; brand fill only on the one primary button (G5, G6) | G5/G6 | P1 |
| 3-stat strip | segmented bordered tiles "₹0 Pending / ₹50 Approved / ₹0 Rejected" (card-in-card) | group rows `LabeledContent("Waiting", "RM 0.00")` | G2 | P1 |
| Two lime things on one screen | hero card + "Claim an expense" button | one tinted element per screen | B1 | P1 |
| "Approved, not paid yet" | grey filled pill | secondary text | B3 | P2 |
| Row | "Medical" 20 pt semibold, "9 Sep · ₹ 50" | Wallet row: merchant 17, date 15 secondary, amount trailing 17 tabular | R2 | P2 |
| Empty | dashed box | ContentUnavailableView | R7 | P1 |

**Apple build:** Wallet-like: `List { Section { VStack(alignment:.leading) { Text("Claimed this year").font(.subheadline).secondary; Text(total, format: .currency(code: "MYR")).font(.largeTitle.bold()).monospacedDigit() } } Section { LabeledContent × 3 } Section { Button("Claim an Expense").buttonStyle(.glassProminent) } Section("Recent") { rows } }`.

**Score: 38** — the lime hero card is the single most non-native element in my set.

## 13–19. List screens (pushed, same template)

Screens: **Your time off** (leave-applications), **Your day fixes** (attendance-requests), **Shift changes** (shift-requests), **Your expenses** (expense-claims), **Your overtime** (ot-requests), **Your shifts** (shift-assignments), **Your check-ins** (employee-checkins). Staff vs approver differ only in data (staff has rows on leave/day-fix/expense/shifts, approver mostly empty). **iOS analogue:** Mail mailbox / Reminders list (pushed, filter in toolbar, compose button).

Shared differences:

| Element | Nadi now | iOS 26 | Rule | Sev |
|---|---|---|---|---|
| Date + duration | "10 Jun · 0d", "1 Aug - 31 Dec · 153d" (hyphen, "d" unit) | "10 Jun · Half day", "1 Aug – 31 Dec" (en dash), "153 days" | W7 | P2 |
| Row title weight | 17 pt **semibold** + tracking | 17 regular | T5 | P2 |
| Row height | 66 pt (leave list), 52 pt (shift) | not published; 2-line inset rows ≈ 60 by eye | R5 | P3 |
| Cell colour | (47,49,55) — **lighter than More's cells** (21–34) | one #1C1C1E everywhere | K1 | P2 |
| Status pills | filled salmon "Rejected" (#F87171 on dark text), filled dark-teal "Approved", outlined orange "Waiting", filled grey "Scheduled" / "Approved, not paid yet" — **four different pill styles** | one style: trailing coloured text | B3, K1 | P1 |
| Filter button | 34 pt rounded-square, 1 pt grey stroke, outline glyph | circular glass bar button 44 pt, `line.3.horizontal.decrease` symbol; or Mail's bottom filter | B7 | P1 |
| "New" | lime text capsule 60×38 pt in bar | `+` glass button (compose), tint glyph | B7, TOOL | P1 |
| Title | inline left-aligned 20 pt after back chevron, "Your …" | centred inline 17 pt semibold; drop "Your" (T8: short nouns) — "Time off", "Day fixes", "Expenses" | N3, W3 | P1 |
| Bell + avatar | absent on list screens but present on Team/Help/SOPs — two header styles for pushed screens | one pushed-bar style | N4 | P2 |
| Empty | dashed box pinned under the bar, 13 pt body, no symbol, no full stop on some ("…will appear here") | ContentUnavailableView centred, button "New Time Off Request" | R7 | P1 |
| Tab bar | hidden | stays (N2) | N2 | P2 |
| Long list | 12+ rows endless, no month grouping | section by month ("June", "May") | R6 | P2 |
| Empty-state title wording | "No attendance requests yet" on a page titled "Your day fixes"; "No shift requests yet" under "Shift changes" | same noun as title (W4) | W4 | P2 |

**Apple build (all 7):** `List { ForEach(groupedByMonth) { month in Section(month.title) { ForEach(month.items) { item in NavigationLink { Detail } label: { VStack(alignment:.leading) { Text(item.type); Text(item.dateRange).font(.subheadline).foregroundStyle(.secondary) }; Spacer(); Text(item.status).foregroundStyle(item.color) } } } } }.listStyle(.insetGrouped).navigationTitle("Time off").navigationBarTitleDisplayMode(.inline).toolbar { Menu { Picker filter } label: { Image(systemName: "line.3.horizontal.decrease") }; Button { new } label: { Image(systemName: "plus") } }.refreshable { }.overlay { if items.isEmpty { ContentUnavailableView(…) } }`, `.swipeActions` for Cancel on waiting items.

Per-screen scores:

| Screen | Persona difference | Score | Reason |
|---|---|---|---|
| Your time off | staff 12+ rows with 3 pill styles; approver empty | **45** | pill rainbow + no month sections |
| Your day fixes | staff 2 rows ("On Duty", "Work From Home" — ERP names, W1); approver empty | **48** | pills, ERP names |
| Shift changes | both empty | **50** | dashed box, lime New |
| Your expenses | staff 1 row with grey pill + "₹"; approver empty | **46** | wrong currency, pill |
| Your overtime | both empty | **50** | dashed box, lime New |
| Your shifts | staff 1 row "Scheduled" pill, "153d"; approver empty; no New (correct) | **54** | cleaner bar, still pill + dashed box |
| Your check-ins | both empty; filter only | **55** | cleanest; still dashed box, left title |

---

## Score table

| # | Screen | Score |
|---|---|---|
| 1 | Home | 45 |
| 2 | Requests | 44 |
| 3 | Calendar | 50 |
| 4 | Score | 40 |
| 5 | More | 62 |
| 6 | Notifications | 55 |
| 7 | Help | 50 |
| 8 | Approvals (+ remote-approvals) | 48 |
| 9 | Team | 45 |
| 10 | SOPs | 45 |
| 11 | Time off overview | 42 |
| 12 | Expense overview | 38 |
| 13 | Your time off | 45 |
| 14 | Your day fixes | 48 |
| 15 | Shift changes | 50 |
| 16 | Your expenses | 46 |
| 17 | Your overtime | 50 |
| 18 | Your shifts | 54 |
| 19 | Your check-ins | 55 |
| | **Average** | **~48** |


Not published by Apple (used measured or left open): list radius (26 measured), row height (54 measured), tab bar height (61 measured), 2-line row height, bar-button diameter (44 = minimum target, BTN), search field height.
