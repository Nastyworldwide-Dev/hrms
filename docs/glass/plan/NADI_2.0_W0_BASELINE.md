# Nadi 2.0 W0 baseline — 14 September 2026

Status: W0 in progress. Nabil authorised beginning W0 on 14 September.
Owner: Codex. Reference application commit: `396817e9dd32b8264bf736a081ebf81c10c04846`.
Companions: [waves](NADI_2.0_EXECUTION_WAVES.md),
[RPC inventory](NADI_2.0_API_CONNECTIONS.md),
[Announcements](NADI_2.0_ANNOUNCEMENTS.md).

## Evidence collected

| Check / command | Result | Limit |
|---|---|---|
| `node --experimental-test-module-mocks --test frontend/tests/*.test.mjs` from root | 166 passed, zero skipped | Excludes colocated tests under src. |
| `node --experimental-test-module-mocks --test` from frontend | Initial: 299 passed, 5 failed, zero skipped | Final rerun: 304 passed, zero failures/skips. |
| `python3 -m pytest -q hrms/tests/test_pwa_resource_states.py hrms/tests/test_ot_filing_edits.py hrms/tests/test_filing_guard_is_filing_only.py hrms/api/test_decision_access.py` | 19 passed, 1 skipped, 3 subtests passed | Stub-based selected suites, not a site journey. |
| `./node_modules/.bin/eslint src --ext .vue,.js` from frontend | Initially 7 formatting errors in two push test files; corrected | Full rerun passed after final edits. |
| `./node_modules/.bin/vite build --base=/assets/hrms/frontend/ --outDir /tmp/nadi-w0-build` from frontend | Passed, including service worker; 152 precache entries | Isolated output; no deployed assets or HTML entry changed. |
| `node design/gates/contrast.mjs` | 54 checks, zero failures/skips | Static colour calculations. |
| `node design/gates/surfaces.mjs` | Passed, 45 screen entries | Static surface count, not visual acceptance. |
| `./node_modules/.bin/playwright test --config=e2e/playwright.config.js --grep 'offers email and password' --output=/tmp/nadi-w0-browser` from frontend | 1 passed | Anonymous login controls only on localhost:8080; not authenticated journeys or proof this server serves HEAD. |
| HTTP GET localhost:8080 `/api/method/ping`, `/hrms/login` | Both 200 | Reachability only. |
| Read-only DB transaction on fresh.local | Connected; installed models/apps queried; rolled back | Metadata only, no business records or identity payloads output. |

Local diagnostic logs: `/tmp/nadi-w0-node.log`, `/tmp/nadi-w0-all-node.log`,
`/tmp/nadi-w0-all-node-green.log`, `/tmp/nadi-w0-lint.log`, `/tmp/nadi-w0-build.log`.
These are temporary diagnostics; this document records durable results.
Initial gate calls from frontend used the wrong relative path and failed to load;
both were rerun from root. Initial bench metadata probe used the wrong working
directory for Frappe logging; rerun from sites succeeded without configuration changes.

## Baseline repairs and findings

| ID | Finding | Action / acceptance |
|---|---|---|
| W0-T1 | Push tests assign to Node 22's getter-only navigator: four failures before behaviour executes. | Inject navigator/window into the existing evaluated helper. Preserve all four destination/no-registration assertions; no global mutation. |
| W0-T2 | Check-in test reads only 3000 characters after submit; current onError falls beyond that limit. | Assert callback start/end boundaries; preserve existing checks and execute actual callback to prove idle state, one camera restart and visible fallback error. |
| W0-T3 | Seven Prettier errors in push tests prevent lint passing. | Formatting only; assertions preserved. |
| W0-J1 | Critical-path leave test visits `/hrms/leaves`; router uses `/hrms/dashboard/leaves`. Forced-failure check stays on Home after login. | Repair browser journeys in W0.2 with fixtures and actual navigation; currently not runtime evidence. |
| W0-J2 | Approval browser test accepts a refusal and skips failed seeding; check-in test stops before punching. | Separate refusal assertions from successful persisted-state journeys; cannot count these as successful approval/punch evidence. |
| W0-J3 | Visual screen resolver drops detail screens when records are absent. | Record resolved/omitted screens explicitly and require fixture-backed coverage. |
| W0-A1 | FormView awaits allSettled uploads but does not inspect rejected results before routing after creation. | Investigate with a failing upload journey before W2 acceptance; ensure retained document identity and retry. Source finding, not a reproduced end-to-end defect. |
| W0-E1 | Required `scripts/ci-local.sh` absent. | Proposed quick gate below; CI boundary requires approval before applying. |

## Generic RPC expansion: initial form contracts

The following are distinct contracts even though they share a component/API name.
All have runtime verdict **Pending**, owner Codex. This is the initial FormView
expansion, not a replacement for the complete 102-name inventory.

| DocType | Frontend form | Verification wave |
|---|---|---|
| Leave Application | `views/leave/Form.vue` | W2 pilot |
| Expense Claim | `views/expense_claim/Form.vue` | W3 |
| Shift Request | `views/attendance/ShiftRequestForm.vue` | W3 |
| Attendance Request | `views/attendance/AttendanceRequestForm.vue` | W4 |
| OT Request | `views/ot/OTRequestForm.vue` | W4 |
| Replacement Leave Claim | `views/ot/ReplacementLeaveClaimForm.vue` | W4 |
| Employee Issue | `views/issues/IssueForm.vue` | W6 retained journey |
| Shift Assignment | `views/attendance/ShiftAssignmentForm.vue` | W6 retained journey |

For EACH row, record separately: metadata/permitted fields; existing document get;
insert; set_value; delete where permitted; attachment list/upload/delete/private
read; decision capability; finalize where supported. Generated Frappe resource
operations resolve in installed `frappe-ui/src/resources/listResource.js` and
`documentResource.js`; declarations alone do not mean the UI enables every operation.
Exercise owner, permitted actor, unrelated employee, foreign-company actor and
guest. Assert server permission, response shape, visible state and persisted state.

Other retained contracts still need individual rows: notification list/read/count,
team roster, generic `/form` consumers, profile/settings, payroll, helpdesk, SOP,
HR contacts, session/identity/cache changes and notification destinations.

## ANN.0 installed-model result

Read-only fresh.local inspection found no DocType matching `%Announcement%`.
Installed candidates: Note, Event, Notification Log, PWA Notification.
Installed apps: frappe, erpnext, payments, hrms, project_board.
Bench HRMS is a symlink to this checkout. Framework source HEADs: Frappe
`6a329d0684`, ERPNext `81a6f97`; these are source identifiers, not schema parity proof.

Note already sanitises content and supports public/owner visibility plus login
notifications. Its permission predicates do not implement company/department
audiences or HR-only publishing. Notification Log/PWA Notification are recipient
notification records, not the planned shared publication lifecycle. Event is a
calendar entity. None is established as a drop-in fit. Prepare a dedicated minimal
schema/permission proposal next; no schema or permission change is approved here.

## Concrete W0.2 setup proposed for approval

Target only `/home/nabil/verify-bench`, site `fresh.local`; no production use.
The read-only query found `allow_tests=true`, `mute_emails=false`.

1. Capture existing values privately; set site `mute_emails=true` before fixture
   writes. Add test-process interception that fails any external email, push,
   webhook or sync attempt; inspect active hooks first. No scheduler/worker starts.
2. Create only namespaced synthetic W0 fixtures: two companies, departments,
   shifts, leave type/allocation, eight synthetic users/personas (employee, named
   approver, manager, scoped HR, HR without Employee, CEO, invalid employee mapping,
   foreign-company employee). Guest uses no account. Use `.invalid` email addresses;
   test credentials stay outside git/logs. Reuse installed role definitions.
3. Scope User Permissions and approver links to these fixture records only.
   Configure one workflow restricted to the fixture company; first confirm the
   installed framework supports that isolation. Otherwise propose a separate site
   before creating a workflow that would affect unrelated records.
4. Seed draft/rejected/cancelled scenarios through supported APIs on synthetic
   records; drive login, leave and permission-denial journeys against local HTTP.
   Record sanitized response shapes and persisted effects. No historical repairs,
   migration, payroll submission or deletion of existing records. Keep a fixture
   manifest for review; cleanup is limited to records this run creates.
5. Before any mutating browser run, prove localhost:8080 resolves fresh.local and
   serves this checkout. Never infer this from a ping or directory name.

Proposed `scripts/ci-local.sh --quick` contract: fail-fast; require dependencies
already installed; run full frontend node discovery with module mocks, full ESLint,
selected backend suites above, static contrast/surface gates, isolated temporary
Vite build and git diff --check. Preserve each command's exit code and test counts;
missing tools or zero selected tests fail. No network installs, migrations, smoke
script, credentials or site writes. Report site journeys separately; quick pass
must never imply full W0 runtime completion. The script remains a separate CI
packet; this turn requests only the fixture setup approval, not approval for an
unwritten script.

W0 exit remains open: isolated fixture setup, authenticated persona journeys,
complete route/operation ledger and usable quick gate. No push or deployment.
