# Alpha 6 research: iOS 26 Liquid Glass + HIG rules for the Nadi PWA

Gathered 24 Sep 2026. Every rule has a source URL.
Apple HIG pages were read in full through Apple's own JSON feed
(`developer.apple.com/tutorials/data/design/human-interface-guidelines/<page>.json`), which holds
the same text as the page. Quotes are Apple's wording. Where Apple gives no number, it says so.

Short keys used below:
- MAT = https://developer.apple.com/design/human-interface-guidelines/materials
- LAY = https://developer.apple.com/design/human-interface-guidelines/layout
- TYP = https://developer.apple.com/design/human-interface-guidelines/typography
- TB = https://developer.apple.com/design/human-interface-guidelines/tab-bars
- TOOL = https://developer.apple.com/design/human-interface-guidelines/toolbars
- SHEET = https://developer.apple.com/design/human-interface-guidelines/sheets
- SCROLL = https://developer.apple.com/design/human-interface-guidelines/scroll-views
- COLOR = https://developer.apple.com/design/human-interface-guidelines/color
- A11Y = https://developer.apple.com/design/human-interface-guidelines/accessibility
- W = https://developer.apple.com/design/human-interface-guidelines/writing
- MEET = https://developer.apple.com/videos/play/wwdc2025/219/ (Meet Liquid Glass)
- NDS = https://developer.apple.com/videos/play/wwdc2025/356/ (Get to know the new design system)
- SUI = https://developer.apple.com/videos/play/wwdc2025/323/ (Build a SwiftUI app with the new design)
- UIK = https://developer.apple.com/videos/play/wwdc2025/284/ (Build a UIKit app with the new design)

---

## 1. Liquid Glass

### Where glass goes
- Glass is only for the controls and navigation layer that floats above content. — MAT, MEET
  ("a distinct functional layer for controls and navigation elements — like tab bars and sidebars — that floats above the content layer")
- **Never put glass in the content layer.** Use it for bars, not for cards, rows or lists. — MAT
  ("Don't use Liquid Glass in the content layer.") MEET: making a table view glass "would make it compete with other elements and muddy the hierarchy."
- One exception: a toggle or slider takes on glass only *while being touched*. — MAT
- Use glass sparingly on custom controls. Limit it to "the most important functional elements." — MAT
- Content-layer structure uses standard materials (ultra-thin, thin, regular, thick), not glass. — MAT
- At rest (for example on first launch), content and glass should not overlap. Move or scale the content. — MEET

### Glass on glass
- **Never stack glass on glass.** — MEET ("Always avoid glass on glass.")
- Items sitting on glass use fills, transparency and vibrancy, not a second glass layer. — MEET
- Apply the glass to the control itself, not to views inside it. — NDS

### Variants
- Two variants: regular (default, most system parts) and clear. Never mix them. — MAT, MEET
- Use regular when there is lots of text (alerts, sidebars, popovers). — MAT
- Use clear only over photos or video. Add a dark dimming layer of **35% opacity** if the content behind is bright. — MAT

### Tint and colour
- Glass has no colour of its own. It takes colour from what is behind it. — COLOR
- **Tint only the primary action.** "Refrain from adding color to the background of multiple controls." — COLOR
- To stress a primary action, colour the background, not the symbol or text (like the system Done button). — COLOR
- "When every element is tinted, nothing stands out." Put brand colour in the content layer instead. — MEET
- Do not fake tint with a solid fill. It "breaks the visual character of Liquid Glass." — MEET
- Bar icons and labels are monochrome by default. Do not give tab labels a colour close to the content background. — TB, TOOL, COLOR
- Small glass (tab bar, nav bar) flips light/dark with what is behind it. Large glass (menus, sidebars) does not. — MEET, COLOR

### Scroll edge effect
- Do not put a solid or semi-opaque background under bars. Use a scroll edge effect instead. — LAY
- The effect is a soft blur and fade under the bar. Remove any custom backgrounds or darkening behind bar items. — SUI
- **Only use it where a scroll view sits behind floating UI.** "Scroll edge effects aren't decorative." — SCROLL, NDS
- **One scroll edge effect per view.** Do not mix or stack soft and hard. — SCROLL, NDS
- Prefer the automatic style. Hard style is for dense bars, text outside glass, pinned table headers. — SCROLL, UIK

### Tab bar
- On iPhone the tab bar **floats above content** at the bottom, on glass. — TB
- It can **minimise on scroll down** and re-expands on scroll the other way (`tabBarMinimizeBehavior(.onScrollDown)`). — SUI, UIK
  Note: HIG text ties minimise mainly to tab bars with an accessory (like the Music mini player). — TB
- Tabs are for moving between sections, **never for actions**. Actions go in a toolbar. — TB
- Keep the tab bar visible in every section. Only a modal may cover it. — TB
- Do not hide or disable tabs. If a section is empty, say why. — TB
- Always show tab labels. Use one word where possible. Prefer filled symbols. — TB
- Fewer tabs are easier. Avoid a "More" overflow tab. iPad guidance: aim for **five or fewer**. — TB
- Badges only for critical info. — TB
- Do not put screen-specific actions (like a checkout button) in the tab bar accessory. — NDS

### Toolbars and navigation bar
- Group bar items **by function and how often they are used**. Aim for **at most three groups**. — TOOL, NDS
- Do not place a text button next to a symbol button in one group. It reads as one button. — TOOL, NDS
- Prefer plain system symbols with no borders. Text only where no symbol is clear (for example Edit). — TOOL
- **One primary action, `.prominent` style, on the trailing (right) side.** — TOOL
- Use the standard Back and Close buttons. Do not write "Back" or "Close" as text. — TOOL
- Title: a word or short phrase, **under 15 characters**. Never the app name. — TOOL
- Too crowded? Move secondary actions into a More menu. — TOOL, NDS
- Remove custom bar backgrounds and borders. Hierarchy comes from layout and grouping. — TOOL, NDS

### Sheets (iOS 26)
- Sheets are for a simple, short task. For long or multi-step flows, consider full screen. — SHEET
- **Cancel/Close on the leading (left) edge. Done on the trailing (right) edge.** — SHEET (iOS section)
- iOS 26 look: Done "often as a blue checkmark", tinted and separate. Close is the standard close (X) symbol, not text. — NDS, TOOL
- Always pair Done with Cancel (or Back). Never show Cancel, Done and Back together. — SHEET
- Two detents: **large** (full height) and **medium** (about **half** the full height). — SHEET
- Use medium for progressive disclosure. Skip it when the content needs full height (compose screens). — SHEET
- **Add a grabber** to a resizable sheet. — SHEET
- Support swipe down to dismiss. If there are unsaved changes, confirm with an action sheet. — SHEET
- Show one sheet at a time. Close the first before opening a second. — SHEET
- Partial-height sheets are **inset, with a glass background**. Bottom corners nest into the screen's curve. At full height the glass turns opaque and anchors to the edges. — SUI
- Remove custom sheet backgrounds. — SUI, UIK
- Modal sheets pair glass with a dimming layer behind. — NDS
- Sheets can morph out of the button that opened them. — SUI

---

## 2. Layout and spacing

- Put the most important thing at the top and leading side. — LAY
- Group related items with space, containers or separators. Indent to show "belongs under". — LAY
- Use progressive disclosure: menus, disclosure rows, nested views. — LAY
- Respect safe areas and system margins. — LAY
- Default layout margin for subviews is **8 pt each side**. The root view uses the system minimum margins. — https://developer.apple.com/documentation/uikit/uiview/directionallayoutmargins
- **Side margin 16 pt (compact) / 20 pt (regular): NOT FOUND in current Apple text.** The HIG layout page no longer lists margin numbers. Treat 16/20 as UIKit default behaviour, not a cited rule.
- **Hit target: at least 44 × 44 pt. Absolute minimum 28 × 28 pt.** — https://developer.apple.com/design/human-interface-guidelines/buttons, A11Y
- Spacing between controls: about **12 pt** around bezelled controls, about **24 pt** around borderless ones. — A11Y
- Rows grow with Dynamic Type. Text must not be cropped. Adjacent items may stack at large sizes. — LAY

### Lists (grouped / inset grouped)
- Prefer lists for text. Keep row text short; long text goes to a detail view. — https://developer.apple.com/design/human-interface-guidelines/lists-and-tables
- Grouped style "uses headers, footers, and additional space to separate groups of data." — same page
- A row may have a small leading image then a label (UIListContentConfiguration). — same page
- Drill-in rows use the disclosure chevron. The info (i) button is only for extra info, never navigation. — same page
- Navigation lists keep the selected row highlighted. Option lists flash then show a checkmark. — same page
- **Row height 44 pt, separator inset to the text, section header style: NOT in current HIG text.** Only the 44 pt hit target is cited (above). Separators inset past the leading icon is UIKit default behaviour, not a written rule.

### Corner radii (concentricity)
- Three shapes: fixed radius, capsule (radius = half the height), concentric. — NDS
- **Concentric: inner radius = outer radius − padding.** "Calculate their radius by subtracting padding from the parent's." — NDS
- A button at the bottom of a sheet shares its corner centre with the sheet. — SUI
- Watch for corners that look "pinched or flared". — NDS
- On iPhone, a control near the screen edge: capsule with extra margin. — NDS
- Toolbar custom parts must be concentric with the bar corners. — TOOL
- Reusable card: concentric shape with a fallback radius for when it stands alone. — NDS

---

## 3. Typography

iOS default text size **17 pt**, minimum **11 pt**. — TYP

Dynamic Type at the default "Large" size (size / line height, pt). — TYP

| Style | Weight | Size | Leading | Bold variant |
|---|---|---|---|---|
| Large Title | Regular | 34 | 41 | Bold |
| Title 1 | Regular | 28 | 34 | Bold |
| Title 2 | Regular | 22 | 28 | Bold |
| Title 3 | Regular | 20 | 25 | Semibold |
| Headline | Semibold | 17 | 22 | Semibold |
| Body | Regular | 17 | 22 | Semibold |
| Callout | Regular | 16 | 21 | Semibold |
| Subhead | Regular | 15 | 20 | Semibold |
| Footnote | Regular | 13 | 18 | Semibold |
| Caption 1 | Regular | 12 | 16 | Semibold |
| Caption 2 | Regular | 11 | 13 | Semibold |

- SF Pro tracking at 17 pt: **−0.43 pt**. At 13 pt: −0.08. At 12 pt: 0. — TYP (tracking table)
- Avoid Ultralight, Thin and Light weights. Use Regular, Medium, Semibold, Bold. — TYP
- Use the built-in text styles so text scales with Dynamic Type. — TYP
- Three or more lines: do not use tight leading. — TYP
- Keep truncation low at large sizes. — TYP
- iOS 26 text is "bolder and left-aligned" in alerts and onboarding. — NDS
- **Large title collapses to a standard title on scroll**, and returns at the top. — TOOL (iOS section)
- iOS 26: large title sits at the top of the scroll view and scrolls under the bar. A subtitle can sit under it. — UIK
- Which style when: Apple gives no per-style usage list beyond the table. Headline = heading within content, Footnote = secondary/footer text, Body = reading text (inferred from the TYP definitions of body and headline).

### Contrast (A11Y, WCAG AA)
- Text up to 17 pt: **4.5 : 1**. 18 pt+ or bold: **3 : 1**. Check light and dark. — A11Y

---

## 4. Controls

### Toggle (switch)
- **Switch only inside a list row.** The row text is the label; the switch sits trailing. — https://developer.apple.com/design/human-interface-guidelines/toggles
- Outside a list, use a button that acts like a toggle, not a switch. — same page
- Only for two opposite states. For choosing from a list, use a pop-up button. — same page
- Default green is fine; accent colour allowed if contrast holds. Do not show state by colour alone. — same page
- Help text for a setting: say what it does when ON. People infer OFF. — W

### Segmented control
- **Max about 5 segments on iPhone** (5–7 on wide screens). — https://developer.apple.com/design/human-interface-guidelines/segmented-controls
- Text or icons, never both in one control. Nouns as labels. Equal widths. — same page
- Use it to switch closely related sub-views. For separate app sections use the tab bar. — same page

### Pickers and menus instead of dropdowns
- Short list of choices: use a pull-down or pop-up button (menu), not a picker. — https://developer.apple.com/design/human-interface-guidelines/pickers
- Show a picker in context, near the field. Do not switch screens for it. — same page
- **Compact date picker when space is tight**: a button showing the date in accent colour, opens a calendar. — same page
- Minute steps can be coarser (0, 15, 30, 45). — same page
- Pull-down button: at least **3 items**; for 1–2 use buttons or toggles. Do not hide primary actions in it. — https://developer.apple.com/design/human-interface-guidelines/pull-down-buttons
- Destructive menu items are red and ask for confirmation. — same page

### Text fields
- Placeholder hints the format; also keep a label, since the placeholder disappears. — https://developer.apple.com/design/human-interface-guidelines/text-fields
- Size the field to the expected input. Stack fields vertically. — same page
- Show the right keyboard (number, email). Use a number formatter for money. — same page
- Clear (x) button at the trailing end. — same page
- Validate at the right moment (email: when leaving the field). — same page
- **Boxed vs label-in-row styling: not specified in HIG text.** No cited rule for "no heavy boxes".

### Buttons
- **One prominent (filled, accent) button for the most likely action.** — https://developer.apple.com/design/human-interface-guidelines/buttons
- Show preference by **style, not size**. — same page
- Roles: normal, primary, cancel, destructive. Destructive = system red. — same page
- **Never give the primary role to a destructive button.** — same page
- Labels start with a verb ("Add to Cart"). — same page
- Always show a pressed state. Show a spinner inside the button for slow actions. — same page
- iOS 26 styles: `.glass` and `.glassProminent`; new extra-large size for key actions. — SUI

### Action sheets and menus
- Action sheet, not alert, for choices after a deliberate action. Use sparingly. — https://developer.apple.com/design/human-interface-guidelines/action-sheets
- Destructive choices at the **top**, in destructive style. Cancel at the **bottom**. Never scrolling. — same page
- iOS 26: action sheets spring from the button that opened them. — NDS
- Menus: most-used items first; group related items with a separator. — https://developer.apple.com/design/human-interface-guidelines/menus
- Icons for all items in a group or none. Do not repeat the same icon for related items. — menus, NDS
- Submenus: one level; more than about **5 items** → a new menu. — menus
- Ellipsis (…) when the item needs more input. — menus
- Alerts: up to **3 buttons**. Titles that describe the result ("View All"). "OK" only for pure information. Cancel always titled "Cancel". — https://developer.apple.com/design/human-interface-guidelines/alerts

---

## 5. Forms and settings

- **Keep settings few.** Too many make the app less approachable. — https://developer.apple.com/design/human-interface-guidelines/settings
- Pick good defaults so most people never change them. — settings
- Do not ask for things you can detect yourself. — settings
- Task options belong on the screen they affect, not in Settings. — settings
- Use disclosure to hide advanced options; put common controls at the top. — https://developer.apple.com/design/human-interface-guidelines/disclosure-controls
- Label a disclosure clearly (for example "Advanced Options"). — disclosure-controls
- Grouped lists use section headers and footers. — lists-and-tables
- **"Don't show empty sections": no Apple text found.** Closest: tab bar rule "if a section is empty, explain why". — TB
- NN/g: every field you cut raises completion. Remove fields you can derive or collect later. — https://www.nngroup.com/articles/web-form-design/
- NN/g: single column; labels close to fields; do not use placeholder as the label; mark optional fields; state format rules up front. — same
- NN/g: Cancel much less prominent than Submit; no Reset button. — same
- NN/g: show only the most important options first; more on request. **More than 2 disclosure levels usually tests badly.** — https://www.nngroup.com/articles/progressive-disclosure/

---

## 6. Motion

- Add motion only with purpose. — https://developer.apple.com/design/human-interface-guidelines/motion
- Motion must be optional. Never the only way to show information. — motion
- Keep feedback animations short and precise. Avoid motion on frequent actions. — motion
- Let people cancel or interrupt motion. — motion
- Motion should follow the gesture: slid down to open → slide down to close. — motion
- **Reduce Motion**: cut zoom, scale and side motion; tighten springs; swap x/y/z moves for **fades**. — A11Y
- Glass under Reduce Motion drops its elastic effects automatically. — MEET
- Springs are the default. **Bounce 0** when unsure. **~0.15** = brisk. **0.3** = visibly bouncy. **Avoid above ~0.4**. — https://developer.apple.com/videos/play/wwdc2023/10158/
- Example durations from that session: `spring(duration: 0.5)`, `snappy(duration: 0.4)`, `spring(duration: 0.6, bounce: 0.2)`. — same
- **Exact sheet or push/pop durations: Apple publishes none.** Do not cite a number.
- Sheet dragged up: glass gets more opaque and grows slightly. — NDS
- Prefer dismissing with an explicit action over timers. — A11Y

---

## 7. UX writing

### Apple (W)
- Plain, simple words. No jargon. Fewer words. Read it aloud. — W
- Most important information first on each screen. — W
- **Buttons: use a verb.** "Send" beats "Let's do it!". No "Click here". Say "tap", not "click". — W
- Choose one capitalisation per element type and stay consistent. — W
  Apple's own components lean to title case (menus, alert titles). — menus, alerts
- **Use "my/your" sparingly** ("Favorites" not "Your Favorites"). **Never "we".** "Unable to load content", not "We're having trouble…". — W
- Multi-step flows: pick "Continue" or "Next" and keep it. — W
- Settings labels: practical. Explain what ON does. — W
- **Empty states: say what to do next, with a button if possible.** Don't put crucial info there. — W
- **Errors: next to the problem, no blame, say how to fix.** "Choose a password with at least 8 characters" beats "That password is too short". No "oops". — W
- Label every field; use hints like "name@example.com". Errors next to the field. — W
- Alert titles: never just "Error". Describe what happened and why. — alerts

### Support sources
- GOV.UK: plain English is mandatory. Avoid jargon and buzzwords. Short words over long. **Active voice.** Split sentences over **25 words**. Paragraphs max **5 sentences**. Address the reader as "you". — https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-language/
- Mailchimp: "Write short sentences and use familiar words. Avoid jargon and slang." Links say where they go. — https://styleguide.mailchimp.com/writing-for-accessibility/
- NN/g errors: next to the field; plain words; say exactly what went wrong; offer a fix; **avoid "invalid", "illegal", "incorrect"**; keep what the person typed; don't show errors too early; never colour alone. — https://www.nngroup.com/articles/error-message-guidelines/
- NN/g empty states: never totally blank; short status message; a direct action (for example a Create button); don't show a loading state as "no data". — https://www.nngroup.com/articles/empty-state-interface-design/
- **Sentence case vs title case: no NN/g article found** (the URL tried returned 404). Apple asks for consistency, not a case. GOV.UK uses sentence case throughout its own pages.

### Applied to our jargon (inference from the rules above, not a quote)
- "Posting date" → "Date". "Accounting dimensions" → hide. "Exchange gain/loss" → hide. All fail W "avoid jargon" and GOV.UK "avoid jargon".

---

## 8. Long lists

- NN/g: infinite scroll suits browsing. It is bad for **finding a specific item, comparing, or checking the top few**. — https://www.nngroup.com/articles/infinite-scrolling-tips/
- NN/g: a **"Load more" button** stops the endless flow, shows more exists, and saves data. Cost: one extra tap. — same
- NN/g: no pattern wins everywhere. — same
- Apple (watchOS, but stated generally): show the most relevant items and "a way for people to view more". — lists-and-tables
- Apple: long row text → titles only, detail on tap. — lists-and-tables
- NN/g accordions: collapse loosely related groups; keep headings visible; allow several open; remember open/closed state. — https://www.nngroup.com/articles/mobile-accordions/
- NN/g: submenus work best with **fewer than 6** items; lists spanning 3+ screens are hard to use. — https://www.nngroup.com/articles/mobile-subnavigation/
- NN/g: if people need most of the content, show it all; collapsing helps when they need a few pieces. — https://www.nngroup.com/articles/accordions-complex-content/
- For the claim list, the fit is: open items first, history grouped (for example by month) and collapsed, "Show more" not endless scroll. That is an inference from the above, not a single quoted rule.

---

## Not found or not fetchable
- The HIG HTML pages render empty for the fetch tool. Read through Apple's JSON feed instead (same text).
- HIG "navigation-bars" JSON is empty. The content now lives under Toolbars (TOOL).
- No current Apple text gives: 16/20 pt side margins, 44 pt row height, separator inset, section header text style, sheet or push animation durations.
- No NN/g sentence-case article at the tried URL (404).
