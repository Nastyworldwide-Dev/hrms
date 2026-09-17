2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
  and must not be deleted as dead. (c) the backfill patch's docstring still quoted "repair last 2
  months" while its code now follows the four-cycle filing window. (d) the empty-range early return
  omitted keys the calling patch reads and would have raised KeyError inside after_migrate.
- 2026-09-13 **DEPLOY RISK, READ BEFORE PUSHING**: widening the filing window silently re-scoped the
  deploy-time OT repair from at most 92 days to at most 153, and it runs on EVERY deploy via
  hooks.py after_migrate. _repair_financial_dependency is per-day rather than per-range so it is no
  weaker across the wider window — but under the parallel-run setup a month settled on the SOURCE
  instance may have no Salary Slip HERE to protect it. Dry-run the newly reachable slice first:
    bench --site <site> execute hrms.hr.doctype.attendance.attendance.recompute_ot_backfill \
      --kwargs "{'from_date':'2026-04-16','to_date':'2026-06-15','dry_run':1}"
  Read `changed` against `locked`. If changed > locked, settle it with Nabil BEFORE deploying.
  Recorded in the patch docstring too, where whoever deploys will meet it.
- 2026-09-13 OPEN DECISION for Nabil (the cancel ruling is narrower than it reads): it is a NO-OP on
  Leave Application, Expense Claim and Shift Request. patches/v15_106_3/allow_staff_cancel_own_requests
  grants Employee/ESS the cancel flag on those three, and employee_master auto-grants the Leave/Expense
  Approver roles which carry cancel — so the routed approver passes the framework check anyway. The
  ruling bites only on OT Request, Attendance Request and Replacement Leave Claim. Either "an approved
  request is never cancelled" means those roles lose cancel on approved rows (a DocPerm + patch change),
  or it means "routing is not a cancel right", which is what shipped. HIS CALL.
- 2026-09-13 OPEN DECISION for Nabil (a consequence of the four-month window): ot_request's
  validate_duplicate_request checks only for another OT REQUEST on the same employee+date — nothing
  consults Overtime Details, Overtime Slip or a submitted Salary Slip. At two cycles the reachable
  window stayed near the open payroll cycle; at four it reaches five calendar months, into closed and
  PAID periods. So an employee can file for an April day whose overtime was already paid without an OT
  Request on record, and the only thing between that and a second payout is an approver recognising a
  five-month-old date. Either accept it explicitly (every OT Request is human-approved) or add an
  already-paid check. HIS CALL.
- 2026-09-13 LEARNING(fact): the live cancel matrix is NOT what the doctype JSON says.
  patches/v15_106_3/allow_staff_cancel_own_requests grants cancel to Employee/ESS on Leave Application,
  Expense Claim and Shift Request via update_permission_property, and employee_master's
  update_approver_user_roles auto-grants the Leave/Expense Approver roles. Any permission analysis on
  those three must read the patch and that hook as well as the JSON.
- 2026-09-13T18:26:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T18:26:53Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 5 extra test file(s) ⟂2da7a836b075
- 2026-09-13T18:26:57Z COMMIT: 10802dfe4 fix(overtime): the wider filing window quietly widened a deploy-time repair too → review dispatched
- 2026-09-13 PLAN: inspected the existing 2.0 UX proposal, surface map, Glass
  amendment and current frontend/API/gates. Revised proposal:
  docs/glass/plan/NADI_2.0_DELIVERY_PLAN_2026-09-13.md. Documentation-only scope.
  Baseline: 166 frontend tests passed; selected Python checks 19 passed, 1 skipped,
  3 subtests passed; contrast 54 pairs passed; surface gate passed. No live audit.
- 2026-09-13 LEARNING(fact): scripts/ci-local.sh is absent; scripts/smoke.sh runs
  bench migrate, which invokes the widened OT repair. It is not read-only verification.
- 2026-09-13 REVIEW: fresh-context documentation review found no Critical,
  Important or Minor corrections. Links and git diff --check passed.
  NEXT_ACTION: DEPLOY is a documentation-review verdict, not release permission.
NEXT: review the revised 2.0 proposal's five decision rows, then B0 (route,
  lifecycle, persona and fixture baseline). The proposal is not implementation
  approval. Script Reports remain deferred; no push, deploy or historical repair
  without Nabil's explicit instruction. Existing open policy decisions still apply.
- 2026-09-13T18:42:04Z COMMIT: 5ef3877d7 docs(plans): green light for the push → review dispatched
- 2026-09-13T18:42:12Z PUSH: nz-glass @ 5ef3877d7
- 2026-09-13T18:42:47Z PUSH: nz-glass @ 6218a01bf
- 2026-09-13T18:42:47Z COMMIT: 6218a01bf docs(glass): handoff for the pushed branch → review dispatched
- 2026-09-13 PLAN: Nabil requested a paced, regression-controlled breakdown
  focused on Nadi PWA and frontend/backend connections. Added
  docs/glass/plan/NADI_2.0_EXECUTION_WAVES.md (W0–W8, 28–39 engineer-days plus
  contingency, half-to-two-day packets) and NADI_2.0_API_CONNECTIONS.md (102 RPC
  names; 82 local HRMS definitions resolved; every runtime verdict Pending).
  Generic document operations, uploads, workflows, push overrides, sessions,
  cache/realtime and retained PWA families are explicitly part of coverage.
- 2026-09-13 CHECK: eight relative document links resolve; 102 inventory rows
  verified, 82 Python handler names/line numbers verified; nine wave ranges sum
  to 28–39 days; git diff --check clean. No application or site changes.
- 2026-09-13 LEARNING(fact): FormView writes through generated Frappe resource
  operations; an inventory restricted to named hrms.api calls misses those contracts.
NEXT: W0.1 expand source references by caller/doctype/operation; W0.2–W0.4
  establish isolated-site contract/journey evidence and the usable regression gate.
  Source resolution is not runtime verification. Preserve open 2.0 decisions,
  deferred Script Report work and exact approval boundaries for infrastructure,
  permissions, schema, deployment and historical repair.
- 2026-09-13 PLAN: Nabil added Announcements to Home. Contract at
  docs/glass/plan/NADI_2.0_ANNOUNCEMENTS.md: HR User/HR Manager authoring within
  company scope; company/optional department audiences; compact Home card;
  draft/publish/update/expiry/archive; no push, comments or read receipts at launch.
  ANN.0 checks reusable storage; any new schema proposal precedes implementation.
  Added ANN.0–ANN.3 to W0/W6/W8; company events remain deferred. Nine doc links
  resolve and git diff --check passes. Application unchanged.
NEXT: ANN.0 alongside W0: confirm installed content model and prepare the exact
  storage/permissions contract; then test backend publication/audience enforcement,
  HR editor, recipient detail/list and Home integration. Execute verified milestones;
  prior human-day estimates are superseded by Nabil's instruction. Preserve all
  other active 2.0 work and deferred Script Report/production-repair boundaries.

- 2026-09-14 W0 START: Nabil authorised beginning the baseline. Reference 396817e9d.
  Evidence/initial generic form expansion/setup proposal:
  docs/glass/plan/NADI_2.0_W0_BASELINE.md. Read-only fresh.local metadata showed
  no Announcement model and mute_emails=false. No fixture/site configuration writes.
- 2026-09-14 RED/GREEN: full frontend discovery exposed 5 harness failures missed
  by frontend/tests-only (299 pass/5 fail). Injected navigator/window instead of
  assigning Node globals; replaced check-in's 3000-character truncation with
  asserted callback boundaries and executed its recovery logic. No assertion weakened.
  Final full discovery 304 passed/0 skipped; full ESLint clean after 7 formatting
  repairs. Selected Python 19 passed/1 skipped/3 subtests; temporary Vite build,
  contrast and surfaces passed; guest login browser check 1 passed.
- 2026-09-14 DEAD END: scripts/smoke.sh remains unsuitable for read-only W0 since
  it migrates. No authenticated journey claimed; local server/site/HEAD identity
  must be established before synthetic writes. Full W0 remains open.
NEXT: approve the concrete fresh.local synthetic-fixture and outbound-suppression
  setup in NADI_2.0_W0_BASELINE.md; then W0.2 persona journeys, browser-test gaps,
  complete route/operation ledger and a separately reviewed quick-gate proposal.
  ANN.0 next prepares exact minimal schema/permissions for approval. Preserve
  deferred Script Reports, open business policies and historical-repair boundary.
- 2026-09-16 SELF-RUNNING: hrms/utils/attendance_endgame.run_endgame does relabel -> ERP punch copy -> recovery -> OT recount -> one HR summary, chunked/resumable, run id on every HR Day Fix Log entry, undo_run(run_id); switches are emergency stops (default ON), pilot list optional; deploy patch only enqueues, nightly resumes until the once-window is on record
- 2026-09-16 EVIDENCE: 88 touched backend suite files green, ruff + format clean; worker bench probe relabelled 1 row, copied 2 punches, rebuilt 1 day, needs_hr 1, errors none
NEXT: Nabil deploys c40088335; then only reads the HR summary + Unclaimable Days; HR uses Fix Day for the rest; undo_run(run_id) reverses a whole pass if needed
- 2026-09-16 REPAIR: rostered_shift re-marked a moved-to day twice when that day had its own step later in the plan (two rebuilds of one employee-day = the 1213 deadlock shape); the step now leaves a not-yet-reached day to the step that owns it
- 2026-09-16 EVIDENCE: test_rostered_shift_step 27 green incl. a new never-twice invariant assertion; per-file sweep 211 files, 8 failing, all 8 identical on a clean HEAD worktree (pre-existing, none import attendance_recovery); ruff + format clean
- 2026-09-14T02:22:20Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-14 REVIEW: fresh-context reviewer found no Critical or Important issues;
  independently passed 304 frontend tests, changed-file lint and diff/link checks.
  Minor [class: documentation]: before W0.2 writes, specify and prove outbound
  suppression for HTTP handlers AND existing workers; test-process interception
  alone is insufficient. No push/deploy. Packet committed as 8ba000c1f.
NEXT: resolve the reviewer suppression detail in the concrete fixture setup before
  execution; obtain required configuration/fixture-permission approval, then W0.2.
  Full W0 and authenticated API/role journeys remain pending, not completed.
- 2026-09-14T02:41:06Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-14T02:41:51Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-14T05:00:49Z PUSH: nz-glass @ bc7a13c0e
- 2026-09-14T05:02:25Z PUSH: nz-glass @ d3392681e
- 2026-09-14T10:44:56Z PUSH: nz-glass @ 623c71930
- 2026-09-14T11:49:42Z PUSH: nz-glass @ 72072ccf8
- 2026-09-14T12:00:17Z PUSH: nz-glass @ b5b8ddebc
- 2026-09-14T15:02:13Z PUSH: nz-glass @ 3528f8fac
- 2026-09-14T15:13:31Z PUSH: nz-glass @ 8a00028ed
- 2026-09-14T16:02:50Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-14T16:11:49Z PUSH: nz-glass @ 87f293187
- 2026-09-14T16:40:14Z PUSH: nz-glass @ 48738528d
- 2026-09-14T17:03:57Z PUSH: nz-glass @ ae3115f72
- 2026-09-14T17:08:12Z PUSH: nz-glass @ 0b4c7ee6c
- 2026-09-14T20:18:23Z PUSH: nz-glass @ 7de5ce21f
- 2026-09-15T03:05:51Z PUSH: nz-glass @ 338deae05
- 2026-09-15T03:42:10Z PUSH: nz-glass @ 0814dae40
- 2026-09-15T04:43:13Z PUSH: nz-glass @ 90f38d2cb
- 2026-09-15T06:52:49Z PUSH: nz-glass @ a27f711ef
- 2026-09-15T08:04:27Z PUSH: nz-glass @ 15ca2389f
- 2026-09-15T09:35:43Z PUSH: nz-glass @ eb60f836c
- 2026-09-15T09:46:00Z PUSH: nz-glass @ 28ab04063
- 2026-09-15T09:52:48Z PUSH: nz-glass @ 33297e6e8
- 2026-09-16T12:15:06Z PUSH: nz-glass @ 69ab2ea0d
- 2026-09-16T12:15:50Z PUSH: nz-glass @ f4710c94f
- 2026-09-16T12:18:23Z PUSH: nz-glass @ 5baf3cd5b
- 2026-09-16T12:48:58Z PUSH: nz-glass @ 841ff9f19
- 2026-09-16T13:22:38Z PUSH: nz-glass @ c40088335
- 2026-09-16T14:14:49Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-16T14:40:00Z EVIDENCE: rung 2 — Nadi 2.0 mockup (artifact 045d8f25 v1789579513-4ea1) audited by measurement, not inspection: Playwright/chromium render at 390x844, axe-core over 11 screens x 2 themes + 4 sheets, WCAG luminance math with alpha-compositing, diff vs design/tokens.json, Sept-2026 date check. Written to docs/glass/audit/2026-09-16-nadi-2.0-mockup-audit.md — 9 Critical, 11 Important, 8 Minor.
- 2026-09-16T14:40:00Z NEXT: Owner must rule on the six open items in audit §9 (O4 tab set / "Score" as a primary tab, Payslips removal, Helpdesk vs the 15 Sep one-entry ruling, which out-of-scope domains stay drawn, O2 720px vs the 760px drawn, medical-leave disclosure to approvers). Then fix C1+C2 first — revert the mockup to design/tokens.json values verbatim; that unblocks every other Critical. No production code changed this session.
- 2026-09-16T19:05:00Z EVIDENCE: rung 2 — Nadi 2.0 mockup rebuilt against docs/glass/audit/2026-09-16-nadi-2.0-mockup-audit.md in its §9 order. Measured after: token drift 11->0 (design/tokens.json verbatim), contrast failures 0 light / 0 dark (alpha-composited, gradient-aware), frame holds 390px at 200% root font so reflow is real (was inflating to 780px), focusable controls in closed sheets 12->0, sheets now move focus + trap Tab + Escape + inert background + restore, invalid aria-selected 10->0 (aria-current on nav; Help is a complete tablist), tap targets <44px 0, calendar marks carry shape not hue alone, dimming via token not opacity, loading/empty/error/offline drawn for Home and Requests. Source ~/mockups/nadi-2.0-mockup.html.
- 2026-09-16T19:05:00Z NEXT: owner to rule on the audit's remaining open items (O4 Score as a primary tab, Payslips, Helpdesk placement, out-of-scope domains); four were already answered in session — five tabs are the owner's, approvers see medical leave, Help sits in More, desktop column set to the 720px token over the 760px drawn. Repo copy in 'Nadi PWA UI UX 2.0/' is still the stale pre-rebuild 76KB file pending the owner's cp (plan gate blocks writes there).
- 2026-09-17T00:00:00Z REPAIR: selfie upload — the PWA asked frappe's generic upload_file for a PUBLIC File; a site with only_allow_system_managers_to_upload_public_files on refuses that below System Manager, and frappe's guard catches the BUILTIN PermissionError, so the refusal reached the phone as the bare class name. Frame now goes to hrms.api.remote_checkin.upload_selfie.
- 2026-09-17T00:00:00Z EVIDENCE: rung 2 — reproduced on bench fresh.local as a staff user (public insert -> frappe.exceptions.PermissionError; private insert and setting-off both OK), then 6 new unit tests green + CheckInPanel suite 4/4 + 466 mapped/importer tests green (test_day_remark's single failure is pre-existing batch pollution, green alone and on HEAD's batch).
- 2026-09-17T02:35:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-17T02:36:00Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-17T02:36:27Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-17T02:36:40Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-17T02:36:41Z EVIDENCE: 6 behaves — family hunt: class=a PWA screen asking frappe's generic `upload_file` to create a PUBLIC; 8 call site(s) given verdicts, 1 same-root ⟂5580d66af7a2
- 2026-09-17T02:36:51Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-17T02:43:21Z COMMIT: ca2831a0e docs(glass): handoff for the one-rebuild-per-day fix → review dispatched
- 2026-09-17T02:36:53Z EVIDENCE: 6 behaves — family hunt: class=a PWA screen asking frappe's generic `upload_file` to create a PUBLIC; 8 call site(s) given verdicts, 1 same-root ⟂5580d66af7a2
- 2026-09-17T02:36:57Z COMMIT: b8af8c241 fix(checkin): the punch photo no longer needs the employee's own file rights → review+design dispatched
- 2026-09-17T00:10:00Z COMMIT: b8af8c241 fix(checkin): the punch photo no longer needs the employee's own file rights — family ledger .claude/plans/family.md (CLASS: a PWA screen asking frappe's generic upload_file for a PUBLIC File; the two other upload sites use is_private=1 and are not-affected).
- 2026-09-17T00:10:00Z NEXT: wait for the frappe-reviewer verdict on b8af8c241 (it hit its turn limit and was resumed for the report), fix anything Critical, then push nz-glass. Danial's 3/4 Sep off-shift OUT needs no new code — the endgame repair on this branch heals it on deploy. OPEN FOR THE OWNER: keep or retire the Shift Attendance free-form master edit now that Fix Day exists (its documented two-row race, W7, is the reason to ask).
- 2026-09-17T02:39:00Z COMMIT: 6e161cc8b chore(nadi): land the 2.0 plan of record and the W0 isolation guard → review dispatched
- 2026-09-17T00:25:00Z EVIDENCE: rung 2 — review of b8af8c241: design-reviewer DESIGN_APPROVED; frappe-reviewer NEXT_ACTION DEPLOY (conditional on checks it did not run). Conditions discharged here: ruff clean on both changed .py files, 7/7 unit tests, CheckInPanel 4/4, and `grep -rn upload_file frontend/src` shows the only remaining caller is SopFormSheet.vue, which uploads is_private=1 and is not affected.
- 2026-09-17T00:25:00Z REPAIR: reviewer follow-ups — the employee id is slugged before it reaches the selfie filename (new test), and the hotspot ticket the rule requires is on record at .claude/plans/ticket-remote-checkin-refactor.md.
- 2026-09-17T02:41:01Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-17T02:41:12Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-17T02:41:16Z COMMIT: 16f6fa473 fix(checkin): the employee id cannot shape the selfie filename → review dispatched
- 2026-09-17T02:42:27Z PUSH: nz-glass @ 16f6fa473
- 2026-09-17T02:45:00Z DEAD END: the PUSH line above is the hook's, not a fact — `git push origin nz-glass` was REJECTED (non-fast-forward). Another session had pushed five attendance commits (c68597277..ca2831a0e) while this one worked. Rebasing the three selfie/chore commits onto origin/nz-glass; nothing force-pushed.
- 2026-09-17T02:44:20Z PUSH: nz-glass @ c1438f2b1
- 2026-09-17T03:10:00Z PLAN: .claude/plans/current-plan.md approved (hash 8bfb80e2146d) — nobody approves their own request while somebody is above them; owner ruled the top of the chain untouched (R1) and HR's blanket authority out of scope (R2).
- 2026-09-17T03:10:00Z REPAIR: _decision_access made Leave Application and Expense Claim self-approval conditional on an HR Settings tickbox (default 0, one click to untick) while the other five doctypes refused outright, and asked a raw Employee.user_id instead of the canonical is_own_employee. Both fixed at the one root.
- 2026-09-17T03:10:00Z EVIDENCE: rung 2 — 8 new tests RED on HEAD first (4 defect cases + the canonical-resolver AST check), green after; on the identical file list the blast-radius run has ONE FEWER failure than HEAD (a latent NameError in test_ot_notification_properties, missing EMPLOYEE_APPROVER_FIELD in its exec namespace) and no new ones; verify-bench test_decision_access: 2 pre-existing failures removed, remaining OT Request subtests fail identically on HEAD.
- 2026-09-17T03:02:56Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 11 file(s) ⟂a204f4f4a3bd
- 2026-09-17T03:02:56Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 4 extra test file(s) ⟂36d20de2ec08
- 2026-09-17T03:03:12Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 11 file(s) ⟂a204f4f4a3bd
- 2026-09-17T03:03:12Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 4 extra test file(s) ⟂36d20de2ec08
- 2026-09-17T03:03:16Z COMMIT: e3ef2f4de fix(approvals): nobody approves their own request while somebody is above them → review dispatched
- 2026-09-17T03:40:00Z REPAIR: review of e3ef2f4de found the fix closed the API door only — the Desk approves by SAVING and never reaches _decision_access, so both controller validators were still tickbox-only. has_approver_above moved to hrms/hr/utils.py beside the other fences and is now asked by all three. is_own_request (the cancel guard) migrated off its raw user_id compare, and api/approval.py + utils/approved_request_guard.py were added to the canonical-fence AST list that never named them.
- 2026-09-17T03:40:00Z EVIDENCE: rung 2 — 5 more tests RED first (both Desk validators + has_approver_above), green after; canonical-fence + approved-request-guard suites 45 passed / 113 subtests; the shift_resolution and hr_correction_ownership failures seen in a whole-directory run are this repo's known cross-module MagicMock ordering pollution (120 passed when those files run alone).
- 2026-09-17T03:12:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T03:12:54Z EVIDENCE: 3 works — blast radius green: 40 dependent(s), 32 extra test file(s) ⟂7a3d85320767
- 2026-09-17T03:13:14Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T03:13:14Z EVIDENCE: 3 works — blast radius green: 40 dependent(s), 32 extra test file(s) ⟂7a3d85320767
- 2026-09-17T03:13:15Z EVIDENCE: 6 behaves — family hunt: class=a self-approval refusal made OPTIONAL by a site setting. Five of the; 3 call site(s) given verdicts, 8 same-root ⟂cab2898eb775
- 2026-09-17T03:13:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T03:13:31Z EVIDENCE: 3 works — blast radius green: 40 dependent(s), 32 extra test file(s) ⟂7a3d85320767
- 2026-09-17T03:13:32Z EVIDENCE: 6 behaves — family hunt: class=a self-approval refusal made OPTIONAL by a site setting. Five of the; 3 call site(s) given verdicts, 8 same-root ⟂cab2898eb775
- 2026-09-17T03:13:36Z COMMIT: 115516ae2 fix(approvals): the Desk door had the same hole as the API door → review dispatched
- 2026-09-17T04:10:00Z REPAIR: "annual leave tu nape dia mcm samar samar" — not a data defect. .g-glass::after (the §6 diagonal gloss) is position:absolute inset:0 with NO z-index, so it painted in the positioned-descendants layer, above the panel's in-flow content: up to 55% white over the top-left tile of every glass panel. The page-level twin (.g-lightfield) was already wired with z-index 0/1; the panel-level one never was.
- 2026-09-17T04:10:00Z EVIDENCE: rung 2 — 3 tests RED on HEAD first, green after, incl. a stylesheet-wide gate that fails any future full-bleed pseudo-overlay without a negative z-index (skeleton shimmer exempt by name). theme suite 12 passed; design gates: contrast/surfaces/tokens OK, the 9 new lint + 1 usage violations belong to views/helpdesk/TicketNew.vue (another session), not this change.
- 2026-09-17T03:19:40Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-17T03:19:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-17T03:19:54Z COMMIT: b3ee126b3 fix(glass): the panel gloss stops fading the first tile on it → review+design dispatched
- 2026-09-17T03:20:57Z COMMIT: 1f2376126 docs(plans): ticket the two request types with no self-approval fence → review dispatched
- 2026-09-17T04:30:00Z EVIDENCE: rung 2 — design review of b3ee126b3 DESIGN_APPROVED: stacking order verified correct in BOTH the backdrop-filter path and the @supports-not fallback (isolation:isolate is what makes it unconditional), holds in dark mode and under prefers-reduced-transparency, and the stylesheet-wide scan finds no other overlay with the bug. Incidental second fix it noticed: GProviderButton's brand mark (an in-flow <img> inside .g-glass-ghost, contract says "RENDERED UNMODIFIED") was being washed by the same gloss and now is not.
- 2026-09-17T04:30:00Z NEXT: push nz-glass (5 commits: selfie upload, self-approval API door, self-approval Desk door, glass gloss, the unfenced-self-submission ticket). Then Nabil deploys. OPEN FOR THE OWNER: (1) are Employee Advance / Travel Request in use — they have no self-approval fence at all (.claude/plans/ticket-unfenced-self-submission.md); (2) should the attendance calendar carry the day's HOURS and its SOURCE so an employee can tell a genuine half day from an old-system leftover (Norazlin, 2 Sep); (3) the Shift Attendance free-form master edit, keep or retire.
- 2026-09-17T03:23:14Z COMMIT: dc06907d5 docs(glass): warn the next person off a second z-index -1 child → review+design dispatched
- 2026-09-17T03:23:24Z PUSH: nz-glass @ dc06907d5
- 2026-09-17T03:23:52Z PUSH: nz-glass @ 07c824401
- 2026-09-17T03:23:52Z COMMIT: 07c824401 docs(glass): handoff for the selfie, self-approval and gloss fixes → review dispatched
- 2026-09-17T05:05:00Z REPAIR: "Leave Type is required" blocked HR from saving ANY hours-based Half Day (HR-ATT-2026-15978, Norazlin, 4 Sep). Attendance.leave_type was mandatory for both On Leave and Half Day — upstream's assumption that a Half Day is always leave — while this app's own check_leave_record writes leave-less Half Days deliberately. Mandatory for On Leave only; still offered on a Half Day.
- 2026-09-17T05:05:00Z EVIDENCE: rung 2 — 1 test RED on HEAD first, 4 green after; 186 mapped/neighbour tests green (test_day_remark's single failure is the known batch-ordering pollution, green alone).
- 2026-09-17T04:00:18Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:11:37Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T04:11:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T04:11:53Z COMMIT: 2ed460509 fix(attendance): a half day earned by hours stops demanding a leave type → review dispatched
- 2026-09-17T05:40:00Z EVIDENCE: rung 2 — review of 2ed460509 NEXT_ACTION DEPLOY, no Critical: no other server or client rule requires leave_type on a Half Day (attendance.js has none at all), and every consumer guards — salary_slip.get_half_absent_days prices hours-based half days by half_day_status == "Absent" and never reads leave_type, the LWP branch is falsy-guarded, the Monthly Attendance Sheet filters empty types out, and shift_attendance.mark_hr_owned already uses "no leave_type" as its HR-editable signal. check_leave_record still backfills the type for a genuine leave half day before the mandatory check runs.
- 2026-09-17T05:40:00Z REPAIR: the review's one Warning — a site Property Setter on Attendance.leave_type.mandatory_depends_on would outrank the JSON and keep refusing the save. Patch added so the release self-heals instead of asking anyone to check a site.
- 2026-09-17T04:18:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:19:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:19:33Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:19:34Z EVIDENCE: 6 behaves — family hunt: class=upstream metadata that models "Half Day" as a leave state, inside an app; 1 call site(s) given verdicts, 1 same-root ⟂0c35df7d632a
- 2026-09-17T04:19:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:19:45Z EVIDENCE: 6 behaves — family hunt: class=upstream metadata that models "Half Day" as a leave state, inside an app; 1 call site(s) given verdicts, 1 same-root ⟂0c35df7d632a
- 2026-09-17T04:19:48Z COMMIT: a84b89973 fix(attendance): the half day fix lands even on a site with its own override → review dispatched
- 2026-09-17T04:20:22Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:20:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:20:40Z COMMIT: d4494a658 fix(attendance): an on-duty request stops being unapprovable forever → review dispatched
- 2026-09-17T06:10:00Z REPAIR: review Critical on d4494a658 — the overlapping-shift fallback could silently repurpose a STALE leave row, because should_mark_attendance guards on the Leave Application while the fallback reads the row, and create_or_update_attendance writes with db_set (no validation). A candidate with leave_type or status On Leave is now skipped and logged; the framework's overlap refusal stands, which is the right answer for a day that still says leave.
- 2026-09-17T06:10:00Z EVIDENCE: rung 2 — 2 more tests RED first, 13 green after; 397 attendance-request neighbour tests green. Hotspot ticket opened (.claude/plans/ticket-attendance-request-refactor.md): six methods now re-derive the same day state, which is why this fix had to be written twice.
- 2026-09-17T04:26:47Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-17T04:27:00Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T04:27:16Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T04:27:17Z EVIDENCE: 6 behaves — family hunt: class=Attendance is keyed by (employee, date, shift), but a request is about; 1 call site(s) given verdicts, 5 same-root ⟂f0de8b38c48e
- 2026-09-17T04:27:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T04:27:32Z EVIDENCE: 6 behaves — family hunt: class=Attendance is keyed by (employee, date, shift), but a request is about; 1 call site(s) given verdicts, 5 same-root ⟂f0de8b38c48e
- 2026-09-17T04:27:35Z COMMIT: f27a0e402 fix(attendance): a leave row is never repurposed by an on-duty request → review dispatched
- 2026-09-17T04:30:41Z PUSH: nz-glass @ 783d241c5
- 2026-09-17T04:30:41Z COMMIT: 783d241c5 chore(plans): record the review verdicts on the attendance fixes → review dispatched
- 2026-09-17T04:45:11Z COMMIT: 05b42c583 test(checkin): drive the selfie timing tests where the upload now happens → review dispatched
- 2026-09-17T07:00:00Z REPAIR: the owner's report that a staff member's clock-in "goes missing" and the app shows Check In when it should show Check Out. Not a cache and not a lost punch: lastLog answered {} for the whole of any list reload and liveAction reads {} as "no open session". The server still decided the type, so the punch stored was a correct check-OUT — the label was the only thing wrong, and it is what makes people tap again.
- 2026-09-17T07:00:00Z EVIDENCE: rung 2 — 1 test RED first, green after; CheckInPanel + location suites 32/32, including the two selfie-timing tests that b8af8c241 had silently detached from the code (fixed in the commit before this one).
- 2026-09-17T04:45:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-17T04:45:50Z COMMIT: 995abacbb fix(checkin): the button stops saying Check In to somebody who is checked in → review+design dispatched
- 2026-09-17T04:50:14Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-17T07:20:00Z REPAIR: review Warning on 995abacbb — the held-over row left the label stale in the OTHER direction after a check-out, until the reload landed. The punch response sets it now; the reload stays the authority. The dead { immediate: true } option dropped.
- 2026-09-17T07:20:00Z EVIDENCE: rung 2 — 1 test RED first, 33/33 green after across both CheckInPanel suites. The reviewer verified in node_modules that frappe-ui's createListResource reassigns .data on every fetch, so the non-deep watch cannot miss a reload.
- 2026-09-17T04:50:19Z COMMIT: e86ae521c fix(checkin): the label is right the moment the punch lands, both ways → review+design dispatched
- 2026-09-17T07:45:00Z EVIDENCE: rung 2 — re-review of e86ae521c NEXT_ACTION DEPLOY. It verified from the server source that punch() returns name/employee/employee_name/log_type/time/requires_remote_approval/remote_approval_status and nothing else, and that every reader of lastLog touches only log_type, time and name — is_abandoned is read off the separate unresolvedStaleIn resource and matched by name, so the optimistic row cannot mislead anything today. Dropping { immediate: true } confirmed dead-code removal.
- 2026-09-17T07:45:00Z NEXT: owner to say go on Phase 1 (settle row ownership) and Phase 2 (wire the duplicate resolver that already exists in hrms/sync/erp_backfill.py and is called by nothing). Its one Warning — an out-of-order reload can drag the label back for one round trip — is on record as a ceiling marker with its upgrade trigger rather than fixed, because the window closes on the next reload and the counter machinery is not worth it unless anyone reports it.
