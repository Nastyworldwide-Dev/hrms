# Nadi PWA 2.0 — delivery pace and regression controls

13 September 2026. Documentation-only refinement of the
[delivery proposal](NADI_2.0_DELIVERY_PLAN_2026-09-13.md), requested by Nabil:
focus on Nadi PWA, connect frontend and backend correctly, and avoid regressions.
The scope/material/policy decisions still marked open there remain open. This
document authorises no migrations, deployment, historical repair or new policies.

## 1. Delivery pace

**Superseded timing guidance:** Nabil subsequently directed agent execution by
verified milestones. All human-day ranges below are historical planning notes,
not current delivery promises or mandatory waits. The dependency order and
regression gates remain active; proceed when each packet is proved complete.

Use **one active implementation packet at a time in the integration branch**.
A packet changes one observable behaviour, normally half to two focused working
days including its tests and review. If it grows beyond two days, split at a
working boundary. Do not split the frontend from the API it requires and merge
either half as a completed feature. Keep commits small and self-contained.

Reserve approximately 60% of each wave for implementation, 25% for contract and
journey testing, and 15% for review and corrections. Testing starts before the
change; those percentages are effort allocation, not a waterfall sequence.
Only start the next packet when the current one passes its acceptance checks.
Investigation/testing may run independently; avoid concurrent changes to
`FormView`, request resources, permission helpers, router or global tokens.

Initial planning allowance: **28–39 focused engineer-days**, plus about 20%
contingency = **34–47 days (roughly 7–10 working weeks for one delivery stream)**.
This is human-equivalent implementation/review effort, not a prediction of agent
runtime or a fixed delivery date. It assumes an available isolated test site,
existing dependencies, prompt scope decisions and no substantial new backend
defects. Approval/environment waiting is additional. Re-estimate after W0 and
after the leave pilot; do not spend contingency by dropping verification.

| Wave | Scope | Effort, days | Depends on | Exit evidence |
|---|---|---:|---|---|
| **W0** | Baseline, API contracts and usable verification | 3–4 | Existing source inspection; environment authority for any fixture/CI changes | Every enabled Nadi family inventoried; baseline journeys run; failing/skipped checks identified; change gate usable. |
| **W1** | Accessible Glass components on a contained sample | 2–3 | W0; applicable material decision | Sample meets visual/accessibility checks and shared-component consumers still work. |
| **W2** | Leave lifecycle pilot | 3–4 | W0–W1 | Create, upload, submit, decision, detail/history and allowed withdrawal proven against persisted state. |
| **W3** | Expense and shift requests | 4–6 | W2 | Each type separately verified; expense lines/taxes/currency and shift validators preserved. |
| **W4** | Attendance correction, OT, replacement leave | 4–6 | W2; applicable policy decisions | Each type separately verified including side effects, rejection, retries and boundary dates. |
| **W5** | Unified approvals and All requests | 3–4 | W2–W4 | Queue, count, permissions, detail and decisions agree; complete own history; no invented actor history. |
| **W6** | Requests hub, Home and navigation | 3–4 | W5; navigation decision | Every old route works; capped Home still reaches all work; retained pages and role access survive. |
| **W7** | Calendar actions and check-in flow | 3–4 | W4, W6 | Day → prefilled form → saved result; punch → server result → refreshed day proven. |
| **W8** | Whole-PWA acceptance and release preparation | 3–4 | W0–W7 | Complete connection ledger, regression matrix, tested release candidate and reviewed release/rollback procedure. |

The ordered sequence prioritises learning from one lifecycle and delaying
high-consequence attendance/payout changes until the shared flow is proven.
W3 and W4 are distinct waves even though both depend on W2. Internal integration
checkpoints occur after every wave; production deployment is a separate action.

## 2. Work packets inside each wave

### W0 — prove the existing connections before changing them (B0 + B1)

1. **W0.1: inventory and reachability.** Start with
   [API connections](NADI_2.0_API_CONNECTIONS.md): 102 source-discovered RPC names,
   including implicit insert/delete; 82 HRMS definitions resolved locally.
   Expand generic RPCs by operation and doctype. Map each route, resource,
   endpoint, handler, controller, permission hook and notification destination.
   Mark references used only in configuration separately from actual callers.
2. **W0.2: contract fixtures.** Capture sanitised request/response shapes on an
   isolated site. Include normal employee, named approver without reports,
   manager, scoped HR, HR without Employee, CEO, guest and invalid identity.
   Include two companies, rejected/cancelled/draft records and a real configured
   workflow. Never use production identities or send real approval notifications.
   Fixture writes and external-service suppression need an approved setup.
3. **W0.3: baseline gate.** Run the existing frontend and relevant backend tests,
   lint/build and browser journeys. Record existing failures without relabelling
   them green. Ensure actual test counts, not only exit code: `conftest.py` can
   collect zero site tests successfully. Prepare the missing quick-check script
   and CI change concretely, obtain required infrastructure approval, then apply.
4. **W0.4: agree the execution ledger.** Each connection gets an owner (the
   packet owner), current verdict and planned wave. Every retained feature gets
   a baseline journey. Freeze the reference commit/site schema/app versions and
   screenshots. Reconcile browser network calls with the source inventory.

Exit: the verification path works locally on an isolated site, and the push
checks required by the working agreement have a working implementation. Local
read-only analysis can continue while infrastructure approval is pending, but
implementation waves do not claim completion on skipped journey tests.

### W1 — contained visual foundation (B2)

1. **W1.1:** review Home/form/approval composite: Glass placement, legible text,
   hit areas, focus and safe areas. Preserve the current navigation destinations.
2. **W1.2:** adapt existing G* components used by the pilot, one component family
   at a time. List every consumer before changing shared props, slots or CSS.
3. **W1.3:** verify both themes, 320/390/768/1440 widths, 200% text enlargement,
   reduced motion/transparency, keyboard and mobile keyboard. Defer global token
   rollout until all affected consumers pass; avoid a simultaneous global reskin.

### W2 — leave is the complete pilot (B3)

1. **W2.1:** check form metadata, permitted fields, types, balance and approver
   payloads. Implement summary from authoritative results; preserve half-day,
   holiday and overlap validation. A loading balance is not a zero balance.
2. **W2.2:** create/update, attachments and explicit submission. Distinguish
   “draft saved” from “sent for approval.” If document creation succeeds but
   upload fails, retain the document identity and retry the upload; do not
   create a second request or show a false completion screen.
3. **W2.3:** detail/timeline, approval/rejection, own history and permitted
   withdrawal. Test the real configured workflow as well as ordinary decisions.
   Reload and read server state after each mutation; verify balance/ledger effects.
4. **W2.4:** run the importer regression set for shared form/action changes,
   including expense, shift, correction, OT, RL and the other FormView consumers.
   Re-estimate remaining waves from measured pilot effort.

### W3 — two independent request packets (first part of B4)

1. **W3.1 expense:** preserve multi-line expenses, taxes, sanctioned amounts,
   company currency, attachments, cost centre/account defaults and decision
   semantics. Test create/edit/submit/reject and authoritative totals after reload.
   Approved is not Paid; never infer a payroll date from an unpaid status.
2. **W3.2 shift:** verify current employee, allowed approver, date range, shift
   options and overlap rejection; run the same full lifecycle. Avoid changing
   roster cover policy or shift-generation rules.
3. **W3.3 integration:** run leave + both new journeys on the same build and
   verify that a change of employee/company/session invalidates personal options.

### W4 — three consequence-sensitive packets (rest of B4)

1. **W4.1 correction:** prefill dates/times, preserve validation, and inspect
   Attendance records after approval, rejection and allowed cancellation.
2. **W4.2 OT:** discovery and filing use the same server window; summary uses
   exact server hours/rates; approval and retries create the expected consequence
   once; rejection creates no payout consequence. Cover four-cycle boundaries,
   overnight shifts, rest days and public holidays. Carry the open paid-period
   policy into its explicit decision, not a new frontend eligibility rule.
3. **W4.3 RL:** prove bank summary and claim cost agree with the server setting;
   approve/reject/withdraw affect the appropriate allocation once. Include missing
   or cancelled allocation behaviour already fixed in the backend.
4. **W4.4 integration:** execute all six request lifecycles together. Validate
   native docstatus, decision status and workflow distinctions in each list/detail.

### W5 — integrate queues only after individual types work (B5 + All requests)

1. **W5.1:** bounded queue and count contract, server permissions and stable
   pagination; test six types plus remote check-in as a distinct approval family.
2. **W5.2:** queue/detail actions use existing decision capabilities, revision
   checks and endpoints. Test two approvers/tabs racing, repeat taps, timeout after
   server success and stale reviewed revision. A failed refresh must be visible.
3. **W5.3:** All requests and own history, type/status chips and page boundaries.
   “Decided by me” uses persisted actor evidence only; unavailable history must
   be explicitly labelled, not reconstructed from today's approver assignment.
4. **W5.4:** prove queue rows/count/Home source share eligibility, with bounded
   queries and no cross-company data in responses. Self-decision follows existing
   type-specific HR settings. Test capability changes while the page is open.

### W6 — compose the PWA, then switch navigation (B6)

Home now includes [Announcements](NADI_2.0_ANNOUNCEMENTS.md), requested by Nabil.
Prepare ANN.0 during W0; complete ANN.1–ANN.2 before connecting the Home card in
ANN.3/W6. HR publication and audience-scoped reading are required W6/W8 journeys.
This addition is separate from deferred company events. The earlier human-day
estimates are historical and superseded by Nabil's instruction to execute through
verified milestones; they are not a schedule or a reason to wait between packets.

1. **W6.1:** Requests hub uses verified balances, summaries and lists. New request
   sheet opens the correct existing form with valid prefill and a working back path.
2. **W6.2:** Home consumes the verified queue/count, own requests and punch state.
   Remove duplicate entry points only after their replacements are tested.
3. **W6.3:** migrate tab ownership and legacy URLs together. Preserve document
   names, query parameters, notification links, reload and Ionic back stacks.
4. **W6.4:** repeat retained-feature journeys: KPI personal/manager/HR/CEO scopes,
   team and roster, SOP read and authorised editing, Helpdesk availability and
   reply/upload, confidential issues and HR board, Profile/contacts/settings,
   notifications and auth recovery. Record failures before accepting the shell.

### W7 — calendar and check-in (B7)

1. **W7.1:** day-state/action matrix and server eligibility; day → prefilled
   correction/OT/leave/RL form → submitted result → refresh calendar and request list.
2. **W7.2:** check-in pending/strict rejection/stale IN/late checkout/offline
   paths, location/selfie upload and failure recovery. Keep current server checks.
   No offline punch queue is introduced. For uncertain submission outcomes,
   reconcile against server state before offering a retry.
3. **W7.3:** group punch history using shift/timezone rules, not browser-local
   date guesses. Verify overnight, missing OUT, holiday/rest day and remote-review
   outcomes. Exercise actual permitted device/browser behaviour on the test site.

### W8 — acceptance and release preparation (B8)

1. **W8.1:** close every applicable connection verdict; run the whole-PWA
   regression matrix and strict rendered design checks on the candidate build.
2. **W8.2:** test installed-PWA update, old cached chunk/deep link, logout/login
   as a different user, socket reconnect, expired session and private downloads.
3. **W8.3:** review cumulative changes, API compatibility, migrations and rollback.
   Frontend assets and HTML must belong to the same build. Record exact app/schema
   versions and release identifiers. An API rollback must support the served PWA.
4. **W8.4:** prepare the admin release and observation checklist. Deployment
   requires its own authorisation. After authorised deployment, check read-only
   pages first and use only explicitly authorised test identities for writes.

## 3. What “connected properly” means

For every changed screen, prove this chain with the real test-site handler:

`UI action → resource/fetcher → HTTP method + parameters → effective endpoint`
`→ identity/permissions/workflow → controller/hooks → persisted records`
`→ response/error → resource refresh/cache → list/detail/badge/calendar`

Checking HTTP 200 alone is insufficient. Check the Frappe response envelope,
the returned fields the UI reads, domain status, and the saved record. Test
negative cases: forbidden employee/company, missing required input, invalid
transition and stale revision. For a write, verify both intended side effects
and absence of duplicate/unwanted effects. The PWA must not report success before
the server confirms the relevant operation.

The integration record belongs to the caller and operation: a shared RPC does
not make leave, expense and OT interchangeable. Trace effective framework
overrides (notably push), generic document APIs, field permissions, metadata,
attachments, workflow RPCs, boot/session handling and realtime invalidation.
Use current server behaviour as the contract unless an explicit requirement
changes it; turn discovered defects into separate fixes with failing tests.

## 4. Checks at each boundary

| Boundary | Required check | A failure means |
|---|---|---|
| Before a packet | Read caller/handler/controller; list consumers; contract fixture; failing behaviour test for change (RED on old code for fixes). | Scope/investigate before editing. |
| Before commit | Changed and importer tests, frontend lint/build as affected, backend lint/tests as affected, focused real-site contract/journey, diff review. | Repair the same packet; do not stack more work on it. |
| Before wave acceptance | All completed-wave journeys plus touched retained families, both themes, capability/error states; no test unexpectedly skipped. | Wave stays open; the passing subset is not acceptance. |
| Before push | Required quick gate green, fresh-context review; Critical fixed, Important fixed, Minor recorded. | No push. Current missing quick script is resolved in W0. |
| Before release | All enabled Nadi connections covered, full persona matrix and built-PWA journeys green, no regression baseline growth, release/data effects reviewed. | No release; reduce proposed scope only through an explicit scope amendment. |

Always run a compact common set after shared resource/router/form/token changes:
login + identity; leave draft/submit; approval/reload; check-in state; cross-company
denial; logout/login cache separation. Add every affected importer family; the
common set never substitutes for that coverage. Keep detailed failures in the
packet ledger so unrelated work is not repeatedly re-investigated.

Build a case matrix instead of a wasteful full Cartesian product: each applicable
endpoint has permitted and denied contract cases; every mutation has persisted
effect/retry assertions; every feature family has a real journey; every shared
shell change gets the retained-feature sweep. Do not substitute string/AST
tests or mocked-success browser tests for real integration evidence.

## 5. Compatibility, stopping and rollback

- Prefer existing endpoints. If a new field/API is needed, make the server
  change additive, prove old and new consumers, then switch the PWA. Retire old
  contracts only in a later approved cleanup after cached-client use is resolved.
- Keep a known-good integration commit for every accepted wave. “Known good”
  includes site/schema/build versions and test evidence, not just a Git tag.
- Stop the packet for an unknown payload, lost draft/upload, permissions drift,
  duplicate mutation, changed financial/attendance result, broken old route,
  unexplained network error or lost cache isolation. Add a regression test and
  correct the cause; never weaken the assertion or baseline to continue.
- If a packet destabilises shared consumers, restore the last compatible code
  through a reviewed revert/fix. Do not reset unrelated work or treat a code
  revert as reversal of data writes. Data repair requires its own exact approval.
- A failed required test cannot be waved through because it “was already red.”
  Record baseline debt, fix launch-relevant blockers, and keep the wave open
  until its required checks pass. Out-of-scope debt is explicit and not a green
  verdict for an untested feature.
- Script Reports remain deferred. Backend work here is limited to the contract
  and correctness needs of Nadi PWA. The earlier approval for a different branch
  push does not authorise a 2.0 deployment.
- Inspect `scripts/smoke.sh` before use: it migrates and can invoke the expanded
  OT repair. Do not execute it as read-only verification or silently include
  historical repair in a UI release.

## 6. Packet handover template

Record: packet ID; observable change; frontend consumers; endpoints and
operation/doctype; controller/hooks; expected request/response/effects; personas;
RED evidence; test commands/counts/results; browser/site/build evidence;
compatibility/revert path; review findings; commit; remaining NEXT item.
The packet is complete only when another session can reproduce its evidence.

Next: W0.1 expands the source inventory into caller/operation contracts, followed
by W0.2–W0.4 to establish runtime proof. No application implementation was performed
while writing this breakdown. The historical 166 frontend and selected 19 backend
test passes in the parent proposal are a baseline, not proof of these future waves.

Documentation verification: eight relative links resolved; all 102 inventory
rows and 82 local handler definitions checked; effort ranges reconciled;
`git diff --check` passed. Fresh-context review found no Critical or Important
issues; minor login/logout source references were corrected. Review verdict
`NEXT_ACTION: DEPLOY` applies to documentation only, not application release.

LEARNING(fact): many Nadi writes come from generic Frappe resource operations;
matching named HRMS endpoints alone would miss important frontend/backend contracts.
