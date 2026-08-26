# The plan — everything remaining, in order

Branch `nz-glass`. Rewritten 26 August 2026, after a week in which an employee
found four defects we did not.

Supersedes the ordering in `RELEASE_READINESS.md`, which was written before
those findings and still reads as though design work were the critical path. It
is not. Keep that file for the design detail in GATE 2–4; this file is the
order.

---

## 0. What this week actually taught us

Four defects reached Mirza before they reached us:

| What he hit | Root cause | Why nothing caught it |
|---|---|---|
| `EMP-CKIN-…-000001 already exists` | mirrored rows took the numbers `autoname` was about to issue | no test checks in |
| approval did not stick | `setValue` cannot write `docstatus`; the call threw into a toast | no test approves anything |
| HR Settings would not save | blank leave templates, mandatory while notifications are on | no test touches HR Settings |
| no location prompt | one setting off; the whole geofence inert | nothing reported settings state |

**They are one defect wearing four hats: code that exists, reads correctly, and
silently does nothing.** Absence raises no error. A feature switched off,
unconfigured or unreachable is indistinguishable from one that works.

Two consequences shape everything below:

1. **The instruments are the deliverable.** `critical-paths.spec.js` has four
   tests — login, forgot-password, and two on the leave balance panel. It tests
   the door and one window. Not one of them could have caught anything above.
2. **A green board that measured nothing is worse than no board.** Three of
   eight design gates render no screen without a served site, and until
   `d76a86119` they printed `OK` while doing it.

---

## Phase 0 — Deploy · IN FLIGHT

```sh
cd <bench>/apps/hrms && git pull
cd <bench> && bench --site <site> migrate && bench build --app hrms
```

`migrate` is not optional: `restore_hr_settings_defaults` and
`repair_mirrored_naming_series` only run there.

**Exit criteria**

- [ ] An approver approves a request and it **stays** approved
- [ ] HR Settings saves without the mandatory-template dialog
- [ ] `Cancel` works on a submitted request
- [ ] Mirza checks in without `already exists`

---

## Phase 1 — Settings · *yours, ~30 minutes, no code*

Nothing here is engineering, and each blocks the thing under it.

| # | Task | Where | Why it matters |
|---|---|---|---|
| 1.1 | Enable the **scheduler** | hosting dashboard | 23 jobs are dormant, including the one that turns check-ins into Attendance. Without it staff punch in all week and the report stays empty |
| 1.2 | Tick **Allow Geolocation Tracking** | HR Settings → Shift and Attendance | the only reason iOS never asks for location. The whole geofence is inert without it |
| 1.3 | Create one **Shift Location** | `/app/shift-location` | coordinates + `checkin_radius`, then link via Shift Location Rule. Until it exists nothing is range-checked, while appearing to be |
| 1.4 | Tick **Enable Auto Attendance** | each Shift Type | second half of 1.1 — both are needed or check-ins stay raw logs |
| 1.5 | Push relay + credentials | `/app/push-notification-settings` | notifications currently only appear if somebody opens the app |

**Exit criterion:** `hrms.utils.readiness.system_readiness` returns **no
findings**. That endpoint exists precisely so this phase can be checked rather
than assumed — and it is whitelisted for on-demand use because the first thing
it reports is the scheduler, which a scheduled check could never report.

---

## Phase 2 — Prove it works · *the anti-gap work, ~1 day*

**The highest-value engineering left.** Everything in phase 0 was found by a
human; this is what stops that.

| # | Task |
|---|---|
| 2.1 | e2e: check in → check out. Asserts a row is created and no duplicate |
| 2.2 | e2e: submit a request → approve it → **assert it stays approved**. This single test catches the defect Mirza reported |
| 2.3 | e2e: HR Settings loads and saves |
| 2.4 | Fix the 2 red tests in `critical-paths.spec.js`. Suspected: `cache: "hrms:leave_balance"` satisfies the assertion before the network is touched. **Do not weaken the assertion** |
| 2.5 | Run the suite in CI against a served site, and make `glass-gates` a required check |

**Exit criteria**

- [ ] `critical-paths.spec.js` green, and it covers check-in and approval
- [ ] A deliberately broken approval fails CI
- [ ] `node design/gates/run.mjs` reports no `SKIP`

---

## Phase 3 — Close the known bugs · *~1 day*

Found, understood, not yet fixed.

| # | Task |
|---|---|
| 3.1 | **OT Request notifies nobody.** Its three siblings all notify their approver; OT has no mixin and no approver field. Resolve via `reports_to` → HR, matching how OT visibility already works. This is Mirza's *"approver dapat noti dekat mana?"* — push notifications cannot fix it, because there is no notification to deliver |
| 3.2 | Run `docs/glass/runbook/find-duplicate-employees.sql`. Project Board shares this Employee table, so a duplicate splits project assignments AND leave history |
| 3.3 | 3 pre-existing test failures — `test_erp_instance_doctype` (child table points at the wrong doctype), `test_pwa_resource_states` (`BaseLayout.vue`), `test_pwa_session_scope` (`get_ot_requests` needs an `employee` it is not sent). All three predate this session |
| 3.4 | Classify the 16 visual diffs, then re-baseline. Cause known; "known" is not "checked" |

---

## Phase 4 — Cutover · *decisions, not engineering*

The goal: **Verifica as single source of truth.** Everything here is what stands
between now and that.

| # | Item | State |
|---|---|---|
| 4.1 | **Schedule `run_sync`** | Blocks everything below. `REQUIRED_CLEAN_RUNS = 4` — consecutive clean parity checks. A streak cannot accumulate while the mirror only moves when somebody presses a button. One line in `hooks.py`, reversible, and the staleness heartbeat proves it ran |
| 4.2 | **3 schema rulings** on Nasty-Dev | One dialog of dropdowns. `Not needed on hub` = **parked**, and parking is a valid answer that never blocks. What blocks is `unruled` — nobody having said either way |
| 4.3 | **R1** | ✅ decided — one HR covers every entity, fail-open is correct. `decisions/R1-company-fence-fails-open.md` |
| 4.4 | **R2** | ✅ decided — staff transact in Nadi. Instruments shipped (`e9d735d27`, `7a8c48227`) |
| 4.5 | **R6** | ⬜ open — retention and DSAR while PII sits in the hub *and* every source. `user_data_fields` is commented out at `hooks.py:638` |
| 4.6 | Dev/live untangle | `Nasty-Dev` **disabled, not deleted** — per the standing rule that nothing gets removed, only parked. Full sync from live re-stamps the shared rows |

**Cut over per company, not all at once.** `unlock_mirrored_writes` is already
per-instance. Take the smallest company to four clean runs, cut it over, let it
run alone a fortnight. A big-bang cutover on a system where four silent failures
surfaced in one week is not a risk worth taking.

**Order at cutover, and it matters:** last sync → parity READY → **untick
`enabled`** → *then* tick `unlock_mirrored_writes`. Unlocking while the instance
still syncs means the next pull overwrites local edits silently.

---

## Phase 5 — Design · *3–4 days, and it blocks nothing*

25 items across GATE 2–4 in `RELEASE_READINESS.md`. Real work, properly
specified, and **not one of them stops a person doing their job.**

Two carry most of the visible weight:

- **9.5a** — the ported-not-rebuilt screens (Profile, SOP, Issues, AppSettings).
  This is the "same old language" complaint in one item.
- **Ionic** — 37 files, marked out of scope. That ruling looks wrong now:
  `<ion-content>`, `<ion-modal>` and `<ion-page>` own the page transitions and
  modal motion, which is why screens still *move* like old Frappe HR even when
  they are coloured like Glass. No amount of token work reaches it.

Measured, not asserted: **231 lint violations across 37 files** (arbitrary 116,
rawPalette 60, hex 51, colorfn 4) and **60 frappe-ui UI import sites across 14
components**. The 61 `createResource`-style data-layer imports are fine and
should stay.

---

## The standing rules

Learned this week, and they outrank convenience.

1. **Nothing is deleted, only parked.** Every doctype and function on
   ERP/Verifica either works or is explicitly parked, because it may be needed
   later. `Not needed on hub` is the mechanism, and it is a signed record with
   `ruled_by` and `ruled_on` — not forgetting.
2. **Never `Purge` before a source census.** Purge deletes by
   `synced_from_instance`, and on a hub that ran two instances that stamp says
   who synced *last*, not where a row came from. It already cost one real
   record.
3. **Verify against a real database, not a stub.** Three defects this week hid
   behind fake objects that answered for predicates MariaDB rejects.
4. **A decision not written down did not happen.** R1 was decided in
   conversation, asked again the same day, and only stopped resurfacing once it
   became a file.
5. **One cause per commit.** A regression in a 400-change tree cannot be
   bisected.

---

## If only three things happen

1. **Phase 0 + Phase 1** — the system does what people already think it does
2. **Phase 2.2** — the one test that catches the class of bug Mirza keeps finding
3. **Phase 4.1** — schedule the sync, or cutover stays permanently out of reach
