# iOS 26 component spec for the Nadi PWA (alpha 7 research)

Gathered 24 Sep 2026. Read-only research. Builds on `docs/glass/plan/alpha6-research.md` (not repeated here).
Rule: every number has a source. Where Apple gives no number: **not published**.
Where a number comes from a third party (measured, not Apple), it is marked **[measured, non-Apple]**.

HIG pages read via `https://developer.apple.com/tutorials/data/design/human-interface-guidelines/<slug>.json`.
API docs read via `https://developer.apple.com/tutorials/data/documentation/<framework>/<symbol>.json`.
WWDC25 transcripts read from the session pages.

Short keys:
- TB = https://developer.apple.com/design/human-interface-guidelines/tab-bars (changelog: 8 Jun 2026 "Updated terminology and art")
- TOOL = https://developer.apple.com/design/human-interface-guidelines/toolbars
- SF = https://developer.apple.com/design/human-interface-guidelines/search-fields (changelog: 8 Jun 2026 "refined guidance for search as a tab in iOS")
- SHEET = https://developer.apple.com/design/human-interface-guidelines/sheets (changelog: 24 Mar 2026 "Updated guidance for button placement")
- COLOR = https://developer.apple.com/design/human-interface-guidelines/color (changelog: 9 Jun 2025 "Updated system color values")
- TYP = https://developer.apple.com/design/human-interface-guidelines/typography
- BTN = https://developer.apple.com/design/human-interface-guidelines/buttons
- TOG = https://developer.apple.com/design/human-interface-guidelines/toggles (last changed Mar 2024 — no iOS 26 update)
- MENU = https://developer.apple.com/design/human-interface-guidelines/menus
- ICON = https://developer.apple.com/design/human-interface-guidelines/app-icons
- LAUNCH = https://developer.apple.com/design/human-interface-guidelines/launching
- HAPT = https://developer.apple.com/design/human-interface-guidelines/playing-haptics
- SYM = https://developer.apple.com/design/human-interface-guidelines/sf-symbols
- MEET = https://developer.apple.com/videos/play/wwdc2025/219/
- NDS = https://developer.apple.com/videos/play/wwdc2025/356/
- SUI = https://developer.apple.com/videos/play/wwdc2025/323/
- UIK = https://developer.apple.com/videos/play/wwdc2025/284/

---

## 1. Tab bar (iPhone, iOS 26)

| Item | Spec | Source |
|---|---|---|
| Position | "floats above content at the bottom of the screen. Its items rest on a Liquid Glass background" | TB |
| Height | **not published** for iOS. (HIG gives 68 pt only for **tvOS**.) One developer measured 62 pt reserved height **[measured, non-Apple, unverified]** | TB; search result via github.com/pixelbuyte/Skintel/pull/35 |
| Inset from screen edges / bottom | **not published**. Only rule: on phone, "use a capsule with extra margin to create space near the screen edge" | NDS |
| Shape | Capsule. "Capsules use a radius that's half the height of the container"; capsule is used "in bars" | NDS |
| Selected-item highlight ("lens") | **No published size or colour.** Apple describes glass "lensing" generally and controls that "lift up into Liquid Glass temporarily ... when you interact". tvOS only: "only the selected tab is opaque" | MEET, TB |
| Icon vs label layout | Compact width: icon **above** label. Regular width: side by side | TB |
| Icon style | Prefer **filled** SF Symbols; "an iOS tab bar prefers the fill variant" | TB, SYM |
| Label size / weight | **not published** in HIG text | — |
| Icon point size | **not published** | — |
| Labels | Always shown, monochrome by default | TB (see alpha6) |
| Minimize on scroll | `TabBarMinimizeBehavior`: `.automatic`, `.never`, `.onScrollDown`, `.onScrollUp`. "A minimized tab bar becomes smaller so that the content behind it has more room." Re-expands on scroll the opposite way. Exit minimized state "by tapping a tab or scrolling to the top" | https://developer.apple.com/documentation/swiftui/tabbarminimizebehavior, SUI, UIK, TB |
| What the minimized bar looks like | Not specified numerically. With an accessory, "the accessory view animates down to display inline with the tab bar" | UIK |
| Bottom accessory | `tabViewBottomAccessory(content:)` — sits **above** the tab bar; only for app-wide features (Music mini player). No screen-specific actions | UIK, NDS, https://developer.apple.com/documentation/swiftui/view/tabviewbottomaccessory(content:) |
| Search tab | "A tab bar can include a dedicated search tab at the trailing end." SwiftUI: `Tab(role: .search)` + `.searchable` on the `TabView`. "When someone selects this tab, a search field takes the place of the tab bar." A search-role tab "is separated from your other tabs" (shown as its own glass circle) | TB, SUI, https://developer.apple.com/documentation/swiftui/tabrole/search, donnywals.com/exploring-tab-bars-on-ios-26-with-liquid-glass/ |
| Two search-tab styles (HIG June 2026) | **Standard tab**: looks like other tabs, opens a search landing page with field at top. **Button appearance**: separate button, tapping focuses the field and shows the keyboard at once, returns to previous tab on exit | SF |
| UIKit auto-focus | `automaticallyActivateSearch = true` on the search tab | UIK |
| Max tabs | **No hard number for iPhone.** "Avoid overflow tabs"; when space runs out "the trailing tab becomes a More tab". The iPad "five or fewer" guidance is in alpha6 | TB |
| Badge | "a red oval containing white text and either a number or an exclamation point" | TB |

## 2. Navigation bar (top toolbar)

| Item | Spec | Source |
|---|---|---|
| Large title size | **34 pt, Regular, leading 41; emphasized = Bold.** The nav bar uses the bold variant (system behaviour; HIG table lists Large Title Regular 34/41 with Bold emphasized) | TYP |
| Inline (collapsed) title | **not published** as a number. In practice it is the Headline style (17 pt Semibold) — inference, not Apple text | TYP (Headline row) |
| Collapse behaviour | "a large title transitions to a standard title as people begin scrolling the content, and transitions back to large when people scroll to the top" | TOOL (iOS section) |
| Where large title sits (iOS 26) | "Large titles are now placed at the top of the content scroll view, and scroll with the content underneath the bar." Extend scroll view fully under the bar | UIK |
| Subtitle under large title | `largeSubtitleView` (UIKit) / `ToolbarItemPlacement.largeSubtitle` (SwiftUI): "items in the navigation bar's large title subtitle area" (Mail's filter button) | UIK, https://developer.apple.com/documentation/uikit/uinavigationitem/largesubtitleview, https://developer.apple.com/documentation/swiftui/toolbaritemplacement/largesubtitle |
| Bar background | "the bar background is now transparent by default." Remove `UIBarAppearance`/`backgroundColor` | UIK |
| Bar buttons | "Bar buttons use a glass background." Image buttons **share** one glass background; "Text buttons, the system Done and Close buttons, and prominent style buttons have separate glass backgrounds" | UIK |
| Grouping | `ToolbarSpacer` ("a standard space item in toolbars"); each flexible space separates backgrounds | https://developer.apple.com/documentation/swiftui/toolbarspacer, UIK |
| Back button | Standard Back = chevron symbol, no "Back" text; system back is grouped **separately** from custom items (so it is its own glass circle). Exact circle size **not published** | TOOL, SUI |
| Back gesture (iOS 26) | Swipe back **anywhere in the content area**, not just the edge; back can be tapped repeatedly mid-transition | UIK |
| Avatar / account button | Allowed as a toolbar item **without** glass: "Some toolbar items can do without this visual grouping, like this item from Books showing my avatar. Apply the sharedBackgroundVisibility modifier to separate an item into its own group without a background." Placement in large-title row: **not published** | SUI |
| Title length | under 15 characters | TOOL (alpha6) |
| Nav bar height | **not published** | — |

## 3. Inset grouped list (Settings style)

| Item | Spec | Source |
|---|---|---|
| Style | `InsetGroupedListStyle` / `.insetGrouped`; grouped style "uses headers, footers, and additional space to separate groups" | https://developer.apple.com/documentation/swiftui/insetgroupedliststyle, https://developer.apple.com/design/human-interface-guidelines/lists-and-tables |
| Group corner radius (iOS 26) | **not published.** Apple only says capsule/concentric geometry is "echoed in ... the rounded corners of grouped table views". Apple forum threads confirm the radius cannot even be read at runtime (`effectiveRadius` returns 0) | NDS; https://developer.apple.com/forums/thread/794685 |
| Row minimum height (iOS 26) | **52 pt** minimum for a stock cell; row = content + 30 pt (15 top + 15 bottom margins) **[measured, non-Apple, iOS 26.5 simulator]**. iOS 18 and earlier: 44 pt | https://github.com/water-rs/apple-backend/pull/186 |
| Row content margins | top 15 / leading 16 / bottom 15 / trailing 16 pt (`UIListContentConfiguration.cell().directionalLayoutMargins`) **[measured, non-Apple]** | same PR |
| Row with icon | Height rule same (min 52 pt). Icon tile size/radius: **not published** | — |
| Separator inset | **not published** (UIKit default: inset to the text, past the icon) | — |
| Separator colour | `separator` (see §4). Materials: "a single, default vibrancy value for a separator" | COLOR, https://developer.apple.com/design/human-interface-guidelines/materials |
| Section header/footer text style | **not published** | — |
| Gap between groups | **not published** ("additional space") | lists-and-tables |
| Disclosure chevron size/colour | **not published** | — |
| Value text colour | **not published** (convention: `secondaryLabel`) | — |
| Backgrounds | Grouped list uses `systemGroupedBackground` (page) + `secondarySystemGroupedBackground` (cells) | COLOR |

## 4. System colours (exact values)

### 4a. Accent colours — Apple-published, iOS 26 values ("Updated system color values", 9 Jun 2025)
Source: COLOR (values read from the image alt text in the HIG JSON). sRGB 0–255.

| Name | Light | Dark | Increased contrast light | Increased contrast dark |
|---|---|---|---|---|
| Red | 255,56,60 `#FF383C` | 255,66,69 `#FF4245` | 233,21,45 | 255,97,101 |
| Orange | 255,141,40 `#FF8D28` | 255,146,48 `#FF9230` | 197,83,0 | 255,160,86 |
| Yellow | 255,204,0 | 255,214,0 | 161,106,0 | 254,223,67 |
| Green | 52,199,89 `#34C759` | 48,209,88 `#30D158` | 0,137,50 | 74,217,104 |
| Mint | 0,200,179 | 0,218,195 | 0,133,117 | 84,223,203 |
| Teal | 0,195,208 | 0,210,224 | 0,129,152 | 59,221,236 |
| Cyan | 0,192,232 | 60,211,254 | 0,126,174 | 109,217,255 |
| Blue | **0,136,255 `#0088FF`** | **0,145,255 `#0091FF`** | 30,110,244 | 92,184,255 |
| Indigo | 97,85,245 | 109,124,255 | 86,74,222 | 167,170,255 |
| Purple | 203,48,224 | 219,52,242 | 176,47,194 | 234,141,255 |
| Pink | 255,45,85 | 255,55,95 | 231,18,77 | 255,138,196 |
| Brown | 172,127,94 | 183,138,102 | 149,109,81 | 219,166,121 |

Note: iOS 26 changed Blue (old `#007AFF` → `#0088FF`), Red (old `#FF3B30` → `#FF383C`), Orange (old `#FF9500` → `#FF8D28`). Green light is unchanged (`#34C759`).

### 4b. System grays — Apple-published (COLOR)
| Name | Light | Dark | IC light | IC dark |
|---|---|---|---|---|
| systemGray | 142,142,147 | 142,142,147 | 108,108,112 | 174,174,178 |
| systemGray2 | 174,174,178 | 99,99,102 | 142,142,147 | 124,124,128 |
| systemGray3 | 199,199,204 | 72,72,74 | 174,174,178 | 84,84,86 |
| systemGray4 | 209,209,214 | 58,58,60 | 188,188,192 | 68,68,70 |
| systemGray5 | 229,229,234 | 44,44,46 | 216,216,220 | 54,54,56 |
| systemGray6 | 242,242,247 | 28,28,30 | 235,235,240 | 36,36,38 |

### 4c. Semantic colours — **Apple does not publish values** (COLOR lists names only; values "may change across OS versions")
Best available values are a runtime dump from iOS 13 **[measured, non-Apple]** — https://noahgilmore.com/blog/dark-mode-uicolor-compatibility . No iOS 26 dump was found; no source says they changed.

| Name | Light rgba | Dark rgba |
|---|---|---|
| systemBackground | 255,255,255,1 | 0,0,0,1 |
| secondarySystemBackground | 242,242,247,1 | 28,28,30,1 |
| tertiarySystemBackground | 255,255,255,1 | 44,44,46,1 |
| systemGroupedBackground | 242,242,247,1 | 0,0,0,1 |
| secondarySystemGroupedBackground | 255,255,255,1 | 28,28,30,1 |
| tertiarySystemGroupedBackground | 242,242,247,1 | 44,44,46,1 |
| label | 0,0,0,1 | 255,255,255,1 |
| secondaryLabel | 60,60,67,0.60 | 235,235,245,0.60 |
| tertiaryLabel | 60,60,67,0.30 | 235,235,245,0.30 |
| quaternaryLabel | 60,60,67,0.18 | 235,235,245,0.18 |
| placeholderText | 60,60,67,0.30 | 235,235,245,0.30 |
| separator | 60,60,67,0.29 | 84,84,88,0.60 |
| opaqueSeparator | 198,198,200,1 | 56,56,58,1 |
| systemFill | 120,120,128,0.20 | 120,120,128,0.36 |
| secondarySystemFill | 120,120,128,0.16 | 120,120,128,0.32 |
| tertiarySystemFill | 118,118,128,0.12 | 118,118,128,0.24 |
| quaternarySystemFill | 116,116,128,0.08 | 118,118,128,0.18 |
| link | 0,122,255,1 | 9,132,255,1 (iOS 13 value; iOS 26 link likely follows new Blue — unverified) |

## 5. Search (iPhone)

| Item | Spec | Source |
|---|---|---|
| Placements | As a tab; in a bottom toolbar; in a top toolbar (nav bar); inline above a list | SF |
| Default | "Place search at the bottom if there's room" (Settings: only item; Mail/Notes: alongside others). Top only when bottom content must not be covered | SF |
| Bottom toolbar behaviour | "either as an expanded field or as a toolbar button ... When someone taps it, it animates into a search field above the keyboard" | SF |
| Minimized search | `searchToolbarBehavior(.minimize)` — "On iPhone, the search field in the bottom toolbar can be configured to appear as a button-like control when inactive." System may minimize on its own depending on space | https://developer.apple.com/documentation/swiftui/view/searchtoolbarbehavior(_:), SUI |
| API | `searchable(text:placement:prompt:)`, placement default `.automatic`; `.toolbar` = "The search field appears in the toolbar" | https://developer.apple.com/documentation/swiftui/view/searchable(text:placement:prompt:), https://developer.apple.com/documentation/swiftui/searchfieldplacement/toolbar |
| Field anatomy | "displays a Search icon, a Clear button, and placeholder text"; default placeholder "Search" | SF, https://developer.apple.com/documentation/swiftui/adding-a-search-interface-to-your-app |
| Mic (dictation) icon | **not mentioned** in HIG text | — |
| Field height / radius | **not published** (glass capsule by default per `glassEffect` default shape — inference) | — |
| With tab bar visible (UIKit) | "When the tab bar is visible, the search bar is placed below it" (iPad context) | UIK |

## 6. Sheets (iOS 26)

| Item | Spec | Source |
|---|---|---|
| Detents | `large` (full) and `medium`: "approximately half the height of the screen, and is inactive in compact height". Custom detents allowed. Default = large only | SHEET, https://developer.apple.com/documentation/swiftui/presentationdetent/medium, https://developer.apple.com/documentation/swiftui/view/presentationdetents(_:) |
| Inset at partial height | "partial height sheets are inset by default with a Liquid Glass background" | SUI |
| Full height | "the glass background gradually transitions, becoming opaque and anchoring to the edge of the screen" | SUI |
| Drag up | glass "becoming more opaque and gently growing in size" | NDS |
| Corner radius | **not published** as a number. Concentric with device ("controls nest perfectly into the rounded corners of windows"); a bottom button "should share the same corner center with the corners of the sheet". Override API exists: `presentationCornerRadius(_:)` | SUI, MEET, https://developer.apple.com/documentation/swiftui/view/presentationcornerradius(_:) |
| Inset distance | **not published** | — |
| Grabber | "small horizontal indicator ... at the top edge"; tap cycles detents; VoiceOver-operable. Off by default in UIKit (`prefersGrabberVisible = false`). Size **not published** | SHEET, https://developer.apple.com/documentation/uikit/uisheetpresentationcontroller/prefersgrabbervisible |
| Toolbar | Cancel/Close **leading**, Done **trailing** (single-view sheet). Multi-step sheets: placement varies per step (Mar 2026 update) | SHEET |
| Done look | "stays separate and appears tinted, often as a blue checkmark on iOS" | NDS |
| Close look | Standard Close symbol (xmark), no text; system Close has its own glass background | TOOL, UIK |
| Placement API | `ToolbarItemPlacement.confirmationAction` = "confirmation actions in a modal interface" | https://developer.apple.com/documentation/swiftui/toolbaritemplacement/confirmationaction |
| Morph from button | "Sheets can also directly morph out of buttons that present them" — via `matchedTransitionSource(id:in:)` + `navigationTransition(.zoom)` | SUI, https://developer.apple.com/documentation/swiftui/view/matchedtransitionsource(id:in:) |

## 7. Buttons (iOS 26)

| Item | Spec | Source |
|---|---|---|
| `.glass` | "applies a Liquid Glass effect based on the button's context" | https://developer.apple.com/documentation/swiftui/primitivebuttonstyle/glass |
| `.glassProminent` | "applies a prominent Liquid Glass effect" (tinted glass; "the approach the system uses for prominent button styling") | https://developer.apple.com/documentation/swiftui/primitivebuttonstyle/glassprominent, COLOR |
| UIKit | `UIButton.Configuration.glass()` / `.prominentGlass()` | https://developer.apple.com/documentation/uikit/uibutton/configuration-swift.struct/glass() |
| Shape | "Bordered buttons now have a capsule shape by default." "Large controls will now use capsule shapes" | SUI, NDS |
| Sizes | `ControlSize`: mini, small, regular, large, **extraLarge** ("The largest control size. Resolves to large on platforms other than visionOS"). Note: this doc says extraLarge falls back to large outside visionOS — conflicts with SUI's "support for extra large sized buttons"; verify on device | https://developer.apple.com/documentation/swiftui/controlsize/extralarge, SUI |
| Heights (iOS) | **not published.** Only visionOS publishes: Mini 28, Small 32, Regular 44, Large 52, Extra large 64 pt | BTN (visionOS section) |
| Hit target | 44×44 pt (alpha6) | BTN |
| Interaction | Glass "reacts to user interaction by scaling, bouncing, and shimmering"; use `Glass.interactive()` for custom controls | SUI, https://developer.apple.com/documentation/swiftui/glass |

## 8. Toggle (switch)

| Item | Spec | Source |
|---|---|---|
| Size change | "Sizes are updated slightly for controls like UISwitch. Check that your layouts are set up to accommodate size updates." **Exact size not published.** Old size 51×31 pt. A "63×28" figure could not be verified from any source | UIK; openradar 31777116 (old size) |
| Shape | Capsule; "mirrored proportions of sliders and switches" | NDS |
| Thumb | "Control thumbs, like those on switch and segmentedControl, automatically have a new liquid glass appearance for interactions" — glass only while touched | UIK, SUI |
| Colour | Default green (systemGreen, §4a); accent colour allowed with enough contrast | TOG |
| Use | Only inside a list row | TOG |

## 9. Menus, context menus, pull-down buttons

| Item | Spec | Source |
|---|---|---|
| Morph | "When a presentation, like a menu or a popover is originated from a glass button, the button morphs into the overlay. Menus get this behavior automatically." "the bubble simply pops open" | UIK, MEET |
| Material | Menus are large glass: "more pronounced lensing ... deeper, richer shadows"; large glass does **not** flip light/dark | MEET |
| Layouts (iOS) | Small: row of **4** icon-only items on top; Medium: row of **3** icon+short label on top; Large (default): all items in a list. API `preferredElementSize` | MENU |
| Anatomy | "selection indicator, icon, label, and accessory item" | NDS |
| Symbols | Bars and menus "rely more on symbols than text"; don't repeat icons for related actions | NDS |
| Destructive | Context menu: destructive items at the **end**, red | https://developer.apple.com/design/human-interface-guidelines/context-menus |
| Row height, width, radius | **not published** | — |

## 10. Motion and haptics

| Item | Spec | Source |
|---|---|---|
| SwiftUI default spring | `.spring` = `spring(response: 0.5, dampingFraction: 0.825)`; `spring(duration: 0.5, bounce: 0.0)` | https://developer.apple.com/documentation/swiftui/animation/spring(response:dampingfraction:blendduration:), https://developer.apple.com/documentation/swiftui/animation/spring(duration:bounce:blendduration:) |
| Presets | `.smooth` (0.5 s, no bounce), `.snappy` (0.5 s, "small amount of bounce"), `.bouncy` (0.5 s, "higher amount of bounce"); all tunable with `extraBounce` | https://developer.apple.com/documentation/swiftui/animation/smooth(duration:extrabounce:) and siblings |
| Push / sheet / tab switch springs | **not published** | — |
| Glass morph | `GlassEffectContainer(spacing:)`: "As shapes near one another, their paths start to blend ... The higher the spacing, the sooner blending begins." `glassEffectID(_:in:)` pairs shapes across states | https://developer.apple.com/documentation/swiftui/glasseffectcontainer, https://developer.apple.com/documentation/swiftui/view/glasseffectid(_:in:) |
| Appear/disappear | "Instead of fading, Liquid Glass objects materialize in and out by gradually modulating the light bending and lensing" | MEET |
| Touch feedback | "the material illuminates from within" | MEET |
| Haptic types | Notification (success, warning, error), Impact, Selection ("while the values of a UI element are changing"). SwiftUI: `sensoryFeedback(_:trigger:)` | HAPT, https://developer.apple.com/documentation/swiftui/view/sensoryfeedback(_:trigger:) |
| Web note | Safari has no haptics API for web pages (no Vibration API on iOS) — known platform limit, not an Apple doc quote | — |

## 11. App icon and launch

| Item | Spec | Source |
|---|---|---|
| Native iOS 26 icon | Layered (background + 1 or more foreground layers), built in **Icon Composer**; system adds specular highlights, refraction, translucency | ICON, https://developer.apple.com/design/resources/ |
| Canvas | **1024×1024 px**, square, unmasked; system masks the rounded corners | ICON |
| Appearances | Default, dark, clear light, clear dark, tinted light, tinted dark | ICON |
| Don't bake in | "no need to include specular highlights, drop shadows ..., beveled edges, blurs, glows" | ICON |
| Web app (home screen) | `<link rel="apple-touch-icon" sizes="180x180">` for iPhone (152 / 167 iPad). Square PNG; iOS 7+ adds no effects; system rounds corners | https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html |
| Web app and Liquid Glass icon | **No documented way** for a web app to supply a layered/glass or dark/tinted icon. Not found | — |
| iOS 26 web-app behaviour | Every site added to Home Screen opens as a web app by default ("Open as Web App" toggle) | https://webkit.org/blog/17333/webkit-features-in-safari-26-0/ |
| Launch image | `apple-touch-startup-image`; default is a screenshot of last launch | archive doc above |
| Launch rules | Nearly identical to first screen; no text; no logo/branding; not a splash | LAUNCH |

## 12. Typography

| Item | Spec | Source |
|---|---|---|
| Text vs Display switch | **No longer a fixed 20 pt switch in current HIG.** "system fonts support dynamic optical sizes, which merge discrete optical sizes (like Text and Display) ... into a single, continuous design". Web: `-apple-system` / `system-ui` gets this automatically; `font-optical-sizing: auto` | TYP |
| Tracking | "In a running app, the system font dynamically adjusts tracking at every point size" | TYP |
| iOS 26 weight change | No change to the Dynamic Type table weights. Dec 2025: "Added emphasized weights to the Dynamic Type style specifications". Emphasized weights "can be medium, semibold, bold, or heavy". NDS: text in alerts/onboarding is "bolder and left-aligned" | TYP, NDS |

SF Pro tracking (TYP, iOS table), size pt → tracking pt (1/1000 em in brackets):

| pt | track | pt | track | pt | track |
|---|---|---|---|---|---|
| 11 | +0.06 (+6) | 19 | −0.45 (−24) | 27 | +0.29 (+11) |
| 12 | 0.00 (0) | 20 | −0.45 (−23) | 28 | +0.38 (+14) |
| 13 | −0.08 (−6) | 21 | −0.36 (−18) | 29 | +0.40 (+14) |
| 14 | −0.15 (−11) | 22 | −0.26 (−12) | 30 | +0.40 (+14) |
| 15 | −0.23 (−16) | 23 | −0.10 (−4) | 31 | +0.39 (+13) |
| 16 | −0.31 (−20) | 24 | +0.07 (+3) | 32 | +0.41 (+13) |
| 17 | −0.43 (−26) | 25 | +0.15 (+6) | 33 | +0.40 (+12) |
| 18 | −0.44 (−25) | 26 | +0.22 (+8) | 34 | +0.40 (+12) |

Web use: `letter-spacing` in em = the 1/1000 em column ÷ 1000 (e.g. 17 pt → −0.026em; 34 pt → +0.012em). Only needed with a non-system font; the system font on iOS Safari already applies it.

---

## Not published by Apple (do not invent)
- Tab bar: height, edge/bottom inset, label size/weight, icon size, selected-pill size/colour, iPhone max tabs.
- Nav bar: height, inline title size (Headline is inference), back-button glass circle size, avatar placement in large title.
- Inset grouped list: corner radius, row height (52 pt is a non-Apple measurement), icon tile size/radius, separator inset, header/footer style, gap between groups, chevron size/colour, value colour.
- Semantic colours (backgrounds, labels, separators, fills): Apple publishes names only; values are an iOS 13 runtime dump.
- Search field: height, radius, mic icon.
- Sheets: corner radius number, inset distance, grabber size.
- Buttons: iOS heights per size (only visionOS has numbers).
- Switch: iOS 26 dimensions ("updated slightly" only).
- Menus: row height, width, radius.
- Springs for push, sheet, tab switch.
- A way for a web app to supply a layered/Liquid Glass or dark/tinted icon.

## Open conflicts to check on a real device
- `ControlSize.extraLarge` doc says it resolves to `.large` outside visionOS, but WWDC25 323 says iOS gets extra-large buttons.
- Apple's UI kit page now lists iOS 27 kits (https://developer.apple.com/design/resources/); iOS 26 kit specs are only inside the Figma/Sketch files.
