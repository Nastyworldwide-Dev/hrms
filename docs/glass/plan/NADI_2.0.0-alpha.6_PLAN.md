# Nadi 2.0.0-alpha.6 — plan (for approval)

Theme: **one feel everywhere, human words, no defects.** Nothing is coded until approved.
Research with a URL per rule: `/tmp/alpha6/research.md` (Apple HIG read in full through Apple's JSON feed, WWDC25 sessions 219/356/323/284, NN/g, GOV.UK).

## 1. The rules we will hold Nadi to (sourced)

| # | Rule | Source |
|---|------|--------|
| R1 | Glass only on bars, tab bar and sheets. Never on content. No glass on glass. | HIG Materials; WWDC25 219 |
| R2 | One tinted (filled) button per screen, for the most likely action. | HIG Buttons, Color |
| R3 | Tap targets at least 44 × 44 pt. | HIG Buttons, Accessibility |
| R4 | Inner corner radius = outer radius − padding (concentric). A capsule is half its height. | WWDC25 356 |
| R5 | A switch lives inside a list row: label on the left, switch on the right, hint in the group footer. | HIG Toggles |
| R6 | Short choice lists use a menu/picker button, not a boxed dropdown. Dates use the compact date picker. | HIG Pickers, Pull-down buttons |
| R7 | Sheets: Close at top-left, Done/Send at top-right, grabber, one sheet at a time. | HIG Sheets; WWDC25 356 |
| R8 | Menus/action sheets: most-used first, related items grouped with a separator. | HIG Menus, Action sheets |
| R9 | Keep forms short. Cut any field that can be derived. Hide advanced options behind disclosure. | HIG Settings, Disclosure; NN/g forms |
| R10 | Type ramp at default size: 34/28/22/20/17 semibold/17/16/15/13/12/11. Minimum 11. | HIG Typography |
| R11 | Springs by default, bounce 0 unless there is a reason. Respect Reduce Motion. | HIG Motion; WWDC23 10158 |
| R12 | Verbs on buttons. Plain words, no jargon, "you". Errors beside the field, and say how to fix it. | HIG Writing; GOV.UK; NN/g errors |
| R13 | Long lists: show the few that matter, then "Show more". No endless list. | NN/g infinite scroll, accordions |

**Honest gaps.** Apple's current text gives no exact figure for side margins, row height, separator inset or animation timing. For those we keep Nadi's own tokens (16 px gutter, 44/56 px rows) and do not claim an Apple number.

## 2. Nadi today vs the rules (measured on the live build, 390 px, dark)

| Where | What we measured | Breaks | Evidence |
|---|---|---|---|
| Every form field | Radius **0 px** (square). The design token says 12 px. | R4, consistency | `FormView.vue:1023` forces `border-radius: 0` on every input inside a form, overriding `.g-input` |
| Picker fields | "Shift type"/"Approver" pickers: **44 px, 12 px radius**. Other fields: **48 px, 0 px**. Two looks on one form. | consistency | measured `controls.json` |
| Approver field | Shows the raw address "muhammadnurhafiz@…com : H…" | R12 | expense and shift forms |
| Expense form | 9 section headings. **6 are empty**: Currency, Taxes, Advance payments, Totals, Exchange gain/loss, Accounting dimensions. "Accounting details" holds only "Posting date". | R9, R12 | The form's field list (`expense_claim/Form.vue:188`) removes the fields but **keeps every section heading** |
| Overtime | Every past day is a full card: open, claimed ("Claimed · Approved") and unclaimable, newest first, **no limit**. | R13 | `claimEmptyReason.js:34` returns all three kinds in one list |
| Home | "No shift today" while Profile says "9AM – 6PM". | bug | Home reads only a shift *assignment* (`api/now.py:65`). Profile reads the *default shift* (`Profile.vue:321`). You have no assignment. |
| Settings | Switches on the **left**, hint floating underneath, outside any group. | R5 | `Profile.vue:69-89` |
| New request sheet | 5 plain words. No icon, no hint, no separators. | R8 | `Requests.vue:35`, `GActionSheet.vue:31` |
| Half day | Square checkbox, 20 px (target under 44). | R3, R5 | `controls.json` |
| Section headings | Lime headings on forms ("Claim", "Reason"). The same lime is also the button colour. | R2 (the tint means "act") | `.g-eyebrow` |
| Buttons | "Save" on something sent to your manager. | R12 | FormView footer |
| Time off | Sideways scroll on your iPhone. **Not reproduced** in Chrome (fits, 390 = 390). | bug | needs Safari's engine (see §5) |

## 3. Words: from ERP to human (R12)

| Now | Proposed |
|---|---|
| OT date | Day you worked |
| Claimed hours | Hours |
| Explanation / Reason (OT) | What was the work? |
| You claim · Overtime Pay | "Paid as overtime" (one line, no card) |
| HR can see this | HR will sort this out |
| Posting date | (hidden. It's today) |
| Expense approver / Leave approver / Approver | Goes to |
| Leave type | Kind of leave |
| From date / To date | From / To |
| Half day | Half day (switch row) |
| Save (a request) | Send to {name} |
| Shift type | New shift |
| Accounting details / dimensions, Exchange gain/loss, Taxes & charges, Advance payments, Currency | removed from the employee's form |

## 4. Work, one concern per commit

| # | Slice | Change | Locked by |
|---|---|---|---|
| A1 | Shift truth | One rule for Home and Profile: today's assignment, else the default shift, else none. | backend test: default-only employee gets a shift |
| A2 | Empty sections | A form section with no visible field is not drawn. Removes all 6 empty expense headings. | invariant test on FormView |
| A3 | Approver names | Pickers show the person's name. The email never shows. | test on the option label |
| A4 | Time off sideways | Reproduce in WebKit first, then fix. No blind fix. | e2e: scrollWidth = width, WebKit |
| B1 | One field | Delete the radius-0 override. One height (48), one radius, one border for input, date, picker, text. | gate: every control on every form measures the same |
| B2 | Switch rows | Settings: grouped list with a trailing switch and footer hint. "Half day" becomes a switch row. GCheckbox is kept only for multi-pick lists. | a11y + unit test |
| B3 | New request sheet | Grouped rows: icon, title, one-line hint ("Book days away", "Get paid for extra hours"…), separators. | unit test |
| B4 | Overtime | Open days first, max 5, then "Show more". Claimed and unclaimable folded under "Already claimed (7)" and "Can't claim (2)". Form stays on screen. | unit test on the list shape |
| B5 | Headings | Form section headings become quiet grey (footnote style). Lime stays for actions only. | contrast + coherence gate |
| C1 | Words | Everything in §3, plus a banned-words gate (Posting date, Explanation, OT date, approver…). | vocabulary gate test |
| C2 | Buttons | "Send to {name}" instead of Save on requests. Sheet close/confirm placement checked on all sheets. | e2e |
| D1 | Motion | Record every push/pop/sheet on phone size. Any screen that skips or doubles its animation gets fixed. | motion gate + recording |
| E | Release | Whole-app walk (staff + approver, phone + desktop, light + dark), all gates, re-baseline, tag alpha.6. | as alpha.5 |

## 5. Needs you (one each)

1. **"Send to {name}" instead of "Save"** on requests. Yes or no?
2. **Lime section headings → grey.** Yes or no? (Lime stays for buttons and "needs you".)
3. **Sideways scroll:** I can't run Safari's engine on this machine because system libraries are missing. Either
   run `! sudo npx playwright install-deps webkit` once, or I test on Chrome's iPhone mode only.
4. **Expense "Posting date":** hide it (it defaults to today), or keep it for back-dated receipts?

Pipeline: approve → slices A → B → C → D, each one test red first, one commit each → review hook → whole-app walk → gates → tag `v2.0.0-alpha.6` → push → you deploy.
