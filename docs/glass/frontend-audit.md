# Frontend audit — rendered, not read

> **STATUS — the fix pass has run.** This document is the *pre-fix* audit and is
> kept as written, because the findings are the evidence and rewriting them
> would erase what was actually observed. What changed since is recorded in
> **[fix-pass-8.md](fix-pass-8.md)**: every P0 is closed, three findings turned
> out to be wrong, and the screenshots referenced below have been **re-shot
> against the fixed build**. To see a defect as this document describes it, use
> git history — `git show f0d15792b:docs/glass/audit/screens/<name>.png`.

Audit only when written. Spec v1.7, audited 21 August 2026, against the
production build in `hrms/public/frontend` (built 01:55, 21 Aug).

Every finding below was **seen in a screenshot**, and every screenshot is named.
Where a finding asserts a *cause*, the cause was verified afterwards in the DOM or
the CSS — the finding never comes from reading the markup.

---

## 1. Method

**The app was run, not read.** `bench --site fresh.local serve --port 8080`,
production bundle, Playwright + Chromium.

**Content was seeded first**, because mock data hides the CONTENT class of bug.
Employee `HR-EMP-00001`, *Nurul Aisyah binti Abdul Rahman* — a long Malaysian
name — with 80 leave applications, 3 leave allocations, 5 check-ins, a shift
assignment, 2 attendance requests, 2 employee issues and an 8-holiday Malaysian
holiday list.

**273 captures / 351 image files** in `docs/glass/audit/screens/`, indexed by
`docs/glass/audit/manifest.json` (per-capture console errors included).

| Variant | Widths | Themes | Extra |
|---|---|---|---|
| Mobile reference | 390×844 @2× | dark, light | plus a **scroll-bottom** shot of each |
| Reduce-transparency | 390×844 @2× | dark | §6.2 fallback |
| Tablet | 768×1024 | dark, light | |
| Desktop | 1440×900 | dark, light | |

Two categories were **measured, not eyeballed**, because the eye is the wrong
instrument for them: contrast ratios were computed as WCAG 2.x relative luminance
from the live DOM with alpha compositing, and touch targets from
`getBoundingClientRect()`. Hit-testing used `document.elementFromPoint()` plus a
real Playwright click.

### Data caveats — do not chase these, they are mine

Seeding artifacts, **not defects**: leave rows showing `0d` (I bypassed
validation, so `total_leave_days` was never computed); balance bars at 100%
(remaining == allocated, so no approved leave was deducted); zero expense claims
and zero appraisals (creation failed on this fixture site).

---

## 2. Headline

The material is right. The **wiring underneath it is not**, and four defects
account for most of what the human saw.

1. **Nobody can sign in.** The login form's fields are absolutely positioned at
   `inset: 0` with `pointer-events: none`. A real click times out; the element at
   the input's own centre is the page div. This is not a styling problem.
2. **Every multi-line text field in the app is missing** — the same cause. The
   reason/explanation/description control on eight forms renders as a 12px slab
   at the top of the page instead of under its label.
3. **Every list row in the app is broken**, from one line of Vue: `<component
   :is="'button'">` resolves to frappe-ui's registered `Button`, not a native
   `<button>`.
4. **Content is cut off behind the tab bar on every tab screen** — `ion-content`
   reserves `0px` of bottom padding for a 58px floating bar.

Beyond those: two screens were never migrated at all, one banner renders
chartreuse-on-chartreuse at **1.00 contrast**, list rows have so little padding
that their first letter is sliced by the panel's corner radius, eight of the ten
list screens have no tab bar, and the 44px touch minimum is honoured almost
nowhere.

**143 findings — 20 P0, 83 P1, 40 P2 — clustering into 23 root causes.** Five
small changes retire every P0.

One caveat on that count: a large share of the P2 findings are *downstream* of the
four P0 causes above. Dead space, orphaned labels and clipped glyphs are symptoms
of a field rendered at `inset: 0` or a row with no padding, and an unknown number
of them will vanish when those are fixed rather than needing their own prompt.
That is the argument for fixing the shared causes first and re-shooting before
touching anything cosmetic.

---

## 3. Root causes

Ranked by blast radius × severity. IDs are used by the per-screen tables in §4.

| id | root cause | owner | screens | sev |
|---|---|---|---|---|
| **RC3** | `.g-field` is **two different components sharing one class name** | `glass-components.css:12` + `:714` | ~41 | P0 |
| **RC1** | `<component :is="'button'">` resolves to frappe-ui `Button` | GListRow, GIssueCard, GGoalsPanel, GSelfiePanel | ~30 | P0 |
| **RC2** | no scroll padding reserved for the floating tab bar | `.g-page ion-content` | ~15 | P0 |
| **RC6** | screens that never adopted `GPage` — no light field, no glass, no layering | `views/FormShell.vue:2` + 7 list views | 19 | P1 |
| **RC9** | the 44px touch minimum is honoured almost nowhere | tab bar, back button, GSegmented, link actions | all | P1 |
| **RC10** | Modernist utility classes surviving inside views | `CheckInPanel.vue:43-46` | 1 (severe) | P0 |
| **RC11** | `bg-white` hardcoded over the themed page | ChangePassword, ForgotPassword | 2 | P1 |
| **RC4** | vendor copy, **half of it not translatable** | GAppHeader + `index.html` | ~all | P1 |
| **RC7** | accent fill marks *selected*, so a one-option control reads as the primary action | GSegmented | 4 | P1 |
| **RC8** | **two chip implementations** — `GStatusChip` vs frappe-ui `Badge` | `FormView.vue:33` | ~14 | P1 |
| **RC12** | desktop two-column grids contradict §20.3's single 720px column | Home, Leaves, Attendance | 3 | P1 |
| **RC13** | the dashed rectangle means both "empty" and "drop a file"; empty states have **three** treatments | GEmptyState + ad-hoc | ~12 | P1 |
| **RC16** | radius drift — square-cornered controls in a 17–20px system | segmented, steppers, Log Out, numeric inputs | ~10 | P2 |
| **RC17** | back affordance and header pattern drift — arrow vs chevron, **three** header layouts | app bar | ~20 | P2 |
| **RC5** | calendar cells outlined, not tinted | `.g-cal__day--rest` | 2 | P2 |
| **RC18** | the avatar has **three** forms — 72px sharp square, 33px rounded square, 28px circle | Profile, header, notifications | 3 | P2 |
| **RC20** | issue rows render **no subject** and print the literal string `null` | issue list rows | 2 | P1 |
| **RC15** | link-picker permission failures surface as an unhandled toast with raw doctype names | expense claim form | 1 | P1 |
| **RC14** | **no catch-all route** — any unknown URL renders a blank page | `router/index.js` | all | P1 |
| **RC21** | list rows have **no padding** — leading glyphs sliced by the panel's corner radius | list panel row | 4 | P0 |
| **RC22** | **the tab bar is absent on 8 of the 10 list screens** | list layout | 8 | P1 |
| **RC23** | empty states **promise an action they do not offer** — "claim it here" with no link | GEmptyState consumers | 3 | P1 |
| **RC19** | double-letter pairs render with a visible gap — *"Request At tendance"* | unconfirmed | all | P2 |

### RC3 — `.g-field` is two components sharing one class name

The single worst defect in the build.

`frontend/src/theme/glass-components.css` defines `.g-field` **twice**:

```css
/* line 12 — the §4 light field */          /* line 714 — the GInput wrapper */
.g-field {                                   .g-field {
  position: absolute;                          display: block;
  inset: 0;                                    width: 100%;
  z-index: 0;                                }
  overflow: hidden;
  pointer-events: none;
  contain: paint;
}
```

The later rule overrides only `display` and `width`. **`position: absolute`,
`inset: 0` and `pointer-events: none` still apply to every form field**, because
`GInput`, `GTextarea`, `GDatePicker` and `GLinkPicker` all render
`<label class="g-field">`.

Measured on `/hrms/login`:

| probe | result |
|---|---|
| `label.g-field` computed | `position: absolute`, `inset: 0px 0px 0px 0px`, `pointer-events: none` |
| `input.g-input` box | `[0, 19, 390, 46]` — pinned to the viewport corner |
| `elementFromPoint()` at the input's centre | `div.g-auth` — **not the input** |
| real Playwright click | **times out after 3000ms** |
| forced fill (bypasses hit-testing) | succeeds — the control itself is fine |

Evidence: `login__390-dark.png`, `login__768-dark.png`. Both field labels paint at
the same coordinates, so "EMAIL" and "PASSWORD" overprint into unreadable glyph
soup, and both inputs collapse into one box at the top of the screen, 218px above
the logo.

The same cause produces the **missing textarea on eight forms** — the control
renders as a ~12px full-bleed slab under the header instead of under its label
(`attendance-requests-new`, `issues-new`, `leave-applications-new`,
`ot-requests-new`, `replacement-leave-new`), and the **orphaned labels on the
detail screens** (`EMPLOYEE NAME`, `REASON`, an entirely empty `DETAILS` section).

**Fix:** rename one of the two. One line of CSS plus its consumers.

### RC1 — `:is="'button'"` resolves to frappe-ui's `Button`

`main.js:51` does `app.component("Button", Button)`. Vue resolves a dynamic
`:is="'button'"` against **registered components first**, capitalising as it goes,
so the string `'button'` finds frappe-ui's `Button` instead of the HTML element.

Rendered HTML of the first QuickLinks row on `/hrms/home`:

```html
<button class="g-row g-row--tappable inline-flex items-center justify-center gap-2
               transition-colors ... bg-surface-gray-2 h-7 text-base px-2 rounded
               g-row g-row--tappable">
  <span class="">                       <!-- frappe-ui wraps ALL slot content -->
    <span class="g-row__well">…</span>
    <span class="g-row__body">…</span>
    <svg class="g-row__chevron">…</svg>
  </span>
</button>
```

Four consequences, all visible in `home__390-dark.png` and `more__390-dark.png`:

- `justify-center` **centres the label**; `h-7` forces 28px against `.g-row`'s
  44px `min-height`, so content overflows its own row box
- frappe-ui wraps every slot in one `<span>`, so the well, body and chevron are
  **no longer flex children of the row** — they stack and wrap, which is why the
  chevron lands below-left and crosses into the next row
- `bg-surface-gray-2` paints a Modernist background on a row that must be
  transparent inside a glass panel; `rounded` adds a stray radius
- `g-row g-row--tappable` appears **twice** in the class list

Affected: `GListRow.vue:24`, `GIssueCard.vue:20`, `GGoalsPanel.vue:16`,
`GSelfiePanel.vue:23` — all four use the identical ternary.

**It is not the components' own CSS.** `.g-row` computes correctly as
`display:flex; align-items:center; gap:11px`, and `QuickLinks.vue` composes the
slots properly. Proof that a working row exists: **`profile__390-dark.png` renders
its rows correctly** — icon left, label, chevron right — because those rows are
not built this way.

**Fix:** `:is="tappable ? 'button' : 'div'"` → a real element, four files.

### RC2 — nothing reserves room for the floating tab bar

`.g-page ion-content` (line 51) sets only `--background: transparent` and
`z-index: 1`. The tab bar floats at
`bottom: calc(env(safe-area-inset-bottom, 0px) + var(--g-tabbar-gap))`.

Measured on `/hrms/home`: `--padding-bottom: 0px`, inner `scrollHeight` 1398 vs
`clientHeight` 773, tab bar at `y=777`, height `58`, bottom gap `9`. **67px+ of
content is permanently behind the bar** and the scroll cannot reach past it.

Evidence: `home__390-dark__bottom.png` (a "Privilege Leave / REJECTED" row
bisected), `dash-leaves__390-dark__bottom.png`, `dash-attendance__390-dark.png`
(cuts "UPCOMING SHIFTS"), `notifications__390-dark__bottom.png` ("Load more" 10px
off the viewport floor), `invalid-employee__390-dark.png` (the "Go to Login"
button sliced flat on the final pixel row).

**Fix:** one `--padding-bottom` on `.g-page ion-content`.

### RC10 — a banner rendering at 1.00 contrast

`CheckInPanel.vue:43-46` still carries Modernist utility classes:
`text-card-title font-semibold text-accent-…` and `text-kra-label
text-accent-800/80`. In dark theme those resolve to the accent itself, **on an
accent-filled banner**.

Computed from the live DOM:

| text | colour | background | ratio | needs |
|---|---|---|---|---|
| "Forgot to check out from 02:12 am yesterday?" | `rgb(200,255,0)` | `rgb(200,255,0)` | **1.00** | 4.5 |
| "Tap to submit a late check-out for approval." | `rgba(200,255,0,.8)` | `rgb(200,255,0)` | **1.00** | 4.5 |

Seen directly: in `home__390-dark.png` the banner is a **blank chartreuse
rectangle**. In `home__390-light.png` the identical banner is fully legible. The
text is there in the DOM the whole time.

This is the one that best explains "content unreadable": it is not cut off, it is
*invisible*.

---

## 4. Per-screen findings

Severity: **P0** unreadable/broken · **P1** systemically incoherent · **P2** polish.
Every row names the image it was seen in. Screens are grouped; `__bottom` means
the scroll-bottom capture.

### 4.1 Home

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| LAYOUT | P0 | RC1 | QuickLinks rows: icon centred above, label centred below, chevron floating left into the next row; icons clipped by the panel rim | `home__390-dark.png` |
| MATERIAL | P0 | RC10 | the check-out banner is a blank chartreuse block — text at 1.00 contrast | `home__390-dark.png` vs `home__390-light.png` |
| LAYOUT | P0 | RC2 | scroll bottom leaves a request row bisected by the tab bar | `home__390-dark__bottom.png` |
| HIERARCHY | P1 | RC7 | "MY REQUESTS" is a full-width chartreuse bar competing with "Check In" — it is a **one-option `GSegmented`**, a tab with nothing to switch to, not a header | `home__390-dark.png` |
| COPY | P1 | RC4 | header wordmark reads "Frappe HR"; at 1440 it appears **twice at once**, in the sidebar and the top bar | `home__390-dark.png`, `home__1440-dark.png` |
| HIERARCHY | P2 | RC7 | at desktop a correct "REQUESTS" eyebrow sits directly above the chartreuse bar, labelling the section twice | `home__1440-dark.png` |
| RESPONSIVE | P1 | RC12 | `lg:grid-cols-2`; measured columns 550px / 549px, neither is §20.3's 720px | `home__1440-dark.png` |
| LAYOUT | P2 | — | the left column ends at y≈690 while the right runs to 800, leaving the halves visibly unbalanced | `home__1440-dark.png` |
| INTERACTION | P1 | RC9 | "View List" is 56×**15**px; the five tab items are 69×**36**px | measured |

### 4.2 Attendance dashboard

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| LAYOUT | P0 | RC2 | "Work From Home / DRAFT" is behind the tab bar in the *unscrolled* view; "UPCOMING SHIFTS" cut at 768 | `dash-attendance__390-dark.png`, `__768-dark.png` |
| MATERIAL | P2 | RC5 | day cells are **hollow outlined rectangles**. Computed: `border: 1px solid rgb(135,143,155)`, `background: rgba(0,0,0,0)`. Size and radius *are* spec-correct (10.5px, r8) — the tint is missing and a border was used instead | `dash-attendance__390-dark.png` |
| MATERIAL | P2 | — | the "Half Day" legend dot is dark olive on near-black — effectively invisible | `dash-attendance__390-dark.png` |
| COPY | P1 | — | "View list" (sentence case) here vs "View List" (title case) on Leaves — same action, two labels | `dash-attendance__390-dark.png` vs `dash-leaves__390-dark.png` |
| RESPONSIVE | P1 | RC12 | `lg:grid-cols-[1.1fr_1fr]`; ~320px of dead space in the left column while the right overflows the fold | `dash-attendance__1440-dark.png` |
| RESPONSIVE | P1 | — | at 768 the content column is only ~416px wide, leaving large dead margins | `dash-attendance__768-dark.png` |
| LAYOUT | P1 | — | the action list sits **after** two request lists on mobile but directly after the primary at desktop — the two orders disagree | `dash-attendance__390-dark.png` vs `__1440-dark.png` |
| INTERACTION | P1 | RC9 | 42 of 58 controls are under 44px; month steppers are 32×32 | measured |

### 4.3 Leaves dashboard

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| LAYOUT | P1 | — | the third balance cell renders **inside its own rounded border** that the first two lack, and that border stops at the panel's midpoint leaving a floating corner | `dash-leaves__390-dark.png` |
| HIERARCHY | P1 | RC7 | two chartreuse filled actions — "CLAIM" and "Request a Leave" — violating §18's one primary | `dash-leaves__390-dark.png` |
| COMPONENTS | P2 | RC16 | "CLAIM" is square-cornered while "Request a Leave" is a pill | `dash-leaves__390-dark.png` |
| SPACING | P2 | — | "LEAVE BALANCE" has no divider under it while "REPLACEMENT LEAVE" and "RECENT LEAVES" both do | `dash-leaves__390-dark.png` |
| SPACING | P2 | — | the replacement-leave figure is indented 24px further than its own section header | `dash-leaves__390-dark.png` |
| LAYOUT | P0 | RC2 | scroll bottom bisects a row; another row renders *below* the tab bar | `dash-leaves__390-dark__bottom.png` |
| RESPONSIVE | P1 | RC12 | `lg:grid-cols-[1fr_280px]`; the primary is **stranded top-right** in otherwise empty space; three different content widths (855/555/550) | `dash-leaves__1440-dark.png` |

### 4.4 KPI

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| STATES | P1 | RC13 | the empty state is a **bare centred sentence** with no icon, title/body hierarchy or action, while Attendance and Leaves use a composed bordered panel for the same job | `dash-kpi__390-dark.png` |

*KPI is otherwise **unaudited** — no appraisal data exists on this site (§5).*

### 4.5 More

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| LAYOUT | P0 | RC1 | all three rows broken; the first row's icon is **sliced by the panel's top rim** and the last chevron by its bottom rim — the panel box is shorter than its content | `more__390-dark.png` |
| LAYOUT | P1 | — | scrolling moves the panel but the clipping persists, confirming the box (not the page) is short | `more__390-dark__bottom.png` |
| COPY | P1 | — | the header says "More" and a chartreuse eyebrow 47px below says "MORE" | `more__390-dark.png` |
| LAYOUT | P1 | — | three destinations occupy the top 250px; ~62% of the viewport is empty | `more__390-dark.png` |
| CHROME | P1 | — | the active tab changes container, shape **and** glyph family at once — a filled glowing squircle with a solid mark against four bare outline glyphs — so it reads as a button dropped into the bar | `more__390-dark.png` |
| ICONS | P2 | — | tab glyphs are not optically matched; EXPENSES is a dollar sign inside a full circle, denser than its outline siblings | `more__390-dark.png` |
| CHROME | P1 | RC17 | **three** app-header patterns across the app: title+bell+avatar, back+title, back+title+refresh | `more`, `profile`, `hr-contacts` |
| INTERACTION | P1 | RC9 | avatar 33.5×33.5, bell glyph ~18.5px wide | measured |

### 4.6 Login

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| LAYOUT | P0 | RC3 | "EMAIL" and "PASSWORD" overprint at the same coordinates into unreadable glyph soup, glyph tops shaved by the viewport edge | `login__390-dark.png` |
| LAYOUT | P0 | RC3 | both inputs collapse into one box with both placeholders overprinted; the block sits 218px above the logo it belongs to | `login__390-dark.png` |
| INTERACTION | P0 | RC3 | **the form cannot be used** — a real click times out, `elementFromPoint` returns the page div | measured |
| RESPONSIVE | P0 | RC3 | reproduces identically at 768 | `login__768-dark.png` |
| SPACING | P1 | RC3 | the input is full-bleed 0→390 with its rim cut flat at both edges while everything else is inset 16px | `login__390-dark.png` |
| COPY | P2 | — | the mark reads "HR" but the heading names the product "Sign in to NSTY People" — mark and product name disagree | `login__390-dark.png` |

### 4.7 Forms (8 screens)

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| COMPONENTS | P0 | RC3 | **the multi-line field is missing on every form** — a label with nothing under it. `EXPLANATION` (attendance, OT, replacement leave), `REASON` (leave), `DESCRIBE THE ISSUE *` (issues — the screen's mandatory field) | `*-new__390-dark.png` |
| LAYOUT | P1 | RC3 | a ~12px full-bleed slab under the header on exactly the five screens with a missing control — the displaced field itself | `attendance-requests-new__390-dark.png` |
| MATERIAL | P1 | RC6 | **no light field and no glass on any form screen** — flat `#07070A` at all corners, opaque grey fields. The dashboards at the same viewport show tinted corners | all `*-new__390-dark.png` |
| COMPONENTS | P1 | — | **four field treatments within 800px**: near-black 6px-radius date inputs, identical time inputs, mid-grey 14px-radius borderless selects, square-cornered bordered numerics | `attendance-requests-new__390-dark.png` |
| COMPONENTS | P1 | — | date and time fields are **unstyled native controls** — UA calendar/clock glyphs and the literal placeholders `mm/dd/yyyy` and `--:-- --` | `attendance-requests-new__390-dark.png` |
| CONTENT | P2 | — | US date format `mm/dd/yyyy` throughout, in a Malaysian HR app | all form screens |
| HIERARCHY | P1 | — | checkbox labels ("Half Day", "Include Holidays") are chartreuse Title Case semibold — two unchecked options are the loudest text on the screen | `attendance-requests-new__390-dark.png` |
| COMPONENTS | P2 | — | those checkboxes are **circles** — radio geometry for independent toggles | `attendance-requests-new__390-dark.png` |
| TYPOGRAPHY | P1 | — | the required marker is a red/salmon asterisk (~`#e5484d`), a hue absent from the chartreuse/teal/violet palette | all form screens |
| COMPONENTS | P1 | RC13 | the attachment dropzone is a square-cornered dashed box — dashed borders and square corners exist nowhere else in the system | all form screens |
| LAYOUT | P0 | RC2 | on attendance-requests-new the dropzone is **sliced by the sticky Save bar** and the page does not scroll, so the clipped edge is the end of reachable content | `attendance-requests-new__390-dark__bottom.png` |
| COPY | P2 | — | section eyebrow and field label duplicate the same word 60px apart — "REASON" / "REASON *", "CURRENCY" / "CURRENCY *" | attendance, expense forms |
| COPY | P2 | — | three primary-label conventions in one batch: "Save", "Update Password", "Send Reset Link" | forms batch |
| CONTENT | P2 | — | the approver field is required on expense and shift forms but not on leave — same role, two rules | `leave-applications-new` vs `expense-claims-new` |
| LAYOUT | P2 | — | 265–530px of dead space between the last field and the Save bar on unscrollable pages | issues, OT, replacement-leave, shift-requests |
| MATERIAL | P1 | — | shift-requests-new has **no eyebrows, no dividers, no panel** — four bare fields on flat black, unlike every sibling form | `shift-requests-new__390-dark.png` |

### 4.8 Expense claim form — additional

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| LAYOUT | P0 | RC15 | a "Could not load" toast is anchored **over the primary button**, covering its label and middle 60% | `expense-claims-new__390-dark.png` |
| COPY | P1 | RC15 | the error reads "Insufficient Permission for **Account**" — raw backend vocabulary with a capitalised doctype name, shown to an employee | `expense-claims-new__390-dark.png` |
| STATES | P1 | RC15 | the manifest records 7 `PAGEERROR … PermissionError` per capture for Account/Currency/Branch/Location — the link pickers throw **unhandled** rejections rather than rendering an error state | `manifest.json` |
| MATERIAL | P2 | — | the toast is flat solid near-black with a pure-red icon — no glass, and the red is off-palette | `expense-claims-new__390-dark.png` |
| TYPOGRAPHY | P2 | — | "EXPENSES" appears as a Title Case 17px tab and an UPPERCASE 11px section header 700px apart | `expense-claims-new__390-dark.png` |

### 4.9 Detail screens (4)

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| LAYOUT | P0 | RC2 | **the detail screens do not scroll** — bottom captures are pixel-identical to top — and content is cut at the viewport edge, so approve/reject/submit controls are unreachable | `attendance-requests-detail__390-dark__bottom.png`, `leave-applications-detail__390-dark__bottom.png` |
| LAYOUT | P0 | — | a line of text reading "morning" is **sliced in half by the header's bottom edge** | `attendance-requests-detail__390-dark.png` |
| TYPOGRAPHY | P1 | — | the document title truncates to "Employ…" while the 18-character system ID chip beside it renders in full — the least meaningful element wins the space. Also "Leave…", "Attendance R…", "Shift A…" | `issues-detail__390-dark.png` |
| LAYOUT | P1 | RC3 | orphaned labels with no field: `EMPLOYEE NAME`, `REASON`, and an entirely empty `DETAILS` section | `issues-detail__390-dark.png`, `leave-applications-detail__390-dark.png` |
| STATES | P1 | — | a document stamped **"Rejected"** renders every field as a live editable control — no read-only or disabled treatment | `leave-applications-detail__390-dark.png` |
| COMPONENTS | P1 | RC8 | the same status renders as a **filled amber "Open"** pill in the app bar and an **outlined uppercase "OPEN"** on the list. `FormView.vue:33` uses frappe-ui `Badge`; the lists use `GStatusChip` | `issues-detail__390-dark.png` vs `issues__390-dark.png` |
| COMPONENTS | P1 | — | two primary-button designs: 40px flat centred "Save" here, 53px glowing left-aligned pill with a trailing arrow on the list screens | `issues-detail__390-dark.png` |
| HIERARCHY | P1 | — | on two detail screens the **only** chartreuse elements are checkbox labels ("Half Day", "Follow via Email") — a notification preference carries the primary-action colour and no primary action exists | `attendance-requests-detail`, `leave-applications-detail` |
| MATERIAL | P1 | RC6 | no light field, no glass — flat `#07070A`, fully opaque fields with no rim | all four detail screens |
| COMPONENTS | P1 | — | two boolean shapes on one screen: "Half Day" an unfilled grey circle, "Follow via Email" a chartreuse-filled circle with a check | `leave-applications-detail__390-dark.png` |
| CONTENT | P2 | — | no activity, approval-trail, comment or timeline block on any detail screen | all four |
| HIERARCHY | P1 | — | shift-assignments-detail has **no action of any kind** and 164px of empty space below the last field | `shift-assignments-detail__390-dark.png` |
| SPACING | P2 | — | a leading divider is drawn above the first section eyebrow, separating content from nothing | `shift-assignments-detail`, `issues-new`, `replacement-leave-new` |

### 4.10 Issues list

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| CONTENT | P1 | RC20 | **rows show no subject** — the only text is `HR-ISS-26-08-00002 · 21 Aug, 07:51 · null`. Both seeded issues have subjects; the list renders none | `issues__390-dark.png` |
| CONTENT | P1 | RC20 | the literal string **`null`** is printed as the last meta segment on every row | `issues__390-dark.png` |
| LAYOUT | P0 | RC1 | rows broken: meta line flush against the card's top rim, chip stacked below it, chevron below that crossing the row divider; a 65px empty well runs down the card's left side | `issues__390-dark.png` |
| MATERIAL | P2 | — | the CTA's glow bleeds ~40px past the pill, tinting the background and washing over the eyebrow below it | `issues__390-dark.png` |
| ICONS | P2 | — | the notification dot is fully detached from the bell — a clear gap reads as a stray dot | `issues__390-dark.png` |
| LAYOUT | P2 | — | 478px of empty background between the only card and the tab bar | `issues__390-dark.png` |

### 4.11 Notifications

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| LAYOUT | P0 | — | "Mark all as read" **wraps to two lines and overflows its fixed-height pill** — caps sit above the rim, "read" is jammed against the bottom | `notifications__390-dark.png` |
| HIERARCHY | P1 | — | "Settings" and "Mark all as read" are identical grey pills; the bulk action is indistinguishable from a navigation link | `notifications__390-dark.png` |
| COMPONENTS | P1 | — | each row carries **two** status marks — a blank grey circle with no initials or icon, plus a hard-cornered chartreuse square as the unread flag, in a rounded system | `notifications__390-dark.png` |
| TYPOGRAPHY | P1 | — | bold is applied to arbitrary mid-sentence fragments, and **"Approved" and "Rejected" are typeset identically in white** — outcome cannot be told apart at a glance | `notifications__390-dark.png` |
| MATERIAL | P1 | — | the list is unpanelled — rows on flat background — while the same pattern on More is wrapped in a rimmed glass panel | `notifications__390-dark.png` |
| MATERIAL | P2 | — | the light field is attached to the scrolled document, not fixed to the viewport: the first screen is flat, and the blobs only appear once scrolled to the end | `notifications__390-dark__bottom.png` |
| CONTENT | P2 | — | document ids break mid-token: `HR-LAP-2026-` / `00043` | `notifications__390-dark.png` |
| LAYOUT | P1 | RC2 | "Load more" sits 10px from the viewport floor with no trailing padding | `notifications__390-dark__bottom.png` |

### 4.12 Profile, Settings, HR contacts, Invalid employee

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| COMPONENTS | P1 | RC1 | **Profile's rows render correctly** — icon left, label, chevron right — proving a working row implementation exists alongside the broken one | `profile__390-dark.png` |
| HIERARCHY | P1 | — | sign-out is the **only** accented element on Profile: a chartreuse-outlined box with chartreuse text and icon. The destructive action wears the primary colour and nothing marks it destructive | `profile__390-dark.png` |
| COMPONENTS | P1 | RC18 | the same user's avatar is a 72px sharp square, a 33px rounded square and a 28px circle on three screens | `profile`, `more`, `notifications` |
| CONTENT | P2 | — | a normal-length Malay name truncates on one line: "Nurul Aisyah binti Abdul…"; the desktop sidebar cuts it to "Nurul Aisyah binti …" | `profile__390-dark.png`, `home__1440-dark.png` |
| COMPONENTS | P1 | RC16 | the theme picker is a **zero-radius rectangle** with a hard-cornered chartreuse segment, no dividers and no thumb — a second, contradictory answer to the "pick one of N" problem the pill tab bar already solves | `settings__390-dark.png` |
| TYPOGRAPHY | P1 | — | two row-title styles on one screen: "Enable Push Notifications" in the light body face at a larger size, "Theme" and "Change Password" in the bold heading face | `settings__390-dark.png` |
| SPACING | P1 | — | three different left edges in one list — eyebrows at 16, helper text at 24.5, "Change Password" at 48 | `settings__390-dark.png` |
| INTERACTION | P1 | RC9 | the push toggle is ~31×17px and its off-state track and knob are two near-identical greys, so "off" is indistinguishable from "disabled" | `settings__390-dark.png` |
| COPY | P1 | — | server vocabulary leaks to employees: "Push notifications have been disabled **on your site**"; "Ask your **administrator** to assign the **HR Manager or HR User role**" | `settings`, `hr-contacts` |
| STATES | P1 | RC13 | HR contacts' empty state offers **no action**, is not centred (top 137–260px, ~580px empty below), and its icon well is a hard-cornered flat grey square | `hr-contacts__390-dark.png` |
| LAYOUT | P0 | RC2 | the invalid-employee sheet is clipped — "Go to Login" is still solid chartreuse on the **final pixel row**, its corner radius sliced flat, zero safe area | `invalid-employee__390-dark.png` |
| MATERIAL | P1 | — | that page's background is `rgb(3,3,4)` where every other screen is `rgb(7,7,10)`, and the sheet is opaque with no rim | `invalid-employee__390-dark.png` |
| COMPONENTS | P2 | — | the sheet shows a drag handle implying dismissal, but dismissing leaves an empty black page with no route out | `invalid-employee__390-dark.png` |
| COPY | P2 | — | the auth pair is labelled four ways: "Log Out", "Login", "Sign in to NSTY People", "Go to Login" | across the batch |

### 4.13 Team, Remote approvals

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| STATES | P1 | — | a screen titled "Team" renders **no roster at all** — no rows, no avatars, no names, and no empty state for the roster | `team__390-dark.png` |
| COMPONENTS | P1 | RC16 | the date stepper buttons are perfectly square, sharp-cornered outline boxes, 34×34px | `team__390-dark.png` |
| COMPONENTS | P1 | RC13 | the empty-state panel uses a **dashed border — the same device as the file-upload dropzone**, so "nothing here" and "drop a file here" are drawn identically | `team__390-dark.png` vs `issues-detail__390-dark.png` |
| TYPOGRAPHY | P2 | — | "NOT IN YET" wraps, orphaning "YET" and breaking the stat row's baseline | `team__390-dark.png` |
| COPY | P2 | — | "Approvals will appear here when your team submits" — the sentence has no object | `team__390-dark.png` |
| COMPONENTS | P1 | RC13 | remote-approvals' empty state is **bare left-aligned text**, a third empty-state treatment | `remote-approvals__390-dark.png` |
| HIERARCHY | P2 | RC7 | its active segment uses the exact primary-action chartreuse across half the screen width | `remote-approvals__390-dark.png` |
| ICONS | P2 | RC17 | back is a left **arrow** here and on Settings, a left **chevron** on all four detail screens | `remote-approvals__390-dark.png` |
| CHROME | P2 | — | content passes under the opaque header with a hard chop — no fade or mask — leaving a bright sliver stuck under the hairline | `team__390-dark__bottom.png`, `issues__390-dark__bottom.png` |

### 4.14 List screens (10)

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| SPACING | P0 | RC21 | **list rows have effectively no padding** — the title's first pixel is 1 CSS px from the panel's inner edge and chips end 0.5px from the rim, so the leading glyph is **sliced by the panel's rounded corner**: the "O" of "On Duty", the "0" of "07:26 pm", the "C" of "Casual Leave", the "A" of "Audit Morning Shift" | `attendance-requests__390-dark.png`, `employee-checkins__390-dark.png`, `leave-applications__390-dark.png`, `shift-assignments__390-dark.png` |
| SPACING | P1 | RC21 | no vertical padding either — 40.5px per row, so the first row's title touches the top rim and the last row's date touches the bottom rim | `attendance-requests__390-dark.png` |
| CHROME | P1 | RC22 | **eight of the ten list screens have no tab bar at all** — flat black below the content — while issues and sop show it | `leave-applications__390-dark__bottom.png` and 7 others |
| MATERIAL | P1 | RC6 | seven of the ten render on flat `rgb(7,7,10)` with **no light field**; issues, sop and replacement-leave do show the corner blobs | `attendance-requests`, `employee-checkins`, `expense-claims`, `leave-applications`, `ot-requests`, `shift-assignments`, `shift-requests` |
| CHROME | P0 | — | **replacement-leave has neither a back chevron nor a tab bar** — no navigation affordance anywhere on the screen | `replacement-leave__390-dark.png` |
| COMPONENTS | P1 | RC8 | three chip constructions of equal importance in one list: REJECTED a light salmon fill `rgb(249,127,127)` with dark text, APPROVED a dark teal fill with light text, OPEN **no fill at all** — a 2px amber outline | `leave-applications__390-dark.png` |
| HIERARCHY | P1 | RC8 | because REJECTED is the only high-luminance chip, **the eye is pulled to every rejection first** — rejected rows outrank approved ones purely on chip brightness | `leave-applications__390-dark.png` |
| HIERARCHY | P1 | RC7 | on expense-claims, shift-requests and leave-applications the **only** chartreuse element is the segmented control's thumb, while the real primary "+ New" is a white pill — the brightest object is a view switcher | `expense-claims__390-dark.png`, `shift-requests__390-dark.png` |
| HIERARCHY | P1 | — | ot-requests has **not a single chartreuse pixel** — no primary action reads as primary | `ot-requests__390-dark.png` |
| HIERARCHY | P1 | — | on employee-checkins and shift-assignments the accent is spent on **neutral status chips** (IN/OUT, SUBMITTED), the loudest thing on screens with no primary action | `employee-checkins__390-dark.png`, `shift-assignments__390-dark.png` |
| STATES | P1 | RC23 | empty states **promise an action they do not offer**: "Paid for something for work? Claim it here", "claim it here", "Claim the time back here" — the box contains no button or link, so "here" points at nothing | `expense-claims`, `ot-requests`, `replacement-leave` |
| COMPONENTS | P1 | RC13 | the empty state is a dashed-outline box on five list screens — a border style used nowhere else except the upload dropzone | `expense-claims`, `ot-requests`, `shift-requests`, `replacement-leave`, `sop` |
| COMPONENTS | P1 | — | **no list row carries a leading icon or type marker** — 18 leave rows differ only by one word, so Casual, Privilege and Sick are indistinguishable at a glance | `leave-applications__390-dark.png` |
| COMPONENTS | P1 | — | the create action has **three sizes, two colours and three placements**: a 358×52 full-width chartreuse bar (issues), a 113×50 chartreuse pill (replacement-leave), a 70×28 white pill (five screens) | `issues`, `replacement-leave`, `leave-applications` |
| CHROME | P1 | RC17 | **three header patterns inside the list family alone**: back+title+filter+"New" (rule at y=120), title+bell+avatar with no back (rule at y=140), and a bare title with no rule and no back | `leave-applications`, `issues`, `replacement-leave` |
| COPY | P1 | — | expense-claims names one object **four ways**: header "Claim History", tabs "MY CLAIMS / TEAM CLAIMS", empty state "expense claims", tab bar "EXPENSES" | `expense-claims__390-dark.png` |
| COPY | P2 | — | "OT Request" in the header vs "overtime claims" in the empty state; "Employee Checkin History" uses the internal record name | `ot-requests`, `employee-checkins` |
| COMPONENTS | P2 | — | "MY CLAIMS" is a chartreuse section eyebrow on replacement-leave and a segmented-control thumb on expense-claims — one label, two component roles | `replacement-leave` vs `expense-claims` |
| MATERIAL | P1 | RC16 | SOP's search field and replacement-leave's "AUGUST 2026 BANK" panel are **zero-radius rectangles** in an 18px-rounded system; the bank panel's fill is identical to the page background | `sop__390-dark.png`, `replacement-leave__390-dark.png` |
| TYPOGRAPHY | P1 | — | the SOP search placeholder measures **2.7:1** against its own field fill | `sop__390-dark.png` |
| TYPOGRAPHY | P2 | — | tab bar labels measure **3.6:1** — independently matching my computed 3.84:1 — under the 4.5:1 needed at 10px | `issues__390-dark.png` |
| INTERACTION | P1 | RC9 | rows are 41px tall, the filter button 28×28, "+ New" 70×28, the SOP search field 39.5px — all under 44px | measured, four screens |
| SPACING | P2 | — | header and content use different left margins — chevron at 23px, title at 45px, panel rim at 16px | `leave-applications__390-dark.png` +4 |
| SPACING | P1 | — | the issues panel insets its divider 16px each side while the leave, attendance and check-in panels draw theirs full-bleed — two list components, two divider rules | `issues` vs `leave-applications` |
| COMPONENTS | P2 | — | IN and OUT chips alternating down one list use two different fills, so OUT reads lighter than IN for states of identical importance | `employee-checkins__390-dark.png` |
| TYPOGRAPHY | P2 | — | "Claim History" wraps, orphaning "History", pushing this screen's header rule 38px below every sibling's | `attendance-requests__390-dark.png` |
| SPACING | P2 | — | the expense-claims segmented thumb is 168px inside a 357px track, so the boundary sits 9px left of centre and the segments are visibly unequal | `expense-claims__390-dark.png` |

### 4.15 Cross-cutting

| cat | sev | rc | finding | image |
|---|---|---|---|---|
| MATERIAL | P1 | RC11 | **`change-password` and `forgot-password` were never migrated** — the `__390-dark` captures render a *white* page with no chartreuse anywhere. Cause: `<div class="w-full h-full bg-white sm:w-96">` paints over the themed page | `change-password__390-dark.png`, `forgot-password__390-dark.png` |
| HIERARCHY | P1 | RC11 | on both, the primary is a **near-white pill on a white page** — no visually primary action exists | same |
| LAYOUT | P1 | RC11 | on both, the bottom bar's outline enters and exits the frame instead of closing — its side edges are clipped by both screen edges | same |
| COMPONENTS | P1 | RC11 | the password inputs are near-black fully-rounded pills on white, reading as **redaction bars**; ~24px radius matches nothing else | `change-password__390-dark.png` |
| STATES | P1 | RC14 | **no catch-all route exists** — any unknown URL renders a blank page. `/design` is dev-only by design, and in the production build it renders as a single flat colour rather than a not-found state | `design-specimen__1440-dark.png` |
| TYPOGRAPHY | P2 | RC19 | double-letter pairs render with a visible gap, breaking words mid-token: "Request At tendance", "Request a Shif t", "Set t ings", "Not if icat ions", "AT T END". Present at both 1× and 2×, so not a capture artifact. **Cause unconfirmed** — the self-hosted fonts are present and serve 200 | `home__390-dark.png`, `settings__390-dark.png`, `notifications__390-dark.png` |
| MATERIAL | — | — | **reduce-transparency is correct.** Panels go opaque, rims appear, the tab bar solidifies. §6.2 behaves | `home__390-dark-rt.png` |

---

## 5. Screens I could not render, and why

| screen | why |
|---|---|
| **HR issue board** (`/hr/issues`) | **silently redirects to the staff Issues view** — my user has no HR role. `issues__390-dark.png` and `hr-issue-board__390-dark.png` are byte-identical (md5 `2d48fd59…`). The board itself was never rendered; findings labelled "issue board" belong to the staff list |
| **KPI** | no Appraisal records exist; the screen renders only its empty state |
| **Team roster** | my user manages nobody, so no member rows render. Avatars, long-name truncation and row anatomy in that list are unassessed |
| **Remote approvals (populated)** | the PENDING tab is empty and HISTORY was not captured; approval rows and their actions are unassessed |
| **Expense claim list/detail** | claim creation failed on this fixture site, so both render empty |
| **Design specimen** | dev-only by design (`import.meta.env.DEV`), absent from the production bundle. **The system's own reference rendering was therefore unavailable for comparison** |
| **Below-the-fold on all forms and details** | those pages do not scroll; every `__bottom` capture is identical to its top |
| **Focus, press, error and loading states** | no capture puts a control in those states |
| **SSO provider button** | no Social Login Key is enabled on this site, so `GProviderButton` never rendered |
| **iOS safe area** | Chromium reports `env(safe-area-inset-*)` as 0; real device behaviour is unverified |

---

## 6. Ranked fix plan

Ordered by **screens affected × severity**, shared components first. The first
three prompts are worth more than everything after them combined.

| # | prompt | root causes | files | screens | est |
|---|---|---|---|---|---|
| **8.1** | Rename the light-field `.g-field`; verify every `GInput`/`GTextarea`/`GDatePicker`/`GLinkPicker` is clickable and in flow | RC3 | 1 CSS + 5 components | ~41 | S |
| **8.2** | Replace `:is="tappable ? 'button' : 'div'"` with real elements in the four components | RC1 | 4 components | ~30 | S |
| **8.3** | Reserve tab-bar height + gap + safe area as `--padding-bottom` on `.g-page ion-content`; re-shoot every `__bottom` capture | RC2 | 1 CSS | ~15 | S |
| **8.4** | Give `FormShell` and the seven bare list views the `GPage` shell, so they get the field, the layering and the glass; restore the tab bar on the eight list screens missing it | RC6, RC22 | 8 views | 19 | M |
| **8.4b** | Restore `--g-pad-row` on list panel rows — leading glyphs are currently sliced by the corner radius | RC21 | 1 component | 4 | S |
| **8.5** | Purge surviving Modernist utilities from views, starting with `CheckInPanel.vue:43-46`; drop `bg-white` from ChangePassword/ForgotPassword | RC10, RC11 | 3 views | 3 | S |
| **8.6** | Raise every interactive element to 44px — tab bar, back button, `GSegmented`, header controls, "View list" links | RC9 | tab bar + 4 components | all | M |
| **8.7** | Vendor copy: wrap `GAppHeader.vue:30` in `__()`, fix `index.html`, then create the Translation records (§7) | RC4 | 2 files + data | all | S |
| **8.8** | Stop using accent fill for *selected*; give `GSegmented` a non-accent active state and hide a one-option control | RC7 | 1 component | 4 | S |
| **8.9** | Replace frappe-ui `Badge` in `FormView.vue:33` with `GStatusChip` | RC8 | 1 view | ~14 | S |
| **8.10** | Run the three 7.3 rulings: remove the `lg:` two-column grids, amend §12 for server-ordered forms, fix Attendance's stack order | RC12 | 3 views + spec | 3 | M |
| **8.11** | One empty-state component everywhere; stop using the dashed rectangle for two meanings; give every empty state the action its copy already promises | RC13, RC23 | ~8 views | ~15 | M |
| **8.12** | Render the issue subject; stop printing `null` in the meta line | RC20 | 1 component | 2 | S |
| **8.13** | Catch-all route with a real not-found state; handle link-picker permission failures as an error state, not an unhandled toast | RC14, RC15 | router + 1 component | all | S |
| **8.14** | Polish sweep: radius drift, back-affordance and header patterns, avatar unification, calendar cell tint, read-only treatment on submitted documents | RC5, RC16, RC17, RC18 | ~10 files | ~20 | M |
| **8.15** | Investigate the double-letter gap on a real device before touching it | RC19 | — | all | ? |

**Estimate.** 8.1–8.5 are five small, surgical changes that between them retire
every P0 and touch roughly 45 of the 47 screen-variants where a P0 was observed.
8.6–8.9 are the systemic-coherence pass. 8.10–8.15 are the long tail.

---

## 7. Vendor copy — exactly what to create, and what a record cannot fix

`fresh.local` has **three** Translation records, all written in 7.2, all
login-only — which is precisely why the login heading reads "Sign in to NSTY
People" while the app header still reads "Frappe HR".

**Create on the target site** (source → your product name):

| source string | appears in |
|---|---|
| `Frappe HR` | `BaseLayout.vue:6` page title, `Login.vue:11` logo label, `SideNav.vue:26` |
| `Install Frappe HR` | `InstallPrompt.vue:3`, `:20` |
| `Frappe HR · Mobile & Tablet` | already recorded — recreate on the real site |
| `Employee self-service portal` | already recorded — recreate |
| `Login to Frappe HR` | already recorded — recreate |

**A Translation record cannot fix these** — they need a code change:

- `GAppHeader.vue:30` — `{{ title || "Frappe HR" }}` is **not wrapped in `__()`**.
  This is the wordmark the human saw on Home.
- `frontend/index.html:15` `<title>` and `:21` `apple-mobile-web-app-title`,
  which generate `hrms/www/hrms.html`
- `DesignSpecimen.vue:242` (dev-only, low priority)

Separately: the SSO button label "Office 365" is a `provider_name` on the Social
Login Key record in Desk — data, not code.

---

## 8. What the gates cannot catch

**All five gates pass right now.** They passed while the login screen was
unusable.

```
lint       OK   196 known, 0 new
usage      OK   0 known, 0 new
contrast   OK   54 pairs, 0 failed, 0 skipped
surfaces   OK   40 screens, 0 over 6, flattening held
a11y       OK   ok (report-only)
```

They pass because **every one of them reads source, not pixels**:

- `contrast.mjs` checks the §14.2 **token matrix** computed from
  `design/tokens.json`. The 1.00-contrast banner is invisible to it because
  `text-accent-800/80` is a leftover Tailwind class, not a token pairing.
- `usage.mjs` checks that screens *compose* primitives. `QuickLinks.vue` composes
  `GListRow` correctly — the failure is Vue resolving `'button'` at runtime.
- `surfaces.mjs` counts surfaces in the source. Every count was right.
- `lint.mjs` enforces token discipline in CSS, not layout.
- **`a11y.mjs` already found the problem and threw it away.** It reports
  `serious: color-contrast (3 nodes)` and `critical: image-alt (1 node)` and then
  calls `process.exit(0)` — "report-only by design". It also tests **exactly one
  route, `/hrms/login`**: the single most broken screen in the app.

### What to add

1. **Turn the a11y gate on.** It is already producing the evidence. Make it
   blocking, and run it over every route rather than one.
2. **A render-time DOM gate.** Cheap, deterministic, and it catches every P0 here:
   - every interactive element's `getBoundingClientRect()` ≥ 44px
   - `elementFromPoint()` at each control's centre returns that control — this
     alone catches RC3
   - no two focusable boxes overlap by more than half their area — catches the
     overlapping login labels
   - `scrollHeight - scrollTop - clientHeight` clears the tab bar — catches RC2
   - no text node's computed colour resolves within 1.5:1 of its composited
     background — catches RC10
3. **Computed contrast on the rendered DOM**, replacing (or beside) the token
   matrix. The matrix can only see pairings the system already knows about; the
   defects live in the pairings it doesn't.
4. **A duplicate-selector check** over the Glass CSS layer. `.g-field` is defined
   twice in one file; a 20-line script would have caught it before it shipped.
   (Nine other selectors are duplicated; the rest are legitimate at-rule variants.)
5. **Visual regression baselines.** The 273 captures in `docs/glass/audit/screens/`
   are a baseline set as they stand — approve them once fixed and diff on every PR.
6. **A real-content specimen route.** The design specimen is dev-only, so the
   production build has no reference rendering to compare against. A route that
   renders every component with *long Malaysian names, 40-row lists, zero rows and
   wide currency* would have surfaced the truncation, wrapping and orphan findings
   in §4 without a data seed.

---

## 9. Totals

| | count |
|---|---|
| **Findings** | **143** |
| P0 — unreadable or broken | **20** |
| P1 — systemically incoherent | **83** |
| P2 — polish | **40** |
| **Root causes** | **23** |
| Findings rolled up under a root cause | 69 |
| One-off findings | 74 |
| Screens rendered | 39 of 41 routes |
| Screens fully or partly unaudited | 10 (see §5) |
| Captures | 273 (351 image files, 23 MB) |

By category: LAYOUT 25 · COMPONENTS 24 · MATERIAL 15 · HIERARCHY 14 · COPY 12 ·
SPACING 10 · TYPOGRAPHY 10 · STATES 7 · CONTENT 7 · INTERACTION 6 · CHROME 6 ·
RESPONSIVE 5 · ICONS 3.

**One thing passes cleanly:** reduce-transparency (§6.2). Panels go opaque, rims
appear, the tab bar solidifies. It was the only subsystem this audit could not
fault.

### Estimate for the fix phase

**15 prompts.** Five of them (8.1–8.5) are small, surgical, and retire every P0:
one CSS rename, one ternary in four components, one `--padding-bottom`, one page
shell, and a Modernist purge in three views. That is roughly a day's work and it
is worth more than the other ten prompts combined.

8.6–8.9 are the systemic-coherence pass — touch targets, vendor copy, accent
discipline, one chip — call it two days. 8.10–8.15 are the long tail plus the
three unrun 7.3 rulings: two to three days.

**Do not start the polish tail until 8.1–8.5 have landed and the screens have been
re-shot.** A large share of the P2 findings here (dead space, orphaned labels,
unbalanced columns, clipped glyphs) are *downstream* of the four P0 causes, and an
unknown number of them will simply disappear when those are fixed. Re-running the
capture is one command.
