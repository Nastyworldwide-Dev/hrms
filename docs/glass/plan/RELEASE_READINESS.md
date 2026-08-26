# Release readiness — the road to live-ready

Branch `nz-glass`. Written 26 August 2026, after a full end-to-end check.

Companion to `HR_Glass_Phase_9_Work_Order.md`, which holds the *what*. This
holds the **order, the exit criteria, and the definition of done.** A phase is
not finished because its edits landed; it is finished when its exit criterion
holds and someone has seen it hold.

---

## 0. Where this actually stands

**The system is live and serving people. It is not ready to cut over, and the
next release is not ready to ship.** Those are three separate statements and
only the first is currently true.

| Layer | State | What blocks it |
|---|---|---|
| ERP → verifica (sync) | works, verified end to end | 3 schema rulings outstanding on Nasty-Dev; R1 and R2 decided, R6 open |
| verifica hub (Desk) | functioning | launcher broken until phase 0 deploys; unthemed |
| ESS PWA | functioning | design incomplete; **no offline handling at all** |
| Roster SPA | never migrated | no tokens, no dark mode |
| Release | **blocked** | 32 commits undeployed; 16 visual diffs unclassified |

### What was found on the end-to-end check, 26 August

The only functional e2e suite — `critical-paths.spec.js` — **had never once
passed.** `playwright.config.js` defaulted `baseURL` to `:8000` while
`screens.mjs`, `a11y.mjs` and `visual.mjs` all default to `:8080`, so it ran
against a different server entirely and its assertions were never evaluated
against this app. Fixed in `7c00fb434`; 2 of 4 now pass.

That is the readiness problem in miniature. **The system mostly works. The
things that are supposed to prove it works mostly do not.** Five of eight gates
read a proxy (source text, a token matrix) rather than a rendered pixel, the
e2e suite guarded nothing, and the sync has no heartbeat until phase 0 ships.

---

## 1. The gates

Sequential. Each one's exit criterion must hold before the next begins, because
each later gate assumes the earlier one's guarantees.

### GATE 0 — Ship what is already written  ·  *hours*

32 commits sit in git and nothing is on the site. This is the highest
value-per-effort action available and it is not close.

```sh
bench --site <site> migrate     # fixtures land first, then the repair patch
bench build --app hrms          # the Desk buttons and the PWA bundle
```

**Exit criteria**

- [ ] The Nadi app icon opens its workspace modal, like Accounting does
- [ ] `Desktop Icon` with `parent_icon = "Frappe HR"` returns **zero** rows
- [ ] HR Setup shows the **Data Migration** card and its ERP Instance links
- [ ] Shift Assignment Tool is back in the Shift & Attendance sidebar
- [ ] `Employee Leave Balance` and `…Summary` no longer carry the `Employee` role
- [ ] The ERP Instance form shows **Purge Mirrored Data** and, if any company
      qualifies, the unregistered-companies prompt
- [ ] Deployed asset directory is ≈8.5 MB, not 21 MB

**Why first:** everything below is verified against a deployed site, and five
shipped-but-never-delivered changes are already paid for.

### GATE 1 — Make the checks trustworthy  ·  *1 day*

Nothing below can be believed until the instruments are.

| id | Work |
|---|---|
| 1.1 | The two red e2e tests. Both force a 500 on `hrms.api.get_leave_balance_map` and assert the app admits it; the resource carries `cache: "hrms:leave_balance"`, which likely satisfies it before the network is touched. Confirm, then fix the test or the cache — **do not weaken the assertion** |
| 1.2 | Put `critical-paths.spec.js` in CI against a served site. It is the only thing in this repo that answers "can an employee see their leave balance" |
| 1.3 | Classify the **16 visual diffs**, then re-baseline. Cause is known — the lint sweep reformatted `FormView.vue`/`CheckInPanel.vue` templates and `ExpenseClaimSummary` changed — but "known" is not "checked" |
| 1.4 | Make `glass-gates` a required check in branch protection. The workflow already runs on `pull_request`; the switch is a repo setting |

**Exit criteria**

- [ ] `critical-paths.spec.js` — **4 of 4 passing**
- [ ] `node design/gates/run.mjs` — **8 of 8 green**, nothing skipped
- [ ] A deliberately broken PR fails CI on lint, on tests, and on the gates

### GATE 2 — The design batch  ·  *3–4 days*

**One re-baseline for all of it.** Every item here moves pixels; doing them
separately means paying the classification cost several times.

| id | Work | From |
|---|---|---|
| 9.3a | 5 new tokens in, 4 retired | work order §2.1 |
| 9.3b | `.g-glass` = tint + 10-layer specular bevel | measured: **0 ms** frame cost |
| 9.3c | Concentric radii | 9 unrelated radius tokens today |
| 9.4a | §3.3 → a measured contrast floor on the rendered DOM | measured: 4.78 worst case |
| 9.4b | Bring the light field inboard | blob A is 78% off-canvas |
| 9.1a | `--g-font-ui` → Inter Tight | closes RC19, drops ~3.8 MB |
| 9.5a | Forms, detail screens and Profile get the page shell | the screens that were ported, not rebuilt |
| 9.5b | One field component, one boolean shape, one required marker | 4 treatments in one form today |
| 9.5c | Trace the mark to SVG; use it in login, side nav, header | login renders the character "N" |
| 9.5d | RC18's two open-coded avatars; the copy drift | `SideNav.vue:105`, `ContactCard.vue:7` |
| 9.7e | Re-seed for `/hr/issues`, KPI and Team | never rendered by any audit |

**Exit criteria**

- [ ] Every visual diff classified before re-baselining — the rulings pass
      accounted for all 64; this one accounts for all of its own
- [ ] `coherence` green across 38 screens
- [ ] `surfaces` 0 over budget — giving 8 form screens panels is exactly what
      blows it, so the form shell is **one panel containing sections**
- [ ] Reduce-transparency still unfaultable — it is the one subsystem the
      original audit could not fault
- [ ] The bevel checked on a **real phone**, not headless Chromium

### GATE 3 — Resilience  ·  *2–3 days*

The axis no phase touched, and it holds the only P0.

| id | Work |
|---|---|
| **9.7b** | **Offline.** There is none. The designed banner exists only at `DesignSpecimen.vue:88`, drawn and never built. Detect, tell, queue the punch — server clock stays authoritative on arrival |
| 9.7a | Loading, error and pending at the three shared containers. `FormView` — 860 lines, behind ~14 routes — has **no skeleton and no `ResourceError`** |
| 9.7c | Permission failures and server vocabulary become designed states |
| 9.7d | The two dead ends in first-run: `/invalid-employee`, the expired-password path |
| 9.6c | The 26 critical a11y nodes, fixed at source. Expect them to collapse into 2–3 shared components, as every count in this project has |

**Exit criteria**

- [ ] Playwright `setOffline(true)` → punch → online → **exactly one** Employee
      Checkin row, not two
- [ ] Every container renders a distinguishable loading, empty and error state
- [ ] `a11y` critical count reaches **0** and the baseline **shrinks**

### GATE 4 — Retire the old system  ·  *1–2 days*

| id | Work |
|---|---|
| 9.8a | Delete `theme/variables.css` — `--ion-color-*` referenced **0** times |
| 9.8b | The 12 remaining frappe-ui UI components → Glass equivalents, 37 sites |
| 9.8c | Drop `frappeUIPreset` once 9.8b lands |
| 9.8d | Ratchet the lint baseline down: 239 today (arbitrary 116, rawPalette 60, hex 59, colorfn 4) |
| 9.7f | Bridge the tokens into the roster SPA |

**Exit criteria** — the six lines from work order §8:

```
frontend/src/theme/variables.css                 deleted
frappe-ui UI components in src/views/**          0
frappeUIPreset in tailwind.config.js             removed
design/lint-baseline.json total                  < 239, ratcheted, never rises
--ion-color-* referenced in src/                 0   (already true)
glass.variables.css                              the only Ionic bridge
```

### GATE 5 — Cutover  ·  *decisions, not engineering*

These will sit open indefinitely unless someone rules on them. **None is fixed
by writing code first.**

| | Question |
|---|---|
| 3 schema rulings | Outstanding on Nasty-Dev. `Review Schema Gaps` on the instance form is the whole workflow — one screen, no typing |
| **R1** | **DECIDED 26 Aug — no change.** One HR function covers every entity, so company-wide visibility is the requirement, not a hole. `require_unfenced` still gates hub-wide ACTIONS. See `decisions/R1-company-fence-fails-open.md` |
| **R2** | **Decided: staff transact HERE.** The two blind spots that decision exposed are closed — parity now reports `local_own` beside the mirrored count (`e9d735d27`), and mirrored leave overlapping hub leave is detected daily (`7a8c48227`). One item is still open and is **not** engineering: **should `run_sync` be scheduled?** It is operator-initiated today, so the mirror only moves when somebody presses a button. Unattended writes to a mirror is the question `write_block.py` exists for — see below |
| **R6** | `user_data_fields` is commented out at `hooks.py:638`. No DSAR or retention path while PII is duplicated across the hub and every source |

**Exit criteria**

- [ ] `cutover_readiness` reports **READY** — 4 consecutive clean parity checks
      and zero outstanding rulings
- [x] R1 recorded — `decisions/R1-company-fence-fails-open.md`
- [x] R2 recorded — staff transact in Nadi; instruments shipped (`e9d735d27`, `7a8c48227`)
- [ ] R6 still needs a recorded decision in `docs/glass/decisions/`

#### The one R2 question left: schedule the pull, or not

Stated here rather than decided in code, because it is the same class of
decision as R1 and R6 and it is not mine.

**Why it matters.** Every guard on this hub reads local rows. A leave applied
for here is checked against what the mirror currently holds — so a mirror that
last moved on Friday means Monday's approvals are checked against Friday's
truth. `7a8c48227` catches the resulting collision the next morning; nothing
prevents it.

**Why it is not obviously "yes".** `hrms/sync/write_block.py` exists because
writing to a mirror with no human present was taken seriously once already. A
scheduled pull is exactly that, every night, unattended. A run that goes Partial
holds its watermark and re-reads the same window — safe, and silent unless
somebody reads the heartbeat.

**The middle option, if the full one is unwelcome:** schedule it, keep it
hourly-or-slower, and treat the existing `report_stale_instances` entry as the
thing that proves it is still running. That is one line in
`hooks.py: scheduler_events`, and it is reversible.

**Not a reason to wait:** this changes nothing about cutover. After cutover
there is one writer, no mirror to pull, and the question disappears.

---

## 2. Explicitly out of scope

Named rather than forgotten, so nobody rediscovers them as gaps.

- **Frappe Desk theming.** 194 doctypes, 33 reports, 147 client scripts, all
  stock. It is the larger half of the product by hours-of-use and deserves its
  own plan. Excluded by decision.
- **Dropping Ionic.** The frontend's biggest available simplification — 16
  `ion-*` elements carrying page transitions, a tab bar, modals and
  pull-to-refresh, against a running argument with the Glass layer. Reopen it
  as a scoped spike **after** GATE 2, because a smaller Glass layer changes the
  estimate.
- **frappe-ui 0.1.105 → 0.1.278.** 173 releases. Its own project.

---

## 3. Sequencing, in one line each

1. **GATE 0 today.** Nothing else is verifiable against an undeployed site.
2. **GATE 1 next.** Believing a green board is worse than having no board.
3. **GATE 2 and 3 can overlap** — 9.7a/b/c are code, GATE 2 is pixels — but
   they share the re-baseline, so land GATE 2's re-shoot before 9.7's captures.
4. **GATE 4 last of the engineering.** It is the only one that can silently
   change appearance app-wide, and it wants the strongest instruments.
5. **GATE 5 runs in parallel throughout** and gates nothing except cutover.

**One exception to all of it: 9.7b (offline) is the only P0 and depends on
nothing.** If a check-in has ever failed in the field, it jumps to the front and
ships on its own.
