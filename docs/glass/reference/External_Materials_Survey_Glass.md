# External Materials Survey — what to adopt to deliver the Glass mockup

**Question:** are there existing components / primitives / kits out there that get us to the mockup, rather than authoring all ~30 primitives by hand?
**Short answer:** yes for the expensive 80%, no for the part HR is actually looking at.
**Verified:** all versions below checked against the npm registry on 20 Aug 2026.

---

## 1. The honest framing

Glassmorphism is not installable. There is no production-grade Vue/Tailwind component kit that ships translucent surfaces, backdrop blur, light fields and rim lighting as a coherent system. What exists in that space is demos, CSS generators and Apple-Liquid-Glass clones — none of them accessible, themed, tested, or safe on a mid-range Android under `backdrop-filter`.

But the glass *skin* is not where the work is. The work is in the behaviour underneath it: focus management in a modal, keyboard navigation in a combobox, date arithmetic and locale in a picker, ARIA wiring, dismissal semantics, list virtualisation. That layer **is** installable, it's the part that takes months to get right by hand, and it's where your current app is weakest — because `frappe-ui@0.1.105` gives you styled components you can't theme, so any glass treatment means fighting them.

So the strategy is: **buy the behaviour, author the skin.** Roughly 80% of the effort is purchasable; the remaining 20% is the brand, and that 20% is what HR will see.

---

## 2. The biggest find is a library you already depend on

You are pinned at **`frappe-ui@0.1.105`**. Current is **`0.1.278`**. In between, Frappe rebuilt it into exactly the architecture the Glass spec prescribes:

| What changed | Why it matters to you |
|---|---|
| `darkMode: ['selector', '[data-theme="dark"]']` | **The exact `data-theme` mechanism spec §13 asks for**, built in |
| Semantic token system — `surface-*`, `ink-*`, `outline-*` generated as CSS variables from `colors.json` (lightMode / darkMode / overlay / neutral / themedVariables), with a `figma-variables-to-colors.js` pipeline | This is the token architecture you hand-built as Modernist, and the reason you're maintaining a palette in three files by hand |
| Now built on **reka-ui** (+ `lucide-static`, `unplugin-icons`, `@tiptap`, `echarts`, `@floating-ui`) | Aligns you with the mainstream Vue headless ecosystem instead of a bespoke one |
| **56 components**, up from ~20 | See the mapping table below |
| Inter variable bundled with `opsz` / `cv11` variation settings | Spec §13's "self-host Inter" — already done, and better than the CDN Archivo you load today |
| `.story.vue` files per component | A ready-made specimen convention for the `/design` route |

**Components in 0.1.278 that map directly onto gaps in the Glass spec:**

| frappe-ui component | Fills |
|---|---|
| `CircularProgressBar` | **§8.8 KPI progress ring** |
| `DatePicker`, `MonthPicker`, `Calendar` | The date picker and calendar the spec never defines — your highest-friction control |
| `Combobox`, `MultiSelect`, `Autocomplete` | Frappe link fields |
| `Alert` | **§8.9 Banner** |
| `Dialog`, `Popover`, `Dropdown` | Modals and sheets |
| `ListView`, `ListItem`, `ListFilter` | List rows and filters |
| `Progress`, `Badge`, `Switch`, `Slider`, `Rating`, `Tabs`, `TabButtons`, `FileUploader`, `Sidebar`, `CommandPalette`, `Charts` | The rest of the inventory gap |

**The catch, stated plainly:** it's a 173-version jump on a library that's pre-1.0 and moves fast. Breaking changes are certain. And frappe-ui's token vocabulary (`surface-gray-2`, `ink-gray-8`, `outline-gray-3`) is *its own* system — Glass would sit on top of it as a theme, not replace it. Its radius scale tops out at 20px (`2xl`); Glass needs 22px for the tab bar. Its `fontSize` scale bottoms out at 11px (`2xs`); Glass wants 7.5px and 8.5px — which, per the accessibility audit, it probably shouldn't have anyway.

**Recommendation:** spike the upgrade on a branch before committing to anything else. It plausibly deletes half the work in the reuse map, and it plausibly breaks 103 files. You need to know which before sequencing.

---

## 3. Candidate libraries — verified

| Library | Latest | Last publish | Verdict |
|---|---|---|---|
| **reka-ui** | 2.10.3 | 10 Aug 2026 | **Adopt.** The Vue headless standard (ex-Radix Vue). Unstyled dialog / combobox / listbox / tabs / toast / tooltip with full a11y. Arrives transitively with frappe-ui ≥ 0.1.2xx anyway |
| **shadcn-vue** | 2.8.2 | 8 Aug 2026 | **Adopt as source, not dependency.** It's copy-in components over reka-ui + Tailwind + CSS-var tokens. Take its component *structure* and variant patterns, restyle to Glass. Its token model is the one the spec describes |
| **style-dictionary** | 5.5.2 | 19 Aug 2026 | **Adopt.** One `tokens.json` → `glass.css` + Tailwind config + `variables.css`. This is the direct fix for the 3-way manual palette sync your own comments warn about |
| **@fontsource-variable/inter** | 5.3.0 | 19 Jul 2026 | **Adopt.** Self-hosted variable Inter, WOFF2, subsettable — spec §13 verbatim |
| **@fontsource-variable/inter-tight** | 5.3.0 | 19 Jul 2026 | **Adopt.** The display family the spec calls for. Replaces the Google Fonts CDN Archivo link |
| **tailwind-variants** | 3.3.1 | 3 Aug 2026 | **Adopt.** Typed variant/slot API. Makes "one component, six states, two themes" declarative instead of a `:class` ternary pile |
| **@axe-core/playwright** | 4.13.0 | 11 Aug 2026 | **Adopt.** The a11y CI gate. Given the contrast findings, non-optional |
| **@vueuse/core** | 14.4.0 | 29 Jul 2026 | **Adopt.** `usePreferredColorScheme`, `useMediaQuery('(prefers-reduced-motion)')`, `useNetwork` for §9.3 offline |
| **@vuepic/vue-datepicker** | 14.0.0 | 2 Jun 2026 | **Fallback only.** Try frappe-ui's `DatePicker` first; this is the escape hatch. Themeable via CSS vars |
| **motion-v** | 2.4.0 | 15 Aug 2026 | **Consider.** Motion for Vue. Only worth it if §6's spring/sheet choreography needs it — CSS transitions cover most of the table, and the spec restricts you to `transform`/`opacity` regardless |
| **unplugin-icons / @iconify/vue** | 23.0.1 / 5.0.1 | 2026 | **Consider.** Build-time SVG icons, any set, tree-shaken. Note: **no popular set matches the spec's 16×16 grid at 1.55 stroke.** Lucide and Tabler are 24×24/2px, Iconoir 24×24/1.5px. Either rescale a set and accept sub-pixel strokes at 14px, or keep drawing your own — you already have 9 |
| **konsta** | 5.3.0 | 28 Jul 2026 | **Skip.** Tailwind mobile components in iOS/Material idiom. Well-made, but it's a *different* design language and you already have Ionic for the mobile shell. Adopting it means two opinions about what a sheet is |
| **radix-vue** | 1.9.17 | 28 Feb 2025 | **Skip — superseded.** Renamed to reka-ui |
| **@headlessui/vue** | 1.7.23 | 9 Sep 2024 | **Skip — stale.** Two years without a release |
| **vaul-vue** | 0.4.1 | 15 Mar 2025 | **Skip.** Drawer/sheet; Ionic already gives you gesture sheets with hardware-back handling |
| **tailwindcss** | 4.3.3 | 16 Jul 2026 | **Not yet.** v4's `@theme` is token-native and would suit Glass well, but frappe-ui's preset is v3-shaped (`tailwindcss/plugin`, `darkMode: ['selector', …]`). Don't stack a major Tailwind migration on top of a 173-version frappe-ui jump |
| **@ionic/vue** | 9.0.0 | 19 Aug 2026 | **Assess separately.** You're on 7.4 — two majors behind. Ionic 8/9 changed theming defaults. This is its own project, not part of the redesign |

---

## 4. What no library gives you

These are yours to author, and they are the entire visual identity:

- The glass recipe — fill / rim / inset highlight / inset shadow / sheen / lift, as one class
- The light field — three blobs, per page, inside the correct stacking context
- The chartreuse system and the "never sets type on light" rule
- The type scale, the tracking, the tabular-figure discipline
- The 6-surface performance budget and the glass-stop rule for disputable numbers (§8.12)
- The motion vocabulary

That's roughly 20% of the build — and it's 100% of what HR is evaluating. Which is the useful thing to know: **adding libraries de-risks the schedule and the accessibility, but it does not move you toward the mockup.** Only the token values and the glass recipe do that. If the pitch to HR is "we're adopting a component library to modernise the UI", that's the wrong pitch; the library work is invisible to them.

---

## 5. Recommended stack

```
Behaviour      reka-ui (via frappe-ui ≥0.1.278)
Components     frappe-ui 0.1.278 — upgrade from 0.1.105
Patterns       shadcn-vue, copied in and reskinned — not a dependency
Tokens         style-dictionary → glass.css + tailwind config + ion variables
Variants       tailwind-variants
Type           @fontsource-variable/inter + inter-tight (drop the Google CDN)
Icons          keep hand-drawn on the 16×16 grid; unplugin-icons only if the set grows
Shell          Ionic stays — pages, sheets, action sheets, refresher, tabs
Motion         CSS transitions; motion-v only if §6 demands it
Gates          @axe-core/playwright, Playwright visual regression, eslint no-hex/no-arbitrary
```

**The rule that keeps this coherent:** one owner per concern. Ionic owns navigation-level surfaces (page, sheet, action sheet, refresher). frappe-ui/reka owns in-page behaviour (combobox, date picker, dialog, tabs). Your Glass layer owns *all* appearance and nothing else. The moment two libraries both provide a dialog and both get used, the system has forked.

---

## 6. Risks

1. **frappe-ui upgrade blast radius.** 173 versions, pre-1.0. Spike it first, on a throwaway branch, and count the breakages before anything is scheduled.
2. **Bundle weight.** This is a PWA for mid-range Android on 4G. Every dependency is checked against that, not against developer convenience. `echarts` arriving transitively with frappe-ui is worth measuring specifically.
3. **Double-provisioning.** Ionic + reka both do dialogs, tabs, toasts. Pick per surface, write the decision down, gate it in lint.
4. **The `frappe-ui` directory at your repo root** appears to be a submodule. If you're vendoring or patching frappe-ui, the upgrade path is different and I'd need to see it.
5. **Token vocabulary collision.** frappe-ui's `surface-*`/`ink-*` and Glass's `--ink`/`--ink2`/`--glass-fill` must be explicitly layered, not merged. Decide which is the base and which is the theme.

---

## 7. What to do next

1. **Spike `frappe-ui@0.1.278`** on a branch. Count what breaks. This single result reshapes the whole plan and is a day's work.
2. Send me `HR_FRAPPE_Glass_Light_and_Dark.html` — still the blocker for spec v1.1.
3. Confirm whether the root `frappe-ui/` directory is a submodule, a vendor copy, or a fork.

---

*All package versions verified against the npm registry, 20 Aug 2026. frappe-ui token architecture read from the published 0.1.278 tarball.*
