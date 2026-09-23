# Recollection: gates, tests, lint, build, grep counts

Date: 2026-09-23 · Branch: nz-glass · HEAD e6eb026cb · Measurement only (nothing edited, committed or stashed)

## 1. Design gates: `yarn gates` (= `node design/gates/run.mjs`, run from frontend/)

Runner exit 0. **7 PASS, 0 FAIL, 3 SKIP.**

| Gate | Result | Findings |
|---|---|---|
| lint | PASS (report mode) | 127 known, 0 new (rawPalette 54, hex 52, colorfn 4, arbitrary 15, outline 2), baselined across 39 files |
| usage | PASS | 0 known, 0 new |
| contrast | PASS | 44 pairs, 0 failed, 0 skipped |
| surfaces | PASS | 49 screens, 0 over 6, flattening held |
| tokens | PASS | 3 role bindings hold, 6 known dark-only collapses, 0 new |
| scale | PASS | 8 type steps, 19 spacing/radius values on 4pt grid, 0 off-grid |
| motion | PASS | 155 files, 0 dead vars, 0 off-scale |
| a11y | **SKIP** | no site at http://localhost:8080 |
| visual | **SKIP** | no site at http://localhost:8080 |
| coherence | **SKIP** | "the spec produced no report" (same cause: no site) |

The runner prints its own warning: "3 of 10 gates MEASURED NOTHING … Do not read this board as a pass."

`node design/gates/lint.mjs --strict`: **exit 1**. The 127 baselined violations count as failures under strict mode.
Top baseline files: components/AttendanceCalendar.vue (arbitrary 1), components/BottomTabs.vue (arbitrary 2), components/CheckInPanel.vue (rawPalette 5, hex 4, colorfn 3, arbitrary 4).

## 2. Unit tests

- `cd frontend && node --experimental-test-module-mocks --test` (the `yarn test` script): **814 tests, 814 pass, 0 fail**, 0 skipped, about 6.4 s.
  153 test files (89 .js, 64 .mjs) across src/**/__tests__, src/data, tests/, tests/audit.
- `node --test design/gates/*.test.mjs` (contrast-column, tabbar-reservation, verdict): **15 tests, 15 pass, 0 fail.**
- No tests failed.

## 3. Lint

- `npx eslint src --ext .vue,.js` (the `yarn lint` script, .eslintrc.cjs): **323 files, 0 errors, 0 warnings.**
- No biome or oxlint config or binary in frontend/.

## 4. Build: `npx vite build --base=/assets/hrms/frontend/ --outDir /tmp/nadi-build-check`

Checked first: vite.config outDir is `../hrms/public/frontend`, and it was overridden. The frappe-ui plugin's type generation is off (there is no frappeui config). The `copy-html-entry` step was not run.

- Result: success, built in 11.9 s, 2644 modules. Service worker precaches 177 entries (3736 KiB).
- Total output: **8.5 MB, 218 files.** JS 3.74 MB, CSS 188 KB, fonts about 4.3 MB (39 woff2 files, 37 of them Inter: the full Inter + Inter Display family, every weight and italic, still bundled).
- Largest 5 files:
  1. assets/pdf.worker.min-*.js: 1,344 KB
  2. assets/frappe-ui-*.js: 928 KB (gzip 298 KB)
  3. assets/index-*.js: 490 KB (gzip 119 KB)
  4. assets/PdfInlineViewer-*.js: 377 KB (gzip 114 KB)
  5. assets/Inter-Italic.var-*.woff2: 297 KB (next is sw.js at 107 KB)
- Warnings:
  - CSS minify `css-syntax-error`: "Expected identifier but found whitespace" at bundled CSS line 6011:72, next to the comment "…tabbar-reservation.test.mjs guards. */".
  - Chunks larger than 500 KB (frappe-ui, pdf.worker).
  - FilePreviewModal.vue and WorkflowActionSheet.vue are both dynamically and statically imported, so the dynamic import in RequestActionSheet.vue does not split anything.
  - Inter-DisplayRegular.woff2?v=3.19 did not resolve at build time.
  - Stencil `/*@__PURE__*/` annotation notices (from dependencies). Browserslist data is 19 months old.
- **/tmp/nadi-build-check was NOT deleted.** The permission system denied `rm -rf`, so it still needs deleting by hand. It is outside the repo.

## 5. Grep counts (frontend/src, `__tests__` excluded)

| Pattern | Count | Examples |
|---|---|---|
| `text-overflow: ellipsis` | 4 in 2 files | views/kpi/Dashboard.vue:843 · theme/glass-components.css:272 · theme/glass-components.css:1296 |
| `truncate` class | 19 in 11 files | components/SideNav.vue:142 · components/SideNav.vue:145 · components/ContactCard.vue:21 |
| `line-clamp` | 2 in 1 file | theme/glass-components.css:1457 (comment) · :1471 `-webkit-line-clamp: 2` |
| Emoji in strings | 3 in 2 files, 1 user-facing | components/CheckInPanel.vue:14 `__("Hey, {0} 👋")` · composables/index.js:39, :58 (console.log "✅", not user-facing) |
| `toUpperCase()` | 9 in 9 files | components/ContactCard.vue:72 (initials) · components/CheckInPanel.vue:5 (date kicker) · components/AttendanceCalendar.vue:165 (day abbr) |
| `uppercase` Tailwind class | 18 in 14 files | components/LateCheckoutDialog.vue:26 · :40 · components/ContactCard.vue:13 |
| `text-transform: uppercase` (CSS) | 17 in 3 files | views/sop/SopFormSheet.vue:460 · views/sop/SopDetail.vue:184 · :251 (rest in theme/glass-components.css) |
| Title Case `__()` strings (2+ words, all capitalised) | 130 in 50 files | see sample below |
| Hex colours, views + components (not theme/) | 5 in 2 files | components/CheckInPanel.vue:1520 `#2563eb` · :1521 `#ffffff` · :1548 `#111827 !important` |
| `rgb()/rgba()`, views + components (not theme/) | 9 in 4 files | components/PdfInlineViewer.vue:31 (inline style) · components/CheckInPanel.vue:1522 · :1532 |
| `backdrop-filter` in theme/ | 24 mentions, all in theme/glass-components.css: 8 `backdrop-filter:` + 8 `-webkit-backdrop-filter:` declarations, the rest comments/vars | theme/glass-components.css:185 (comment) · :210 · :211 |
| Raw `<ion-modal` outside GModal/CustomIonModal | **8 in 8 files** | components/RequestActionSheet.vue:209 · components/RequestList.vue:40 · components/FileUploaderView.vue:58 · components/FormView.vue:319 · views/RemoteApprovals.vue:203 · views/Profile.vue:95 · views/sop/SopFormSheet.vue:2 · views/issues/HRIssueBoard.vue:95 |

`<IonModal` (PascalCase) outside those two: 0.

Title Case sample (10):
- components/LateCheckoutDialog.vue:27 `__("Actual Check-Out Time")`
- components/RequestList.vue:28 `__("View List")`
- components/ExpenseClaimSummary.vue:8 `__("Total Claimed")`
- components/ContactCard.vue:22 `__("Unnamed Employee")`
- components/CheckInPanel.vue:517 `__("Check In")`
- components/CheckInPanel.vue:519 `__("Check Out")`
- components/RequestPanel.vue:167 `__("My Requests")`
- components/RequestPanel.vue:167 `__("Team Requests")`
- components/AttendanceCalendar.vue:105 `__("Half Day")`
- components/AttendanceCalendar.vue:107 `__("On Leave")`

Note: the lint gate's 52 hex / 54 rawPalette count is higher than the 5 hex here. The gate also counts Tailwind palette classes and the theme-adjacent files it scopes differently.

## 6. Working tree check

`git status --short` was captured before starting and compared after every run. No gate, test, lint or build run changed it. Afterwards the tree differs only by new untracked files in docs/glass/audit/:
- `2026-09-23-recollection-platform.md`, `-rulings.md`, `-screens.md`: written by parallel sibling agents during this run, not by this one.
- `2026-09-23-recollection-gates.md`: this report (requested).
