# The 64 visual diffs — classified before re-baselining

Rulings 1–7 changed 64 of 342 committed baselines. Every one was inspected as
an image **before** `--update-baseline`, because an unexamined re-baseline
turns a regression into the expected state — the same failure as the
self-comparing baseline that made this gate vacuous for weeks.

**61 intended · 0 regressions · 3 not code changes at all.**

## Method

Reading 64 screenshots one by one invites pattern-matching on filenames. So
each diff was **measured** first — changed-pixel count and bounding box — and
the 64 fell into five geometric signatures. Then before/after crops were
rendered for every screen and looked at, with the signature acting as a check
on the eye rather than a substitute for it.

The measurement earned its place immediately: it isolated
`employee-checkins-390-light` as the only diff with no dark twin and a 60px-wide
bounding box. That asymmetry is what a regression looks like. It was the clock.

## The split

| Cause | Screens | What the image shows |
|-------|--------:|----------------------|
| Ruling 3 — accent fill, submit → `GButton` | 24 | Olive `Save` → chartreuse, every form |
| Ruling 6 — a create action is a `GButton` | 12 | White `+ New` header pill → `New` `GButton` |
| Ruling 7 — duplicate create removed | 10 | Second *New* gone from the empty state |
| Ruling 5 — `GPage` owns back | 9 | `‹` present on pushed screens, absent on tab roots |
| Ruling 4 — one eyebrow treatment | 6 | Section labels grey → `--accent-ink` |
| Ruling 1 — no primary on a hub | 3 | *Request Attendance* demoted to a peer row |
| Coherence gate — `GEmptyState` | 2 | `remote-approvals` left-aligned → centred/dashed |
| **Baseline rot — no code change** | **3** | Date drift only |

Ruling 2 has no diffs of its own. It appears as a light-field gradient shift on
the 1440 shots, which is what one shell-owned field replacing three looks like.

## The three that were not changes

`home-390-dark`, `home-390-light` and `employee-checkins-390-light` differ only
because the seeded data aged: "yesterday" → "20 Aug", `FRIDAY, 21 AUGUST 2026` →
`SUNDAY, 23 AUGUST 2026`. `team` ×3 carried the same rot **on top of** a real
ruling-5 change, which is the dangerous shape — a real diff and a fake one in
one image.

`data-visual-mask` already existed for exactly this, and covered exactly **one**
element, in `Notifications`. Five more are now masked:

| Element | File |
|---------|------|
| header date kicker | `glass/GAppHeader.vue` (covers `BaseLayout` + `FormView`) |
| greeting date eyebrow | `CheckInPanel.vue` |
| "Last check-out was at …" | `CheckInPanel.vue` |
| stale check-in banner title | `CheckInPanel.vue` |
| per-row day label | `EmployeeCheckinItem.vue` |
| "TODAY · …" date nav | `team/TeamDashboard.vue` |

Masked at the **element**, not the row, so a layout regression inside these
containers is still caught. `utils/formatters.js:formatTimestamp` is the shared
root — anything new that calls it renders clock-dependent text and needs a mask.

## Two things the reconciliation exposed

**72 baselines changed, not 64.** The extra 8 carry a newly-masked element that
had not rotted yet, so they matched before and carry mask paint now. Worth
checking that arithmetic on any re-baseline: a file that changes without having
differed is either a mask or a regression that slipped the tolerance.

**The 0.2% tolerance hides small colour shifts on large viewports.** Ruling 4's
eyebrow recolour is real on `home-1440-dark` but was under `maxDiffPixelRatio`,
so the gate never reported it. At 1440×900 the threshold is ~2,500px and the
label is ~300px. The tolerance is correct for antialiasing, but it means the
visual gate is not the instrument for small type-colour changes — the contrast
and token gates are.

---

# Addendum — the 225 uppercase runs, classified

Same method, applied to the number the coherence gate was reporting instead of
asserting. `284 uppercase runs, 225 not using .g-eyebrow (reported, not
enforced)` is not a finding; it is a refusal to make one.

## The split, by declared role

| Category | Runs | Bare | Is it a section header? |
|----------|-----:|-----:|-------------------------|
| chip | 78 | 78 | No — status/badge text |
| field-label | 72 | 72 | No — labels ONE control |
| tabbar | 50 | 50 | No — tab labels |
| **section** | **48** | **0** | **Yes — enforced** |
| interactive | 13 | 1 | No — button text |
| segmented | 8 | 8 | No — segmented options |
| column-head | 7 | 7 | No — calendar day-of-week |
| stat-label | 7 | 7 | No — labels ONE number |
| nav-label | 1 | 1 | No — a date stepper's value |

So 236 of the 284 were correct all along, and the 225 was mostly noise hiding a
signal of two.

## What it caught

**`.g-quicklinks__title` — a seventh section-header treatment.** It lived in
`QuickLinks.vue`'s `<style scoped>` block and copied five of the six eyebrow
tokens by hand — family, size, weight, tracking, transform — then set the sixth,
the colour, to `--ink2`. Measured on `home`:

```
'Quick Links'  g-quicklinks__title  rgb(84, 92, 104)  10.5px   grey
'Requests'     g-eyebrow            rgb(63, 92, 0)    10.5px   accent-ink
```

Same screen, same role, same size, two colours. Ruling 4 consolidated six
treatments and missed this one **because it reads as an eyebrow in source** —
the tokens are right there. Only the rendered colour gives it away, and only
when compared against a sibling header on the same screen. That is a
cross-screen/cross-element question, which is exactly what gate 8 exists for and
exactly what a count cannot ask.

**The `team` date-stepper label** carried no role class at all — ad-hoc
`font-sans font-extrabold text-card-title uppercase text-inkbase`. Nothing
declared what it was, so nothing could check it. Moved to `.g-datenav__label`
in the theme layer, reproducing the previous appearance exactly (`team` did not
move a pixel in the visual gate, which is the proof).

## Why the rule is derived, not listed

The category is computed **in-page on every run** from the DOM — a structural
container (`ion-tab-bar`, `.g-seg`) or a role class the app already owns
(`.g-field__label`, `.g-stat__label`, `.g-cal__dow`). It is not a stored list of
225 approved strings, which would have frozen on the day it was written and
rotted from the next component onward — the same failure as a baseline nobody
re-derives.

Adding a role means editing `ROLES` in `frontend/e2e/coherence.spec.js`, which
is a deliberate and reviewable act. The gate cannot be quieted by sprinkling
classes on markup.

The remaining eight categories are baselined **by category** in
`design/eyebrow-baseline.json`, so a chip becoming a heading moves a number
someone is watching instead of disappearing into a total.

## Known gap

Detection only catches `text-transform: uppercase`. Text typed in capitals in
the source — `DRAFT` written literally — is not in the 284 and is not checked.
Widening it would change the population; it is recorded here rather than
silently left out.

---

# Addendum 2 — RC18, and the tolerance that hid it

## Four forms, not three

Measuring the DOM found one more than the audit named, and the extra one was
invisible to source search because it has no name:

| Form | Size | Radius | Fallback | Filter | Origin |
|------|------|--------|----------|--------|--------|
| `GAvatar` | `size` prop px | 9px | missing **and broken** image | none | component |
| `.g-header__avatar` | fixed 34 | 9px | missing only | none | hand-rolled CSS |
| Profile hand-rolled | fixed 72 | **0** | missing only | **grayscale** | open-coded Tailwind |
| `EmployeeAvatar` | frappe-ui: `sm`=20 `lg`=28 | 5–6px | frappe-ui's | **grayscale** | third-party wrapper |

`GAvatar` — the canonical one — rendered on **no production screen**. It was
used only by the DEV-only design specimen while three non-canonical forms served
every real screen.

`.m-avatar-sq` has not crept back; it exists only under `.reference/` and in
comments recording that it was not ported. **The treatment came back without
it**: `Profile.vue` open-coded `h-[72px] w-[72px] object-cover grayscale` — zero
radius plus desaturation, reconstructed by hand. A grep for "avatar" does not
touch it, which is why the rule finds avatars by **shape** rather than by class.

## The visual gate missed all of it

Ten avatars on `notifications` changed from a blank frappe-ui circle to a `?`
in a 9px box, and `toHaveScreenshot` **passed**. Reproduced exactly, one screen,
same masks, same tolerance: `1 passed`, `avatars=10`, `avatarsInsideMask=0`.

At 390×844 the 0.2% `maxDiffPixelRatio` is a **658-pixel budget**. Ten small
glyph-and-corner changes came to roughly 600. The header avatar's initial
growing 11.5px → 14px across eleven screens was likewise ~100px per screen —
also invisible.

**And a re-baseline could not repair it.** `--update-snapshots` defaults to
`changed`, so a screen that passes is never re-shot: under-tolerance means
"unchanged", permanently. Twenty-six baselines were silently stale and would
have stayed that way. They were corrected by deleting the gate-owned files for
the 13 avatar-bearing screens and re-shooting; the capture-only variants
(`-bottom`, `-rt`), which the gate does not own, were restored untouched.

The lesson is the same one the eyebrow rule taught, in a different instrument:
**a gate that compares is bounded by its threshold; a gate that asserts is
not.** `coherence` caught every one of these because it asks "is this the
avatar component?" rather than "do these pixels match?".

## Baselines drift looser than the app

Third instance this pass. `lint` reported 190 against a baseline of 194 — and
tightening it dropped `Login.vue` (6), `ForgotPassword.vue` (1) and
`ChangePassword.vue` (1) entirely: files cleaned in an earlier session whose
baseline entries were never reduced. A baseline looser than reality is a gate
that will not notice those violations returning. Worth re-running every
`--update-baseline` after a cleanup pass, not only after a deliberate change.
