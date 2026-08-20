# Mockup ↔ Spec Reconciliation

**Inputs:** `HR_FRAPPE_Glass_Light_and_Dark_2.html` (the mockup) and `HR_FRAPPE_Glass_Implementation_Spec__1_.html` (the spec).
**Governing rule, per spec §1:** where the two disagree, **the mockup is correct and the spec should be corrected**. Applied throughout below, with two stated exceptions where the mockup value fails an accessibility criterion the spec itself sets.

---

## 0. Verdict

The mockup and spec are unusually well-aligned — the light-field geometry, the glass recipe, the type scale and the screen anatomies all match to the pixel. Whoever produced these worked from one source. Nine real conflicts, five of them trivial value drift; two decisions the mockup can't resolve on its own; and one class of problem the mockup introduces that the spec doesn't cover.

Most useful outcome: **the mockup separates cleanly into app material and presentation material**, and roughly a third of what makes it look good is the second kind — the animated blobs, the film grain, the cursor light, the shimmer sweep. Those must not ship as-is. Knowing which is which is what stops the build chasing an effect that was never meant for a phone.

---

## 1. Value conflicts — mockup wins

| # | Property | Spec says | Mockup says | Resolution |
|---|---|---|---|---|
| 1 | Primary action padding | `16px 18px` (§4 `pad-action`) | `.act` → **`17px 18px`** | **17px 18px** |
| 2 | List row padding | `12px 15px` (§4 `pad-row`) | `.row` → **`11.5px 15px`** | **11.5px 15px** |
| 3 | Balance number tracking | `−0.03em` (§3.1) | `.bcard .n` → **`−0.02em`** | **−0.02em** |
| 4 | Badge padding | `4px 8px` (§8.6) | `.badge` → **`3.5px 8px`** | **3.5px 8px** |
| 5 | Ghost action blur | §5 "one class, do not create variants" (20px) | `.act.ghost` → **`blur(18px)`** | **Two blur values are correct.** `--blur-panel: 20px`, `--blur-ghost: 18px`. §5's "no variants" line is what's wrong |

None of these are individually interesting. Together they're the reason a spec and a mockup have to be reconciled before prompting rather than after — five silent drifts is five components that will each be "nearly right".

---

## 2. Structural conflicts

### 2.1 The fifth tab changes between screens

The mockup's tab bar reads `HOME · ATTEND · LEAVE · PAY · ISSUES` on five screens — but on the KPI screen the fifth slot is **KPI**, not Issues. So the mockup implies **six destinations in five slots**, while spec §8.7 states *five items max, never scrolls*.

Your app has **eight**: Home, Attend, Leaves, Expenses, My KPI, Issues, SOPs, More.

Nothing in either document resolves this. It's an IA decision, and it's the one that most affects how the app feels day to day. Options:

- **A.** Five fixed + `More` as the fifth (Home / Attend / Leave / Pay / More) — everything else lives behind More. Cleanest, matches the spec's constraint, costs one tap to KPI and Issues.
- **B.** Five fixed with KPI and Issues promoted, Expenses and SOPs behind a `More` inside Home. Matches the mockup's apparent intent, drops `Pay` from the bar.
- **C.** Contextual fifth slot — what the mockup literally shows. **Don't.** A navigation bar whose destinations change under you is disorienting, and it breaks Ionic's per-tab navigation stacks.

Recommend **A**. It's the only option that survives the app growing again.

### 2.2 Screen count

Spec §1 says seven screens; §10's table lists eight; the mockup renders eight (Sign in, Home, Check in, Leave, Attendance, Overtime, KPI, Issues). **Eight.** Spec §1 is a typo.

### 2.3 Component count

Spec §8 claims twelve components and documents nine (8.1–8.9, then jumps to the 8.12 callout). The mockup contains, by my count, **21 distinct app-level components** — adding: calendar, stat tile trio, issue card, score panel, KRA panel, goals panel, map panel, selfie panel, clock, eligibility-note panel, textarea variant, logo well. The spec's inventory needs to be rebuilt from the mockup, not amended.

---

## 3. Presentation material that must not ship

The mockup is a pitch document. Four effects belong to the document, not the app. The spec catches one of them (§2.4, blob drift); it should catch all four.

| Effect | Mockup | Ship it? |
|---|---|---|
| Drifting light-field blobs | `.b1–.b4`, 34–46s infinite `transform` | **No** — spec §2.4 already declassifies this. Static in-app |
| **Film grain overlay** | `.grain`, fixed inset-0, SVG turbulence, `mix-blend-mode: overlay/multiply`, opacity .10–.16 | **No.** Not mentioned in the spec at all. `mix-blend-mode` on a full-viewport layer **creates a backdrop root** — it would neuter every `backdrop-filter` beneath it, and it's a full-screen composite per frame. If the texture is wanted, bake it into the field layer *below* the glass as a static image, never as a blend-mode overlay above it |
| **Cursor-following light** | `.cursor-light`, radial gradient tracking pointer | **No.** No pointer on a phone |
| **Shimmer sweep on the primary action** | `.act::before`, `animation: sweep 4.2s infinite` | **Decide.** It animates `left`, which triggers layout every frame — a direct violation of spec §12's "`transform` and `opacity` only". If it ships, it must be rewritten as `transform: translateX()`. My recommendation: drop it. A 4.2-second infinite shimmer on the one button people press twelve times a day is exactly the "constant motion adding zero information" that Liquid Glass got criticised for |

**The blob geometry itself is confirmed** — the mockup's in-phone `.sf-a/b/c` (230/210/180px, blur 36px, opacity .85 dark / .62 light, at the stated offsets) match spec §2.4 exactly. That part of the spec is accurate and buildable.

---

## 4. Accessibility failures the mockup introduces

These are cases where the mockup's value fails a criterion the **spec itself** sets in §11. Per the governing rule the mockup wins on values — but §11 is also normative, and the two cannot both be satisfied. These need an explicit ruling, and I'd rule for §11.

| Element | Value | Measured | Required | Note |
|---|---|---|---|---|
| **Screen eyebrow** `.hd .w` | `--ink2` at `opacity: .6` | **2.66:1** light / 3.65:1 dark | 4.5 | On **every screen**. The spec's §3.1 eyebrow row omits the opacity — remove it and it passes at 6.36:1 |
| **Calendar rest days** `.cal-g u.o` | `--ink3` at `opacity: .45` | **1.55:1** light / 1.72:1 dark | 4.5 | Dates are content, not decoration |
| **Ticket IDs** `.iss-id` | mono 8px `--ink3` | **2.96:1** light / 3.59:1 dark | 4.5 | Also 8px |
| **Calendar on-leave** `.cal-g u.l` | violet on violet-26% | **2.95:1** | 4.5 | Violet needs a darker light-theme value, same treatment as `--accent-ink` |
| **Legend swatch, rest day** | `#B6BDC9` | **1.78:1** | 3.0 | Also an untokenised colour — appears in neither document's palette |
| **Badge RESOLVED** | `#00806B` on teal-20% | **4.09:1** | 4.5 | Confirmed from the first audit |
| Balance bar / map pin / present-day fill | `#C8FF00` | **1.11:1** | 3.0 | Acceptable *only* because each carries a text label too (§11's "colour is never the only signal"). Verify per instance |

Everything else measured clean: ghost-button ink 18.4:1, stat labels 6.36:1, the eligibility hint in olive 7.21:1.

**Pattern worth naming:** every failure above is either an `opacity` multiplier applied to an already-tertiary ink, or an 8px type size. Both are habits that read as "refined" in a 1440px pitch deck viewed on a laptop and as "unreadable" on a 390px phone in a warehouse. The fix is mechanical — drop the opacity multipliers, raise the floor to 10px — and it costs the design nothing.

---

## 5. The glass budget is already at its ceiling

Counting glass surfaces per screen as the mockup renders them, against §12's limit of six:

| Screen | Glass surfaces | Headroom |
|---|---|---|
| Sign in | logo well + 2 inputs = 3 | 3 |
| Home | rows panel + 2 balance cards + tab bar = 4 | 2 |
| Check in | map + selfie + tab bar = 3 | 3 |
| **Leave** | 4 balance cards + rows panel + tab bar = **6** | **0** |
| **Attendance** | calendar + 3 stat tiles + ghost button + tab bar = **6** | **0** |
| **Issues** | 3 stat tiles + 2 issue cards + tab bar = **6** | **0** |
| KPI | score + KRA + goals + tab bar = 4 | 2 |
| Overtime | 3 inputs + note panel + tab bar = 5 | 1 |

Three screens sit exactly at the ceiling **in their happy-path state**. The spec then requires banner, empty, loading, error and offline states on top (§9) — every one of which adds a surface. Leave, Attendance and Issues will exceed the budget the moment a real state appears.

Two ways out, and one has to be chosen before build:
- **Raise the ceiling to 8** and re-validate on the target handset, or
- **Flatten the grids** — the 4-card balance grid and the 3-tile stat row become one glass panel with internal dividers. This is one surface instead of four or three, costs almost nothing visually, and is what I'd do.

---

## 6. Confirmed by the mockup

Useful to state, so these stop being open questions:

- **Blur 20px / saturate 180%** for in-app panels; the 26px/190% in the mockup is document chrome only, exactly as spec §12 says
- **Panel radius 20px**, card 17, action 19, input 14, well 9, tab bar 22 — all match
- **Light field geometry** — matches §2.4 exactly
- **Row divider** — `::before`, inset 15px each side, first row exempt — matches §8.3
- **Progress ring** — 88×88, r=38, stroke 7, circumference 238.8, rotate(−90deg) — matches §8.8
- **Mono is in-app**, not just documentation: pro-rated notes, geo coordinates, ticket IDs, the eligibility hint, the KPI pill. JetBrains Mono ships
- **Textarea** — input variant at `height: 66px`, `align-items: flex-start` — matches §10
- **`data-theme` on `<html>`** — matches §13, and matches what frappe-ui ≥0.1.2xx already expects
- **`prefers-reduced-motion`** — the mockup already kills all animation and transition
- **Font stack** — `-apple-system` first, Inter/Inter Tight fallback, no SF Pro bundled. Both documents agree, and the reasoning is sound

---

## 7. Token inventory needs rebuilding

The mockup's hero claims **18 tokens flip**. The spec's §2.2 table lists **12**. The mockup actually defines **22** themed custom properties — but seven of those (`--frame`, `--frame-rim`, `--screen-bg`, `--nav-bg`, `--code-bg`, `--cursor-light`, `--grain-op/--grain-blend`) are the phone bezel and document chrome, not the app.

**Actual app tokens that flip: 15** — `--bg`, `--ink`, `--ink2`, `--ink3`, `--accent-ink`, `--accent-glow`, `--glass-fill`, `--glass-rim`, `--rim-hi`, `--rim-lo`, `--lift`, `--hair`, `--icon-bg`, `--sheen`, `--blob-opacity`.

Plus **constants** that don't flip and are currently hardcoded at usage sites in both documents: `#C8FF00`, `#A8DC00`, `#0A0C05`, `#00E5C0`, `#7B5CFF`, `#F87171`, `#F59E0B`, `#00806B`, and the orphan `#B6BDC9`. All nine need names.

---

## 8. Ready for v1.1

With the mockup in hand, the spec amendment is now unblocked. v1.1 changes:

1. Correct the five value drifts to the mockup (§1 above)
2. Rebuild the component inventory from the mockup's 21 — plus the fork's real surface
3. Add the presentation-vs-app material rule, covering grain, cursor light and the sweep
4. Fix the contrast failures — drop the opacity multipliers, raise the type floor, add a light-theme violet, darken the resolved badge, redesign the focus ring
5. Tokenise the nine constants; correct the token count to 15
6. Resolve the tab bar to five fixed destinations
7. Flatten the balance and stat grids to one surface each, restoring budget headroom
8. Correct §1's screen count to eight
9. Add the reduce-transparency mode and the blob-placement constraint from the direction note

Say the word and I'll write it. After that, the prompt sequence.
