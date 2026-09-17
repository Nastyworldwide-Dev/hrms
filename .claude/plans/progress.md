2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
  Then the two rulings: approval.py:413-414 must stop elevating CANCEL on routing alone (an approved
  request is never cancelled), and the filing window widens to four months keeping its 16th-to-15th
  cycle shape.
- 2026-09-13T18:07:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T18:07:05Z COMMIT: bdcb02fcb fix(hr): a manager's team was re-derived here, and the fences drifted → review dispatched
- 2026-09-13 EVIDENCE(2): C4 done. reverse_replacement_leave fetched the Leave Allocation with a bare
  get_doc while running INSIDE A CANCEL, so an allocation that HR had cancelled or that the sync had
  re-pulled under a new name froze the employee's own withdrawal with DoesNotExistError. And a
  CANCELLED allocation is worse than a missing one — decrementing it writes a negative ledger entry
  onto a document no longer in force. Existence and docstatus are both checked now; it returns cleanly
  and records the skip in the Error Log rather than throwing, because the person's cancellation
  succeeded and the allocation's fate is not theirs to fix. Four AST cases (the module cannot be
  imported without a bench — pypika), proven red by restoring the bare get_doc.
NEXT: the two rulings, both from Nabil in this session. (1) "an approved request is never cancelled" —
  hrms/api/approval.py:413-414 elevates CANCEL on routing alone (`elif _is_routed_approver(doc):
  doc.flags.ignore_permissions = True`), with only _request_read_allowed ahead of it, and the guard at
  :400 means the else branch is reachable ONLY on cancel. Close it. (2) the filing window widens to
  four months from the present day while KEEPING its 16th-to-15th cycle shape, and covers OT Request
  and expense-shaped requests alongside it — hrms/utils/filing_window.py currently implements two
  cycles.
- 2026-09-13T18:08:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T18:08:50Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 12 extra test file(s) ⟂ca1c1f300426
- 2026-09-13T18:08:53Z COMMIT: d2f9602b3 fix(hr): withdrawing a request must not freeze on an allocation that moved on → review dispatched
- 2026-09-13 EVIDENCE(2): RULING 1 implemented. "An approved request is never cancelled" — Nabil, this
  session. approval.py::finalize's else branch is reachable ONLY on a cancel (the first branch catches
  every submit of a decide-then-submit doctype, and every request doctype is in that set), and it
  elevated on ROUTING alone with only _request_read_allowed ahead of it — so a settled approval could
  be withdrawn with the framework's own cancel right bypassed. The elevation is gone; cancelling needs
  the cancel right. The refusal also names cancellation instead of saying "not routed to you for
  approval", which sent the reader looking for the wrong thing. Three AST cases, including one pinning
  that `decide` STILL elevates — so a future narrowing of cancellation cannot quietly take approval
  away. Proven red by restoring the elevation.
NEXT: RULING 2 — the filing window widens to FOUR MONTHS from the present day while KEEPING its
  16th-to-15th cycle shape, covering OT Request and expense-shaped requests alongside it.
  hrms/utils/filing_window.py currently implements two cycles. Read it, widen it, and check every
  caller: filing, discovery and validation all consult it and must move together.
- 2026-09-13T18:10:49Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T18:10:49Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-13T18:10:52Z COMMIT: 9fbd5085f fix(approval): being the approver is not permission to undo an approval → review dispatched
- 2026-09-13 EVIDENCE(2): RULING 2 implemented. Backdated OT filing widens from two cycles to FOUR
  (Nabil, this session: "4 month before the current date", and separately "still 16th to 15th" — so the
  cycle shape is untouched and only the depth changes). hrms/utils/filing_window.py BACKDATE_CYCLES
  2 -> 4. Anchoring to the 16th means four cycles back from the CURRENT cycle's start reaches a little
  beyond four calendar months for most of a cycle; that is the anchoring the module was built around,
  not a rounding error, and it errs towards letting somebody file.
- 2026-09-13 EVIDENCE(3): every consumer moves together because they all read the same function —
  filing (ot_request.validate_filing_window), discovery (api/__init__.py:636) and the deploy-time
  backfill (backfill_ot_after_rounding_rule:63) all call earliest_filable_date. Verified by grep; no
  second copy of the rule exists.
- 2026-09-13 SCOPE NOTE on ruling 2: it names "OT request and related requests like expenses". Expense
  Claim enforces NO filing window at all — there is nothing to widen there, and nothing was invented.
  Recorded so the next reader does not go looking for the expense half of this change.
- 2026-09-13 LEARNING(gate): test_ot_filing_edits.py hardcoded CUTOFF as a literal date, so a policy
  change broke a test that was only ever meant to say "an edit gets the same window as a new filing" —
  true whatever the window is. It DERIVES the cutoff from the module now (loaded by path, because
  importing through the package pulls hrms/__init__.py and needs a bench), so the next policy change
  moves the fence and the test keeps asking its own question.
- 2026-09-13T18:13:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T18:13:48Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 2 extra test file(s) ⟂a5801cfef452
- 2026-09-13T18:13:51Z COMMIT: fa8565990 fix(approval): being the approver is not permission to undo an approval → review dispatched
- 2026-09-13T18:14:32Z COMMIT: f2e8dd05f feat(overtime): backdated filing reaches four months instead of two → review dispatched
- 2026-09-13 DEAD END (twice now, same trap): a commit message written with `cat > $GD/MSG` inside a
  command that a PreToolUse gate BLOCKS never runs, so the following `git commit -F` silently reuses
  the PREVIOUS message. 616d6b119 and fa8565990 both landed with the wrong subject and had to be
  amended. ALWAYS write the message file in its own command, then commit in the next.
NEXT: every defect on the ranked plan is CLOSED. What remains is the report project (26 Script Reports
  with no company fence + 4 that read past one), the tickets filed today (C-routing, C-mayread,
  C-roster, C-appraisal, C-ctc, C-1on1, C-fence, the session_state refactor, the two permanently-red
  timezone tests, the spurious-extra-session invariant, KPI route state DSN-16, the provenance Recover
  button), and Nabil's three production questions (is a biometric device in use; is HR Settings
  allow_multiple_shift_assignments on; did the OT precision patches ever run on Verifica). Historical
  data repair still needs his explicit word for that exact change. NOTHING IS PUSHED.
- 2026-09-13T18:15:25Z COMMIT: 7472b03ef docs(plans): every defect on the ranked plan is closed → review dispatched
- 2026-09-13 RULING (Nabil): **THE SCRIPT REPORT PROJECT IS DEFERRED. DO NOT OPEN IT.** That covers all
  three steps proposed today — the role patch stripping Accounts User / Projects User / Manufacturing
  User / Expense Approver / Leave Approver / System Manager off the pay reports, the company guard on
  frappe.desk.query_report.run, and the per-report self-scoping. No commits, no patches, no probes
  against it until he says otherwise, in those words.
  The exposure is recorded and understood: those roles can read gross pay, employer contributions,
  whole-company leave balances and full CTC today, and 26 of 32 Script Reports accept any company typed
  into the filter. It is written down in .claude/plans/audit-2026-09-13-approver.md. Leaving it open is
  HIS CALL, made with the facts in front of him — not an oversight for a later session to "helpfully"
  correct.
  The two policy questions that would gate the work if it resumes: should Accounts see gross pay (they
  may have a legitimate cost-allocation reason), and should a Leave Approver see whole-company balances
  or only their team.
NEXT: nothing is queued. Every defect on the ranked plan is closed and committed; the reports project
  is DEFERRED by ruling; historical data repair still needs Nabil's explicit word for that exact
  change. 50 commits sit unpushed on nz-glass ahead of the live build a741f3e. Do not push, deploy or
  repair anything without him saying so.
- 2026-09-13T18:21:43Z COMMIT: ffcfcc52b docs(plans): the reports project is deferred, by decision not by oversight → review dispatched
- 2026-09-13 REPAIR: acted on the ruling review's four spec warnings. (a) test_ot_discovery_window still
  hardcoded the fence — the exact rot its sibling had just been fixed for — so it DERIVES it now; that
  file's question ("discovery offers exactly what filing accepts, never wider") is policy-independent
  and must not need editing when the policy moves. (b) the comment in approval.py claimed the else is
  "reachable only on a CANCEL": finalize is whitelisted with no doctype allow-list, so a submit of any
  other submittable doctype lands there too, which is why the "not routed to you" refusal is still live
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
