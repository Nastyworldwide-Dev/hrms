# The Nadi standard — iOS 26 / Liquid Glass, Apple only

This is the rulebook alpha.6 builds to and every later release is checked against.
One rule per line. Each rule has an ID (used in the violation table and in the gates) and a source.
**No Material Design, no Android patterns, no web-dashboard patterns.** If Apple has a native answer, we use it.

Sources (full quotes and URLs: `/tmp/alpha6/research.md`; Apple text kept in `/tmp/alpha6/hig/`):
MAT Materials · LAY Layout · TYP Typography · TB Tab bars · TOOL Toolbars · SHEET Sheets · SCROLL Scroll views ·
COLOR Color · A11Y Accessibility · W Writing · LIST Lists and tables · TOG Toggles · PICK Pickers · BTN Buttons ·
MENU Menus · ASH Action sheets · SET Settings · MOT Motion — all at developer.apple.com/design/human-interface-guidelines/<name>.
WWDC25 219 "Meet Liquid Glass", 356 "Get to know the new design system", 323/284 "Build an app with the new design";
WWDC23 10158 "Animate with springs". NN/g and GOV.UK where Apple is silent.

Where Apple gives **no number**, this says "Nadi token" and does not pretend it is Apple's.

---

## 0. The model: three layers

| Layer | What lives there | Material | Source |
|---|---|---|---|
| **Content** | text, lists, rows, cards, forms, numbers | solid system backgrounds. **Never glass** | MAT "Don't use Liquid Glass in the content layer" |
| **Controls & navigation** | top bar, tab bar, toolbar buttons, floating buttons | Liquid Glass, regular variant | MAT, WWDC25 219 |
| **Modal** | sheets, menus, alerts, action sheets | glass (partial height) → opaque (full height), with dimming behind | SHEET, WWDC25 356 |

Everything below follows from this. One thing = one layer. Glass never sits on glass.

---

## 1. Glass and colour (G)

- **G1** Glass only on bars, tab bar, sheets, menus, floating buttons. Never on a card, row or list. — MAT
- **G2** No glass on glass. Things *on* glass use plain fills, not a second glass. — WWDC25 219
- **G3** One glass variant (regular) everywhere. Never mix regular and clear. — MAT
- **G4** Bars have **no custom background, border or hairline**. Content scrolling under them gets a scroll-edge fade. One per edge. — LAY, SCROLL, TOOL
- **G5** **Tint means "act".** Only the one primary action on a screen is filled with the brand colour. — COLOR ("refrain from adding color to the background of multiple controls")
- **G6** Brand colour is **not** used for decoration: not headings, not labels, not numbers. "When every element is tinted, nothing stands out." — WWDC25 219
- **G7** Bar icons and labels are monochrome. Only the selected tab takes the tint. — TB, TOOL
- **G8** Colour never carries meaning alone. Status also has a word. — A11Y
- **G9** Contrast: text ≤17 pt ≥ 4.5 : 1; larger/bold ≥ 3 : 1, in light **and** dark. — A11Y
- **G10** Semantic colours only: label / secondaryLabel / tertiaryLabel for text; systemBackground / secondarySystemBackground for grounds; red = destructive; green = on. — COLOR

## 2. Type (T)

The iOS ramp at default size. **Nadi uses these sizes and no others.** (1 pt = 1 CSS px.)

| Style | Size / line | Weight | Nadi use |
|---|---|---|---|
| Large Title | 34 / 41 | Bold | tab-root screen title (Home, Calendar, Requests, Score, More) |
| Title 1 | 28 / 34 | Bold | the one big number on a screen (clock, score) |
| Title 2 | 22 / 28 | Bold | — rare |
| Title 3 | 20 / 25 | Semibold | sheet big heading, name on Profile |
| Headline | 17 / 22 | Semibold | pushed-screen title, row title that must stand out, button labels |
| Body | 17 / 22 | Regular | row titles, field values, reading text |
| Callout | 16 / 21 | Regular | — rare |
| Subhead | 15 / 20 | Regular | row subtitles, secondary lines |
| Footnote | 13 / 18 | Regular | **section headers and footers** of grouped lists, hints |
| Caption 1 | 12 / 16 | Regular | timestamps, badges |
| Caption 2 | 11 / 13 | Semibold | tab bar labels only |

- **T1** Only the sizes above. — TYP
- **T2** Weights: Regular, Medium, Semibold, Bold. **No 800/900 (Heavy/Black).** Avoid Light and Thin too. — TYP
- **T3** Font: the system font (SF Pro on Apple devices). No Inter Tight "display" face; it reads as web, not iOS. — TYP (system font), inference for the removal
- **T4** Minimum 11 pt anywhere. — TYP
- **T5** Tracking follows SF (−0.4 at 17, 0 at 12). No positive letter-spacing on body text. — TYP
- **T6** No ALL-CAPS headings. iOS 26 section headers are sentence case, Footnote, secondary colour. — TYP, iOS 26 Settings (observed)
- **T7** Large title on tab roots collapses to an inline title when you scroll. Pushed screens use the inline title. — TOOL
- **T8** Screen titles under 15 characters, never the app name. — TOOL

## 3. Layout and spacing (L)

- **L1** A vertical page moves only vertically. **Nothing pans sideways.** Only a deliberate horizontal carousel may scroll on x. — LAY (content fits the safe area); defect class seen on Time off
- **L2** Side gutter 16 px on phone, 20 px on wide screens. — Nadi token (Apple gives no number; UIKit default behaviour)
- **L3** Respect safe areas: status bar, home indicator, notch. — LAY
- **L4** Tap targets ≥ 44 × 44. — BTN, A11Y
- **L5** Space: ~12 px between bordered controls, ~24 px around borderless ones. Groups separated by space, not lines. — A11Y, LAY
- **L6** Most important thing top-leading. — LAY
- **L7** **Concentric corners:** inner radius = outer radius − padding. A capsule's radius = half its height. — WWDC25 356
- **L8** Radius set (Nadi tokens that satisfy L7): screen-edge sheet 28 · grouped list 20 (was 16; revisit against L7) · field 12 · capsule = h/2. No other values. — Nadi token under L7
- **L9** Desktop (≥1024): the sidebar plus one content column. The same components, never a separate "desktop design". — LAY (iPad sidebar)

## 4. Lists (R), the backbone of an iOS app

- **R1** Content is a **grouped (inset) list**: rounded group, rows inside, hairline separators inset to the text (never under the icon), no separator after the last row. — LIST
- **R2** A row = optional leading icon (in a rounded square), title (Body), optional subtitle (Subhead, secondary), trailing value/accessory. — LIST
- **R3** Rows that open something show a **chevron**. Rows that act do not. — LIST
- **R4** Group **header**: Footnote, secondary colour, sentence case, above the group. Group **footer**: Footnote, secondary, below. Guidance text goes in the footer, never floating. — LIST, SET
- **R5** Row min height 44. Two-line rows grow with content. — BTN/A11Y (target), Nadi token 44/56
- **R6** Long lists: the few that matter, then "Show all". Older items grouped (by month) or folded. No endless scroll where the task is "find" or "check". — NN/g
- **R7** Empty group: one line saying what is true and what to do, with a button if there is an action. Never blank, never a loading state shown as "nothing". — W, NN/g
- **R8** Cards are for one standalone object (a score, a check-in). A list of things is a list, not a stack of cards. — LIST, MAT (content layer)

## 5. Controls (K)

| Need | iOS control | Never |
|---|---|---|
| on / off | **Switch in a list row, trailing** (R-side), footer explains ON | checkbox, switch on the left, switch outside a row — TOG |
| pick one of a few (≤5) that change the view | **segmented control** | tabs drawn by hand — SEGMENTED |
| pick one from a short list | **menu (pop-up) button in a row**: label left, value + chevron-up-down right | boxed dropdown, raw `<select>` look — PICK, PULL-DOWN |
| pick one from a long list (people, types) | **pushed / sheet list with search**, checkmark on the chosen row | autocomplete box |
| date / time | **compact date picker in a row**: label left, date pill right, calendar pops on tap | a full-width empty box — PICK |
| text | **text field in a row** (label left or placeholder), clear button | heavy boxed field floating alone — TEXT FIELDS |
| long text | text view in its own group, grows | fixed short box |
| actions | buttons (below) | links styled as buttons |

- **K1** Every control type above has **one** look, used everywhere. Same height, radius, padding, font. — consistency (NN/g), TOOL
- **K2** A form **is a grouped list** (R1). Fields are rows in groups, not boxes stacked on the page. — SET, LIST (iOS Settings/Contacts/Calendar "New Event" pattern)
- **K3** Picker values show **names**, never emails or IDs. — W
- **K4** A checkbox is used only for picking several from a list (with a checkmark on the row, iOS style). — TOG, LIST

## 6. Buttons (B)

- **B1** **One** filled (tinted) button per screen, for the most likely action. — BTN, COLOR
- **B2** Secondary = gray fill (bordered). Tertiary = plain text in tint colour. — BTN
- **B3** Destructive = red text, never the primary role, always confirms. — BTN
- **B4** Labels are verbs that name the result: "Send to Hafiz", "Check in", "Claim 1h". Never "Submit", "OK", "Click here". — W, BTN
- **B5** Preference by style, not size. — BTN
- **B6** Pressed state always. Slow action = spinner inside the button, label stays. — BTN
- **B7** Bar buttons: SF-style symbol, no border, no text next to a symbol in the same group. Max three groups. — TOOL
- **B8** Back = the chevron symbol, not the word. Close = the × symbol. — TOOL
- **B9** Label weight Semibold (17), not Heavy. — TYP

## 7. Navigation (N)

- **N1** Tab bar: floats on glass at the bottom, labels always shown, one-word labels, ≤5 tabs, only for sections, **never for actions**. — TB
- **N2** The tab bar stays visible on every section screen. Only modals cover it. — TB
- **N3** Pushed screens: top bar with back chevron (left), inline title, at most one primary action (right). — TOOL
- **N4** One way to each place. No page reachable by two different header styles. — NN/g consistency
- **N5** Desktop: sidebar on glass replaces the tab bar. Same destinations, same order. — TB (iPad)

## 8. Sheets, menus, alerts (S)

- **S1** Sheet = a short, self-contained task. A long form is a pushed screen, not a sheet. — SHEET
- **S2** Sheet bar: **× Close on the left, the confirm action (✓ or verb) on the right**, title centred. Always paired. — SHEET, WWDC25 356
- **S3** Grabber on resizable sheets. Swipe down closes; if something was typed, confirm with an action sheet ("Discard changes?"). — SHEET
- **S4** One sheet at a time. — SHEET
- **S5** Partial sheets are glass and inset; full-height sheets are opaque. Dimming behind. — WWDC25 323/356
- **S6** Action sheet / menu: rows with icon + title (+ one-line hint when the choice needs one), grouped by separators, most-used first, destructive red, Cancel last (or tap outside). Never scrolls. — ASH, MENU
- **S7** Alert: title says what happened, ≤3 buttons, verbs, "Cancel" is always "Cancel". Never just "Error". — ALERTS

## 9. Motion (M)

- **M1** Push: slides in from the right, back slides out right, and the edge swipe goes back. Same on every pushed screen. — MOT (follow the gesture)
- **M2** Sheet: rises from the bottom, and falls with the swipe. Same on every sheet. — MOT, SHEET
- **M3** Springs, bounce 0 (brisk ≤0.15). Nothing bouncy above 0.3. — WWDC23 10158
- **M4** Durations are Nadi tokens: tap 90 ms, press 120 ms, state 200 ms, push/sheet ≈ 350–500 ms spring. Apple publishes none. — Nadi token
- **M5** No motion on things that happen often (every row tap). Feedback short. — MOT
- **M6** Reduce Motion: slides become fades; no parallax, no scale. — A11Y
- **M7** Tab switches do **not** slide (iOS tabs cross-cut). — TB (observed system behaviour)
- **M8** Nothing animates twice, jumps after landing, or flashes the old page. — MOT (purpose)

## 10. Words (W)

- **W1** Plain words a new employee understands on day one. No ERP/database names (Posting date, Approver, Leave type, Document, Submit, Draft, Employee, Designation). — W, GOV.UK
- **W2** Speak to the person ("you"), active voice, never "we". Use "your" sparingly. — W
- **W3** Buttons are verbs (B4). Titles are nouns ≤15 characters. — W, TOOL
- **W4** One word per thing, everywhere: time off (not leave/absence), overtime, expense, shift, fix a day. — W (consistency)
- **W5** Errors: next to the field, say what to do, no blame, never "invalid". — W, NN/g
- **W6** Empty states: what is true + what to do. — W
- **W7** Numbers people read: "1h 30m", "2 days", "RM 45.00", "Mon 9 Nov". No decimals of hours, no ISO dates. — W
- **W8** Sentence case everywhere in Nadi (Apple asks for one consistent choice; Nadi chose sentence case in alpha.4). — W
- **W9** Sentences ≤25 words; one idea each. — GOV.UK
- **W10** No IDs, emails or codes on screen, ever. — W (+ owner ruling L4)

## 11. Native feel (P), what makes a PWA stop feeling like a website

- **P1** No sideways page drag (L1). No rubber-band that shows a white page under dark UI (overscroll colour = page colour). — native behaviour
- **P2** No grey tap flash (`-webkit-tap-highlight-color: transparent`); rows use their own pressed state. — native behaviour
- **P3** No text selection or long-press callout on controls and chrome. Content text stays selectable. — native behaviour
- **P4** No zoom on focus (inputs ≥16 px). No double-tap zoom. — native behaviour
- **P5** Status bar colour follows the theme. The app is installable with a proper icon and launch screen. — native behaviour
- **P6** Keyboard: the right keyboard per field (numbers for hours and money), Return goes to the next field, and the primary button stays reachable above the keyboard. — TEXT FIELDS
- **P7** Instant feedback: the pressed state shows in <100 ms; skeletons, not spinners, for loading lists. — BTN, LOADING
- **P8** Pull to refresh only on lists that change. — native behaviour

## 12. Every screen must answer (the page contract)

For each screen in the page table (`alpha6-pages.md`):
1. **Purpose.** One sentence: what the person came here to do.
2. **Must show**, in priority order, top-leading first.
3. **Actions.** The one primary action, then the secondary ones.
4. **States.** Loading, empty, error, done — each written.
5. **Never shows.** What is kept off this screen and where it lives instead.
