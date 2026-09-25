# Nadi 2.0.0-alpha.9 — defect list and plan

Owner, 25 Sep 2026 (after deploying alpha.8 slice 1): "each page and screen …
inconsistent, incoherent, imbalanced, incorrect, inappropriate, missing,
over-engineered, under-engineered — icon sizing, margin, padding, text,
typography, all pages, sheets, dialogs. Plan it the Apple way."

## How this was found (method)

1. **Every screen rendered in Safari's engine** at the owner's iPhone size
   (402×874 pt), as the approver (the persona that sees the most): 36 screens.
   Contact sheets reviewed screen by screen.
2. **A measuring script** (`frontend/e2e/ios-consistency-audit.mjs`) that
   checks every screen against ONE standard and against itself: icon sizes by
   role, group margins and radii, row text start, type on the iOS ramp,
   header-to-group gaps, button heights, loose text outside groups.
3. **The reference**: the owner's iOS 26 Settings screenshot, measured at 3×
   (group 16 pt inset, radius 26, tile 29 at x 30.7, text at 76, separator
   74.3 → 369.7, avatar 60, name 22 bold, large title 34 bold), plus the HIG.

## The rules every screen must follow (the "kit")

| Rule | Value | Source |
|---|---|---|
| R1 Everything in a group | content sits in inset groups; only section headers and footers sit outside | HIG Lists; Settings |
| R2 One gutter | groups 16 pt from both screen edges | measured |
| R3 One radius | groups 26 pt | measured |
| R4 Rows | 44 pt plain, 54 with an icon tile; text 17 pt | measured |
| R5 Tiles | 29 pt, coloured, white glyph 18 pt | measured |
| R6 Separators | from the row's text to 16 pt short of the edge | measured |
| R7 Section header | 13 pt, secondary, 16 pt in from the group edge, 6 pt above its group | HIG, measured |
| R8 Type ramp | 11, 12, 13, 15, 17, 20, 22, 28, 34 only | HIG Typography |
| R9 Values | right-aligned, secondary colour, never an ID | HIG |
| R10 One primary action per screen | the lime button; everything else plain | owner Q1 |
| R11 Status | coloured word, once, in the bar | alpha.7 |
| R12 Empty state | symbol + title + one line, centred in the free space | ContentUnavailableView |

## Defects found (by rule, with screens)

### Structure (R1) — loose content outside groups
| # | Screen | What |
|---|---|---|
| D1 ✅ 0f5e6667b | Home (approver) | "Needs you" header + "Nothing waiting on you." as loose grey text |
| D2 ✅ 085680ad0 | Team | "Today · Fri 25 Sep" loose bold text; the calendar is a group, the list below is not |
| D3 ✅ 284caf4bb | Notifications | "67 unread" loose text above the list |
| D4 ✅ 284caf4bb | Who to ask | "Your manager / No manager is set for you" and "HR / HR hasn't listed contacts yet" are all loose small text |
| D5 ✅ 0f5e6667b | Approvals | "Nothing is waiting on you." loose text |
| D6 | Help, HR Issues | "Open" as a loose label above an empty state |
| D7 ✅ 085680ad0 | Overtime (new) | "No overtime recorded in this period…" loose text above the form |
| D8 ✅ 085680ad0 | Expense (new, detail) | "Expenses RM 0 +" loose header row; "Paid back RM 0" group of one |
| D9 ✅ 284caf4bb | You | "Version 2.0.0-alpha.7 · 2026-09-25 07:11" loose (iOS: a footer or About row) |

### Wrong information (R9)
| # | Screen | What |
|---|---|---|
| D10 ✅ 2f2ddb58d | Every sent-request detail (Fix a day, Shift change, Time off, Overtime, Expense) | "Who: HR-EMP-00009" — an employee ID, not the name (owner rule: ids never reach users) |
| D11 ✅ 2f2ddb58d | Same | "Company: Nadi W0 A" on the employee's OWN request — noise |
| D12 ✅ cdf71f556 | Expense detail | bar reads "Expense" + "Approved, not paid yet" overlapping the title ("Expensproved…") |
| D13 ✅ cdf71f556 | Overtime / Time off detail | numeric values show a stray box glyph ("2▪", "1▪", "19▪") — a spinner/stepper artefact of a disabled number input |
| D14 ✅ e8086bfdc | Overtime detail | "Hours from check-ins" wraps to two lines at 17 pt |

### Type (R8)
| # | Where | What |
|---|---|---|
| D15 ✅ 02d619463 (audit counted avatar/logo marks) | Home, Requests, Calendar, Score, More | 18 pt and 14 pt text (off ramp) — the Today card's state line and bar text |
| D16 ✅ 02d619463 (avatar initial) | You, Settings | 24 pt (off ramp) |
| D17 ✅ 085680ad0 (totals now a footer) | Expense | 14 pt totals |

### Shape (R3, R5, R7)
| # | Where | What |
|---|---|---|
| D18 ✅ 02d619463 | Home, Calendar | two radii on one screen (26 and 20): the Today card and the calendar still use 20 |
| D19 | Time off dashboard, Expense dashboard | big "No leave allocated yet" card with an empty state INSIDE a card, then a second empty state below: two empty states on one screen |
| D20 | Expense dashboard | lime "Total claimed" card: lime used as a surface, not an action (R10) |
| D21 ◐ 0f5e6667b (Leave left always answers) | Requests (approver) | "Your last 5" header then an empty state with no group; balances line missing when there is no allocation — the screen is mostly blank |
| D22 | Calendar | "What the colours mean" row inside the calendar card at a different inset from the rows below |
| D23 | Every list screen | Filter and + in the bar; the + duplicates "New request" on Requests (two ways, R10) |
| D24 | Notifications | 12 identical rows "W0 employee asked for …" with a grey tile each — no kind colour (R5), unread dot AND chevron on every row |

### Sheets and dialogs (not yet audited on screen)
| # | Where | What |
|---|---|---|
| D25 | All sheets | the audit above covers pages; sheets and alerts need the same script pass (opened by the sheet crawler) |

## Plan (order = impact)

1. **Kit tokens and one test per rule** (R1–R12) so a new screen cannot break them — extend `ios-consistency-audit.mjs` to fail on each, run it in CI.
2. **D10–D14** wrong information (smallest, most visible): name not ID, drop Company on own requests, status out of the title's way, no stepper glyph, labels that fit.
3. **D1–D9** everything into groups (each is a template change).
4. **D15–D18** type and radius to the ramp and the one radius.
5. **D19–D24** screen structure: one empty state per screen, lime only on the action, notifications with kind tiles, one way to create.
6. **D25** sheets and dialogs through the same script.
7. Prove: the script at 0 findings on all 36 screens + sheets, WebKit audit, journeys, gates; screenshots side by side with the iOS reference.

## Motion and scroll (alpha.8 r3, 25 Sep — owner: "turn off zoom … overflow
## scrolling … jumpy stuff on pages and sheets … every bit measured")

| What | Measured before | After | Commit |
|---|---|---|---|
| Zoom | pinch zoomed freely | off: viewport + gesture guard (iOS ignores `user-scalable=no` alone) | d13122051 |
| List pages scroll past their end | 8 pages, 28 pt | 0 (one scroller: ion-content) | d13122051 |
| Pages move while loading | 7 of 36, 9–132 pt | 0 of 36, first visit AND return visit | 0f5e6667b |
| Sheets move after opening | 0 of 10 | 0 of 10 | — |
| Sheet scroll runs into the page | 10 of 10 | 0 (overscroll contain) | b152fe9c8 |

Proof, re-runnable: `e2e/scroll-and-shift-audit.mjs` (pages, cold + warm) and
`e2e/sheet-shift-audit.mjs` (sheets). Visual baselines re-shot: d261bb7c4.

## Already fixed this round (c8ea821ad, d14e31252)
Doubled title after switching tabs; blue square behind switches; tab icon
moving; separators keyed on their own row; document bounce; HR's OT report
columns inside the existing view.
