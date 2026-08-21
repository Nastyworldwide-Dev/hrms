# Fix pass 8 — closing the P0s, and the gates that should have caught them

Companion to **[frontend-audit.md](frontend-audit.md)**, which is left as
written. This records what changed, what it cost, what closed, and — the part
worth reading — **three findings from the first pass that were wrong**.

Every claim below was verified against the running app, by measurement where a
measurement was possible and by looking at the re-shot screenshot otherwise.

---

## 1. What the fixes were

Nine changes. Five are the ranked plan's 8.1–8.5; four more were needed because
"retire every P0" reached past that plan.

| # | change | root cause | how it was verified |
|---|---|---|---|
| 8.1 | `.g-field` (the §3 light field) renamed **`.g-lightfield`** | RC3 | `elementFromPoint()` at the login input's centre now returns `input.g-input`; a real Playwright click types into it |
| 8.2 | `<component :is="'button'">` → **`GTag`**, a 12-line helper using `h()` | RC1 | rendered class is `g-row g-row--tappable` with no frappe-ui utilities; 3 flex children at x=32 / 70 / 351, one axis |
| 8.3 | `ion-tabs .g-page ion-content` reserves **bar + 2 gaps + safe area**; new `layout.tabbar-height` token, pinned on the bar so the two cannot drift | RC2 | at true scroll bottom the lowest text sits at y=721 against a bar top of 777 |
| 8.4 | `bg-ground` / `bg-white` removed from full-bleed containers in `FormView`, `ListView` and 7 views | RC6, RC11 | the light field is visible on every form, list and detail screen |
| 8.4b | `.g-listview__row` gains `padding: var(--g-pad-row)` | RC21 | no leading glyph is sliced by the panel's corner radius |
| 8.5 | the check-out banner rebuilt on **`GBanner variant="warning"`** | RC10 | legible in both themes; was 1.00 contrast |
| — | `.g-sheet` bottom padding: `max(var(--g-pad-panel), env(…))` was **invalid CSS** and silently dropped | new | sheet `padding-bottom` is 14px; the button's bottom is 830 against an 844 floor |
| — | issue rows: the meta line is built from the parts that have a value | RC20 | the literal string `null` is gone |
| — | `search_link` failures no longer raise a page-level toast | RC15 | the primary button is no longer covered; 3 regression tests |
| — | `ReplacementLeave` gains a back control | new | the screen had **no way off it** — no back, no tab bar |
| — | notification action pills no longer wrap inside a fixed-height pill | new | — |

### The two that were worth the whole exercise

**`.g-field` was defined twice in one stylesheet.** Once as the §3 light field
(`position:absolute; inset:0; pointer-events:none`), once 700 lines later as the
`GInput` wrapper. The second rule overrode `display` and `width` and nothing
else, so **every form field in the app inherited `pointer-events: none` and was
positioned at the page's top-left corner**. The login form could not be clicked
at all. One rename fixed the login screen, every text field on eight forms, and
the "orphaned label with no field" finding on four detail screens.

**`<component :is="'button'">` never rendered a `<button>`.** Vue resolves a
dynamic `is` string against registered components before treating it as a tag,
capitalising as it goes; `main.js` registers `Button`, so `'button'` found
frappe-ui's. Its utilities (`justify-center h-7 px-2 rounded bg-surface-gray-2`)
landed on top of the Glass class and won, and it wrapped every slot in one
`<span>` so the icon well, body and chevron stopped being flex children. That
one line produced the entire "icons misaligned everywhere" symptom across
QuickLinks, More, every list, notifications, approvals and the issue board.

---

## 2. Three findings from the first pass that were wrong

The audit's own rule was that a finding must cite an observed screenshot. These
three did — and were still wrong. The screenshot was real; the *inference* from
it was not.

**"Detail and form screens do not scroll; approve/reject is unreachable." — P0,
false.** It was an artifact of my capture script. `capture.mjs` called
`ion-content.scrollToBottom()`, but `FormView` and `ListView` each own an inner
`overflow-y-auto` div and *that* is what scrolls. The outer call did nothing, so
every `__bottom` capture came back byte-identical to its top and I read that as
"the page cannot scroll". Measured afterwards: the detail screen's inner
scroller is 1233px against an 783px viewport and scrolls normally. **The harness
now scrolls every scrollable box**, and this class of false finding cannot
recur.

**"The design specimen renders completely blank." — P0, not a defect.** The
`/design` route is `import.meta.env.DEV` only and is dropped from production
builds by design, which the router says in a comment I did not read before
believing the image. It does expose a real but much smaller defect: **there is
no catch-all route**, so any unknown URL renders a blank page rather than a
not-found state. That one stands, as P1.

**"Issue rows show no subject." — half true.** The literal `null` was real and is
fixed. But the missing title was my own seed: the row label is `issue_type`,
which my seeded documents never set. The row now falls back rather than
rendering blank, but the finding as written blamed the app for missing data I
failed to create.

**Method note.** Two of the three came from trusting a screenshot without asking
what could produce that image *other than* the defect I had in mind. A blank
page can be a crash or a route that does not exist. An identical pair of
captures can be a page that will not scroll or a script that scrolled the wrong
element. The screenshot is evidence of what rendered — never, on its own, of
why.

---

## 3. The gates

Both of these were **already required by spec §16.5** and neither existed.

### a11y — was reporting failures and passing anyway

`design/gates/a11y.mjs` ran axe on **one route**, `/hrms/login`, printed
`serious: color-contrast (3 nodes)` and `critical: image-alt (1 node)`, then
called `process.exit(0)` — "report-only by design". It did that for fifty
prompts, on the one screen in the app whose form could not be clicked.

Now: **every screen in `frontend/e2e/screens.mjs`, both themes.** Serious and
critical fail; moderate and minor report. Existing debt is carried in
`design/a11y-baseline.json` and a violation whose node count *grows* fails.
`--update-baseline` re-records.

### visual — the layer that was missing

Four gates read source, one reads the DOM, none could see layout. That is the
whole reason a login form nobody could click passed CI.

`design/gates/visual.mjs` renders every screen at 390 dark, 390 light and 1440
dark and diffs against the committed captures in `docs/glass/audit/screens/` —
so **the image a finding cites and the image a regression is measured against
are the same file**. `--update-baseline` re-shoots.

One screen list (`frontend/e2e/screens.mjs`) feeds the a11y gate, the visual
gate and the audit capture, so a route cannot be added to the app and skipped by
all three.

**Both SKIP when there is no running site or no chromium**, matching the
existing convention — a gate that fails on every laptop without a bench gets
deleted, not fixed.

---

## 4. The numbers

Re-shot all 38 screens across 7 variants (342 images) against the fixed build,
and re-reviewed the 390-dark set independently.

| | P0 | P1 | P2 | total |
|---|---|---|---|---|
| **pre-fix** | 20 | 83 | 40 | **143** |
| closed by this pass | 20 | 18 | 0 | **38** |
| **remaining** | **0** | 65 | 40 | **105** |

**9 of 23 root causes fully closed:** RC1, RC2, RC3, RC6, RC10, RC11, RC15,
RC20, RC21. The 14 that remain are the coherence and polish tail — no P0 among
them.

Both reviewers confirmed closure independently on the screens in their batch:
RC1, RC2, RC3, RC6, RC10 and RC21 all read CLOSED against re-shot images.

### One regression, introduced and caught

Removing the opaque `bg-ground` from those containers was right — it was
painting over the light field — but **five sticky headers had been silently
inheriting that fill**. On Notifications the title and back arrow began
overprinting scrolled rows into unreadable glyph soup: a P0 I created. The
review caught it on Notifications, the only one of the five with enough content
to scroll; Profile, HR contacts, Settings and Remote approvals carried the same
defect latent. All five headers now own their fill. This is the argument for
re-shooting rather than declaring victory from a diff.

### Five findings corrected, all failing the same way

Three were retracted in §2. Re-triage produced two more, and every one is the
same error: a real observation, a wrong cause inferred on top of it.

- **"No light field on 7 list screens."** Measured instead: the `.g-lightfield`
  element is present at full viewport, `z-index: 0`, blobs at 0.62 opacity, and
  nothing in the ancestor chain paints over it. Those screens carry a 40-row
  list that simply covers the area the blobs occupy. Content density, not
  material.
- **"The issue detail's DETAILS section is empty" (reported P0).** My seed
  again: `issue_type` was blank, and the section's fields are conditional on it.
  Setting a type renders both "What are you reporting?" and "Describe the
  issue" correctly.

**The standing lesson.** Of 148 findings raised across both passes, **five were
wrong and all five were inference, never observation.** An identical pair of
captures meant my script scrolled the wrong element. A blank page meant a route
compiled out of production. A missing row title, an empty section and absent
blobs all meant my own seed or my own content. The screenshot was accurate every
time. What it was evidence *of* was not.

That applies to the 105 findings still standing: they are observations of what
rendered, and the causes attributed to them deserve the same check before
anyone acts on one.

## 5. What is still open

Nothing at P0. The remaining work is the coherence pass the audit ranked as
8.6–8.15, unchanged by this pass:

- **44px touch targets** (RC9) — the tab bar is still 69×36, back buttons 28×28
- **vendor copy** (RC4) — "Frappe HR" still in the header; needs one `__()`
  wrapper plus Translation records (audit §7 lists them exactly)
- **accent-as-selection** (RC7) — a one-option `GSegmented` still reads as the
  screen's primary action on Home
- **two chip implementations** (RC8) — `FormView` still uses frappe-ui `Badge`
- **the desktop two-column grids** (RC12) — still the unrun 7.3 ruling
- **empty-state treatments** (RC13, RC23) — three designs, and copy promising an
  action the box does not offer
- **RC19** — the double-letter gap ("Request At tendance"). Fonts load and serve
  200; cause still unknown, still needs a device.

### Two decisions that are not mine to make

**The tab bar is absent on 8 of the 10 list screens** (RC22). The audit called it
an inconsistency, which it is — but the two resolutions are opposite. Those
screens are sub-pages reached from a dashboard and routed outside `ion-tabs`;
adding a bar changes the app's navigation model, and removing it from the other
two changes theirs. Left alone deliberately: it is a design decision, not a
defect fix.

**`ReplacementLeave` now has a back control** because it had no way off it at
all, which *is* a defect. Whether it should instead be a tab screen is the same
question as above.
