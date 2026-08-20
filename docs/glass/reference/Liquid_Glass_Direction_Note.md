# Liquid Glass on the web — direction note

**Context:** the design direction is confirmed as glassmorphism in the Apple Liquid Glass lineage. This note covers what that means in August 2026, what CSS can and cannot reproduce, and the three adaptations your user base requires.

---

## 1. Which Liquid Glass you're copying matters

Liquid Glass is Apple's design language introduced with iOS 26 in September 2025 — the biggest visual change since iOS 7. It has been revised **three times** since, all in the same direction: less transparent.

| When | What happened |
|---|---|
| WWDC June 2025 | Reveal. Heavy translucency, refraction, specular highlights |
| iOS 26 betas 2–4 | <cite index="36-1">Apple added opacity to interface elements, reducing transparency — toolbars and buttons became more solid</cite>, specifically because <cite index="36-1">top-level elements were hard to read when text or images sat beneath them</cite> |
| iOS 26.1 (Nov 2025) | <cite index="35-1">A "Tinted" setting that tones down the gloss and restores a flatter, calmer reading surface</cite>, after <cite index="35-1">designers and accessibility advocates said the surface introduced visual noise and undermined outdoor readability</cite> |
| **WWDC June 2026** | <cite index="29-1">Apple scaled back Liquid Glass — improving icon clarity, readability and usability. It keeps the glass look but clearly prioritises usability over visual flair</cite>. <cite index="33-1">iOS 27 shipped explicit refinements to contrast, blur, Reduce Transparency defaults and new opt-outs</cite> |

Nielsen Norman's review was blunt: <cite index="32-1">the interface is restless, less predictable, less legible, and pulls focus rather than supporting access to content</cite>.

**The practical takeaway:** copy iOS 27's glass, not the WWDC 2025 reveal. The reveal is what most web tutorials and Dribbble shots imitate, and it's the version Apple itself has spent a year retreating from. If the mockup was drawn from 2025 reference material, that's worth checking before it's frozen into a spec.

**Your spec mostly gets this right already.** §5's "light glass is 56% opaque, not 7.5% — do not 'correct' this", §12's static blobs, and §8.12's rule that disputable numbers never sit on glass are all the same lessons Apple learned the expensive way. Whoever wrote it was paying attention.

---

## 2. What CSS can and cannot do

Native Liquid Glass is a GPU material with real-time refraction, edge lensing, specular highlights that track device motion, and adaptive contrast that samples the backdrop and flips foreground colour. `backdrop-filter` is a blur. These are not the same tool.

| Effect | Web feasibility |
|---|---|
| Frosted blur + saturation | **Native.** `backdrop-filter: blur() saturate()` — your spec's recipe |
| Rim light / inset highlight + shadow | **Native.** Inset box-shadows — spec already does this |
| Diagonal sheen | **Native.** Gradient on `::after` — spec already does this |
| Depth ordering, shadows | **Native.** |
| **Edge refraction / lensing** | **Approximation only.** Needs an SVG `feDisplacementMap` or WebGL. Expensive, buggy across browsers, and a per-frame cost your §12 budget cannot absorb |
| **Specular highlights tracking motion** | **Skip.** Needs device orientation; battery and motion-sickness cost, no benefit |
| **Adaptive contrast** | **Not available.** CSS cannot sample its own backdrop luminance. This is *the* reason Apple's glass is legible over arbitrary wallpapers and yours will not be — and it's why your light field must be a controlled, known background rather than user content |

That last row is the single most important technical fact in this note. Apple can be transparent because the OS re-computes foreground contrast against whatever is behind. You cannot. Your compensation is that you **own** what's behind the glass — the three blobs — so you can guarantee the worst case by construction. Which is exactly why the blob-placement constraint from the audit (no blob centre inside the content column) is not a nitpick; it is the mechanism that replaces adaptive contrast.

**Recommended fidelity ceiling:** blur + saturate + rim + sheen + lift. No refraction, no lensing, no motion-linked speculars. That's roughly 85% of the perceived effect at 20% of the cost, and it's what your spec already describes.

---

## 3. Three adaptations for your users

Liquid Glass was designed for recent iPhones held indoors. Your users are Malaysian F&B, retail and warehouse staff on mid-range Android, frequently outdoors or under bright fluorescent light, punching in and out.

**3.1 Outdoor legibility.** The sharpest criticism of Liquid Glass came from high-brightness markets: <cite index="35-1">reflective UI layers become liabilities under full sun, and corporate and education fleet administrators flagged legibility and compliance risk</cite>. Malaysia is a high-brightness market. Test the check-in screen outdoors at midday on the lowest-spec handset before the design is signed off — that is the actual use case for the app's most important screen, and it is the worst case for this material.

**3.2 Ship a "Reduce transparency" toggle.** Apple was forced to add one, then to promote it, then to change its defaults. Build it in from the start: one setting that swaps `--glass-fill` to its opaque fallback value across the app. You already have the `@supports not (backdrop-filter)` fallback values in §12 — the toggle reuses them, so it costs almost nothing. It also honours `prefers-reduced-transparency`, and it gives you a real answer if anyone raises an accessibility objection.

**3.3 Glass is chrome, not content.** Apple's own retreat has been consistent about where glass belongs: navigation, toolbars, controls — not text-heavy reading surfaces. Your §8.12 already says this for payslips and KPI scores. I'd extend it: glass on the tab bar, headers, buttons, banners and cards; solid surfaces for any screen a person reads rather than taps.

---

## 4. What this means for the spec

Four additions for v1.1:

1. **A stated fidelity ceiling** — blur/saturate/rim/sheen only, no refraction. Stops someone "improving" it with an SVG displacement map later.
2. **Blob placement as a hard constraint**, framed as the substitute for adaptive contrast.
3. **A reduce-transparency mode** as a first-class state, with token values (it's the `@supports` fallback, reused).
4. **A note on which Liquid Glass is the reference** — iOS 27, not the 2025 reveal — so future contributors calibrate to the same thing.

None of these change the look. All four are what keeps it shippable.

---

*Sources current to August 2026.*
