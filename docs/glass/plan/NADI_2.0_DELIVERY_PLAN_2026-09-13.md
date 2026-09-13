# Nadi 2.0 — revised delivery proposal

Prepared 13 September 2026 against `nz-glass` at `10802dfe4`.
Status: ready for scope review; implementation is not approved by this document.
This task is **normal, documentation only**. Implementation slices declare their
own tier. No application, permission, schema, CI or deployment changes are included.

## Recommended outcome

Launch 2.0 around five complete employee journeys: check in, inspect a calendar
day, file a request, follow its outcome, and decide a routed request. Preserve
Liquid Glass while improving readable content and reachable controls. Complete
these journeys before introducing travel, assets, training or events.

Keep the original [UX proposal](NADI_2.0_UX_PLAN.md),
[surface map](NADI_2.0_SURFACE_MAP.md) and
[Glass amendment](NADI_2.0_AMENDMENT_A_LIQUID_GLASS.md) as source material.
Use this proposal to reconcile their sequencing and acceptance criteria. It
does not turn their unanswered questions into approvals. Once accepted, amend
the old documents with the decision record so there is one execution contract.

## 1. What the inspection establishes

This is a Vue/Ionic PWA on a customised Frappe HRMS fork. Its existing request
controllers, server decision API, identity rules and company scopes are the
foundation. The vanilla-v15 mapping and prototype cannot replace those rules.

| Evidence inspected | Current finding | Planning consequence |
|---|---|---|
| `frontend/src/data/navItems.js`, `views/Home.vue` | Phone tabs remain Home, Attend, Leaves, Expenses, More. Home still includes QuickLinks and RequestPanel. | The navigation and Home restructure remains open. |
| `components/RequestPanel.vue` | Own/team lists combine six types. History combines only leave, expense and shift; its tab is approver-only. Its comment incorrectly says OT/RL lack decision fields. | Separate **my history** from **decided by me**; do not expand the current approver tab and call that employee history. |
| `components/FormView.vue` | Existing-document loading and failure recovery already exist. | Original slice 1.5 is partly implemented. Improve state distinctions and presentation; preserve recovery. |
| `data/config/requestSummaryFields.js`, `tests/request-summary-explanation.test.mjs` | Approver review summaries already include explanation and status for OT/RL. There is no shared `RequestSummary.vue`. | Reuse the field knowledge; pre-submit forecast and post-submit detail are still separate work. |
| `hrms/api/approval.py` | Six decision types; capability checks, revision checks, transaction locking and retry handling already exist. No `list_pending_for_user` endpoint. | Build the queue on current decision authority. Do not create a second approval engine. |
| `utils/requestStatus.js` | Rejection can be submitted; cancellation and decision are distinct. | A universal `docstatus == 1 => Approved` mapping would regress existing behaviour. |
| `hrms/api/kpi.py` | HR and CEO have group sight; managers have their permitted reporting chain. | Preserve all existing tiers. The old CEO-only planning files are stale; generic company-fence rules need the documented KPI exception. |
| `hrms/utils/filing_window.py` | Four prior cycles anchored on the 16th; on 13 Sep the earliest date is 16 Apr. Expense Claim has no corresponding filing window. | Calendar actions, filing and explanatory copy use the server rule. Do not invent an expense cutoff. |
| `design/gates/run.mjs`, `verdict.mjs` | SKIP is now visible; strict mode rejects skips. | Do not plan this as a new feature. Make the required rendered checks actually run. |
| `.github/workflows/glass-gates.yml` | Runs `yarn gates`; no served-site setup or strict invocation in this workflow. | CI execution remains a separate approval-dependent prerequisite. Remote branch protection was not rechecked. |
| `scripts/` | `ci-local.sh` is absent. `smoke.sh` exists and runs `bench migrate`. | The working agreement's quick push gate cannot currently be invoked. Smoke is a mutating operation, not a read-only readiness probe. |

The September 9 dimensions and route counts remain historical evidence, not
measurements of this HEAD. No fresh rendered audit, production inspection or
full backend integration run was performed. At inspection, local HEAD was 41
commits ahead of its locally recorded upstream; this is not proof of live state.
The pre-existing uncommitted progress entry was preserved.

### Checks actually run

| Command from repository root | Result | Limit |
|---|---|---|
| `node --experimental-test-module-mocks --test frontend/tests/*.test.mjs` | 166 passed, 0 skipped | Selected frontend directory; not every test elsewhere in the repository and not browser journeys. |
| `python3 -m pytest -q hrms/tests/test_pwa_resource_states.py hrms/tests/test_ot_filing_edits.py hrms/tests/test_filing_guard_is_filing_only.py hrms/api/test_decision_access.py` | 19 passed, 1 skipped, 3 subtests passed | Bench-free selection; no claim that integration permissions passed. |
| `node design/gates/contrast.mjs` | 54 pairs, 0 failures | Static pairs; does not prove all rendered contrast. |
| `node design/gates/surfaces.mjs` | 45 screen entries, 0 over budget; sheet/flattening checks passed | Existing surface-count rule, not the proposed chrome-only allowlist. |

Logs for the first two checks: `/tmp/nadi-2-plan-node.log` and
`/tmp/nadi-2-plan-python.log` (temporary local evidence).

## 2. Corrections to the older contract

1. **Separate permission to read, decide, withdraw and cancel.** “Routed to me”
   must never imply all four. The latest progress record leaves the approved-row
   cancellation policy unresolved for leave, expense and shift requests. Until
   resolved, display only actions the current server permits and describe them
   accurately. Do not promise “approved requests can never be cancelled.”
2. **Keep status, decision and payment separate.** “Unpaid” does not prove
   “awaiting payroll”; approval does not prove payment. Show payment timing only
   from an authoritative source. Unknown timing gets explicit unknown copy.
   Withdrawn and administratively cancelled need distinguishable semantics.
3. **Do not manufacture history.** A current approver is not evidence of who
   decided an old request. Establish persisted actor/time/outcome sources per
   type before implementing “Decided by you.” Missing old events remain unknown.
4. **Reconcile the layout rules.** The surface map proposes 32px chips and 40px
   approval buttons while the amendment requires 44px targets. Visual controls
   may be smaller only with non-overlapping 44px hit areas. Measure in a browser.
   Use the actual viewport, header, keyboard and safe areas; 752px is a reference
   budget, not a universal content height. Never clip content to meet it.
5. **Resolve thumb reach per journey.** A bottom-third CTA is a useful phone
   target, not a reason to place destructive controls out of keyboard reach or
   force every desktop screen into phone geometry. Define Home header actions
   explicitly: the original bell + approvals + avatar conflicts with “one right
   action.” Keep a reachable Approvals entry in Home content as well.
6. **Make Glass rules internally consistent.** Keep Glass as requested. Choose
   the exact allowed selectors in the mockup contract; existing documents say
   six and seven surfaces. Text on chrome needs a stable contrast backing so
   “glass chrome” does not contradict “no text over a blurred backdrop.” Do not
   apply blur to every permitted surface merely because it is permitted.
7. **Extend the existing components as each journey needs them.** Avoid making
   all 22 primitives a prerequisite. Shared request rows need type-specific
   metadata and actions; punch rows and shift assignments are not requests.
   Preserve expandable details and multi-line expenses at launch.
8. **Test behaviour at the boundary.** AST/grep guards supplement, but cannot
   prove, correct scope, totals, accessibility or navigation. Pair them with
   real assertion tests and seeded-site persona journeys. Do not use a Node
   source-text test to certify a component's rendered height.
9. **Move accessibility throughout delivery.** Keyboard operation, focus return,
   readable errors, text enlargement, reduced motion and narrow reflow belong
   in each slice's acceptance checks, not a last-phase polish queue. Existing
   accessibility baselines must not grow to hide regressions.

## 3. Launch boundary and decisions

**Proposed 2.0:** existing six request types, existing remote check-in review,
daily Home, calendar actions, consolidated request discovery, request lifecycle,
unified pending approvals, navigation compatibility and accessible Glass styling.
Existing KPI, roster, SOP, Helpdesk and confidential HR issue features stay reachable.

Added by Nabil: [Home Announcements](NADI_2.0_ANNOUNCEMENTS.md), authored by HR
and targeted to permitted companies/optional departments. This is launch scope,
distinct from the deferred events feature; ANN.0–ANN.3 define its delivery gates.

**Later, separately scoped:** travel; asset requests; certifications; SOP read
tracking; events; reminders; bulk approvals; offline punch queue; roster cover
policy; Helpdesk/Employee Issue migration. No speculative settings or hidden
new-domain scaffolding at launch. Offline messaging is in launch; queued writes
require a separate conflict, retry and server-validation design.

| Decision | Recommendation for scope review | Blocks |
|---|---|---|
| Navigation (old Q1) | Home · Calendar · Requests · KPI · More. Keep the existing KPI name instead of introducing “Score.” Approvals accessible from Home and header, role-aware. | Shell and redirects. |
| Launch boundary (old Q10) | The five journeys above. Preserve existing expense lines and issue systems. | Final acceptance ledger. |
| Material (Q0a / amendment) | Opaque reading surfaces, Glass chrome, prototype flow; review a composite Home + form + approval mockup before global tokens change. Retiring the blob field remains proposed. | Global material changes. |
| Cancellation and already-paid OT | Carry the two open Sep 13 decisions forward. Preserve current policy until Nabil rules; do not silently broaden UI actions or imply paid-period eligibility. | Policy-sensitive copy/actions and any affected release. |
| Verification infrastructure | Approve an isolated fixture site/CI job and a concrete quick-check script proposal before changing CI or repository settings. | Mandatory browser evidence and push readiness. |

No Q2 bulk-approval decision or Q3 issue migration is needed to build the
pending approvals journey. Q4 leave policy, Q5 receipt/travel rules and Q7 cover
rules must not slip into otherwise presentation-only launch slices.

## 4. Ordered delivery slices

Execution detail: [delivery waves and regression controls](NADI_2.0_EXECUTION_WAVES.md)
break these slices into W0–W8, with effort ranges and packet gates. The
[API connection inventory](NADI_2.0_API_CONNECTIONS.md) seeds the frontend/backend
contract ledger. These companions refine delivery; unresolved decisions above
remain unresolved.

Each row is a reviewable result, split further if it crosses the 400-source-line
budget. Dependencies are explicit; a fixed “55 commits” is not an estimate of
effort. Estimate after B0 and the first vertical slice establish actual cost.

| Slice | Depends on | Work and likely touch points | Acceptance evidence |
|---|---|---|---|
| **B0 — reconcile baseline** | Scope review | Route/name/deep-link inventory from `frontend/src/router`; six-type lifecycle matrix from controllers and `approval.py`; capability/persona matrix; fixture data and current rendered measurements. Record what is available for decision history and payment. | Every existing entry has a destination; known failures/skips named; no implied production equivalence. |
| **B1 — establish verification** | B0; explicit CI approval for CI edits | Run existing browser checks against an isolated fixture site. Add missing punch → persisted result, request → reload, approval → reload journeys. Prepare the missing `ci-local.sh --quick` contract. | Required suites execute with nonzero test counts; missing credentials fail required runs; deliberate defect detected; no production writes. |
| **B2 — accessible shell sample** | B0; navigation/material decisions | Retune only components needed for Home, one form and approval detail using existing G* primitives. Resolve hit areas, header actions, stable text backing and bottom actions. | Both themes; 320/390/768/1440 widths; keyboard/focus; text enlargement; reduced motion/transparency; safe-area and soft-keyboard checks. Review mockups before global application. |
| **B3 — first lifecycle: leave** | B0, B2; B1 for completion proof | Pre-submit summary → server-confirmed success → detail and history → allowed withdrawal. Reuse `FormView`, summary configuration and current controllers. Preserve multi-day/half-day validation. | Submit once under repeat taps; failure preserves input; reload matches server; rejected is read-only; consequence copy uses server results, not an invented balance calculation. |
| **B4 — remaining request types** | B3 | Apply the proven lifecycle to expense, shift, correction, OT and RL; consolidate All requests with type/status filters, pagination and own-history access. | Per-type decision/status matrix, files and multi-line expense intact, no missing/duplicate rows across pages, no staff access to someone else's history. |
| **B5 — unified pending approvals** | B0, B2; reuse B3/B4 detail where ready | Paginated queue plus count derived from the same eligibility rules. Show request age and authorised context. Keep remote check-ins' specialised decision flow. Use current decision endpoint with reviewed revision. | Named approver without reports works; unauthorised and cross-company cases refused; self-decision follows existing per-type HR settings; concurrent/repeated decisions safe; stale review refreshes; row remains pending during request; badge agrees with queue. “Decided by me” only where persisted evidence supports it. |
| **B6 — Home and navigation** | B2, B4, B5 | Compose Needs you (3 + more), own recent requests (2 + more), shift/check-in state. Remove duplicate quick links after every destination is reachable. Add Requests/KPI tabs per decision. | Old URLs including notification links preserve document and query; direct load/reload/back and Ionic tab stacks work; capped lists retain a route to all work; Home approvals do not disappear behind a badge. |
| **B7 — calendar and check-in loop** | B0, B2, B4 | Contextual day sheet with prefilled existing forms; authoritative eligibility; grouped punch history and recoverable missing-punch state; offline explanation and pending punch state. | Overnight shifts, missing OUT, pending/rejected remote check-in, rest day, public holiday, half-day leave and filing boundary fixtures; failed network/retry cannot duplicate a punch. |
| **B8 — release candidate** | B1–B7; explicit release authorisation later | Full persona/state and both-theme sweep; review final route ledger and notification destinations; evaluate PWA update/cache behaviour; review cumulative branch release changes separately. | Required checks actually executed and green; no Critical/Important correctness issues; documented schema/data effects and rollback; admin deployment followed by approved verification. |

Dependencies form B0 → B1/B2 → B3 → B4; B5 can follow the approved detail
contract, then B6 uses both B4 and B5. B7 uses B4. B8 closes the whole scope.
This keeps Home from depending on a nonexistent queue and avoids redesigning
all forms before proving one complete lifecycle.

## 5. Acceptance matrix to fill at B0

For each of Leave, Expense, Shift Request, Attendance Request, OT Request and
Replacement Leave Claim, record: source endpoint, own/team scope, draft editing,
submit transition, approval/rejection field, workflow override, cancellation,
withdrawal effect, list/detail route, notification route, history source and
empty/error/offline/loading/permission/pending states. Add remote check-in as a
separate approval family rather than forcing it through a request controller.

Personas: ordinary employee, named approver without direct reports, manager,
company-fenced HR, HR without an Employee record, CEO, unauthorised/guest user,
and ambiguous or inactive employee identity. Include a second company with
overlapping dates and request types. KPI's existing group-level exceptions
are explicit fixtures, not accidental exceptions to a new blanket scope gate.

For queues, specify a stable order and cursor, a maximum page size, source
doctype + identifier as identity, aggregate count semantics and partial-failure
behaviour. Cap Home presentation without truncating the source queue. Do not
fetch all requests or perform unbounded per-row permission queries. Record
query counts and compare with the existing baseline on the same fixture size.

For notifications and PWA navigation, test an old document URL, a legacy tab
URL, an unknown/forbidden document, an app update with an old cached chunk, and
logout/login as another persona. Personal caches must not carry another user's
queue, request data or KPI access into the new session.

## 6. Release boundaries carried forward

- **Script Report work is expressly deferred.** Do not reopen its role patch,
  global report guard, per-report scoping or probes as part of this plan.
- No push, deployment or historical data repair is authorised by this task.
- The widened OT filing rule also widens the `after_migrate` repair window.
  A source instance may have paid periods absent from the local Salary Slip
  guard. The latest progress entry calls for a dry-run of the newly reachable
  period and a ruling before deployment. This is a release prerequisite,
  not something a visual redesign resolves.
- `scripts/smoke.sh` performs migration. Inspect and approve its site and
  effects before invocation. Prepare read-only post-deployment journey checks
  separately; never label migration as an observation-only smoke test.
- No global permission, schema, dependency, infrastructure or policy change
  is covered by a UI slice. Prepare the exact change and obtain approval first.
- Release the tested cumulative branch or an explicitly reviewed selection;
  do not equate the locally recorded upstream, the latest commit and production.
  Frontend rollback must match its API contract; source revert cannot undo a
  historical repair or schema migration.

## 7. Planning review and next action

Critical [class: requirements]: none identified in this documentation proposal.
Important [class: readiness]: rendered/live evidence remains unmeasured, the
quick-check script is missing, and cancellation/paid-period release questions
remain open. These prevent calling the application release-ready.
Minor [class: documentation]: old planning files retain contradictory scope,
surface counts and policy assumptions; amend them after this proposal is accepted.
This is the author's planning review, not a fresh-context release code review.

Fresh-context documentation review: no Critical, Important or Minor corrections
required. Key code claims, deferred boundaries, test logs, document links and
whitespace were checked. `NEXT_ACTION: DEPLOY` is the working agreement's passing
review verdict only; it grants no deployment permission and does not remove the
application readiness prerequisites above.

Next action: review the five decision rows in section 3, then execute B0 against
an isolated fixture site. No implementation is needed to decide the launch
boundary. Preserve the existing fixes and choose the first complete journey
before funding the later feature domains.

LEARNING(fact): the current smoke script migrates the site, and migration invokes
the widened OT repair; a frontend release plan must account for that backend effect.
