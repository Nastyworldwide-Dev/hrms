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
