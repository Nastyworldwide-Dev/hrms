# 360 audit repair execution

AUTHORIZATION: Nabil's 8 September instruction "go go fix them all" approves repairing the defects and repair sequence in docs/glass/audit/2026-09-08-360-audit.md, including its permission/session boundaries. Preserve existing Track 1 approval. This supplements current-plan.md and does not discard other-session plans or staged work.
TIER: risky. PROPERTY TESTS: REQUIRED for permission, state and financial logic.
GOAL: correct audited checkout/location, attendance/OT/RL, PWA/Desk approvals, notifications/privacy, reports/sync and recovery defects with regression evidence, without reverting Hafiz's valid changes.
DONE WHEN: each confirmed defect has a reviewed tested repair, or an explicit unresolved production/policy dependency; related caller families pass; full frontend tests/lint pass; Python collection/failures are resolved or accurately bounded; no outstanding implementation defect is called done. No fabricated live/device/deployment evidence.

## Parallel isolated slices

1. Checkout worker owns Remote Checkin Request controller, employee checkin approval producers/propagation and late reprocessing hooks plus tests. First fix inherited checkout with verified parent/session relation and negative authorization properties. Then centralize allowed state transitions, Pending evidence eligibility and full-shift/day late rebuild; retain manual/mirrored protections. No blanket permission bypass or historical mass repair.
2. Notification/privacy worker owns frontend personal-resource identity/cache/session/push/feed/navigation files and backend Employee Issue/PWA Notification/mixin routing, their metadata/necessary migration, plus tests. Scope all personal caches and recipient selection, account-bind push registration, validate semantic transport results, publish native delivery after commit, align feed role/row rights, and resolve usable destinations. Remote hook realtime timing is coordinated with checkout worker.
3. Attendance/OT worker owns ot_calculation.py, Shift Type, Attendance, OT Request, filing helper and OT summary APIs, plus tests. One work-date/shift/evidence definition across readers; nonworking-day all eligible worked minutes and configured bands, Present/no flags; weekday behavior preserved. Fix split-session breaks, monthly cap range consistency and changed-date filing bypass. Prepare configurable four-month backdated filing, inactive pending the temporary/permanent policy decision, without guessing settlement.
4. Lead coordinates integration and fresh review; subsequent workers handle PWA shared approvals/forms/location/calendar, Desk report fences/charts/dirty-state, RL allocation/sync ownership and test harness. Specific file ownership assigned before each task to avoid overlapping edits.

## Invariants and decisions

- Nonworking-day HR instruction is explicit: all hours worked, no minimum or weekday attendance flags. Use exact worked minutes (194/60 = 3.2333...) and avoid weekday rounding/caps erasing work. Applicable holiday list determines day type. No invented 3.24-hour rounding rule. Weekday 60-minute minimum remains.
- Existing pay rate bands retained; ensure configured PH 8h@2x + 1h@3x is honored. Do not silently edit live shift/payroll configuration.
- Four months provisionally means calendar months before filing, retaining the actual work date. Temporary grace versus permanent rolling availability remains undecided; do not invent an expiry or enable a policy without that decision. Discovery and validation share the effective window. Closed payroll is not automatically settled by an old-date request; prepare explicit handling without inventing paid-state data.
- Preserve unrelated staged/unstaged work. Workers use isolated worktrees; lead integrates only reviewed source/test paths and commits each root cause separately. Do not stash, reset, force-push or bypass hooks.
- UI repairs follow the existing recovery mockup and established layout. Nabil replaced the working agreement on8September, removing the prior separate mockup-approval requirement; the already authorized OT layout/copy correction may proceed. No new redesign programme.
- Test records may be synthetic/in-memory or isolated rollback fixtures; production attendance, decisions, leave balances, notifications and configuration are not mutated during local repair. Any historical repair must first produce a reviewable candidate set.

## Evidence and checkpoints

Each slice: name public behavior -> failing regression on old source -> implementation -> mapped/importer tests -> fresh verifier -> integrate/commit. Keep source change budget per commit. Convert synthetic audit probes into meaningful regression coverage; retain audit snapshots as historical evidence. Update family.md and progress.md per slice. No production build/migrate/push before relevant gates and admin checks.

## Reviewed OT index proposal

The proposal in docs/glass/audit/2026-09-08-ot-lock-proposal.md names the composite employee/docstatus/ot_date index, Employee-before-request lock order and native concurrency acceptance. After the concrete schema confirmation request, Nabil replied "continue"; lead explicitly acknowledged proceeding with this index and locking implementation plus local testing. This authorizes that proposed schema slice. It does not choose the four-month filing policy or authorize a production migration before validation.

## Approved OT precision proposal

After the concrete six-field precision proposal and implementation/local-testing question, Nabil replied "proceed". This authorizes docs/glass/audit/2026-09-08-ot-precision-proposal.md: the six precision2->9 fields, pre-model capacity guard, post-model verifier and documented storage-boundary Decimal comparison, with local migration tests. It does not authorize production deployment or historical recalculation.
