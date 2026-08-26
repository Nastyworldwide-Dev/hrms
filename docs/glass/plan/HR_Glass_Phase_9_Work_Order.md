# Phase 9 — Work Order

Branch `nz-glass`. Written 24 August 2026 against `6ab5327bc`.

This file is the **build authority for phase 9**. It supersedes nothing in
`spec/HR_Frappe_Glass_Spec_v1.1.md`; it is the ordered work that closes the
findings in `frontend-audit.md`, `session_handoff.md` §5, and the system audit
of 24 August. Any agent picking this up should be able to work from this file
alone.

**Read order for a fresh agent:** this file → `spec/HR_Frappe_Glass_Spec_v1.1.md`
(§3 light field, §6 material, §14 accessibility, §15 surfaces, §16.5 gates) →
`session_handoff.md` (why five earlier findings had wrong causes).

---

## 0. Decisions — locked, do not re-litigate

| # | Decision | Ruling | Date |
|---|---|---|---|
| D1 | Typeface | **Inter Tight only.** Drop frappe-ui's static Inter family. DM Sans is not pursued. | 24 Aug, user |
| D2 | Edge refraction (`backdrop-filter: url(#…)`) | **Cut.** Ship the specular bevel; do not build the SVG displacement lens. | 24 Aug, user |
| D3 | Scope of the migration | **Remove Frappe's *design language* from the PWA. Keep frappe-ui's *data layer*.** See §8. | 24 Aug, user |

D2 means **there is no phase 9.3d**. It was proposed and rejected on measured
evidence (§1.1). Do not reintroduce it without new measurements on a real
device.

---

## 0.5 Phase 0 — production repair. Do this before any of phase 9.

Added 26 August. Phase 9 is quality work on a product that mostly works.
**This is live breakage on `verifica-live`, and it outranks all of it.**

### The reported symptom

Pressing the **Nadi** app icon on `/desk` navigates straight into a workspace.
It should open the permission-filtered workspace modal — nine HR workspaces —
the way **Accounting** does. Accounting is ERPNext's and untouched, which is why
it still works.

### Root cause — traced through the framework, not guessed

Frappe decides modal-vs-navigate on one condition
(`frappe/desk/page/desktop/desktop.js:1123`):

```js
if (this.child_icons?.length && (icon_type == "App" || icon_type == "Folder")) {
    create_desktop_modal(...)      // Accounting takes this
} else {
    navigate to icon_route         // Nadi takes this
}
```

The click handler was never broken. **Nadi has zero children**, and here is the
chain that emptied it:

| # | Evidence | What happened |
|---|---|---|
| 1 | `git show 5854aec26 -- hrms/desktop_icon/*.json` | The rebrand changed `parent_icon` `"Frappe HR"` → `"Nadi"` in nine files **and changed nothing else** — the `modified` timestamps still read `2026-01-01` |
| 2 | `frappe/modules/import_file.py:141` | `if is_db_timestamp_latest and doc["doctype"] != "DocType": continue` — standard-doc import is **timestamp-gated**. On a site whose rows are newer than the file, the new `parent_icon` **never lands** |
| 3 | `frappe/model/sync.py:120` | `desktop_icon/` is an app-level synced folder, imported during `sync_all()`. `nadi.json` is a **new** name, so it is created — no existing row, no gate |
| 4 | `hrms/patches.txt:81`, under `[post_model_sync]` | Patches run **after** `sync_all()`, so `exists("Desktop Icon", "Nadi")` is already True → the patch takes its **delete** branch: `delete_doc("Desktop Icon", "Frappe HR", force=True)` |
| 5 | `desktop.js:204` | `icon_map["Frappe HR"]` is gone, so the nine children are never pushed into `Nadi.child_icons` |

The patch deleted the parent that nine live records still pointed at, and
`force=True` skipped the link check that would have refused.

**Confirm on the site before fixing:**

```sh
bench --site verifica-live execute frappe.client.get_list \
  --kwargs '{"doctype":"Desktop Icon","filters":{"parent_icon":"Frappe HR"},"fields":["name"]}'
```

Nine rows back confirms it.

### It is a defect class, not an instance — two more casualties

Auditing every app-level synced JSON for "content changed, `modified` did not"
found **11 files**, not nine. The other two are Workspace definitions, and both
were shipped as *fixes* that silently did nothing on every existing site:

| File | Commit | What never reached production |
|---|---|---|
| `hrms/hr/workspace/hr_setup/hr_setup.json` | `de65b6379` *"make a sync that cannot start say so, and be findable at all"* | The **Data Migration** card and its **ERP Instance** links. The commit's whole purpose was to make the sync registry findable in Desk. It is still not there. |
| `hrms/hr/workspace/shift_&_attendance/shift_&_attendance.json` | `7b8102af9` *"restore Shift Assignment Tool to the sidebar"* | `link_count: 6 → 7`. The tool is still missing from the sidebar. |

Three shipped fixes that never reached production, and nobody noticed, because
**the failure mode is silent** — no error, no log line, a green migrate.

### Why every gate and every CI job was blind to it

`patch.yml` restores a **v14** backup and migrates forward. v14 predates the
Desktop Icon doctype, so those rows do not exist on that run — no existing row
means no timestamp gate, so the fixtures import cleanly and CI goes green.

> The timestamp gate only fires on a site that already has the rows — that is,
> every production site and no CI run. The migration gate and the defect can
> never intersect. This is not a gap in what CI checks; it is a gap in what CI
> can ever check, so the guard has to live somewhere else.

The eight design gates are equally blind: all of them render the PWA, and none
of this is in the PWA.

### Status — Phase 0 is DONE (26 August)

| id | Landed | Commit |
|---|---|---|
| 0.4 | Launcher discarded; backup at `scratchpad/discarded-launcher/` | — (was uncommitted) |
| 0.3 | Guard + 11 tests, pre-commit hook, PR-wide CI pass | `e76aebaae` |
| 0.2 | 13 fixture timestamps bumped + fixture contract test | `695a9fc9b` |
| 0.1 | Repair patch + 9 tests | `b5f9bdb74` |
| 0.5 | Folded into 0.2 and 0.1 rather than shipped separately | — |

**28 tests green, `ruff` clean.** The guard was verified by forcing the failure
it exists to catch: its suite runs it over `5854aec26` and asserts nine files.

Running it over history found **two more** offenders nobody had recorded — the
`Employee` role removal on both leave-balance reports (`561a9e714`) had never
reached a site. Those are Script Reports over `Employee` with no row scope of
their own, so that is the same org-wide-read hole `restrict_staff_script_reports`
was written to close. It is delivered by 0.2.

**Deploy step:** `bench --site <site> migrate`. The fixtures land first, the
patch backstops the rest. Confirm with the query above returning zero rows.

### The work as planned

| id | Item |
|---|---|
| **0.1** | **New patch** `v16_0/repair_nadi_desktop_icon_children.py`. Repoint every `Desktop Icon` with `parent_icon = "Frappe HR"` to `"Nadi"`, then remove the orphan if it still exists. Idempotent, and safe on a site that was never broken. **A new file, not a re-dated line** — the existing patch has already run on `verifica-live`, and its delete branch is the bug, so it should not be re-run. Leave it in place; it is history. |
| **0.2** | **Bump `modified` on all 11 files** to the current time so the import gate passes everywhere. Nine `desktop_icon/*.json` (excluding `nadi.json`, which was bumped), plus the two workspace JSONs above. This is what actually delivers the 17 August fixes to production. |
| **0.3** | **The guard.** A check that fails when a file under a synced path changes content without its `modified` advancing. Scope it to the diff — `git diff --name-only <base>..HEAD` filtered to `hrms/{desktop_icon,workspace_sidebar}/**` and `hrms/*/{workspace,notification,dashboard_chart}/**` — because a whole-tree heuristic false-positives on old files whose `modified` legitimately predates their last commit. Wire into `.pre-commit-config.yaml` **and** `linters.yml`. Verify by forcing the failure: edit a fixture, leave the timestamp, confirm red. |
| **0.4** | **Drop the launcher workaround.** See below. |
| **0.5** | **Regression test.** Assert `Desktop Icon "Nadi"` has nine children with `parent_icon = "Nadi"`, and that no `Desktop Icon` has a dangling `parent_icon`. A dangling-link assertion generalises past this one icon. |

### 0.4 — why the in-flight launcher is dropped

Uncommitted on the branch as of 26 August: `hrms/public/js/desktop_launcher.js`
(new), `frontend/e2e/hr-hub-launcher.spec.js` (new), plus edits to `hooks.py`
(`app_home` → `/desk/desktop/hrms`, a new `app_include_js`) and
`desktop_icon/nadi.json` (`link` → `/desk/hr-setup`).

It cannot work, because its own guard is the condition that is already failing:

```js
const permittedChildren = icons.filter(i => i.parent_icon === app?.label);
if (!app || !permittedChildren.length || …) return;   // ← returns, does nothing
```

With the children orphaned, `permittedChildren` is empty and the custom
launcher returns without opening anything — the same outcome as the native
handler it was written to replace. It also changes `app_home` for every user as
a side effect of a fix that never fires, and adds a permanent `app_include_js`
payload to Desk to re-implement behaviour the framework already has.

**Once 0.1 and 0.2 land, the modal works natively with no custom JS at all.**
Discard the two new files and revert the two edits. Keep nothing.

*(If the e2e spec is worth keeping, rewrite it against the native behaviour and
drop its hardcoded default user — it currently bakes in a real person's email
address.)*

### Order

`0.3` first — land the guard before the fix, so the fix cannot be written
without it and the guard gets exercised immediately. Then `0.2`, then `0.1`,
then `0.5`. `0.4` is a discard and can happen any time.

Then, and only then, phase 9 as ordered in §6.

---

## 1. Measurements this plan rests on

Every number below was produced on 24 August with Playwright + Chromium against
Nadi's real tokens. Re-measure before contradicting any of them.

### 1.1 The specular bevel is free; refraction is not

Six panels, 390×844 @2×, 90 scrolled frames:

| variant | median | p95 | max |
|---|---|---|---|
| A — shipping recipe | 16.7 ms | 16.9 | 17.5 |
| B — + specular bevel | 16.7 ms | 16.9 | 17.6 |
| C — + SVG displacement lens | 16.7 ms | **19.6** | **26.3** |

A and B are vsync-locked and indistinguishable. C drops frames **on a desktop
GPU**, so a mid-range Android is worse. Three further facts killed it:

- `-webkit-backdrop-filter` **silently ignores** `url()` filter references, so
  iOS Safari — the platform where a "liquid glass" product is most expected to
  look right — never renders it at all.
- `feImage` sizes in absolute pixels, so **one filter cannot serve panels of
  different geometry**. It would need one filter per surface size.
- The bevel already carries the effect. See 1.3.

### 1.2 Bringing the light field inboard is contrast-safe

Composited pixel sampled inside each panel directly over a blob; contrast
computed against the three ink roles.

```
DARK                         accent    ink    ink2
A  shipping                   11.51   13.61   6.10
B  + bevel                    10.77   12.74   5.71

LIGHT  (--c-glass #BBBBBC @36%, the reference value)
A  shipping                    7.08   18.08   6.25
B  + bevel                     5.44   13.90   4.80   ← thin

LIGHT  (--c-glass #FFFFFF @56%, corrected)
B  + bevel                     7.11   18.14   6.27   ← recovered
```

Every variant clears 4.5:1 on every role, in both themes, **with the blobs
fully inside the content column**.

**Therefore §3.3 does not need replacing — it needs re-asserting.** The rule
today is geometric ("no blob centre sits inside the content column", justified
by "CSS cannot re-sample the backdrop"). It becomes a **measured contrast floor
computed on the rendered DOM**. That is a smaller change than the earlier audit
proposed, and it keeps the gate.

### 1.3 The reference's neutral glass is a dark-ground choice

`--c-glass: #bbbbbc` is correct on `#1b1b1d` and wrong on Nadi's `#EDEFF3` — it
greys the panel and costs 1.5 contrast points. The tint must be a **themed**
token: white in light, neutral in dark. Same for the two reflex multipliers.

### 1.4 `color-mix()` adds zero lint debt

`design/gates/lint.mjs:101` matches `rgba?|hsla?\(` only. Every
`color-mix(in srgb, var(--…) …)` in the new recipe reads as clean. Verified
against the rule source, not assumed.

### 1.5 The `surfaces` gate cannot miscount a pseudo-element

`design/gates/surfaces.mjs:39` is `/(?<!-)\bg-glass(?:-ghost)?\b(?!-)/g`. A
`::before`/`::after` implementation adds no class and is invisible to the
counter. A new class named `g-glass-*` would also not be counted — if you add
one, update the regex deliberately.

### 1.6 RC19 root cause — closed

The gap rendering "AT TACHMENTS", "Set t ings", "AT TEND" is **Inter (the
`Inter.var` face frappe-ui ships) + positive `letter-spacing`, on the `tt`
pair.** Isolated across 15 variants:

```
NOT the cause:  font-kerning: none                        → still broken
                font-feature-settings: "calt" 0, "liga" 0 → still broken
                text-transform                            → broken either way
disappears:     letter-spacing: normal                    → clean
                font-family: "Inter Tight", same tracking → clean
                system fallback font                      → clean
```

It "needed a device" because `--g-font-ui` is
`-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, …` — the UI
face is **SF on Apple, Roboto on Android, Inter only on Windows and Linux**,
including every gate capture. The design tokens name Inter; almost no user was
served Inter.

---

## 2. The new material

### 2.1 Token diff

Goes into `design/tokens.json`, regenerates through `design/build-tokens.mjs`
into `frontend/src/theme/glass.css`. **No hand-edited CSS variables.**

| Token | Bucket | Light | Dark | Why |
|---|---|---|---|---|
| `--g-glass-tint` | color-themed | `#FFFFFF` | `#BBBBBC` | Fill colour for `color-mix` |
| `--g-glass-tint-pct` | color-themed | `56%` | `14%` | Measured; light at 36% cost 1.5 pts |
| `--g-reflex-light` | color-themed | `1` | `0.35` | White bevel is too hot on dark |
| `--g-reflex-dark` | color-themed | `1` | `2` | Dark bevel needs depth on dark |
| `--g-saturation` | color-constant | `150%` | `150%` | Was `180%` hardcoded in CSS |
| `--g-bevel` | shadow | 10-layer recipe | — | Replaces the 3-layer `box-shadow` |

**Retired:** `--g-glass-rim`, `--g-rim-hi`, `--g-rim-lo`, `--g-sheen` — all four
are absorbed by `--g-bevel`. Four out, five in. The `tokens` gate will report new
role bindings and collapse pairs; **re-baseline deliberately, do not silence it.**

### 2.2 The recipe

```css
.g-glass,
.g-glass-ghost {
  position: relative;
  background-color: color-mix(in srgb, var(--g-glass-tint) var(--g-glass-tint-pct), transparent);
  -webkit-backdrop-filter: blur(var(--g-blur-panel)) saturate(var(--g-saturation));
  backdrop-filter:         blur(var(--g-blur-panel)) saturate(var(--g-saturation));
  border-radius: var(--g-radius-panel);
  box-shadow: var(--g-bevel);
}
```

`--g-bevel` expands to ten layers — four light, four dark, two cast:

```
inset  0     0    0  1px  #fff @ reflex-light * 26%
inset  1.8px 3px  0 -2px  #fff @ reflex-light * 90%
inset -2px  -2px  0 -2px  #fff @ reflex-light * 80%
inset -3px  -8px 1px -6px #fff @ reflex-light * 60%
inset -.3px -1px 4px  0   #000 @ reflex-dark  * 12%
inset -1.5px 2.5px 0 -2px #000 @ reflex-dark  * 20%
inset  0     3px 4px -2px #000 @ reflex-dark  * 20%
inset  2px -6.5px 1px -4px #000 @ reflex-dark * 10%
       0     1px 5px  0   #000 @ reflex-dark  * 10%
       0     6px 16px 0   #000 @ reflex-dark  *  8%
```

**Both existing fallback paths must survive and be extended:**
`@supports not (backdrop-filter: blur(1px))` and
`@media (prefers-reduced-transparency: reduce)`. With transparency reduced the
**bevel stays** — it is what makes the panel an object — while the blur and tint
go solid. Reduce-transparency was the one subsystem the original audit could not
fault; it must stay unfaultable.

### 2.3 Why this is the whole effect

The shipping panel has a 1px rim and a linear sheen; its edge disappears into
the ground, which is why it reads as "a lighter patch of background". The bevel
lights one edge, shades the opposite, and casts — so the panel reads as a solid
piece of glass sitting *above* the field. That perceptual change, not
refraction, is the difference between frosted and liquid.

---

## 3. A to Z — every surface

**62 PWA surfaces: 44 routes + 18 modal/sheet surfaces.** Each has six states.

### 3.1 The five journeys

**J1 · First run**
`install prompt → /login → [SSO | email+password | OTP] → session.js full reload
→ guard resolves Employee → /home`, with branches to `/invalid-employee` and an
external password-reset page.
*Breaks:* the mark is the character "N", uppercase and colour-inverted against a
brand that is a charcoal lowercase *n* on lime · "Forgot Password?" is ~10px,
under the 44px target · successful login re-parses the whole bundle ·
`/invalid-employee` is a dismissible sheet with nothing behind it · the reset
path leaves the PWA with no route back.

**J2 · The daily loop**
`/home → Check In → geolocation permission → check_geofence preflight →
{ ok → selfie → punch | lenient miss → RemoteCheckinDialog → punch → request
raised | strict block → StrictRejectionDialog → no punch possible }`, later
Check Out, and the nightly sweeper → `LateCheckoutDialog`.
Best-engineered path on the server: self-only enforcement, server-clock stamping
in the employee's timezone, accuracy allowance capped at 250 m with its ceiling
written into the constant.
*Breaks:* **zero client e2e coverage on any of the five outcomes** · **no
offline handling anywhere** (see 3.3) · geolocation denial has no designed state
· the strict-block dialog is a dead end with no "request an exception" route.

**J3 · Ask for something** — leave, OT, expense, shift, attendance, issue
`dashboard → list → [+ New] → form → link pickers → attachments → Save → detail
→ notification on decision`. Six request types share one
`FormShell`/`FormView`/`ListView` stack, so a fix here lands on ~25 routes.
*Breaks:* no glass on any form or detail screen · four field treatments in one
form · "Half Day" drawn as a radio circle with a lime label louder than the
primary action · salmon required-asterisk off the palette · sticky Save bar
slices the last section · link-picker permission failures surface as a raw toast
naming a doctype · `FormView` (860 lines) has **no `ResourceError` and no
skeleton**.

**J4 · Approve something**
`push/badge → /remote-approvals (pending | history) → detail → approve | reject
→ decision propagates`, or `/team` for the manager day view.
*Breaks:* no e2e coverage · no loading state between tapping Approve and the row
disappearing · `/team` renders no roster and no empty state when the caller
manages nobody · nothing tests that the badge and the list agree.

**J5 · The long tail**
`/profile · /settings · /notifications · /hr-contacts · /sop → /sop/:id ·
/issues → /issues/:id · /dashboard/kpi · /employee-checkins`.
*Breaks:* Profile in light theme is a grey Desk list with no glass · Settings has
three left edges in one list and a push toggle whose off state is
indistinguishable from disabled · server vocabulary leaks to employees ·
`/more` is a nav overflow that became a destination, 62% empty.

### 3.2 Screen ledger — all 44 routes

`state` = which of loading / error / empty the route has today, measured per file
**and** per shared container.

| # | Route | Shell | State | What changes | Item |
|---|---|---|---|---|---|
| 01 | `/login` | GPage | none | Real mark, bevel, 44px link, pending | 9.3b 9.5c 9.7a |
| 02 | `/forgot-password` | GPage | none | Bevel; sent/error states | 9.3b 9.7a |
| 03 | `/change-password` | GPage | none | Bevel; validation + pending | 9.3b 9.7a |
| 04 | `/invalid-employee` | GPage | none | Not dismissible; give it a route out | 9.7d |
| 05 | catch-all | GPage | empty | Nothing — already correct | — |
| 06 | `/home` | BaseLayout | none | Skeleton; banner + panel bevel | 9.3b 9.7a |
| 07 | `/dashboard/attendance` | BaseLayout | error | Skeleton; cells tinted not outlined; legend dot | 9.5d 9.7a |
| 08 | `/dashboard/leaves` | BaseLayout | none | Skeleton, error; balance grid bevel | 9.3b 9.7a |
| 09 | `/dashboard/expense-claims` | BaseLayout | none | Skeleton, error; one name for the object | 9.5d 9.7a |
| 10 | `/dashboard/kpi` | BaseLayout | err+empty | Skeleton; unaudited — needs a fixture | 9.7a 9.7e |
| 11 | `/issues` | **none** | none | Adopt the shell; all three states | 9.5a 9.7a |
| 12 | `/sop` | GPage | err+empty | Search radius; placeholder at 2.7:1 | 9.3c 9.5d |
| 13 | `/team` | GPage | all 3 | Roster empty state; stepper radius | 9.5d |
| 14 | `/more` | GPage | none | Drop the duplicate heading; fill or shrink | 9.5d |
| 15 | `/profile` | GPage | none | Glass; GAvatar; destructive Log Out | 9.5a 9.5d |
| 16 | `/notifications` | GPage | empty | Panel the list; distinguish outcomes | 9.5a 9.5d |
| 17 | `/settings` | GPage | skeleton | One left edge; toggle off≠disabled; plain copy | 9.5d 9.7c |
| 18 | `/hr-contacts` | GPage | none | Empty state with an action; plain copy | 9.5d 9.7c |
| 19 | `/remote-approvals` | GPage | skel+empty | Error state; decision pending state | 9.7a |
| 20 | `/attendance-requests` | ListView | err+empty | Skeleton at the container | 9.7a |
| 21 | `/attendance-requests/new` | FormView | none | Glass, one field set, Save bar clearance | 9.5a 9.5b |
| 22 | `/attendance-requests/:id` | FormView | none | Read-only treatment on submitted docs | 9.5a 9.7a |
| 23 | `/shift-requests` | ListView | err+empty | Skeleton at the container | 9.7a |
| 24 | `/shift-requests/new` | FormView | none | Glass; it has no eyebrows or dividers at all | 9.5a 9.5b |
| 25 | `/shift-requests/:id` | FormView | none | Read-only treatment | 9.5a |
| 26 | `/shift-assignments` | ListView | err+empty | Accent spent on neutral status chips | 9.5d 9.7a |
| 27 | `/shift-assignments/:id` | FormView | none | No action of any kind; 164px dead space | 9.5a |
| 28 | `/employee-checkins` | ListView | err+empty | IN/OUT chips: two fills for equal states | 9.5d |
| 29 | `/ot-requests` | ListView | err+empty | No primary reads as primary | 9.5d |
| 30 | `/ot-requests/new` | FormView | none | Glass, one field set | 9.5a 9.5b |
| 31 | `/ot-requests/:id` | FormView | none | Read-only treatment | 9.5a |
| 32 | `/replacement-leave` | GPage | err+empty | Zero-radius bank panel; empty state promises an action | 9.3c 9.5d |
| 33 | `/replacement-leave/claims/new` | FormView | none | Glass, one field set | 9.5a 9.5b |
| 34 | `/replacement-leave/claims/:id` | FormView | none | Read-only treatment | 9.5a |
| 35 | `/leave-applications` | ListView | err+empty | REJECTED chip luminance; no type marker on rows | 9.5d |
| 36 | `/leave-applications/new` | FormView | none | Glass; Half Day control; approver rule parity | 9.5a 9.5b |
| 37 | `/leave-applications/:id` | FormView | none | A Rejected doc still renders live editable fields | 9.5a 9.7a |
| 38 | `/expense-claims` | ListView | err+empty | One object, four names on one screen | 9.5d |
| 39 | `/expense-claims/new` | FormView | none | Glass; link-picker failures as a state | 9.5a 9.7c |
| 40 | `/expense-claims/:id` | FormView | none | Read-only treatment; taxes/advances tables | 9.5a |
| 41 | `/issues/new` | FormView | none | Glass; the mandatory field is the missing one | 9.5a 9.5b |
| 42 | `/issues/:id` | FormView | none | Chip parity with the list; title truncation | 9.5a 9.5d |
| 43 | `/hr/issues` | GPage | err+empty | **Never rendered in any audit** — needs an HR fixture | 9.7e |
| 44 | `/sop/:id` | **none** | err+empty | Adopt the shell; PDF viewer states | 9.5a 9.7a |

Rows 11 and 44 compose no shared shell, which is why they drift. **Row 43 has
never been rendered by any audit in this project** — it silently redirects to the
staff view without an HR role, and the two captures are byte-identical
(md5 `2d48fd59…`). The HR issue board is completely unassessed.

### 3.3 The states axis — the largest uncovered area

The original audit recorded, in its own list of what it could not assess:
*"Focus, press, error and loading states — no capture puts a control in those
states."* No phase addressed it until now.

Measured at the shared containers, where these belong:

```
container      lines   skeleton   error          empty
ListView        495    none       ResourceError  GEmptyState   ← ~10 list routes
FormView        860    none       none           none          ← ~14 form/detail routes
RequestList     118    none       none           GEmptyState   ← dashboards

app-wide   GSkeleton appears in 15 files and in NONE of the three containers
           offline handling: 0 implementations
           DesignSpecimen.vue:88 renders a designed offline banner that is
           DRAWN BUT NEVER BUILT
```

> A PWA whose core action is checking in — often in a basement car park, a
> warehouse, a site with no signal — has no offline state anywhere except in a
> dev-only specimen. That is the single largest functional gap in the product,
> and it is invisible to all eight gates because every gate renders against a
> live site.

| State | Today | Target | Item |
|---|---|---|---|
| Loading | 15 of 44 routes; none of the 3 containers | Skeleton at each container | 9.7a |
| Empty | Good — consolidated in 8.11 | Hold; add roster and KPI cases | 9.5d |
| Error | ListView yes, FormView no, RequestList no | `ResourceError` at all three | 9.7a |
| **Offline** | **Nothing**, outside the dev specimen | Detect, banner, queue the punch | **9.7b** |
| Permission denied | Raw toasts with doctype names | A designed state in plain language | 9.7c |
| Submitting / pending | Login only | Every destructive or slow action | 9.7a |
| Focus · press | `:focus-visible` exists; never captured | Add to the capture set | 9.7e |

### 3.4 The 18 non-route surfaces

Never appear in a route list; this is where a person spends the tense moments.
All need the material; the ones carrying a decision need a pending state.

```
CheckInPanel · RemoteCheckinDialog · StrictRejectionDialog · LateCheckoutDialog
RequestActionSheet · WorkflowActionSheet · ListFiltersActionSheet · SopFormSheet
ContactInfoSheet · ProfileInfoModal · FilePreviewModal · FileUploaderView
Holidays · InstallPrompt · PushNotificationPrompt · GModal · GConfirm · GActionSheet
plus Login's three: reset-password, forgot-password, OTP
```

The `surfaces` gate already counts sheet surface sets separately — 34 of them,
0 over budget — so the accounting exists. The material and the states do not.

---

## 4. Phases

Each item is one commit. `CLAUDE.md` records that four sessions ended with
hundreds of uncommitted changes and that a `git stash` workaround nearly lost
real work twice. **29 items means 29 commits.**

### 9.1 — Payload and type

First: cheapest, entirely mechanical, and one item closes a weeks-old bug.
Nothing here touches layout, so a clean `visual` run doubles as a check that the
gate still works.

**GATE** — all 8 green; `visual` must report **0 differing**. If it doesn't,
something in 9.1 moved pixels and needs explaining before 9.2 starts.

| id | Item | Closes |
|---|---|---|
| **9.1a** | Point `--g-font-ui` at **Inter Tight**; drop frappe-ui's static Inter family. Files: `design/tokens.json` (type.family), `frontend/src/theme/fonts.css`, the frappe-ui style import. Verify: run the 15-variant harness, then `ls hrms/public/frontend/assets/*.woff2 \| wc -l` → expect ≈2, not 39. Risk: frappe-ui components inherit the font — check `Toasts`, `Badge`, `FormControl`. | B03 B05 |
| **9.1b** | Three lines in `vite.config.js`: `sourcemap: "hidden"` (:80), `target: "es2020"` (:76), `theme_color` matched to the dark ground (:38). Verify: `du -sh hrms/public/frontend` → ≈9 MB, not 21 MB. | B04 B06 B07 |
| **9.1c** | Delete the vestigial `frappe-ui` submodule. Files: `.gitmodules`, `frappe-ui/`, the note in `docs/glass/README.md`. Verify: `git status` clean for the first time in weeks. | B13 |

### 9.2 — Enforcement, before anything else changes

Exists so the rest cannot rot. Landing 9.3–9.8 on an unenforced frontend
recreates the backlog this plan clears.

**GATE** — `yarn lint` exits 0; `yarn test` 88 pass; both run in CI on PR.

| id | Item | Closes |
|---|---|---|
| **9.2a** | Run `yarn lint --fix` as its own commit (599 errors, 96 files, all auto-fixable). Add the sha to `.git-blame-ignore-revs`, which this repo already maintains. Verify: lint 0, tests 88, gates unchanged. | B02 |
| **9.2b** | Remove the `frontend/.*` exclusion from the prettier hook in `.pre-commit-config.yaml`. Add a CI job running `yarn lint` and `yarn test`. Promote `glass-gates.yml` from "not a required check yet" to required. Verify: **push a deliberately mis-formatted file and confirm CI fails** — force the failure the gate exists to catch. | B02 |
| **9.2c** | **Do this before 9.3.** Split the evidence captures from the visual baselines. `playwright.config.js:29` currently points snapshots at `docs/glass/audit/screens/` — "one set of images, serving as both the evidence a finding cites and the baseline a regression fails against". Since `visual.spec.js:93` injects `[data-visual-mask]{visibility:hidden}`, **every dynamic string is invisible in the images the audit documents cite**. Point baselines at `design/baselines/`; keep `docs/glass/audit/screens/` as unmasked documentation shot with a frozen clock. Verify: a doc capture shows the banner title and date eyebrow; a baseline does not. | B09 |
| **9.2d** | Three e2e specs: check-in, leave submission, approval. Four functional tests exist for 41 routes, none on the flow that decides whether people are paid correctly. Harness exists and is already configurable against a staging site. Verify: each spec fails when its endpoint is stubbed to error. | audit §gates |

### 9.3 — The material

Only 27 `g-glass` call sites across 21 components — a small blast radius for a
change this visible.

**GATE** — `tokens` re-baselined deliberately; `contrast` green; `visual` will
fail on ~76 screen-themes. **Classify every diff before re-baselining**, exactly
as the rulings pass accounted for all 64.

| id | Item | Closes |
|---|---|---|
| **9.3a** | Add the five new tokens; retire the four the bevel absorbs. `design/tokens.json`, `design/token-collapse-baseline.json`. Verify: `yarn tokens`, diff `glass.css`, `node design/gates/tokens.mjs` reports the new bindings rather than silence. | foundation |
| **9.3b** | Rewrite `.g-glass` as tint + bevel (§2.2). `glass-components.css:254–308`. Keep and extend both fallback paths. Verify: capture `home-390-dark-rt.png` — reduce-transparency must stay unfaultable. | B12 |
| **9.3c** | Concentric radii. Nine unrelated radius tokens today (6, 9, 14, 15, 17, 19, 20, 22px). Derive inner radii from the panel radius so a well inside a panel inside a sheet reads as one machined object. Verify: the `lint` gate's arbitrary count should **fall** from 117. | B12 |

*There is no 9.3d. See D2.*

### 9.4 — The light field

**GATE** — `contrast` rewritten to assert a measured floor, and it must **fail**
when a blob is pushed to an unsafe alpha before it is trusted.

| id | Item | Closes |
|---|---|---|
| **9.4a** | Replace §3.3's geometric ban with a measured contrast floor computed on the rendered DOM. `design/gates/contrast.mjs:112–200`, spec §3.3. Verify: raise a blob's alpha until the gate fails, then restore. If it never fails, the gate is decorative. | audit §glass |
| **9.4b** | Bring the blobs inboard. Today blob A is 230px at `left: -180px` — 78% off-canvas. Move all three so their falloff crosses the content column; size in `vw` so the geometry holds at every breakpoint. `design/tokens.json` field bucket (13 tokens), `glass-components.css:19–109`. Verify: `contrast` green under the new rule; `light-field.spec.js` still proves **one** field during a push, not three. | audit §glass |
| **9.4c** | **No change.** Spec §3.1 forbids drift animation because animating blurred layers behind `backdrop-filter` is the most expensive thing this design can do to a mid-range Android. That ruling was right. Motion comes from the bevel responding to press states, not from the field moving. | — |

### 9.5 — Coverage and identity

**GATE** — `coherence` green across 38 screens; `surfaces` 0 over budget. The
form screens gain panels and must not blow the six-surface limit.

| id | Item | Closes |
|---|---|---|
| **9.5a** | Give forms, detail screens and Profile the page shell. These were ported rather than rebuilt. `FormShell.vue`, `FormView.vue`, `Profile.vue`, the 8 form views, plus rows 11 and 44 which compose no shell. Verify: `surfaces` per-screen ≤ 6; re-capture all `*-new-*` and `*-detail-*`. **Design the form shell as one panel containing sections, not one panel per section**, or it blows the budget. | audit §coverage |
| **9.5b** | One field component, one boolean shape, one required marker. Four field treatments become one. "Half Day" stops being a radio circle with a lime label. The salmon asterisk moves onto the palette. `GInput`, `GTextarea`, `GDatePicker`, `GLinkPicker`, `FormField`. Verify: `coherence` gains a rule — one boolean control shape across all screens. | B12 |
| **9.5c** | Trace `pasted-mt6z286k-0.png` to an SVG path; use it in all three places. Today `/login` renders the character "N" — uppercase, colour-inverted against a charcoal lowercase *n* on lime; `SideNav.vue:11–22` draws an SVG `<text>` glyph whose shape depends on whether Inter loaded; `GAppHeader.vue:44` carries no mark. New `GLogoMark.vue` → `GLogoWell.vue:22`, `SideNav.vue`, `GAppHeader.vue`. **Open sub-decision:** does the mark keep the source's squircle-with-one-cut-corner, or the squared silhouette the current icon set uses? Whichever is chosen applies to the SVG, favicon, maskable icons and splash screens together. | logo |
| **9.5d** | Close RC18 properly and fix the copy drift. `SideNav.vue:105–116` and `ContactCard.vue:7` still open-code avatars (`object-cover grayscale`, no radius, no `GAvatar`) — the shape rule missed them because `SideNav` is `hidden lg:flex`. Plus: "View List" vs "View list"; "More" above "MORE"; outlined rest-day calendar cells; invisible Half Day legend dot; REJECTED chips brighter than everything else so rejections outrank approvals on luminance. Verify: extend the avatar shape rule to `lg:` viewports. | B11 B12 |
| **9.5e** | Desktop 1440: the 720px column is left-aligned against the side nav, leaving ~37% of the viewport empty, and the wordmark renders twice. Either give the column a second rail with something in it, or centre it so the emptiness reads as deliberate. It currently reads as unfinished. | audit §flow |

### 9.6 — Backend and accessibility

Independent; runs in parallel with any other phase.

**GATE** — `ruff` clean; new tests execute a query rather than reading source;
the `a11y` baseline **shrinks**, per §16.5.1.

| id | Item | Closes |
|---|---|---|
| **9.6a** | Fix the report-scope filter syntax. `apply_employee_scope` (`hrms/utils/report_scope.py:53`) writes `("in", [...])` — `get_all` syntax — into a dict that two Script Reports feed to the query builder as an equality operand. Renders `WHERE "company"=('in',['Company A'])`, invalid on MariaDB. Hits exactly the fenced-HR population the fence was built for; unfenced HR (`allowed_companies() == []`) is unaffected, which is why it has not surfaced. Files: `report_scope.py`, `hr/report/shift_attendance`, `hr/report/employee_advance_summary`. Verify: a test that **runs** the report as an HR user carrying a Company User Permission. `test_report_scope.py` reads the module as text and could never catch this. | B01 |
| **9.6b** | Drop the `get_country` Jinja registration (`hrms/hooks.py:92`). Unauthenticated, no request timeout, unbounded per-worker IP cache, and nothing in this fork calls it. Verify: `grep -rn get_country hrms/ frontend/ roster/` returns only the definition. | B08 |
| **9.6c** | Fix the 26 critical a11y nodes at source. `label` 16 nodes / 14 screens, `aria-allowed-attr` 8, `aria-dialog-name` 2, `button-name` 2, plus three landmark rules on 22 screens each — almost certainly one shell component announcing a duplicate `banner`. Every large count in this project has collapsed into two or three shared components; expect the same. Files: `FormField`, `GModal`, `BaseLayout`, `GPage`. Verify: `design/gates/.a11y-report.json` critical reaches **0** and the baseline shrinks rather than absorbs. | B10 |
| **9.6d** | **Three open risks that are decisions, not tasks.** **R1** — the company fence fails open for any HR user with no Company User Permission; only a nightly Error Log report catches it. **R2** — hub-side leave approvals write unstamped ledger entries beside mirrored ones, and parity only counts stamped rows. **R6** — `user_data_fields` is still commented out at `hooks.py:638`, so there is no DSAR or retention path while PII is duplicated across the hub and every source instance. All three are cutover-blocking. None is fixed by writing code first. | R1 R2 R6 |

### 9.7 — States and resilience

The axis no previous phase touched. Everything lands at a **shared container**,
so one change covers every route composing it — the pattern that has repeatedly
collapsed large counts in this project.

**GATE** — a new `states` spec renders each container in loading / error / empty
/ offline and captures all four; `coherence` gains a rule: one loading
treatment, one error treatment.

| id | Item | Closes |
|---|---|---|
| **9.7a** | Loading, error and pending at the three containers. `ListView` has no skeleton. `FormView` — 860 lines, behind every form and detail screen — has no skeleton **and no `ResourceError`**. `RequestList` has neither. Add all three once, at the container, and ~25 routes inherit them. Add a pending state to every action that submits. Files: `ListView.vue`, `FormView.vue`, `RequestList.vue`, `GButton`. Verify: stub each resource to hang, then to 500, then to empty — capture all three per container. | states |
| **9.7b** | **P0 — offline.** There is no offline handling in the app; the designed banner exists only at `DesignSpecimen.vue:88`, drawn and never built. For a check-in product this is the one failure that costs someone their pay. Three parts: **detect** (`navigator.onLine` + a failed-request signal), **tell** (the banner that already has a design), **queue** (persist the punch and replay it, with the server clock still authoritative on arrival). Files: new `composables/useOnline.js`, `CheckInPanel.vue`, `api/remote_checkin.punch`, `sw.js`. Verify: Playwright `context.setOffline(true)`, punch, go online, assert **exactly one** Employee Checkin row — not two. Risk: a replayed punch must not create a duplicate or a backdated row; the server already ignores client-supplied `time`, which is the property that makes this safe. | offline |
| **9.7c** | Permission failures and server vocabulary become designed states. "Insufficient Permission for **Account**" shown to an employee. "Push notifications have been disabled **on your site**." "Ask your **administrator** to assign the **HR Manager or HR User role**." Link pickers throw unhandled rejections instead of rendering an error state. Spec §11.3 already requires plain language and no system vocabulary. Files: `GLinkPicker.vue`, `AppSettings.vue`, `HRContacts.vue`, `glass/toast.js`. Verify: grep the built bundle for doctype names in user-facing strings. | B12 |
| **9.7d** | Close the two dead ends in J1. `/invalid-employee` presents a drag handle implying dismissal, and dismissing leaves a black page with no route out. The expired-password path leaves the PWA for an external page with no way back. Neither is a styling problem — both are missing exits. Verify: dismiss the sheet and assert a route, not a blank page. | journey |
| **9.7e** | Close the three coverage holes in the capture set. `/hr/issues` has **never been rendered** by any audit. KPI has no appraisal data. Team has no direct reports. Add an HR user, an appraisal and a reporting employee to `docs/glass/audit/seed.py`; add focus and press states to `capture.mjs`. Verify: the HR board capture stops matching the staff list's md5. **Re-seeding changes content and therefore every baseline — do this *with* the 9.3 re-baseline, never separately.** | coverage |
| **9.7f** | Bridge the tokens into the roster SPA. Publish the generated `glass.css` into `roster/tailwind.config.js` so the second app inherits the palette and dark mode without rebuilding its components. Verify: toggle the theme in the PWA, open `/hr/roster`, and see it follow. | beyond |

### 9.8 — Retire the old design system

See §8 for the scope ruling this phase implements.

**GATE** — `lint` baseline **shrinks**; zero frappe-ui UI components imported in
`src/views/**`; `theme/variables.css` deleted or reduced to a generated bridge.

| id | Item | Closes |
|---|---|---|
| **9.8a** | **Delete `frontend/src/theme/variables.css`.** It is the last Modernist artifact. Its own header says the palette "mirrors `src/theme/modernist.css` (the canonical palette)" — **that file no longer exists**. It declares `--ion-font-family: "Archivo"`, a face **never loaded anywhere** in the codebase. `glass.variables.css` loads after it and overrides five values; the ~45 `--ion-color-*` Modernist tokens survive untouched. **Measured: `color="primary"` and its eight siblings appear 0 times in `src/`.** The whole file is dead. Verify: delete, build, run all 8 gates; `visual` must report 0 differing. | legacy |
| **9.8b** | Replace the remaining 12 frappe-ui UI components with their Glass equivalents — **37 import sites, and Glass already has a replacement for almost all of them**: `toast`(16)→`glass/toast.js`, `Autocomplete`(5)→`GLinkPicker`, `Button`(4)→`GButton`, `Input`(3)→`GInput`, `DatePicker`→`GDatePicker`, `DateTimePicker`→`GDateTimePicker`, `Badge`→`GStatusChip`, `Switch`, `Popover`, `FormControl`, `ErrorMessage`, `TextEditor`, `Toasts`. **Do not touch the data layer** (§8). Verify: `grep -c` for UI component imports in `src/views/**` → 0. | legacy |
| **9.8c** | Drop `frappeUIPreset` from `tailwind.config.js` once 9.8b lands. It is the source of the shadowing bugs the config's own comments document (`backgroundColor.surface` with no DEFAULT shadowing `colors.surface`). The nine-step `ink`/`accent` ramps are Modernist-shaped and can collapse to the four Glass ink levels they already point at. Verify: `lint` arbitrary + hex counts fall; `visual` 0 differing. | legacy |
| **9.8d** | Burn down the `lint` baseline. 180 violations today: 117 arbitrary Tailwind values, 59 raw hex, 4 colour functions. It is the token system's own debt ledger and it is not shrinking on its own. Ratchet it: after 9.8a–c, set the baseline to the new number and never let it rise. Verify: `design/lint-baseline.json` total falls, and the gate fails if it climbs. | legacy |

---

## 5. Coverage matrix

Every audit finding and carried-over risk, assigned. Nothing unassigned.

| ID | Finding | Sev | Item |
|---|---|---|---|
| B01 | Fenced HR gets a SQL error from two Script Reports | P1 | 9.6a |
| B02 | 599 lint errors, nothing runs the linter | P1 | 9.2a 9.2b |
| B03 | Inter `tt` gap; font stack resolves three ways | P1 | 9.1a |
| B04 | 12 MB of sourcemaps shipped | P1 | 9.1b |
| B05 | 2.2 MB of unused italic faces | P1 | 9.1a |
| B06 | `es2015` build target | P2 | 9.1b |
| B07 | Light `theme_color` on a dark app | P2 | 9.1b |
| B08 | Guest endpoint, no timeout, unbounded cache | P2 | 9.6b |
| B09 | Baselines and evidence are one masked set | P1 | 9.2c |
| B10 | 26 critical a11y nodes baselined | P1 | 9.6c |
| B11 | Two open-coded avatars survive RC18 | P2 | 9.5d |
| B12 | Copy and control drift still shipping | P2 | 9.3b 9.3c 9.5b 9.5d 9.7c |
| B13 | Vestigial dirty submodule | P2 | 9.1c |
| — | **Glass reads as fog; no backdrop to lens** | core | 9.3a–b 9.4a–b |
| — | **Frosted, not liquid; no specular bevel** | core | 9.3b |
| — | **Logo absent from every app surface** | core | 9.5c |
| — | Forms, details, Profile have no glass | P1 | 9.5a |
| — | 4 e2e tests, none on check-in | P1 | 9.2d |
| — | Desktop 1440 dead canvas, doubled wordmark | P2 | 9.5e |
| — | **No offline handling anywhere** | **P0** | **9.7b** |
| — | No skeleton in any shared container | P1 | 9.7a |
| — | `FormView` has no error state | P1 | 9.7a |
| — | No pending state on submitting actions | P1 | 9.7a |
| — | Server vocabulary shown to employees | P1 | 9.7c |
| — | Two dead ends in the first-run journey | P1 | 9.7d |
| — | `/hr/issues` never rendered by any audit | P1 | 9.7e |
| — | KPI and Team unassessed; no focus/press captures | P2 | 9.7e |
| — | 18 sheet surfaces need the material | P1 | 9.3b 9.7a |
| — | Roster SPA has no tokens, no dark mode | P2 | 9.7f |
| — | Modernist Ionic palette still shipping | P2 | 9.8a |
| — | 12 frappe-ui UI components remain | P2 | 9.8b 9.8c |
| — | 180 baselined lint violations | P2 | 9.8d |
| R1 | Company fence fails open | P1 | 9.6d — decision |
| R2 | Dual-writer leave state for mirrored companies | P1 | 9.6d — decision |
| R6 | No DSAR / retention path | P1 | 9.6d — decision |
| R5 R7 | Sync credentials; geofence ownership | closed | verified 24 Aug |
| P0-a | Nadi app icon navigates instead of opening its workspace modal | **live** | 0.1 0.2 |
| P0-b | HR Setup's Data Migration card never reached production (`de65b6379`) | **live** | 0.2 |
| P0-c | Shift Assignment Tool never returned to the sidebar (`7b8102af9`) | **live** | 0.2 |
| P0-d | Fixture edits silently no-op on existing sites; no guard, and CI cannot catch it | **class** | 0.3 |
| P0-e | In-flight launcher workaround cannot fix P0-a and changes `app_home` | — | 0.4 |

**Surface accounting:** 44 routes + 18 sheets = **62 PWA surfaces**, all
assigned, × 6 states. Plus 2 roster routes bridged (9.7f). Frappe Desk
explicitly excluded — see §8.

---

## 6. Order

0. **Phase 0 first (§0.5).** Live breakage outranks quality work. `0.3` guard →
   `0.2` timestamps → `0.1` repair patch → `0.5` test. `0.4` is a discard.
1. **9.2c first.** Split the baselines before anything changes pixels, or you
   re-baseline the wrong set.
2. **9.1** — free wins, and a clean `visual` run proves the gate still works.
3. **9.2** — enforcement, so nothing rots.
4. **9.3 + 9.4 + 9.7e together**, as one design pass with a **single**
   re-baseline. The re-seed in 9.7e changes every capture, so it must ride along
   rather than force a second one.
5. **9.5**, then **9.7**, then **9.8**.
6. **9.6** runs in parallel with any of it.

**One exception: 9.7b (offline) is the only P0 in this plan and depends on
nothing.** If a check-in has ever failed in the field, pull it to the front and
ship it on its own.

---

## 7. What could go wrong

- **The visual gate will fail loudly in 9.3, and that is correct.** ~76
  screen-themes change. The failure mode is re-baselining in bulk to make the
  red go away. Classify every diff first, as the rulings pass did for all 64.
- **The bevel is tuned to the reference's grounds, not Nadi's.** The light tint
  was corrected by measurement; the four reflex offsets are still the
  reference's numbers. Expect one round of tuning on a real device, and change
  them by measuring rather than by eye.
- **9.4b can regress the light-field isolation work.** Moving the blobs touches
  the component §3.2 argued with itself about for a full spec version.
  `light-field.spec.js` must still prove one field during a push, not three.
- **9.5a will pressure the six-surface budget.** Giving eight form screens
  panels is exactly the change that blows `surfaces`.
- **9.2a's autofix makes a month of `git blame` useless** unless the sha goes
  into `.git-blame-ignore-revs`.
- **9.8b/c can silently change frappe-ui component appearance app-wide.** Drop
  the preset only after every UI component is replaced, and read the `visual`
  diff rather than trusting a green gate — the tolerance is 20 absolute pixels
  and a small element changing on many screens is exactly its blind spot.
- **Treat every unverified cause in `frontend-audit.md` as unverified.** Across
  8.1–8.5, five findings were wrong and all five failed the same way: an
  accurate observation with a wrong cause inferred on top of it. Measure the DOM
  before acting on any remaining finding.

---

## 8. Scope ruling — what "migrate off Frappe" means here

The question was whether the goal is to wipe out the old design tokens and
migrate off Frappe entirely. The honest answer has three parts, and they are
different sizes.

**Frappe the framework, and Frappe Desk — NOT in scope, and correctly so.**
Frappe v16 + ERPNext v16 is the right backend for a multi-company HR hub: the
permission model, workflow engine, payroll and migration machinery are why this
product exists at all, and the fork uses them rather than fighting them. Desk
itself — 194 doctypes, 33 reports, 147 client scripts, all stock — is the larger
half of the product by hours-of-use and deserves its own plan, not a line item
at the end of this one. **It is excluded by decision, not by oversight.**

**Frappe's design language in the PWA — YES, remove it completely.** This is
phase 9.8, and it is smaller than it looks:

- `theme/variables.css` is entirely dead. Its canonical source
  (`modernist.css`) no longer exists, its `Archivo` font is never loaded, and
  its nine `--ion-color-*` ramps are referenced **zero** times in `src/`.
- Only **12 distinct frappe-ui UI components** remain, at **37 import sites**,
  and Glass already has a replacement for almost all of them.
- The `frappeUIPreset` in `tailwind.config.js` is the source of the shadowing
  bugs the config's own comments document, and can go once 9.8b lands.
- The 180 baselined `lint` violations are the measurable residue.

**frappe-ui's data layer — KEEP.** `createResource` (45 sites),
`createListResource` (5), `createDocumentResource` (2), `frappeRequest` (2),
`resourcesPlugin`, `setConfig`, `call` — **57 of the 117 frappe-ui imports** —
are the app's entire server-communication layer, plus `FeatherIcon` (21) and
`debounce` (2) as utilities. They carry no design opinion. Removing them would
mean rewriting the data layer for no design benefit, and is explicitly out of
scope.

### Definition of done for the migration

```
frontend/src/theme/variables.css                      deleted
frappe-ui UI components imported in src/views/**      0
frappeUIPreset in tailwind.config.js                  removed
design/lint-baseline.json total                       < 180, ratcheted, never rises
--ion-color-* referenced in src/                      0   (already true)
glass.variables.css                                   the only Ionic bridge, generated
```

When those six lines hold, the PWA carries no Frappe design language — only
Frappe data. That is the goal, stated so it can be checked rather than argued.

---

## 9. Environment

- Site `verify-bench/fresh.local`, served on `:8080` (`bench serve`), employee
  `HR-EMP-00001`, seeded by `docs/glass/audit/seed.py`.
- **The audit credential lives in `.env` at the repo root** — gitignored, mode
  600. Load with `set -a; . .env; set +a`. If it is missing or a gate SKIPs at a
  401, run `docs/glass/audit/reset-audit-pw.sh`. That script deliberately does
  **not** re-run `seed.py`: re-seeding changes content, content changes
  screenshots, and that corrupts every visual comparison.
- Full suite: `set -a; . .env; set +a; node design/gates/run.mjs`
- A full-suite run cleans `test-results/` — read any diff images before starting
  another gate run.
- Gate run artifacts `design/gates/.a11y-report.json` and `.coherence-report.json`
  are gitignored. Do not commit them back.
- Seeding artifacts that are **not** defects: leave rows showing `0d`, balance
  bars at 100%, `_Test Company`, empty KPI and Team screens.
