# Hand-Rolled Patterns & Non-Platform Standards in Nadi PWA

## Summary
A Vue 3 + Ionic PWA with a Glass design system overlay. The PWA retains Ionic core (routing, tab stacks, refresher) but reskins it with Glass components. Key non-iOS patterns: frappe-ui toast/dialogs, inline SVG icons, hand-built tab row in forms, animated page transitions (Ionic + custom fade), skeletons instead of spinners, and webfont loading for desktop fonts.

---

## Findings by Category

### 1. frappe-ui Components (23 files, 8+ active uses)
**Files using frappe-ui imports:**
- Components: LateCheckoutDialog.vue, RequestActionSheet.vue, HolidayList.vue, FormField.vue, ListView.vue, WhoToAsk.vue, CheckInPanel.vue, AttendanceCalendar.vue
- Composables: index.js, workflow.js, approvedCancel.js, decisionCapability.js
- Utils: commonUtils.js, formatters.js, loudRequest.js

**Component usage:**
| Component | Count | iOS Equivalent | Issue |
|-----------|-------|---|---|
| `toast()` | 8+ | Native toast/banner | Toasts are not native iOS; interrupt flow |
| `createResource` | 42 | Network request layer | API wrapper, appropriate |
| `Dialog` | 1 (FormView.vue:370) | UIAlertController / UIAlertAction | frappe-ui Dialog used for cancel confirmation |
| `TextEditor` | 1 (FormField.vue:51) | WKWebView or native text editor | Rich text in field inline |
| `Popover` | 1 (InstallPrompt.vue:11) | UIPopoverPresentationController | iOS Install prompt helper |
| `Button` | 1 (FormView.vue:381) | UIButton | Custom styled buttons via `<Button>` tag |
| `Dropdown` | 1 (FormView.vue:30) | UIMenu / UIContextMenuInteraction | More menu (frappe-ui) |

**Top replacement items:**
1. `toast()` → Native banner or status message (UIAlertController with no actions)
2. `Dialog` → GConfirm already replaces it, but one instance remains (FormView.vue:370)
3. `Dropdown` → UIMenu (iOS 13+) or long-press context menu

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/components/FormView.vue:370 — frappe-ui Dialog for cancel confirmation
- /home/nabil/nz-version-16/frontend/src/composables/index.js:27, 61 — toast calls
- /home/nabil/nz-version-16/frontend/src/components/FormField.vue:51 — TextEditor import
- /home/nabil/nz-version-16/frontend/src/components/InstallPrompt.vue:11 — Popover

---

### 2. Hand-Rolled SVG Icons (15 inline SVGs, 40 lucide imports)

**Inline SVGs found (8 components):**
| File | Count | Sizes | Patterns |
|------|-------|-------|----------|
| AttendanceCalendar.vue | 2 | 16×16 | Prev/Next chevrons, calendar icons |
| GAppHeader.vue | 2 | 16×16 | Back arrow, notification bell |
| GFileUpload.vue | 1 | 16×16 | Upload icon |
| GSearchBar.vue | 2 | 16×16, 19×19 | Search magnifier, clear button |
| GLogo.vue | 1 | — | Nadi brand mark |
| GListRow.vue | 1 | — | Chevron disclosure |
| GProgressRing.vue | 1 | 88×88 | Circular progress ring (SVG circle animation) |
| GSelfiePanel.vue | 1 | 24×24 | Camera shutter / selfie indicator |
| TeamDashboard.vue | 1 | 16×16 | Chart or navigation icon |
| KpiDetail.vue | 1 | 320×110 | Chart rendering (dynamic viewBox) |

**Lucide icon usage:**
- 40 lucide-vue-next icons imported across 12 files
- Usage: component slots (17 files use h-icon-md, w-icon-md classes)
- Stroke width: default (2px per lucide), no custom widths observed

**iOS standard:**
- iOS uses SF Symbols (system icons) with no stroke override
- Custom icons embedded as SVG are anti-pattern (binary bloat, no theme support)

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/components/glass/GAppHeader.vue:39, 65 — inline SVG back & notification bell
- /home/nabil/nz-version-16/frontend/src/components/glass/GProgressRing.vue:27 — animated ring (SVG circle with @keyframes animation)
- /home/nabil/nz-version-16/frontend/src/components/glass/GLogo.vue:12 — brand mark SVG
- 40 lucide imports found via grep (lucide-vue-next)

---

### 3. Hand-Built Lists (no GListRow/GListPanel pattern, border-b dividers)

**Hand-drawn row patterns (20+ instances):**
| File | Pattern | iOS Equivalent |
|------|---------|---|
| ExpenseItems.vue:5 | `class="flex flex-row ... border-b border-divider"` | UITableViewCell |
| ExpensesTable.vue:3 | `border-b-2 border-divider` | Table header separator |
| FormView.vue:71 | Sticky tab bar with `border-b border-divider` | UISegmentedControl or tab bar |
| HolidayList.vue:16 | `border-b border-divider last:border-b-0` | List row divider |
| ProfileInfoModal.vue:9 | `border-b border-divider last:border-b-0` | List row divider |
| RequestActionSheet.vue:5, 91, 114 | `border-t/border-b` sticky headers/footers | Sheet dividers |
| RemoteCheckinDialog.vue:22, 37 | Border styling for alerts | Input field border |

**Pattern frequency:**
- 20+ files use `border-b` or `border-t` + `flex flex-row` for rows
- No use of GListRow/GListPanel in these instances
- Dividers created via Tailwind borders, not platform list components

**iOS note:**
- UITableView/UICollectionView handle row separators automatically
- Hand-drawn borders are brittle (platform doesn't manage insets, safe area)

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/components/ExpenseItems.vue:5 — `flex flex-row py-3.5 px-0.5 items-center justify-between cursor-pointer border-b border-divider`
- /home/nabil/nz-version-16/frontend/src/components/FormView.vue:71 — sticky tab header with `border-b`
- /home/nabil/nz-version-16/frontend/src/components/HolidayList.vue:16 — hand-drawn list row

---

### 4. Animations & Transitions

**CSS @keyframes:**
| Name | File | Purpose | Duration | iOS Pattern |
|------|------|---------|----------|---|
| `g-indeterminate` | glass-components.css:551 | Determinate progress bar sweep | Not specified | CABasicAnimation |
| `g-shimmer` | glass-components.css:838 | Skeleton placeholder shimmer | Not specified | CABasicAnimation gradient |
| `g-pin-ring` | glass-components.css:1938 | Location pin expand/pulse | Not specified | CABasicAnimation |
| `user-pin-pulse` | CheckInPanel.vue:1538 | User location marker pulse | Defined inline | CABasicAnimation |

**Transition usage:**
- `transition: background var(--g-motion-row-tap-duration)` × 5+ rows
- `transition: transform var(--g-motion-button-press-duration)` × 3+ components
- Motion tokens: `--g-motion-row-tap-duration`, `--g-motion-button-press-duration`, `--g-motion-state-change-duration`

**Page transitions (ionicConfig.js):**
- iOS: Native `iosTransitionAnimation` (push animation from Ionic)
- Android/Desktop: Fade-through (Material 3) with 150–200 ms duration
- Reduced motion: Disabled (`prefers-reduced-motion: reduce` checked)

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/theme/glass-components.css:551 — `@keyframes g-indeterminate`
- /home/nabil/nz-version-16/frontend/src/utils/ionicConfig.js:22 — `iosTransitionAnimation` used for iOS
- /home/nabil/nz-version-16/frontend/src/components/CheckInPanel.vue:1538 — `@keyframes user-pin-pulse`

---

### 5. Header (GAppHeader) — No Large Title Pattern

**Current design:**
- Fixed header with inline SVGs (back arrow 16×16, notification bell 16×16)
- Title rendered as `<h1>` with `sr-only` on Home
- Logo (GLogo) shown on tab roots, hidden on pushed screens
- Avatar button (GAvatar) triggers profile route emit

**Missing iOS HIG patterns:**
- No **large title** that collapses on scroll (Apple HIG Lists and Tables)
- No **title view** with subtitle
- Header height is fixed (not dynamic)
- Avatar position: right edge (correct); logo position: left edge (replaces large title)

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/components/glass/GAppHeader.vue:29–82 — fixed header structure
- /home/nabil/nz-version-16/frontend/src/components/glass/GAppHeader.vue:39, 65 — inline SVGs for back & bell
- /home/nabil/nz-version-16/frontend/src/components/glass/GAppHeader.vue:46 — logo replaces large title on Home

---

### 6. Tab Bar (BottomTabs.vue) — Ionic Retained, Reskinned

**Current design:**
- Ionic `ion-tab-bar` + `ion-tab-button` with Glass restyle
- Floating pill shape (not full-width bar)
- No background (transparent so glass shows through)
- Selected state: full-color icon + bold label (no well/capsule around it)
- Icons: 19×19px (component size)

**iOS HIG compliance:**
- Tab bar placement: bottom ✓ (iOS standard)
- Icon-only tabs with labels ✓
- 5-tab max: Not enforced in code (TAB_ITEMS from navItems)
- Floating pill: Non-standard (iOS tab bar is edge-to-edge on iPhone)

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/components/BottomTabs.vue:8–26 — Ionic tab bar with Glass classes
- /home/nabil/nz-version-16/frontend/src/components/BottomTabs.vue:62–79 — Ionic customization (--color, --background)
- /home/nabil/nz-version-16/frontend/src/components/BottomTabs.vue:20 — Icon component at `h-icon-md w-icon-md`

---

### 7. Toasts, Alerts, Dialogs, Spinners

| Component | Count | Implementation | iOS Equivalent | Issue |
|-----------|-------|---|---|---|
| `toast()` | 8+ | frappe-ui toast | UIAlertController (alert style) | Non-native dismissal, interrupts |
| `GConfirm` | ~15 uses | Custom modal with focus trap | UIAlertController (actionSheet) | Correct for Glass |
| `GModal` | 117 uses | Ionic ion-modal + Glass restyle | UIViewController presented modally | Standard pattern |
| `Dialog` (frappe-ui) | 1 | FormView.vue:370 | UIAlertController | Swap for GConfirm (already done) |
| `GSkeleton` | 6 uses | Shimmer placeholder | Loading skeleton / CADisplayLink loop | Correct pattern |
| `GEmptyState` | ~5 uses | Custom state card | Empty view (UIViewController) | Correct pattern |

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/composables/index.js:27 — `toast({ message, icon: 'alert-circle' })`
- /home/nabil/nz-version-16/frontend/src/components/FormView.vue:335–368 — GConfirm for delete/submit/discard
- /home/nabil/nz-version-16/frontend/src/components/FormView.vue:370 — One remaining frappe-ui Dialog
- /home/nabil/nz-version-16/frontend/src/components/FormView.vue:298–302 — GSkeleton for loading state

---

### 8. Tailwind Arbitrary Values & Tokens

**Scan result:** No arbitrary Tailwind values found (`[#...]`, `[rgb(...)]`)

**Custom theme values (all token-based):**
- Colors: `bg-accent`, `bg-ground`, `text-ink`, `text-ink-600`, `border-divider` — all from CSS variables
- Spacing: `px-4`, `py-3`, `gap-3` — Tailwind scale
- Radius: Remapped to Glass ladder (6px, 9px, 14px, 17px, 20px, 22px) — not Tailwind defaults
- Motion: `var(--g-motion-*-duration)` tokens in transitions
- `safe-area-inset-*` env() for notch support

**Evidence:**
- /home/nabil/nz-version-16/frontend/tailwind.config.js — No arbitrary values; all through `extend` object
- /home/nabil/nz-version-16/frontend/src/theme/glass.tailwind.cjs — Generated from design/tokens.json

---

### 9. Fonts & Type System

**Loaded fonts (theme/fonts.css):**
| Family | Source | Display | Weights | Use |
|--------|--------|---------|---------|---|
| Inter | frappe-ui variable | swap | 100–900 | UI primary (already loaded by frappe-ui) |
| Inter Tight | @fontsource-variable | swap | 100–900 | Display/branding |
| JetBrains Mono | @fontsource-variable | swap | 100–800 | Code / mono |

**Font stack (Tailwind config):**
```
sans: "var(--g-font-ui)"  →  -apple-system, BlinkMacSystemFont, "Inter Tight", Inter, sans-serif
```

**iOS note:**
- `-apple-system` is first ✓ (uses native San Francisco)
- Fallback to Inter/Inter Tight for consistency
- JetBrains Mono ships for code snippets (rare in PWA, adds 40+ KB gzipped)
- `font-display: swap` — FOUT (flash of unstyled text) instead of invisible text

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/theme/fonts.css — Three @font-face declarations
- /home/nabil/nz-version-16/frontend/tailwind.config.js:35–38 — Font family as CSS variable

---

### 10. Web APIs & Platform Features

| API | File:Line | Usage | iOS Support | Issue |
|-----|-----------|-------|---|---|
| `document.startViewTransition()` | /data/theme.js:43, 54 | Theme toggle with CSS animation | Safari 18.1+ | Graceful fallback ✓ |
| `window.matchMedia(prefers-reduced-motion)` | ionicConfig.js:9 | Disable animations for a11y | Safari 10+ | Used correctly ✓ |
| No `alert()`, `confirm()`, `prompt()` | — | Avoided throughout | — | Good ✓ |
| No `navigator.vibrate()` | — | — | — | Not needed for PWA |
| No `navigator.share()` | — | Web Share API not called | — | Could use for share sheet |
| No `setAppBadge()` | — | Badge notifications | Safari 15.1+ | Not implemented |
| No `wakeLock` | — | Screen stay-on | Safari not supported | Not needed |
| No WebAuthn (`navigator.credentials`) | — | Biometric auth | Safari 16+ | Not implemented |

**Evidence:**
- /home/nabil/nz-version-16/frontend/src/data/theme.js:43–54 — `document.startViewTransition()` with fallback check

---

## Counts & Summary Table

| Category | Count | iOS Standard? | Top Priority Fix |
|----------|-------|---|---|
| frappe-ui components | 23 files | No (toast, Dialog) | Replace remaining `Dialog` (1 instance) |
| Inline SVGs | 15 | No (use SF Symbols) | Use lucide (already 40 imports) or SF Symbols |
| Lucide icons | 40 imports | Partial (good fallback) | Use SF Symbols for platform parity |
| Hand-built lists | 20+ instances | No (use UITableView) | Not critical for PWA; keep for now |
| CSS @keyframes | 4 named | Partial (custom timing) | Standard; reduce motion respected |
| Page transitions | 3 kinds | Yes (iOS native + fade) | Already correct |
| Toasts | 8+ uses | No | Replace with native banners (low-priority PWA) |
| Dialogs (GConfirm) | ~15 | Yes (Glass standard) | Good |
| GModal | 117 | Yes (standard sheet) | Good |
| Fonts | 3 families | Partial (-apple-system first) | Consider dropping JetBrains Mono |
| startViewTransition | 1 | Safari 18.1+ | Fallback present ✓ |

---

## Top 15 Items an Apple Engineer Would Change First

1. **Replace remaining frappe-ui `Dialog` (FormView.vue:370)** with GConfirm or native UIAlertController
2. **Remove inline SVGs, use SF Symbols** (or keep lucide as cross-platform fallback)
3. **Replace toast() with UIAlertController or banner** (8+ composable calls)
4. **Tab bar: Make full-width instead of floating pill** (BottomTabs.vue) — unless intentional brand choice
5. **Large title header with collapse on scroll** (GAppHeader.vue) — optional but iOS HIG standard
6. **Use UITableView / UICollectionView cell separators** instead of hand-drawn `border-b` (20+ instances)
7. **Drop JetBrains Mono webfont** (adds 40+ KB for code snippets that PWA rarely shows)
8. **Form tab bar: Use UISegmentedControl instead of hand-drawn flex row** (FormView.vue:71–88)
9. **Use native list cell components** for rows (HolidayList, ProfileInfoModal, etc.)
10. **Implement `navigator.share()` for share sheet** (social/forwarding actions)
11. **Add app badge via `setAppBadge()`** (unread notifications count on home icon)
12. **Use UIMenu for dropdowns** instead of frappe-ui Dropdown (FormView.vue:30)
13. **Skeleton loading: Use CADisplayLink loop or native spinner** instead of CSS shimmer (minor)
14. **Verify TextEditor is necessary** (FormView.vue:51) — consider plain textarea for PWA
15. **Enforce motion preferences on all @keyframes** — already respects `prefers-reduced-motion` ✓

---

## Positive Findings (Already iOS-Compliant)

- ✓ `-apple-system` font stack is first
- ✓ Motion reduced on `prefers-reduced-motion`
- ✓ `document.startViewTransition()` has fallback check
- ✓ GModal (Ionic ion-modal) is standard platform sheet
- ✓ GConfirm (custom modal) correctly wraps alertController pattern
- ✓ GSkeleton / GEmptyState patterns match native equivalents
- ✓ No arbitrary Tailwind colors (all CSS variables)
- ✓ Ionic core (tab stacks, page routing) retained as-is
- ✓ No `window.alert()`, `confirm()`, `prompt()` misuse
