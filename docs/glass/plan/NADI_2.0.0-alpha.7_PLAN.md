# Nadi 2.0.0-alpha.7 — plan: from "follows Apple's rules" to "looks and behaves like Apple built it"

**Status:** proposal, for the owner's go. Nothing is coded.
**Owner's ask (25 Sep 2026):** exact 1:1 with iOS 26/27 Liquid Glass, small to big; UI and UX; what an
Apple engineer would do; broaden alpha.6's list; no hand-rolled "AI slop"; new features allowed if backed.

## Evidence this plan stands on (all in `docs/glass/plan/`)

| File | What |
|---|---|
| `alpha7-ios26-spec.md` | Apple's own numbers (HIG JSON, SwiftUI/UIKit docs, WWDC25 219/356/323/284 transcripts). Marks every "not published". |
| `alpha7-web-native.md` | What Safari / iOS Home Screen web apps can do, per version (MDN compat data 17 Sep 2026, WebKit blog 18.0 → 27.0, caniuse). |
| `alpha7-handrolled.md` | Nadi code sweep, file:line: frappe-ui leftovers, hand-built lists, fonts, animations. |
| `alpha7-nadi-measure.json` | Nadi measured at iPhone size (402 pt, 3×). |
| Owner's screenshots | iOS 26 **Settings** and **App Store**, measured pixel by pixel below. |

**Honesty rule.** Apple publishes colours, type, springs and behaviour — but NOT most component sizes (tab bar,
list radius, sheet radius, switch). Where Apple is silent, the number here is **measured from the owner's own
iPhone screenshots** and says so. Nothing is invented.

---

## 1. How close is alpha.6? Measured, side by side

iOS numbers: owner's iPhone screenshots (1206×2622 = 402×874 pt at 3×) unless marked Apple.
Nadi numbers: the alpha.6 build, same viewport.

| Detail | iOS 26 (measured / Apple) | Nadi alpha.6 | Match |
|---|---|---|---|
| Page background, dark | #000000 pure black (Settings) | #07070A | ✗ close |
| Grouped cell, dark | #1C1C1E (28,28,30) (Settings; = Apple systemGray6 dark) | #15171D (21,23,29), bluish | ✗ |
| Cell label | #FFFFFF, 17 pt | #FFFFFF, **15 pt** (lists) / 17 (forms) | ✗ lists |
| Value text ("On", "NASTY Guest") | (158,157,164) ≈ secondaryLabel | ink2 #A8AEB8 | ~ |
| Separator | (56,55,59) 1 px, starts at **74 pt** (after 30 pt icon tile) | hair rgba(255,255,255,.075), inset 16 | ✗ |
| Group corner radius | **26 pt** (measured; Apple: not published) | 16 pt (forms), 20 (list panel) | ✗ |
| Group side margin | 16 pt | 16 pt | ✓ |
| Gap between groups | **35 pt** | 24 pt (forms) | ✗ |
| Row height (with icon) | **54 pt** | 56 (lists) / 44 (forms) | ✗ |
| Icon tile | **29×28 pt**, filled colour tile, white glyph | 32 pt grey tile, grey outline glyph | ✗ |
| Large title | **34 pt bold**, left 17 pt, under the status bar, scrolls away | **20 pt** semibold inline title beside a logo | ✗ biggest gap |
| Account row (avatar + name + subtitle) | 44 pt circle avatar, name 20 pt semibold, subtitle secondary | square 72 pt tile, name bold | ✗ |
| Avatar button top-right | circle, tinted gradient initials (App Store) | rounded square, flat | ✗ |
| Tab bar | floating glass capsule, **~61 pt** tall, inset **~20 pt**, selected tab = **glass "lens" pill** behind icon+label, blue tint | capsule 66 pt, inset 16, selected = bold white label, no lens | ~ |
| Search | bottom glass capsule with mic (Settings), or search tab | none | ✗ missing |
| Buttons | capsule; "Get" = tinted glass capsule (App Store) | lime filled capsule 48 | ~ |
| Accent | system blue #0088FF (iOS 26 dark #0091FF) | lime #C8FF00 | ✗ by design (brand) — see Q1 |
| Switch | iOS 26 wider track, white knob, green when on | hand-built button, lime track, BLACK knob | ✗ |
| Chevron | grey (≈158) thin | grey thin | ✓ |
| Text font | SF Pro (system) | -apple-system first, but Inter / Inter Tight / JetBrains Mono also downloaded | ~ |

**Verdict: about 60% of the way.** The structure (groups, rows, sheets, words, sizes on the ramp) is right since
alpha.6. What still gives it away: no large titles, the wrong greys, rows and icon tiles off by a few points,
a hand-built switch, no search, no selected "lens" in the tab bar, and the lime brand used where iOS uses its accent.

---

## 2. What an Apple engineer would do — the alpha.7 work

Grouped by what the person notices first. Each line: change · evidence · how we prove it.

### A. The frame of every screen (biggest visible gap)
| # | Change | Evidence | Proof |
|---|---|---|---|
| A1 | **Large title** on every tab root (34 pt bold, left 16), scrolling away into a centred 17 pt inline title in the glass bar | HIG Toolbars/Navigation; WWDC25 284 ("large title sits at the top of the scroll view"); Settings/App Store screenshots | measure: title 34 pt at rest, inline after 44 pt scroll |
| A2 | Nadi logo leaves the title position (the title IS the header); logo lives on the login and splash only | HIG: title is never the app name | screenshot |
| A3 | Avatar: **circle**, 36 pt in the bar, initials on a subtle gradient, opts out of glass | App Store screenshot; `sharedBackgroundVisibility` (ios26-spec) | measure |
| A4 | Tab bar: the **selected-tab lens** (a glass pill behind the selected icon+label); height 61, inset 20; minimise on scroll down | App Store screenshot; `tabBarMinimizeBehavior(.onScrollDown)` (SUI, WWDC25 323) | measure + scroll test |
| A5 | **Search**: a trailing search control in the tab bar that opens app-wide search (people, requests, SOPs, days) | HIG Search tab (June 2026 update); Settings/App Store both have it | journey: find a request by name |

### B. Colours and materials to Apple's semantic set
| # | Change | Evidence |
|---|---|---|
| B1 | Dark: page #000, grouped cell #1C1C1E, elevated #2C2C2E; light: page #F2F2F7, cell #FFFFFF (Apple system background set) | ios26-spec §4; Settings pixels (28,28,30) |
| B2 | Text: label white / secondaryLabel (235,235,245,0.6) / tertiary 0.3; separator (84,84,88,0.6) | ios26-spec §4 |
| B3 | Status colours = Apple system colours iOS 26 (green #30D158 dark, red #FF4245, orange #FF9230, blue #0091FF) instead of custom chip inks | ios26-spec §3 (HIG Color, iOS 26 values) |
| B4 | **Accent decision (Q1)** — see §4 | HIG Color: one tint colour for the app |

### C. Lists and forms to the pixel
| # | Change | Evidence |
|---|---|---|
| C1 | Group radius 26, gap between groups 35, row 54 with icon / 44 plain, separator starting at the text (74 with icon) | Settings screenshot measurements |
| C2 | Icon tiles: 29 pt, **filled colour tile with a white glyph** (Settings style), one colour per kind (time off green, overtime orange, expense blue…) | Settings screenshot; HIG Icons |
| C3 | Row label 17 pt everywhere (lists were 15) | HIG Typography (Body 17) |
| C4 | The remaining 20+ hand-built `border-b` lists → the one list component | alpha7-handrolled.md §3 |
| C5 | Account/"You" header as the Settings account row: circle avatar 44, name 20 semibold, subtitle "Manager · Shift" | Settings screenshot |

### D. Controls: native where the platform has them
| # | Change | Evidence |
|---|---|---|
| D1 | **Switch = Safari's native `<input type=checkbox switch>`** — Apple's own switch, VoiceOver role, and the ONLY haptic a web app gets on iOS (iOS 18+) | WebKit 17.4 blog / 18.0 notes (web-native.md) |
| D2 | Menus (the "⋯" on a request, Appearance) → popover + `commandfor` + anchor positioning, glass, morphing from the button; frappe-ui Dropdown goes | web-native.md (Safari 26.2/27); HIG Menus |
| D3 | **Notification banner** replacing all 53 frappe-ui `toast()` calls: one component, top, glass capsule, auto-dismiss, VoiceOver live region | alpha7-handrolled.md (verified 53 calls); HIG Notifications |
| D4 | Alerts (Delete, Discard changes?) → one centred glass alert, ≤3 buttons, Cancel always "Cancel" | HIG Alerts |
| D5 | Sheets: part-height sheets **inset on glass**, full height opaque; ✓ (checkmark, tinted) top-right for confirm | ios26-spec §6 |
| D6 | Buttons: primary = `.glassProminent` look (tinted glass capsule) rather than a flat fill; secondary = `.glass` | WWDC25 323; App Store "Get" |

### E. Type, font, motion
| # | Change | Evidence |
|---|---|---|
| E1 | **Dynamic Type**: root font `-apple-system-body`, every size in rem → the app follows the iPhone's Text Size setting | WebKit "Using the System Font" (web-native.md §1) |
| E2 | SF tracking table applied per size (17 → −0.43, 13 → −0.08, 34 → +0.40) | ios26-spec §12 |
| E3 | Stop downloading Inter / Inter Tight / JetBrains Mono on Apple devices (system font only); keep Inter as the non-Apple fallback | handrolled.md §9; verified fonts.css |
| E4 | Motion = Apple's default spring (response 0.5, damping 0.825) for push, sheet and lens; View Transitions for push/pop | ios26-spec §10; web-native (View Transitions 18.0) |
| E5 | Scroll-driven animations (Safari 26) for the large title and tab-bar minimise; static fallback before 26 | web-native.md §11 |

### F. The app outside the app (native-feel features)
| # | Feature | Why / evidence |
|---|---|---|
| F1 | **App icon badge** = your pending approvals (approvers) or unread notifications | Badging API, Home Screen apps iOS 16.4+ |
| F2 | **Push that lands on the exact screen** (Declarative Web Push, `navigate` + badge in one message). Buttons ON the notification are impossible on iOS — the tap opens the approval sheet directly | web-native.md: notification actions unsupported; Declarative Web Push 18.4 |
| F3 | **Log in with Face ID** (passkeys, autofill sign-in, password→passkey upgrade). Needs a backend endpoint → owner's word required (Q3) | WebAuthn in Safari 16/18/26 |
| F4 | **Offline check-in queue**: if there is no signal at the door, the check-in is kept on the phone and sent on reconnect (iOS has no Background Sync) | web-native.md §9 |
| F5 | **Keep the screen awake** during the selfie (Wake Lock, Home Screen 18.4+); keep one camera stream (WebKit bug 215884 re-prompt) | web-native.md §8 |
| F6 | **Share** a request/payslip via the iOS share sheet (Web Share) | Safari 12.2+ |
| F7 | Launch screen and 180×180 icon per iOS; theme-color per theme | ios26-spec §11 |

### G. Leftovers from alpha.6 (carried)
- The "⋯" menu and delete dialog on a sent request (frappe-ui) → D2/D4.
- Not measured in alpha.6: real Safari, 430 pt and tablet, install/push/out-of-area dialogs → alpha.7 adds WebKit
  runs if `sudo npx playwright install-deps webkit` is run once (Q4), and a 430 pt pass.

---

## 3. How alpha.7 is proven (same discipline as alpha.6)
1. A **pixel-parity script**: renders Nadi's Settings-like screen (You) and a list screen at 402 pt / 3×, measures the
   same points as the iOS screenshots (group radius, row pitch, separator x, title size, colours) and fails on any
   difference > 1 pt / > 2 RGB units. The iOS figures are fixed constants from the owner's screenshots.
2. The alpha.6 audit, journeys (87 server + 10 screens), sheet crawler and all gates re-run at the end.
3. One commit per change, test first.

## 4. Decisions only the owner can make
- **Q1 — Accent colour.** iOS apps have ONE tint. Nadi's is lime. Keep lime as Nadi's tint (brand; Apple allows an
  app tint) — or use system blue like Settings/App Store? *Recommendation: keep lime as the tint, but only on the
  primary action, switches and the tab lens, exactly where iOS uses its tint.*
- **Q2 — Icon tiles in colour** (Settings style) — yes/no?
- **Q3 — Face ID sign-in (F3)** needs a new server endpoint for passkeys (auth change). Yes/no?
- **Q4 — Real Safari testing**: run `! sudo npx playwright install-deps webkit` once? Without it, iPhone-only
  behaviour is checked on your phone after deploy.
- **Q5 — Search (A5)**: what should it find? *Recommendation: requests, people (name only), SOPs, days.*

## 5. Size and order
A (5) → B (4) → C (5) → D (6) → E (5) → F (7) → proof = **32 steps**. F3 waits on Q3.
