# PLAN — Home density, the fold formula, and one real icon library

TIER: risky (many files, UI, touches every page's icon call sites)
STATUS: AWAITING APPROVAL — no code written
SCOPE: frontend only. No backend, no tokens changed, no IA/tab change, no deploy.

---

## 0. THE MEASUREMENTS THIS PLAN RESTS ON

Taken 22 Sep 2026. Every number below is measured, not estimated.
Where a number could not be measured, it says so.

### 0.1 The shipped PWA (docs/glass/audit/2026-09-09-app-measure.json, 390x844)

  screen                content  fold  overflow
  leave-applications       2589   844      1745
  leave-applications-detail 1482  844       638
  home                     1382   844       538
  notifications            1366   844       522
  dash-attendance          1362   844       518
  dash-leaves              1301   844       457
  ... 27 of 36 screens       844   844         0

CAVEAT, and it matters: every row in that file records tabH: 0. It was
measured BEFORE the bottom nav was repaired (3d4fa0dfe). So each "fold"
is ~64-73px too generous and each overflow ~64-73px too small. Home's
real overflow at the time was ~600px, not 538. The file is directionally
sound and precisely wrong. It must be re-run before this plan's slices
are graded — see 0.5.

Home carries 1382px of content for TEN tap targets. That is the defect in
one line: it spends 1.6 screens of height to offer ten things to do.

### 0.2 mockup-4's home does NOT fit, and its "fits" was an artifact

mockup-4 hardcodes .app{width:390px;height:844px;overflow:hidden}
(line 124). A fixed frame cannot overflow visibly, so eyeballing it
reports "no scroll" at every window size. Measured properly, with one
screen visible at a time, inside its own frame:

  screen        scrollH  clientH  over
  s-home            912      774   138  SCROLLS
  s-appr           1030      774   256  SCROLLS
  s-leaveform       915      774   141  SCROLLS
  s-score           801      774    27  SCROLLS
  s-req             799      774    25  SCROLLS
  s-cal/more/anns/help/notifs/profile  774  774  0  fits

And with the frame released to real device heights, home alone:

  360x640 -> 824px over     390x844 -> 229px over
  360x740 -> 501px over     414x896 -> 138px over
  360x800 -> 347px over     430x932 ->  67px over

CORRECTION to my own earlier reading: I cited "home = 723px, 0 overflow"
from docs/glass/audit/2026-09-09-prototype-measure.json. That file
measures nadi-prototype.html (e2e/prototype-measure.mjs:12), a DIFFERENT
file. It was never evidence about mockup-4. Withdrawn.

So "no scroll" is not yet proven anywhere, in the app or the mockup.
This plan has to establish it, not inherit it.

### 0.3 Icons

- feather-icons 4.29.2 is already a dependency (package.json:28).
- frappe-ui's FeatherIcon.vue does `import feather from 'feather-icons'`
  — a NAMESPACE import. All 287 icons ship whatever you use:
      all 287:  52.5 KB raw / 10.5 KB gzipped
      the 13 actually used: 1.6 KB raw / 0.6 KB gzipped
  So ~9.9 KB gzipped is paid for nothing. It cannot tree-shake; the
  component reads Object.keys(feather.icons) at module scope for its
  prop validator.
- 13 distinct feather names in use, across 6 files.
- 14 hand-rolled components in src/components/icons/ (263 lines, 6.9 KB)
  with no shared size, stroke or colour contract.
- 34 inline <svg> across 29 .vue files.
- 0 ion-icon usages. No lucide/heroicons/phosphor/iconify installed.
- Upstream: feather's last commit was 11 Mar 2025; 4.29.2 shipped
  1 May 2024; 300+ open issues. Lucide is its maintained fork, 1780
  icons, ships a first-party tree-shakeable vue package, near-identical
  names.

### 0.4 WCAG facts that bound the work

- SC 2.5.8 Target Size (Minimum), AA: 24x24 CSS px, or a 24px spacing
  circle that does not intersect a neighbour's.
- SC 1.4.10 Reflow, AA: no two-dimensional scrolling at 320 CSS px wide.
- token layout.touch-target-min is already 44px — AAA's 2.5.5 number,
  stricter than required. Keep it.
- mockup-4 audited: exactly ONE interactive target under 24px, a 38x22
  toggle track on s-leaveform. The mockup's tap targets are otherwise
  clean. (My earlier "minTap 12px" figures were measuring card DIVs, not
  controls. Withdrawn.)
- glass.css:96 --g-sheet-max-height: calc(100vh - 5rem) plus 9 more
  100vh/88vh/80vh/70vh sites. 100vh is the LARGEST viewport state on
  mobile, so sheets are cut off while browser chrome is showing. dvh/svh
  reached Baseline Widely Available Jun 2025. This is a real latent bug,
  listed here, fixed in slice 6, NOT bundled into the Home work.

### 0.5 What must be measured before grading (rung 3 evidence)

No site was reachable this session (ports 8080/8000/8001/5173 all
closed), so the shipped app could not be re-measured. Before any slice
here is called done:
  cd frontend && set -a && . ../.env && set +a && \
    W=360 H=640 node e2e/app-measure.mjs   # the hostile case
  ... repeat at 390x844 and 414x896
Re-running it also repairs the tabH: 0 defect in the baseline.

---

## 1. THE FORMULA (this is the answer to "how do pros do it?")

The user's constraint: "no scroll at best, but we dont want to against
screen reso height and width screen size."

Those pull against each other, and the professional resolution is NOT to
pick a height and design to it. It is to stop treating the fold as a
length and treat it as a BUDGET with a fixed part and an elastic part.

    USABLE = 100dvh
             - header
             - tab bar (64px + 9px gap + safe-area-inset-bottom)
             - top/bottom screen padding

    USABLE is a RANGE, not a number. Measured from real tokens:
      360x640  -> ~440px   (the hostile case: small Android, chrome up)
      390x844  -> ~640px
      414x896  -> ~690px
      430x932  -> ~726px

The rule that follows, and it is the whole formula:

    ONE screen = a FIXED anchor block that always fits the SMALLEST
    usable height, plus an ELASTIC list that is allowed to scroll.

  - The anchor block is sized against ~440px, not 640px. If it fits the
    small Android it fits everything. This is what "not fighting the
    screen size" means in practice — you fight the SMALLEST screen once,
    then every larger screen is a gift of extra list rows.
  - The elastic region scrolls, and that is correct, not a failure.
    Pros do not ship zero-scroll screens; they ship screens where
    nothing you MUST act on is below the fold. A list of 30 past
    requests should scroll. A "Check in" button must not.

Stated as the gradeable invariant:

    INVARIANT F1: at 360x640, every PRIMARY ACTION and every UNREAD
    DECISION on a tab-root screen is inside USABLE without scrolling.
    Lists may extend past it.

That is falsifiable, it is measurable with the harness already in the
repo, and it satisfies both halves of the user's sentence. It replaces
"home must not scroll" — which, per 0.2, is not achievable at 360x640
with the information Home owes the user.

Density ceiling, from dashboard research: 4-6 primary items above the
fold; 5-7 is where cognitive load starts degrading decisions. Home
currently offers 10 quick links plus a request list. That is over.

---

## 2. HOME: WHAT CHANGES

Current (Home.vue, 105 lines) — four stacked panels in one column,
gap-8 (32px) between them:

    PendingApprovalsBanner   (conditional, approvers only)
    CheckInPanel             (the anchor: greeting + clock + action)
    QuickLinks               (EIGHT rows, one per line, label only)
    RequestPanel             (segmented 3 tabs + up to 10 rows)

Total 1382px for 10 tap targets.

### 2.1 The four causes of the height, each with its own fix

C1. QuickLinks is 8 full-width rows, ~56px each = ~450px, to show 8
    labels. It is a menu wearing a list's clothes.
    FIX: a 4-across icon grid, 2 rows, ~176px. Same 8 destinations,
    -274px, and the icon carries the meaning so the label drops to one
    word. Targets 44px+ (token minimum), spacing-compliant.

C2. gap-8 = 32px x 3 gaps = 96px of pure air between panels.
    FIX: gap-5 (20px) between panels, gap-8 retained only around the
    anchor. -36px. Panel interiors untouched.

C3. RequestPanel renders a 3-tab segmented control plus 10 rows
    unconditionally. Nine of ten users have 0-2 open requests.
    FIX: cap the Home view at 3 rows + "See all (N)" -> the existing
    route. The full list already exists on its own screen with real
    pagination (ListView.vue page_length 50 + infinite scroll). Home
    stops being a second, worse copy of it. -~330px typical.

C4. Prose where a number would do. "1 remote check-in(s) awaiting your
    approval" / "Tap to review and decide." = 11 words for one count
    and one tap. CheckInPanel adds a greeting line and an h1 that
    duplicates GAppHeader's h1 (a real a11y defect: two h1 on one page).
    FIX: banner becomes "1 approval waiting" + chevron; drop "Tap to
    review and decide" (the whole row is already interactive, so the
    hint is redundant to a sighted user and noise to a screen reader).
    Drop CheckInPanel's greeting h1, keeping GAppHeader's as the only
    h1. -~70px and one a11y defect closed.

Projected: 1382 -> ~670px, inside USABLE at 390x844, and the anchor
(banner + check-in + quick grid, ~420px) inside USABLE at 360x640.
PROJECTED, not measured. Slice 5 measures it; if it misses, the fix is
to cut the quick grid to 6 tiles, not to hide information.

### 2.2 What does NOT change

- No route, tab or IA change. TAB_ROOTS in coherence-rules.mjs stays.
- No token value changes.
- No new information invented. Every element already on Home stays
  reachable; only QuickLinks' presentation and RequestPanel's row count
  change.

---

## 3. ICONS: ONE LIBRARY, AND WHICH ONE

Three options, priced:

  A. Finish adopting feather via frappe-ui's FeatherIcon.
     + zero new dependency, already works, 13 names in use.
     - upstream dead since Mar 2025; cannot tree-shake (namespace
       import) so all 287 icons ship = ~9.9 KB gzipped wasted; 287
       icons do not cover the domain (no fingerprint, no receipt, no
       calendar-clock), which is exactly why 14 were hand-rolled.

  B. Migrate to lucide-vue-next.
     + maintained (releases ~every 2 days), 1780 icons, first-party vue
       package, per-icon imports that actually tree-shake, near-identical
       names to feather so the 13 existing call sites port mostly 1:1,
       24x24 grid and configurable stroke matches the glass look.
     - one new dependency; 13 call sites + 14 components to migrate;
       needs a 114-PNG visual baseline re-bake.

  C. ionicons (already present via @ionic/vue).
     - iOS-flavoured, filled/outline pairs, does not match the glass
       stroke language. Rejected on coherence, not on merit.

RECOMMENDATION: B, lucide-vue-next, with a hard constraint —
ONE library on the page when the sweep ends, not two. The migration is
only worth its churn if feather leaves with it.

Net bundle: -10.5 KB (all of feather) -6.9 KB (hand-rolled) + ~40 icons
x ~0.3 KB tree-shaken = roughly -14 KB gzipped. Estimated; slice 4
measures the real delta and the slice is reverted if it is not negative.

Coverage check to do FIRST, before installing anything (slice 3): map
all 14 hand-rolled icons + the 13 feather names + the 34 inline svg to
lucide names. Any icon with no lucide equivalent stays a local component
— but it then lives in ONE place with the shared size/stroke contract,
not as an inline svg in a view.

---

## 4. SLICES (one concern, one commit; TDD each)

S1  test+fix  Home: the fold invariant F1 as a runnable test.
              RED first: assert the anchor block fits 440px at 360x640.
              Then C2+C4 (spacing and wording). Smallest slice, proves
              the harness grades the invariant.
S2  feat      QuickLinks -> 4-across icon grid (C1). Tap-target test at
              24px and 44px. Visual baselines re-baked for home only.
S3  chore     Icon coverage map, committed as a doc. No code. Decides
              whether S4 is even viable.
S4  refactor  Install lucide-vue-next; migrate the 14 components + 13
              feather call sites; REMOVE feather-icons and FeatherIcon
              usage. Bundle-size delta recorded. Baselines re-baked.
S5  refactor  The 34 inline <svg> -> the icon layer, page by page,
              grouped into at most 3 commits by directory to stay in the
              400-line budget.
S6  fix       RequestPanel: 3 rows + "See all (N)" (C3).
S7  fix       100vh -> dvh/svh across the 10 sites, with a vh fallback
              line first. Separate from all Home work: different root
              cause, different blast radius (sheets everywhere).

Each slice: red test, minimal green, gates (contrast 54/0, 13/13 tests,
a11y, coherence, visual), commit, review. S2/S4/S5 re-bake visual
baselines — that is 114 PNGs and must be its own commit inside the slice.

---

## MOCKUP: NOT NEEDED (owner waived it on approval, 22 Sep 2026 — "okay plan
approved, now implement it this isnt bout mockup right?". The plan originally
required a measured frameless mockup before the QuickLinks grid slice; the
owner explicitly removed that gate. Recorded rather than assumed. The
measurement obligation is NOT waived: the frameless numbers at 360x640 /
390x844 / 414x896 are still owed as rung-3 evidence, and the visual baselines
still re-bake.)

## 5. MOCKUP SIGN-OFF NOTES (retained for the mockup-4 ruling)

Per the earlier per-section recommendation, still standing. Added by
this plan's measurements:

- mockup-4's home does NOT fit at any real device height (0.2). It
  cannot be signed off as a scroll target. Its LAYOUT and LANGUAGE can
  be; its height cannot.
- A new mockup is required for the Home restructure, because S2 changes
  a layout the mockup does not draw (the 4-across grid). Repo rule: UI
  work gets mockup sign-off before code. That mockup must be measured
  at 360x640 / 390x844 / 414x896 with NO fixed frame, and must record
  the three numbers.
- Still rejected: --g-glass-fill .86 (ink-muted 3.84 dark),
  content-column-lg 880px (turns contrast.mjs red), the out-of-scope
  domains drawn with zero markings, the tab set (blocked on O4).

---

## FLOW

  measure (0.5, re-run app-measure at 3 viewports, repairs tabH:0)
    -> mockup for the new Home, measured frameless at 3 heights
    -> sign-off
    -> S1 .. S7, each red -> green -> gates -> commit -> review
    -> final re-measure at 360x640 / 390x844 / 414x896
    -> report the before/after table
    -> STOP. No deploy; the owner deploys.

## EXPECTED OUTPUT

- Home at 390x844: content ~1382px -> ~670px, measured, in the report.
- Home at 360x640: anchor block (banner + check-in + quick grid) fully
  inside USABLE, zero scroll to reach any primary action.
- Tab-root screens: F1 holds at 360x640, asserted by a test that fails
  if it stops holding.
- ONE icon library on the page. feather-icons absent from
  package.json. src/components/icons/ holds only genuinely custom marks,
  all sharing one size/stroke/colour contract.
- Inline <svg> in views/components: 34 -> 0 (excluding decorative
  non-icon graphics, which are listed by name if any remain).
- Bundle: net gzipped delta recorded and negative, or S4 reverted.
- Gates green throughout: contrast 54 checked / 0 failures, 13/13 tests.
- Zero token changes. Zero route changes. Zero backend changes.

## 8. RISKS

- Visual baselines: 3 slices re-bake 114 PNGs. Each re-bake must be its
  own commit or review becomes unreadable.
- Lucide names drift from feather on a few icons; the S3 map catches it
  before install, which is why S3 exists as its own slice.
- F1 at 360x640 may be unreachable even after C1-C4. Then the honest
  answer is fewer quick tiles (8 -> 6), NOT hidden information. Recorded
  here so the fallback is pre-agreed rather than improvised.
- No site was reachable this session. Every "projected" number here is
  arithmetic, and is marked as such. They get replaced with measured
  numbers, and if a projection was wrong the slice is re-scoped.
