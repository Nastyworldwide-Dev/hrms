# Nadi PWA — full recollection, checklist, version (23 Sep 2026)

Branch `nz-glass` at `e6eb026cb` (not yet deployed). Every line below has a file, a measurement or a ruling behind it.

Detail files (same folder):
- `2026-09-23-recollection-screens.md`: all 48 routes, where each is reached, who sees it
- `2026-09-23-recollection-rulings.md`: every owner ruling, with source and status
- `2026-09-23-recollection-platform.md`: manifest, service worker, offline, theme
- `2026-09-23-recollection-gates.md`: gates, tests, lint, build, counts

Two of the four helper reports had errors. They were **corrected by hand**:
- **The rulings report invented a blob ruling.** It cited a "D4" item that is really the word glossary, and an "audio" that doesn't exist.
- **The platform report was wrong twice:**
  - It said 3 blur rules. There are 7 blurred surfaces.
  - It marked portrait lock as passing. **No orientation is set anywhere.**

---

## 1. What exists today

**Navigation**
- Phone tab bar: **Home · Calendar · Requests · Score · More**.
- Desktop: a side nav with the same four, plus the rest under a divider.
- **48 routes** in total: 13 tab pages, 6 standalone, 26 forms, 3 redirects. None are unreachable, and no view is dead.
- **More** holds 8 rows: Leaves, Expenses, Helpdesk, SOPs, Announcements, Team, Remote approvals, HR contacts.
- **Three destinations have two doors each:**
  - Helpdesk
  - Team (More and the side nav)
  - Remote approvals (Profile, and More for managers)

**Quality today**
- Gates: **7 pass, 3 skipped.** Accessibility, visual and coherence need a running site, so **they measured nothing**.
- Tests: **814 / 814 pass**. ESLint: 0 errors.
- Build: works. 8.5 MB, of which **4.3 MB is fonts**: all 37 Inter files ship, italic included.

**Version**
- **The app has no version.** `frontend/package.json` says `0.0.0`.
- The app shows only a build timestamp (`__APP_BUILD__`).
- **The tag names `v2.1.0` … `v2.4.1` are already taken** by old selfie releases. A plain `v2.0.1` tag would read as newer than `v2.4.1`.

---

## 2. The checklist

**PASS / FAIL / PARTIAL**, each with its proof. Sources:
- Nielsen's 10 heuristics
- WCAG 2.2 AA
- Apple HIG and Material 3
- web.dev PWA and installability
- SemVer 2.0.0
- the anti-"AI slop" list in §2.6

### 2.1 Engineering

| # | Check | Result | Proof |
|---|---|---|---|
| E1 | The CSS the browser receives is valid | **FAIL: live defect** | `glass-components.css:117`: the text `pad-*/` closes the comment early. The built CSS drops the whole tab-bar reservation rule. Content sits under the tab bar again. The test reads the source file, so it passed. |
| E2 | One version number, shown in the app, tagged in git | **FAIL** | `0.0.0`; build timestamp only; the `v2.x` tag names are taken |
| E3 | Unit tests green | PASS | 814/814 |
| E4 | Lint clean | PASS | 0 errors (127 old style findings kept as a baseline) |
| E5 | Accessibility, visual and coherence gates actually run | **FAIL** | all 3 SKIP (no local site); they have never run in a commit |
| E6 | Every sheet uses the one fixed sheet component | **FAIL** | raw `<ion-modal>` still in 8 files |
| E7 | Sheets close when leaving the page | **FAIL** | the stuck-sheet cause (`plan/pages/00-sheets-and-transitions.md`) |
| E8 | Download size | PARTIAL | 4.3 MB of fonts; the PDF viewer (1.3 MB) is loaded up front |
| E9 | No offline check-in | PASS | nothing is queued; owner ruling kept |

### 2.2 PWA platform (web.dev)

| # | Check | Result | Proof |
|---|---|---|---|
| P1 | Manifest: id, scope, start URL, maskable icons | PASS | platform report §2 |
| P2 | **Portrait lock on phones** (owner ruling, 22 Sep) | **FAIL** | no `orientation` in the manifest or anywhere else |
| P3 | Update asks first, and a dismissal is remembered | PASS | fixed this morning (`c0c11341a`) |
| P4 | Personal data not cached for the next user | PASS | no runtime API caching |
| P5 | Pinch zoom allowed (WCAG 1.4.4) | PASS | viewport has no `user-scalable=no` |
| P6 | Theme follows system + override, no flash | PASS | pre-paint script |
| P7 | The right animation per device | **FAIL** | iPhone style is forced on every device (`ionicConfig.js`) |

### 2.3 UX: Nielsen's heuristics

| # | Heuristic | Result | Proof |
|---|---|---|---|
| U1 | Visibility of status | PARTIAL | Now bar good; Calendar has no today marker; absent days look blank |
| U2 | Match the real world | **FAIL** | Title Case on **130 strings**; raw "IN/OUT"; decimal hours "8.03 h"; "check in" vs "clock in" |
| U3 | User control | **FAIL** | stuck sheets; Back doesn't close the sheet first |
| U4 | Consistency | **FAIL** | 3 destinations with 2 doors; the same number on 2 pages (OT, balances, missing days) |
| U5 | Error prevention | PARTIAL | the date is "pre-filled" but the forms ignore it, so people re-pick it |
| U6 | Recognition over recall | PARTIAL | Calendar dots have no legend |
| U7 | Efficiency | **FAIL** | Requests needs scrolling past 6 tiles; Home repeats the whole Requests panel |
| U8 | Minimalist design | **FAIL** | greeting, count strips, repeated date (3×), explaining paragraphs |
| U9 | Error recovery | PASS | every list has an error state with "Try again" |
| U10 | Help | PASS | Help reaches HR and IT |

### 2.4 Accessibility: WCAG 2.2 AA

| # | Check | Result | Proof |
|---|---|---|---|
| A1 | Contrast | PASS | contrast gate 44/44 |
| A2 | Colour is never the only signal (1.4.1) | **FAIL** | Calendar dots have no text legend |
| A3 | Text at 200% and 320px wide doesn't cut off (1.4.4, 1.4.10) | **FAIL** | 19 `truncate`, 4 ellipsis; detail-grid values are cut to "Not ma…" |
| A4 | Target size ≥ 24px (2.5.8) | PASS | tokens set 44px |
| A5 | Reduced motion (2.3.3) | PASS | app-wide rule |
| A6 | Orientation must not be *forced* for content (1.3.4) | PASS once P2 is done | phone lock is allowed (essential), and desktop stays free |

### 2.5 Visual design (Apple HIG, Material 3, the Glass spec)

| # | Check | Result | Proof |
|---|---|---|---|
| V1 | Blur only on chrome (tab bar, side nav, sheets): ruling 16 Sep | PASS | blur sits on the tab bar, side nav and `g-glass-ghost` only; content cards don't blur |
| V2 | **No background blobs**: owner, 23 Sep | **FAIL** | `.g-lightfield` + 3 blobs still on every page (`glass-components.css:28-80`, `GPage.vue`, `field.*` tokens) |
| V3 | One type style for buttons (sentence case) | **FAIL** | 130 Title Case strings |
| V4 | No ALL CAPS body text (BDA dyslexia guide) | **FAIL** | 9 `toUpperCase()`, 35 uppercase classes/rules (the date eyebrow, section eyebrows) |
| V5 | Fonts: only the weights used | **FAIL** | 37 files ship |
| V6 | Page transitions are right per device | **FAIL** | see P7 and the transitions plan |

### 2.6 Anti-"AI slop" rules

"AI slop" means the look of an interface made from habit, not from need. This is the list, and each rule is checked:

| # | Slop sign | Result | Where |
|---|---|---|---|
| S1 | Decorative gradient blobs behind everything | **FAIL** | the light field on every page |
| S2 | Emoji in the interface | **FAIL** | `Hey, {0} 👋` (CheckInPanel) |
| S3 | A greeting hero that does nothing | **FAIL** | the same greeting at display size |
| S4 | CAPS eyebrow labels over every block | **FAIL** | `g-eyebrow` on every section + the ALL-CAPS date |
| S5 | An icon on every row "for looks" | PARTIAL | Needs you + Announcements rows each carry an icon. Keep only where it tells a type apart. |
| S6 | Stat tiles counting things that need no action | **FAIL** | the Calendar count strip; the Requests counter rows |
| S7 | Explaining sentences under every control | **FAIL** | *"tap to claim"*, *"Every tap, newest first"*, *"Assigned and upcoming"* |
| S8 | The same number shown in two places | **FAIL** | OT, balances, missing days |
| S9 | Big tiles grid as a menu | **FAIL** | Requests: 6 "start a request" tiles |
| S10 | Glass effect on everything | PASS | ruled chrome-only, and it holds |
| S11 | Made-up data or placeholder text | PASS | every number comes from the server |
| S12 | Arrows or "→" decoration in buttons | PARTIAL | check-in button has a trailing arrow. It's a primary action, not navigation, so **cut**. |

**Score:**
- 16 PASS
- 7 PARTIAL
- **27 FAIL**
- 1 conditional (A6, passes once P2 is done)

---

## 3. Version: the proposal

**Rule (SemVer 2.0.0):**
- `MAJOR.MINOR.PATCH`
- **PATCH** = bug fixes only
- **MINOR** = new features that don't break anything
- A **pre-release** is marked `-alpha.N`, and it ranks *before* the release

**What is true:**
- 2.0 is live.
- It **fails 27 of 51 checks**, including a live CSS defect and stuck sheets.
- It is not a finished 2.0.0.

**Recommendation:**

| Build | Version | Why |
|---|---|---|
| What is live now | **2.0.0-alpha.1** (recorded, not rebuilt) | Honest: it's a working pre-release |
| Next deploy: the foundation fixes (CSS defect, sheets, transitions, blobs, orientation, version display) | **2.0.0-alpha.2** | Fixes on a pre-release stay pre-release |
| Each page from the approved plans | **2.0.0-alpha.3, .4 …** | One page per step, easy to roll back |
| All 51 checks pass, including the 3 gates that skip today | **2.0.0** | The real release |
| Fixes after that | 2.0.1, 2.0.2 … | Patch |
| New features after that | 2.1.0 … | Minor |

**Your "2.0.1" idea:**
- It is correct SemVer **if** what's live is called 2.0.0.
- But the page work adds features (Approvals page, claim from the day). Under SemVer that is **2.1.0**, not 2.0.1.
- The alpha route avoids calling a build with known defects "2.0.0".

**One source of truth:**
- `frontend/package.json` `version` holds the number.
- The build injects it next to the timestamp.
- Profile → About shows **`2.0.0-alpha.2 · 23 Sep 14:02`**.
- Git tag **`nadi-v2.0.0-alpha.2`**. The `nadi-` prefix is needed because the `v2.x` names are taken.
- `docs/glass/CHANGELOG.md` lists each version in plain words.
- A gate fails the build if the version and the newest changelog entry disagree.

---

## 4. The proposal: order of work

One page at a time. Each page is its own deep-dive plan, approved before code.

| Step | Plan file | Status | Version |
|---|---|---|---|
| 0 | **Foundation**: CSS defect E1, stuck sheets, transitions, remove blobs, portrait lock, fonts, version + changelog, the 3 gates actually running | `pages/00-foundation.md` (extends `00-sheets-and-transitions.md`) | **to write next** | alpha.2 |
| 1 | Calendar | `pages/01-calendar.md` | **approved** | alpha.3 |
| 2 | Home | `pages/02-home.md` | **approved** (date title; "Not approved" in Requests only) | alpha.4 |
| 3 | Requests (+ balance breakdown, New request sheet) | `pages/03-requests.md` | to write | alpha.5 |
| 4 | Approvals (its own page) | `pages/04-approvals.md` | to write | alpha.6 |
| 5 | Score | `pages/05-score.md` | to write | alpha.7 |
| 6 | More | `pages/06-more.md` | to write | alpha.8 |
| 7 | You (Profile + settings) | `pages/07-you.md` | to write | alpha.8 |
| 8 | Help | `pages/08-help.md` | to write | alpha.9 |
| 9 | Announcements + Notifications | `pages/09-news.md` | to write | alpha.9 |
| 10 | Team, SOPs, holidays, check-in history | `pages/10-rest.md` | to write | alpha.10 |
| 11 | Forms (all 26 form routes: one pattern) | `pages/11-forms.md` | to write | alpha.11 |

**Why foundation first:**
- Every page sits on it: the sheets, the blobs, the tab-bar space, the words.
- Doing a page first means redoing it after.
