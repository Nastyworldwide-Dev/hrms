# HRMS-side plan: Helpdesk KPI measurement ingestion and next-cycle proposals

Companion to `next-helpdesk/docs/workforce-planning-and-performance-plan.md`
(Phases 6–7). The Helpdesk side is implemented and pushed; this plan covers the
HRMS half that Codex left gated. Target branch: `nz-version-16`, baseline
commit `67229061c` (re-verified as the branch tip on 2026-08-25).

Written for a fresh Claude Code session in this repository. It is a delivery
plan, not authorization to deploy, migrate a site, or touch production data.

## What Helpdesk already sends (the contract this side must accept)

Verified from `next-helpdesk` at `e621cf7ba`:

- `helpdesk/workforce/metric_contract.py` — `CONTRACT_VERSION = "helpdesk-hrms-measurement-v1"`. Payload:

  ```json
  {
    "contract_version": "helpdesk-hrms-measurement-v1",
    "employee": "<HRMS Employee name>",
    "appraisal_cycle": "<Appraisal Cycle name>",
    "appraisal": "<Appraisal name>",
    "kpi": "<KPI name>",
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD",
    "measurement": {
      "metric_key": "sla_compliance",
      "value": 96.25,
      "unit": "percent",
      "direction": "higher_is_better",
      "sample_size": 48,
      "calculation_version": "helpdesk-support-v1"
    },
    "idempotency_key": "<sha256 of (appraisal, appraisal_cycle, employee, kpi, period_end, period_start, metric_key, calculation_version)>"
  }
  ```

- `helpdesk/workforce/metrics.py` — `METRIC_REGISTRY` keys and units:
  `sla_compliance` (percent, higher), `median_first_response_minutes` (minutes, lower),
  `median_resolution_minutes` (minutes, lower), `customer_satisfaction` (ratio, higher, min sample 3).
  `value` is `null` when the sample is below the minimum.
- `helpdesk/workforce/recommendations.py` — `RECOMMENDATION_VERSION = "helpdesk-next-cycle-v1"`;
  produces `{employee, appraisal_cycle, kpi, metric_key, source_period_start, source_period_end,
  sample_size, proposed_value|null, status: "Draft"|"Needs Review", explanation, ...}`.
- `helpdesk/workforce/identity_mapping.py` — classifies `HD Agent.user` → Employee as
  `mapped | ambiguous | inactive | missing` from Employee rows it must be given. It has no
  HRMS read path yet; this plan provides one.
- Helpdesk has **no** `publish` / `retry_delivery` yet (`helpdesk/api/performance_metrics.py`
  only exposes `calculate`). Those are Helpdesk follow-ups listed at the end; they depend on
  the endpoints defined here.

## HRMS baseline facts this plan relies on (at `67229061c`)

- `KPI` fields: `title, kra, default_target, unit_of_measure (Link UOM), description`. No source metadata.
- `Appraisal KRA` fields include `kpi, target, actual, achievement, unit_of_measure, per_weightage, weighted_score`. No direction.
- `Appraisal.validate()` calls `calculate_a1_score()`, which sets `row.achievement = actual / target * 100`
  capped at 100 — **higher-is-better only**. Lower-is-better metrics (response minutes) would score backwards.
- `Appraisal.has_permission` / `get_permission_query_conditions` are hooked in `hooks.py`; employees see only
  their own Appraisal, HR roles are company-fenced (`hrms/utils/company_fence.py`).
- `Appraisal Cycle.status` is `Not Started | In Progress | Completed`; `complete_cycle()` refuses while draft
  Appraisals exist; `validate_active_appraisal_cycle()` blocks transactions on Completed cycles. No lock, no proposal state.
- `hrms/utils/identity.py::resolve_employee_identity(user)` already returns
  `OK | NO_EMPLOYEE | INACTIVE_EMPLOYEE | AMBIGUOUS_EMPLOYEE` with non-leaking messages — reuse, do not reimplement.
- `HRMS Sync Run` is the existing audit-record pattern (status + counts + error_log, `track_changes`, HR-only perms).
- Tests: `FrappeTestCase` (see `hrms/api/test_kpi.py`) need a bench; the repo also has a "pure unit test" pattern
  (`hrms/tests/_erpnext_stub.py`, frappe mocked) but it still `import frappe`, so **no test in this repo runs on a
  machine without the frappe package**. On this machine there is no bench and no `frappe` — all test evidence
  comes from CI (`bench --site test_site run-parallel-tests --app hrms`).
- Style: tabs, double quotes, line length 110, ruff `F E W I UP B RUF`; logging via
  `logger = logging.getLogger(__name__)` with a `[module]` prefix (as in `hrms/api/kpi.py`).

## Decisions fixed by this plan (do not re-litigate in the session)

| Decision | Choice | Why |
| --- | --- | --- |
| Transport | Service functions in `hrms/performance/`, thin `@frappe.whitelist()` wrappers in `hrms/api/kpi_measurement.py` | Works for same-site Python calls and separate-site REST alike; topology stays an open product decision without blocking code |
| Who may submit | Caller must hold `HR Manager` **and** pass `frappe.has_permission("Appraisal", "write", doc)` | Reuses the existing company fence; no new role to maintain. A service account is an HR Manager fenced to its company |
| Where source metadata lives | Standard fields on `KPI` (this fork owns the DocType) | Simpler than Custom Field fixtures; migrates with the app |
| Scoring direction | New `direction` on `KPI`, frozen onto `Appraisal KRA` when KRAs are applied; `calculate_a1_score` inverts for lower-is-better | Direction must not change under an in-progress appraisal |
| Unit check | `KPI.source_unit` (Data) must equal `measurement.unit` | Helpdesk units are strings (`percent`, `minutes`); mapping them to UOM links adds nothing |
| Audit record | One DocType, `KPI Measurement Delivery` | Plan forbids a second performance model; this is the "one narrowly scoped integration/audit DocType" |
| Mutation path | `doc.save()` on the Appraisal after setting `row.actual` | Runs `validate()` → A1 recalculation, permission hooks, version history. Never `db.set_value` on rows |
| Business rejections | Returned as `status: "Rejected"` with a reason, **not** raised | The delivery record must persist; only permission errors raise (before anything is written) |
| Corrections | Same `idempotency_key`, different payload hash → new delivery linked via `previous_delivery`, old one `Superseded` | Append-only history; nothing is rewritten silently |
| Locking | `Appraisal Cycle.locked` (Check) + `locked_on`; a `Locked` cycle refuses measurements and proposals | The plan's `Completed -> Locked` semantics; `status` Select is left untouched for compatibility |
| Recommendations | Stored in HRMS as `KPI Target Recommendation`; approved values reach `Appraisal KRA.target` only via an explicit HR action | Plan: "Store KPI/target recommendations in HRMS so HRMS permissions remain authoritative" |

## Slices (implement in order; each is red → green → refactor)

### Slice 1 — KPI source metadata and direction-aware A1 scoring

Files: `hrms/hr/doctype/kpi/kpi.json`, `hrms/hr/doctype/appraisal_kra/appraisal_kra.json`,
`hrms/hr/doctype/appraisal/appraisal.py`, `hrms/hr/doctype/appraisal/test_appraisal.py`.

1. Add to `KPI`, in a collapsible section "Integration source":
   `source_app` (Select: `\nHelpdesk`), `metric_key` (Data), `source_unit` (Data),
   `direction` (Select: `Higher is better\nLower is better`, default Higher),
   `automation_mode` (Select: `Manual\nPreview\nAutomatic`, default Manual),
   `minimum_sample_size` (Int, default 1), `calculation_version` (Data).
   Validate in `kpi.py`: if `source_app` is set, `metric_key` and `source_unit` are required.
2. Add `direction` (same Select, default Higher) to `Appraisal KRA`. In
   `Appraisal.set_kras_and_rating_criteria` copy it from the KPI. Existing rows default to Higher, so
   nothing changes for current data.
3. In `calculate_a1_score`, replace the ratio with a helper `achievement_percent(target, actual, direction)`:
   higher → `actual / target * 100`; lower → `target / actual * 100` when `actual > 0`, `100` when
   `actual == 0 and target > 0`, `0` when target is 0. Cap stays at 100.
4. Tests (red first): lower-is-better row with actual below target scores 100; actual double the target scores 50;
   higher-is-better rows unchanged from today's numbers; KPI with `source_app` but no `metric_key` fails validation.

### Slice 2 — Delivery record and the preview/submit service

Files: `hrms/hr/doctype/kpi_measurement_delivery/*`, `hrms/performance/__init__.py`,
`hrms/performance/measurement.py`, `hrms/api/kpi_measurement.py`, `hrms/api/test_kpi_measurement.py`,
`hrms/hr/doctype/hr_settings/hr_settings.json` (+ `.py` if validation needed), `hrms/hooks.py` (no change unless
a doc_event is needed — none expected).

1. `HR Settings`: `enable_helpdesk_measurements` (Check, default 0). Every submit path checks it first and
   returns `Rejected: integration disabled` when off (preview still works).
2. DocType `KPI Measurement Delivery` (not submittable, `track_changes`, naming `KMD-.#####`, perms
   read/write/create for System Manager, HR Manager, HR User; **no Employee role**):
   `idempotency_key` (Data, unique, read-only), `payload_hash` (Data), `contract_version`, `employee` (Link),
   `appraisal` (Link), `appraisal_cycle` (Link), `kpi` (Link), `metric_key`, `period_start`, `period_end`,
   `value` (Float), `unit`, `direction`, `sample_size` (Int), `calculation_version`,
   `status` (Select: `Received\nPreviewed\nAccepted\nRejected\nSuperseded`), `rejection_reason` (Small Text),
   `evidence_summary` (Small Text — aggregate text only), `previous_delivery` (Link self),
   `submitted_by` (Link User), `applied_on` (Datetime), `previous_actual` (Float).
3. `hrms/performance/measurement.py` (pure functions + one mutating entry point):
   - `validate_payload(payload) -> list[str]` — contract version, required keys, period order, key recomputation
     (mirror Helpdesk's canonical key exactly: same fields, `sort_keys=True`, `separators=(",", ":")`, sha256).
   - `resolve_target(payload) -> dict` — loads Appraisal; checks `employee` matches, cycle contains the period,
     cycle not Completed/locked, Appraisal `docstatus == 0`, exactly one `appraisal_kra` row with that `kpi`,
     `KPI.source_app == "Helpdesk"`, `KPI.metric_key == measurement.metric_key`, `KPI.source_unit == unit`,
     `KPI.direction` agrees with `measurement.direction`, `sample_size >= KPI.minimum_sample_size`,
     `value is not None`. Returns `{ok, reason, appraisal_doc, row}`; reasons are safe strings that never name
     another employee.
   - `preview(payload, user)` — requires `HR Manager` + Appraisal **read**; returns
     `{status: "Previewed"|"Rejected", reason, proposed: {kpi, previous_actual, new_actual, achievement_before,
     achievement_after}}`. Achievement-after is computed with Slice 1's helper without saving.
     Writes a `Previewed` delivery only when `record=True` (default False) so dry runs stay side-effect free.
   - `submit(payload, user)` — requires `HR Manager` + Appraisal **write** (raise `PermissionError` before any
     write). Then, in order: settings flag → existing delivery with same key:
     same hash → return it unchanged (idempotent replay, log at info);
     different hash → this is a correction: proceed, and on acceptance mark the old row `Superseded` and link it.
     Then `resolve_target`; on failure insert `Rejected` delivery and return. On success set `row.actual`,
     `doc.save()`, insert `Accepted` delivery with `previous_actual` and `applied_on`, return it.
     Whole thing inside `frappe.db.savepoint("kpi_measurement")`; on unexpected exception roll back to the
     savepoint, insert a `Rejected` delivery with the exception class name only, re-raise.
   - `get_delivery_status(idempotency_key, user)` — loads delivery, then `frappe.has_permission("Appraisal",
     "read", delivery.appraisal, throw=True)`; returns status fields only.
   - `resolve_employee(user_id, requester)` — requires `HR Manager`; wraps `resolve_employee_identity(user_id)`
     and returns `{status: mapped|missing|inactive|ambiguous, employee}` using the same words Helpdesk's
     classifier uses. Never returns candidate names for `ambiguous`.
4. `hrms/api/kpi_measurement.py`: `preview`, `submit`, `get_delivery_status`, `resolve_employee` — whitelisted,
   parse JSON string payloads, delegate, nothing else.
5. Tests (`FrappeTestCase`, set up like `test_kpi.py` with two employees and a cycle with appraisals; add a KPI
   with `source_app = Helpdesk`):
   - Employee user calling `submit` → `PermissionError`; HR Manager of another company → `PermissionError`.
   - Valid submit → `Accepted`, `Appraisal KRA.actual` updated, `achievement` recomputed via `validate`,
     one delivery row.
   - Replay identical payload → same delivery name returned, still one row, no second version entry.
   - Same key, new value → new `Accepted` row, old row `Superseded`, `previous_delivery` set, `previous_actual`
     recorded.
   - Rejections (each a separate test, no mutation, one `Rejected` row): submitted Appraisal, Completed cycle,
     KPI not on Appraisal, unit mismatch, direction mismatch, period outside cycle, employee mismatch,
     sample below minimum, `value: null`, tampered `idempotency_key`, flag disabled.
   - `preview` never writes by default; `get_delivery_status` as the employee → `PermissionError`.
   - `resolve_employee` for a user with two active Employees → `ambiguous` and no names in the response.

### Slice 3 — Cycle lock

Files: `appraisal_cycle.json`, `appraisal_cycle.py`, `appraisal_cycle.js` (button), `test_appraisal_cycle.py`,
`hrms/performance/measurement.py`.

1. Add `locked` (Check, read-only) and `locked_on` (Datetime, read-only) to `Appraisal Cycle`.
2. `@frappe.whitelist() def lock_cycle(self)`: requires `HR Manager`, status must be `Completed`, sets both
   fields. No unlock in this slice (an unlock is a product decision; leave a TODO in the tracker, not code).
3. `validate_active_appraisal_cycle` also refuses when `locked`; `resolve_target` rejects with
   `cycle is locked`.
4. Tests: lock on non-Completed cycle throws; submit after lock → `Rejected`; Appraisal save against a locked
   cycle throws.

### Slice 4 — Next-cycle proposal scheduler and approval

Files: `appraisal_cycle.json/.py/.js`, `hrms/performance/cycle_proposal.py`,
`hrms/performance/test_cycle_proposal.py`, `hr_settings.json`, `hrms/hooks.py` (`scheduler_events.daily`).

1. `HR Settings`: `enable_next_cycle_proposals` (Check, default 0), `next_cycle_proposal_lead_days` (Int, default 30).
2. `Appraisal Cycle`: `proposal_status` (Select: `\nProposed\nApproved\nRejected`, read-only),
   `proposed_from_cycle` (Link self, read-only), `proposed_on` (Datetime), `proposal_reviewed_by` (Link User),
   `proposal_reviewed_on` (Datetime), `proposal_comment` (Small Text).
3. `propose_next_cycles()` (daily): when the flag is on, for each cycle with `status != Not Started`,
   `end_date` within lead days of today, not locked, and no cycle whose `proposed_from_cycle` is this one:
   insert a new cycle with `status = Not Started`, `proposal_status = Proposed`, `start_date = end_date + 1`,
   `end_date` = same length, `cycle_name = "<old name> (next)"` de-duplicated, copying company, branch,
   department, designation, a1/a2 weights, scoring method, achievement/manager weights, section percentages,
   score conversion rows, `kra_evaluation_method`. Employees are **not** populated and Appraisals are **not**
   created. Duplicate-run safety: `frappe.db.get_value("Appraisal Cycle", source, "name", for_update=True)`
   before the existence check; each cycle in its own `savepoint`; a failure on one cycle logs and continues.
   Logs `[cycle_proposal] proposed=%d skipped=%d failed=%d`.
4. Guards: `create_appraisals`, `set_employees`, and `Appraisal.validate` (via `validate_active_appraisal_cycle`)
   refuse while `proposal_status == Proposed` with a message telling HR to approve the proposal first.
5. `@frappe.whitelist() def review_proposal(self, decision, comment=None)`: `HR Manager`; `decision` in
   `Approved | Rejected`; only from `Proposed`; records reviewer/time/comment. `Rejected` proposals stay as
   records (audit) and are excluded from list views by a default filter in `.js`, not deleted.
6. Tests: two scheduler runs → one proposal; cycle outside lead window → none; locked source → none; flag off
   → none; `create_appraisals` on a Proposed cycle throws; after `Approved` it works; `review_proposal` as
   HR User → `PermissionError`; `Rejected` cannot be re-reviewed.

### Slice 5 — Target recommendations (ingest, review, apply)

Files: `hrms/hr/doctype/kpi_target_recommendation/*`, `hrms/performance/recommendation.py`,
`hrms/api/kpi_measurement.py` (two more endpoints), `hrms/api/test_kpi_measurement.py`.

1. DocType `KPI Target Recommendation` (HR-only perms, `track_changes`): `employee`, `appraisal_cycle`
   (must be a proposed/approved next cycle), `kpi`, `metric_key`, `source_period_start/end`, `sample_size`,
   `policy_version` (Data — Helpdesk's `RECOMMENDATION_VERSION`), `proposed_value` (Float, nullable),
   `explanation` (Small Text), `status` (Select: `Pending\nApproved\nEdited\nRejected\nNot Applicable`),
   `final_value` (Float), `reviewed_by`, `reviewed_on`, `review_comment`, `dedupe_key` (Data, unique =
   sha256 of employee|cycle|kpi|policy_version|source_period_end).
2. `submit_recommendation(payload, user)`: `HR Manager` + read on an Appraisal of that employee in the source
   cycle; idempotent on `dedupe_key` (replay returns existing); `Needs Review` from Helpdesk maps to `Pending`
   with `proposed_value = None`. Never writes to any Appraisal.
3. `review_recommendation(name, decision, final_value=None, comment=None)`: `HR Manager`; `Edited` requires
   `final_value`; `Approved` copies `proposed_value` into `final_value`.
4. `apply_approved_targets(appraisal_cycle)`: explicit HR Manager action (button on the cycle, available only
   when `proposal_status == Approved` and Appraisals exist). For each `Approved|Edited` recommendation with a
   matching draft Appraisal + KRA row, set `row.target = final_value` and `doc.save()`; returns counts of
   applied/skipped with reasons. Recommendations for employees without an Appraisal are reported, not applied.
5. Tests: replay idempotency; `Edited` without value throws; `apply` skips submitted Appraisals and
   employees without Appraisals; a `Pending` recommendation is never applied; Employee role cannot read
   the DocType (list is empty and `get_doc` throws).

### Slice 6 — Docs, tracker, and the Helpdesk follow-ups

1. Add `docs/helpdesk-kpi-integration.md` (operator guide: enable flags, configure a KPI's source fields,
   run preview → submit → review → submit Appraisals → complete → lock; where deliveries and
   recommendations are viewed). Keep it short; link this plan.
2. Update this file's tracker (below) with the phase-completion template from the Helpdesk plan.
3. Helpdesk follow-ups (separate session in `next-helpdesk`, blocked on Slices 2 and 5 existing):
   `helpdesk.api.performance_metrics.publish` and `retry_delivery` calling `hrms.api.kpi_measurement.submit`
   with an outbox/delivery log on the Helpdesk side; `identity_mapping` wired to
   `hrms.api.kpi_measurement.resolve_employee`; the manager exception queue for `missing|inactive|ambiguous`.

## What stays out of scope here

- AI assistance (Phase 8) — nothing in this plan calls a model.
- Unlocking a locked cycle, range-target KPIs, escalation/reopen/knowledge metrics — product decisions still open.
- Any change to `get_my_kpi_dashboard` — it stays self-scoped, no employee parameter.
- Helpdesk-side code (listed above as follow-ups so nothing is forgotten, but not done in this repo).

## Pipeline Summary

- **Requirements**: this document + the Helpdesk plan's Phases 6–7 and permissions table.
- **Planning agents**: none further needed; scope, impact, and security considerations are resolved above
  (touches shared `Appraisal` scoring and permission-sensitive endpoints — a `security-checker` pass after
  Slice 2 is worthwhile before the PR).
- **MOCKUP**: NOT NEEDED (backend DocTypes, services, scheduler, and whitelisted APIs; the only UI is two
  standard form buttons on Appraisal Cycle. Prototype for the manager experience already exists at
  `/root/next-helpdesk/docs/mockups/kpi-kra-workflow.html`.)
- **Workspace**: `/root/hrms`, branch `feat/helpdesk-kpi-integration` off `nz-version-16` at `67229061c`.
  No bench and no `frappe` package on this machine — `ruff check` and `python3 -m compileall` are the only
  local gates; test evidence is CI.
- **TDD**: per slice, write the `FrappeTestCase` tests first; they fail locally with `ModuleNotFoundError:
  frappe` until CI runs them — record CI run URLs in the tracker, not "passed locally".
- **Auto-commit**: one conventional commit per slice (`feat(performance): …`, `fix:`, `docs:`), body says why.
- **Auto-review**: `frappe-reviewer` after each commit (post-commit hook); `security-checker` after Slice 2.
- **Auto-deploy**: **none**. Bench migration and deployment are admin-only release activities per the Helpdesk
  plan; ship as a PR to `nz-version-16`, do not push to `version-15`/`version-16`.

## EXPECTED OUTPUT

When the slices are done and CI is green:

- HR can mark a KPI as Helpdesk-sourced (`metric_key`, unit, direction, minimum sample) on the KPI form.
- `hrms.api.kpi_measurement.preview` shows what a Helpdesk measurement would change on a draft Appraisal
  without saving; `submit` applies it through `Appraisal.save()` so A1 recalculates — correctly for
  lower-is-better metrics — and leaves a `KPI Measurement Delivery` audit row. Replays are no-ops;
  corrections chain; every rejection is recorded with a reason.
- Employees still see only their own KPI; no endpoint added here is callable by the Employee role.
- A completed cycle can be locked; locked and completed cycles refuse new measurements and proposals.
- A daily job proposes the next Appraisal Cycle as `Not Started / Proposed`; nothing can be created against it
  until an HR Manager approves; rejected proposals remain as audit records.
- Helpdesk's draft target recommendations land in `KPI Target Recommendation`, are approved/edited/rejected
  by HR, and reach `Appraisal KRA.target` only through the explicit "Apply approved targets" action.
- Files changed: 3 new DocTypes (`KPI Measurement Delivery`, `KPI Target Recommendation`, plus fields on
  `KPI`, `Appraisal KRA`, `Appraisal Cycle`, `HR Settings`), new package `hrms/performance/` (3 modules),
  `hrms/api/kpi_measurement.py`, one scheduler entry in `hooks.py`, tests alongside each, one operator doc.
- Ships as a reviewed PR to `nz-version-16`; deployment is a separate admin step.

## Tracker

- [ ] Slice 1 — KPI source metadata and direction-aware A1 scoring
- [ ] Slice 2 — `KPI Measurement Delivery` + preview/submit/get_delivery_status/resolve_employee
- [ ] Slice 3 — Cycle lock
- [ ] Slice 4 — Next-cycle proposal scheduler and approval
- [ ] Slice 5 — Target recommendations (ingest, review, apply)
- [ ] Slice 6 — Docs, tracker, Helpdesk follow-ups filed
- [ ] CI green on the PR; run URLs recorded here
- [ ] One manual cycle exercised on a real site (admin step; record site, date, and outcome)

### Execution evidence

Use the phase-completion template from the Helpdesk plan for each slice.
