# Cross-screen coherence audit

**Report only. Nothing was changed.** Spec v1.10, 21 August 2026.

The 143-finding audit in `frontend-audit.md` asked *is this screen right?* 38
times. This asks *do the screens agree with each other?* — which nothing has
ever checked, and which is what a human reviewing the deployed app complained
about.

**Every cause below is measured from the DOM.** Five of the previous audit's 148
findings were accurate observations with a wrong cause inferred on top, so
nothing here rests on reading an image. Where a claim could not be reproduced by
measurement, it says so.

**Method.** A profiler visited all 38 screens in both themes at 390 and
extracted, per screen: every filled action and its resolved fill, the back
control and its component, header structure and title case, section-header
treatment, empty-state component, and the gaps between content-column children.
Transitions were sampled frame by frame during a real navigation.

> **A correction to my own instrument, recorded because it nearly produced a
> false report.** The first cut resolved design tokens with
> `"#3F5C00".match(/\d+/g)` → `[3, 5, 0]`, which then matched every transparent
> element on the page and reported dark-olive fills on 20+ screens. Tokens are
> hex; they are now resolved *through the engine* by setting `color: var(--tok)`
> on a probe element and reading back the computed value. The numbers below are
> from the corrected run.

---

## 1. The six observations, verified

| # | observation | verdict |
|---|---|---|
| 1 | Save buttons render dark olive | **CONFIRMED — light theme only**, and the cause is a token-alias inversion |
| 2 | Home → More overlaps mid-transition | **CONFIRMED with a correction** — not on tab switches; on *pushes*, and worse than described |
| 3 | Back controls inconsistent | **CONFIRMED** — 26 screens have one, 12 do not, and the split is not the rule anyone intended |
| 4 | Attendance has two competing primaries | **CONFIRMED as a hierarchy defect, not a fill defect** |
| 5 | Expense Claims leads with a raw chartreuse block | **CONFIRMED** |
| 6 | 1440 largely undesigned | **CONFIRMED — 28 of 42 views contain no `lg:` rule at all** |

### 1.1 The Save button is dark olive — and only in light theme

Measured on `/leave-applications/new`:

| theme | Save background | token it equals |
|---|---|---|
| dark | `rgb(200,255,0)` | `--g-brand` ✓ |
| **light** | **`rgb(63,92,0)`** | **`--g-accent-ink`** ✗ |

The cause is in `tailwind.config.js`:

```js
accent: { DEFAULT: --g-accent-ink,   // #3F5C00 dark olive in light
          100:     --g-brand }       // #C8FF00 chartreuse
```

**`bg-accent` gives the INK colour, not the brand.** You need `bg-accent-100`
for the fill. Every author writing `bg-accent` expecting chartreuse gets dark
olive, and the name actively misleads.

**Why it is invisible in dark theme:** `--g-accent-ink` *equals* `--g-brand`
there (both `#C8FF00`). The two tokens collapse to the same value, so the wrong
one looks right. **My entire previous audit ran in dark theme.** Every
screenshot showed a correct chartreuse Save.

**Why lint passes it:** the gate checks hex literals, colour functions,
arbitrary values, `outline: none`, and scoped overrides. `bg-accent` is a
correctly-spelled named class. **No gate knows which token a ROLE should use** —
it cannot tell "the primary action is filled with the ink colour" from a
correct usage. That is the missing rule, and it is a different shape from every
rule the gate currently has.

**Screens affected — all 8 use frappe-ui `Button`, not `GButton`:**
`attendance-requests-new`, `expense-claims-new`, `issues-detail`, `issues-new`,
`leave-applications-new`, `ot-requests-new`, `replacement-leave-new`,
`shift-requests-new`.

**Correct per spec:** `GButton`, which resolves `--g-brand` directly. Measured
across all 38 screens, **every one of the 15 brand-filled actions in the app is
a `GButton`**. The form submit is the *only* primary action in the product that
bypasses the primary component — which is exactly why it is the only one that
drifted.

### 1.2 The transition overlap is real, and it is per-page light fields

The human guessed the mechanism correctly. Sampled every 20 ms through a real
navigation:

| navigation | peak concurrent `.g-page` | peak `.g-lightfield` |
|---|---|---|
| Home → More (**tab switch**) | 1 | 1 |
| Leaves → Request a Leave (**push**) | **3** | **3** |

On a push, three `.g-page` elements exist simultaneously, **each carrying its
own light field**, and for several consecutive frames all three are at
`opacity: 1`. Three sets of §3 blobs paint at once.

**Correction to the observation:** it is not Home → More. Ionic does not animate
between tab roots — measured, 1 page throughout. It animates *pushes*, and every
push in the app stacks fields this way.

**Correct per spec:** §3.2 puts the field inside the page, and §15.3 says it
costs nothing against the surface budget — both true of one page in isolation.
Neither anticipated N pages coexisting. This is a genuine gap in the spec, not
a violation of it: **the field's ownership needs to move to the shell, or be
suppressed on any page that is not the active one.**

### 1.3 Attendance's competing primaries — a hierarchy defect, not a fill one

Measured: `dash-attendance` has exactly **one** brand fill ("Request
Attendance"). "Request Overtime", "Replacement Leave" and "Request a Shift" are
`GListRow`s inside a panel — correct components, no competing fill.

So §18 is not violated by *colour*. It is violated by *rank*: four actions of
equal semantic weight, one promoted to the screen's primary and three demoted to
list rows, with no rule explaining which is which. The same three actions appear
on `/more` styled identically as navigation. **Correct per spec is undefined** —
§18 constrains how many primaries a screen may have, not how sibling actions of
equal weight are ranked. That needs a ruling.

### 1.4 Desktop is undesigned, quantified

**28 of 42 views contain no `lg:` rule whatsoever.** The 14 that do use it
almost entirely for padding (`lg:p-`, `lg:px-`, `lg:py-` — 14 occurrences)
rather than layout. §20 defines the column and the sidebar; beyond those two
things, desktop is the mobile stack in a wider viewport.

---

## 2. Cross-screen inconsistencies

### 2.1 Primary action — no consistent rule for presence, component or position

| pattern | screens | |
|---|---|---|
| one `GButton`, brand fill | 15 | correct |
| one frappe-ui `Button`, **accent-ink fill** | 8 | §1.1 |
| **no filled primary at all** | **16** | see below |
| **two filled actions** | 1 | `replacement-leave` |

**16 screens have no primary action.** Some correctly (`settings`, `profile`,
`notifications` are destinations, not tasks). But the **list screens**
(`attendance-requests`, `leave-applications`, `employee-checkins`,
`shift-assignments`, `sop`) all carry a create action rendered as a **white
pill in the header**, not a filled primary — so the same "create a new X" action
is a chartreuse `GButton` on the dashboards and an unfilled header pill on the
lists.

**`replacement-leave` renders "New Claim" twice** — header (y=24) and empty
state (y=378), both brand-filled. **This one is mine**: 8.11 added an action to
empty states whose copy promised one, without checking whether the screen
already had that action elsewhere.

**Correct per spec:** §18, one primary per screen, and it should be the same
component in the same position for the same role.

### 2.2 Back navigation — the rule is "did someone add one", not a rule

- **26 screens have a back control**, 25 of them `GIconButton`.
- **12 do not**: `dash-attendance`, `dash-expense-claims`, `dash-kpi`,
  `dash-leaves`, `home`, `hr-issue-board`, `invalid-employee`, `issues`,
  `login`, `more`, `sop`, `team`.
- **1 uses a hand-rolled button** rather than the component:
  `replacement-leave`.

**The rule `GPage` actually applies: none.** `GPage` renders the page shell and
has no opinion about back at all — every screen decides for itself, which is why
the set is arbitrary. The 12 without split into two groups that happen to
coincide: the 7 tab roots (correct — a tab root has no parent) and 5 that are
pushed and simply lack one (`hr-issue-board`, `invalid-employee`, `issues`,
`sop`, `team`).

**Correct per spec:** §12 as amended in v1.9 — a pushed screen carries a back
control, a tab root does not. Four screens violate it (`issues`, `sop`, `team`,
`hr-issue-board`); `invalid-employee` is a terminal error state and arguably
correct without one.

### 2.3 Screen header — four different structures

| structure | screens |
|---|---|
| `<header>` + `<h2>` + 1 control | 12 (forms) |
| `<ion-header>` + `<h1>` + 2 controls | 10 (tab roots) |
| `<header>` + `<h2>` + 2 controls | 6 (details) |
| `<ion-header>` + `<h2>` + 4 controls | 5 (lists) |
| `<ion-header>` + `<h2>` + 2 controls | 2 (`employee-checkins`, `shift-assignments`) |
| **no header at all** | 3 (`login`, `invalid-employee`, **`replacement-leave`**) |

Two things stand out. The title is an **`<h1>` on tab roots and an `<h2>`
everywhere else** — the same element, two levels, which is a document-outline
defect as much as a visual one. And `employee-checkins` / `shift-assignments`
are list screens rendering the *detail* header shape, so the list family itself
disagrees internally.

`replacement-leave` has **no header element**, which is why it also has the
hand-rolled back control — it is the one screen built outside every shared
shell.

**Title case:** 29 Title Case, 6 not (`My KPI`, `NSTY People`, `HR Contacts`,
`OT Request History`) — most of which are proper nouns or initialisms and
defensible. No systemic case defect.

### 2.4 Section headers — three treatments, and the accent one is a minority

Measured across every uppercase run under 13px:

| treatment | count |
|---|---|
| `rgb(84,92,104)` 10px / 1.4px tracking | 58 |
| **`rgb(63,92,0)` 10.5px / 1.365px** (accent) | **32** |
| `rgb(135,143,155)` 10px / 0.7px | 30 |
| three further variants | 25 |

**Six distinct section-header treatments.** The §10 eyebrow — accent ink,
10.5px, 1.365px tracking — is used **32 times against 113 uses of something
else**. The most common treatment in the app is not the specified one.

No section header was found styled as a button; the `GSegmented` case that
caused that in 8.x is fixed.

### 2.5 Empty states — one component, one holdout

11 screens use `GEmptyState`. **One does not:** `remote-approvals`, which
renders bare text. Down from three treatments before 8.11; this is the last one.

### 2.6 Vertical rhythm — not measurable as a system

Gaps between content-column children cluster at 20px and 16px, but only two
screens produced a comparable stack shape. **The app has no repeated stack
shape to be consistent about** — each screen composes its own column, so there
is nothing for a rhythm to be consistent *with*. That is itself the finding:
§5's spacing scale exists, but no shared layout component applies it, so
consistency depends on each author choosing the same Tailwind gap.

---

## 3. What no gate can currently see

Every finding here passed all six gates. The gates check tokens, composition,
surface counts, contrast pairs, a11y and per-screen pixels — **all of which are
within-screen properties.** Nothing compares screen A to screen B.

Three rules would have caught most of this, and all three are cheap because the
profiler already exists:

1. **Role–token binding.** "The primary action's fill resolves to `--g-brand`"
   would have caught §1.1 in either theme. The current lint cannot express it.
2. **Cross-screen invariants.** One primary per screen, one back rule, one
   header shape per screen class, one empty-state component — assertions over
   the 38-screen profile rather than over one screen.
3. **Token-collapse detection.** `--g-accent-ink == --g-brand` in dark theme
   masked a light-theme defect on 8 screens. Any two tokens that are equal in
   one theme and different in another are a place where one theme hides the
   other's bugs, and that is computable directly from `tokens.json`.

**And a method note that outranks all three:** this audit was nearly wrong in
exactly the way the last one was. The instrument reported dark-olive fills on
20+ screens because it parsed hex tokens as decimal. It was caught only by
cross-checking one screen against a direct measurement made a different way.
**Two measurements that agree are evidence; one measurement is a hypothesis.**
