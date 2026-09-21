2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
- 2026-09-21T07:31:45Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-21T07:31:47Z COMMIT: f940ba4d7 perf(attendance): hot-filter indexes, re-asserted on every migrate → review+cross-app dispatched
- 2026-09-21T07:33Z RELEASE 1 COMPLETE: 26 commits 4b9290e24..f940ba4d7; notes docs/glass/release-1-notes.md; every fix verified fresh + reviewed (last two reviews in flight: A5 eba706551..f940ba4d7, cross-app f940ba4d7).
NEXT: owner rules on payroll 'consider unmarked attendance as' and deploys nz-glass (migrate + restart); then Release 2 starts with a built mockup of the Correct form on the Employee Check-in page + plan re-approval.
- 2026-09-21T07:33:19Z COMMIT: 3301237b6 docs(glass): Release 1 notes and handoff → review dispatched
- 2026-09-21T07:34:18Z COMMIT: a0b2e3a77 docs(glass): handoff verify line uses repo paths only → review dispatched
- 2026-09-21T08:01:36Z PLAN: approved afde05ce22e6 — # Plan — attendance made deterministic, three releases (21 Sep 2026)
- 2026-09-21T08:02:34Z COMMIT: 6afcab1c1 docs(glass): request dates, types and approval-state addendum; folded into Release 3 → review dispatched
- 2026-09-21T08:06:33Z PUSH: nz-glass @ 6afcab1c1
- 2026-09-21T08:42:04Z PLAN: approved bd020ba50f4c — # Plan — attendance made deterministic, three releases (21 Sep 2026)
- 2026-09-21T08:42Z R1 PUSHED (6afcab1c1), owner deploying; payroll switch stays as is. R2 started: slice 1 fix_days backend (worker), then Check-in dialog, then remove old buttons. Owner's screenshots: Norazmi 1–4 Sep = punches fixed, rows Absent(HR) 0 h + cancelled night rows + Half Day double tap; 3 Sep IN still night-stamped.
NEXT: integrate fix_days backend (verify fresh), then the dialog on employee_checkin_list.js / fix_day.bundle.js.
- 2026-09-21T09:13:53Z COMMIT: 15701f285 test(attendance): fix_days reads a form's string dry_run correctly → review dispatched
- 2026-09-21T09:14:13Z COMMIT: 15701f285 test(attendance): fix_days reads a form's string dry_run correctly → review dispatched
- 2026-09-21T09:14:27Z COMMIT: 62fc68b67 test(attendance): the string dry_run test counts rebuilds from the fixture's own apply → review dispatched
- 2026-09-21T09:33Z EVIDENCE: 2 correct — TestTheRequestsOnADayAreKept 6/6 red on HEAD (no _paid_day / requests_ok), green with the fix (test_fix_days 34). EVIDENCE: 3 works — 15 mapped+dependent files green one at a time + 22 JS.
- R2 landed: e79030f00 (fix_days backend) 72f6ece10 (dialog; other pages link to punches) 15701f285/62fc68b67 (string dry_run test) e80c18259 (approved requests kept). NEXT: review the last commit, push, owner deploys R2 with R1 or next; then R3.
- 2026-09-21T09:36:16Z PUSH: nz-glass @ e80c18259
- 2026-09-21T09:45:18Z PUSH: nz-glass @ a46f43956
- 2026-09-21T09:45:18Z COMMIT: a46f43956 docs(glass): handoff for Release 2 → review dispatched
- 2026-09-21T10:02:30Z COMPACT: context compacted — read the last NEXT above before continuing
COMMIT: ba8ae8c3e fix(pwa): decided request shows without reload (R3 lane A) — JS 25 pass (TZ=Asia/Kuala_Lumpur), eslint/ruff clean, test_request_publish_update 3 pass
EVIDENCE: 2 correct — lane A tests red on a46f43956 (socket gave up after 5; no reload registry; RL/CL publish absent), green on ba8ae8c3e
NEXT: verify lane B (afed63e) + lane C (af0b9bf) diffs with fresh verifiers, integrate as separate commits, push R3, write HANDOFF
EVIDENCE: 2 correct — lane B new tests red on a46f43956 (verifier: recordable 5F/7P, cancel 6F/3P, no_lie 10F/2P, who_approved ImportError), D1/D5 refutation tests red on the worker's version (2 failed), all green after: 13 files per-file (see runB.sh) 100% pass, ruff clean
EVIDENCE: 2 correct — lane C: requestStatus.test.js + review-sheet-buttons-from-doc red on a46f43956 (no export), child-table case red on the shallow compare (1 failed), green now: 9 JS files 63 pass, npm-test suite 491/494 (3 known: dead-code gate, TDZ gate, approved-cancel needs the npm flag), eslint clean, test_api_clean_errors_and_bounds OK, ruff clean
EVIDENCE: 6 behaves — hook reviews: ba8ae8c3e FIX_CRITICAL (boot.time_zone object) → fixed 75e56c451; f04526cea DEPLOY (0 Critical, 1 Warning = product ruling on a stuck cancel); 527baf268 DEPLOY (0 Critical). Verifier refutations (lane B D1/D5, lane C T2) fixed before landing.
- 2026-09-21T10:15:56Z PUSH: nz-glass @ 306394c5f
- 2026-09-21T10:15:56Z COMMIT: 306394c5f docs(glass): Release 3 notes → review dispatched
- 2026-09-21T10:16:21Z PUSH: nz-glass @ 291a20331
- 2026-09-21T10:16:21Z COMMIT: 291a20331 docs(glass): handoff for Release 3 → review dispatched
PUSH: 291a20331 nz-glass — Release 3 complete (4 fix + 2 docs). Retro: 4 shots; causes oracle-gap (boot shape mock) + 2 verifier-caught before landing.
LEARNING(gate): boot-shape mock -> siteTime.test.js now mocks the real {system,user} object; any new reader of frappe.boot must test against a real bootinfo shape
NEXT: wait for the owner: deploy order R2 → R3; four reminder answers; stuck-cancel override ruling. Then build reminders as the last R3 slice.
PLAN: .claude/plans/fix-attendance-plan.md — one "Fix attendance" button, reuse the Fix day dialog (4 changes), guards G1–G15, slices A/B/C; owner: straightforward, build after R3 deploy
NEXT: owner deploys R2 → R3; then slice A (engine save_day + guards, red tests first)
- 2026-09-21T11:14:48Z PLAN: approved b050f780b9c7 — # Plan — one "Fix attendance" button (21 Sep 2026, final shape)
EVIDENCE: 2 correct — test_attendance_fix_day_save_day.py red on 291a20331 (23F/0P, verifier), green 24 (incl. the two-pairs-one-tap refutation); 8 fix-day suites green per file; ruff clean
EVIDENCE: 2 correct — employee_checkin_list.test.js 28 pass (pre-tick pin red on the wrong key: 8 failed, green on the per-tap key); test_fix_day_screen.py 21 pass after the amended pins; save_day/rebuilds/fix_days suites green; ruff + eslint@8 clean
EVIDENCE: 2 correct — G8 locked-instance test red without the seam (2 failed), green 26/26; JS 28 pass; screen pins 21 pass; ruff/eslint clean
EVIDENCE: 5 looks right — real Desk render on verify-bench test.local (yarn --ignore-engines build, frappe serve in tmux): docs/glass/fix-attendance-dialog.png
- 2026-09-21T11:50:30Z COMMIT: ae09f78bd docs(attendance): save_day docstring names the G8 pre-flight → review dispatched
- 2026-09-21T11:50:48Z PUSH: nz-glass @ 33da0c2d8
- 2026-09-21T11:50:48Z COMMIT: 33da0c2d8 docs(glass): Fix attendance in the Release 3 notes → review dispatched
PUSH: 33da0c2d8+handoff nz-glass — Fix attendance complete (engine 00fb350ba, dialog 9e5232647, review fix b6a484247, docs). Reviews: FIX_CRITICAL → fixed → DEPLOY.
LEARNING(gate): vm-harness JS tests pass with an invented server shape -> the real-Desk render on verify-bench (yarn --ignore-engines build + frappe serve in tmux + Playwright with host-resolver-rules) is the check; recipe in memory
NEXT: owner deploys R2 → R3 (+ Fix attendance). Open: reminders (4 answers), stuck-cancel override, ledger reverse, expense_date, live Shift Type working-hours setting.
- 2026-09-21T11:51:22Z PUSH: nz-glass @ 72f6d9069
- 2026-09-21T11:51:22Z COMMIT: 72f6d9069 docs(glass): handoff for Fix attendance → review dispatched
- 2026-09-21T15:53:42Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T16:26:59Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T16:40:21Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T16:57:00Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 17 file(s) ⟂d50eeeeab44e
- 2026-09-21T16:57:00Z EVIDENCE: 3 works — blast radius green: 39 dependent(s), 25 extra test file(s) ⟂03aeaee7733f
- 2026-09-21T16:57:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 17 file(s) ⟂d50eeeeab44e
- 2026-09-21T16:57:32Z EVIDENCE: 3 works — blast radius green: 39 dependent(s), 25 extra test file(s) ⟂03aeaee7733f
- 2026-09-21T16:57:57Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 17 file(s) ⟂d50eeeeab44e
- 2026-09-21T16:57:57Z EVIDENCE: 3 works — blast radius green: 39 dependent(s), 25 extra test file(s) ⟂03aeaee7733f
- 2026-09-21T16:57:59Z COMMIT: 3409a2c7b fix(approval): a superior named as approver can open and decide an On Duty request → review+security dispatched
- 2026-09-21T16:59:14Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T17:07:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-21T17:07:53Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 1 extra test file(s) ⟂878a988d4e57
- 2026-09-21T17:07:54Z COMMIT: 04e7bb62e fix(fix-day): an approved request no longer blocks Save & rebuild → review dispatched

REPAIR: Fix attendance refused every day carrying an approved OT/Attendance Request. The
21 Sep ruling was fully plumbed (requests_ok through day_block_reason, _day_block, _rebuild,
_paid_day, _leave_cover) but NO entry point passed it — plan_day, _screen, _lock_and_guard
and _finish all took the False default. Spec guard G12 had no test. Commit 04e7bb62e.
EVIDENCE: 2 correct — TestAnApprovedRequestDoesNotBlockTheFix red on HEAD (5 failures:
plan/screen/three actions/engine-hold), green after; money and leave still block.
EVIDENCE: 3 works — pytest test_attendance_fix_day + test_fix_days: 105 passed, 47 subtests;
blast radius (attendance_fix_days, attendance_master_edit, fix_day_probe) green via the gate.
LEARNING(gate): spec-gap -> a threaded flag that no caller ever passes reads as implemented.
Gate proposal: a test that drives the ENTRY POINT, never the helper the flag lands in.
NEXT: owner decision needed — reviewers of 3409a2c7b raised (a) reporting managers lost
Desk-side write/submit on OT Request (PWA unaffected), (b) Department Approver now reads the
whole department's requests in list queries. Neither blocks. Nothing pushed.
- 2026-09-21T17:08:18Z COMMIT: c26118547 docs(progress): the G12 spec-gap and the two reviewer questions → review dispatched
- 2026-09-21T17:09:42Z COMMIT: ab601bee3 docs(ticket): five hand-threaded guard call sites are the next bug → review dispatched
- 2026-09-21T17:15:38Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T17:39:45Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T17:43Z REPAIR: approval routing walks each employee's own chain bottom-up; Department Approver is no longer a routing source (owner ruling)
- 2026-09-21T17:43Z EVIDENCE: 2 correct — test_approver_chain_follows_each_employee.py 15/15, proved red before the fix
- 2026-09-21T17:43Z EVIDENCE: 3 works — blast radius green: 85 passed + 121 subtests across 7 dependent suites
- 2026-09-21T17:43:56Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-21T17:43:56Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-09-21T17:45:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-21T17:45:48Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-09-21T17:45:49Z EVIDENCE: 6 behaves — family hunt: class=approval routing asked the wrong question in two opposite directions —; 6 call site(s) given verdicts, 12 same-root ⟂dc8c11dd7807
- 2026-09-21T17:45:51Z COMMIT: cf94549e7 fix(approval): routing follows each employee's own chain, bottom-up → review dispatched
- 2026-09-21T17:49:45Z COMMIT: 12ab90104 docs(ticket): shift requests still route by department, and two walkers drift → review dispatched
- 2026-09-21T17:57Z REPAIR: shift requests route by the employee's own chain too; the department ancestor walk is deleted (owner: "close it")
- 2026-09-21T17:57Z EVIDENCE: 2 correct — test_shift_requests_route_by_the_same_chain.py 7/7, proved red (6 failed) before the fix
- 2026-09-21T17:57Z EVIDENCE: 3 works — blast radius green: 98 passed + 30 subtests, plus 50 passed + 113 subtests across the fence suites
- 2026-09-21T17:58:13Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-21T17:58:16Z COMMIT: 5134f4856 fix(shift-request): a shift request routes up the employee's own chain → review dispatched
- 2026-09-21T17:59:57Z PUSH: nz-glass @ 5134f4856
- 2026-09-21T18:00:18Z PUSH: nz-glass @ c86ebd8ad
- 2026-09-21T18:00:18Z COMMIT: c86ebd8ad docs(glass): handoff for the approver chain → review dispatched
- 2026-09-21T18:03Z REPAIR: an employee with no approver configured is told that, instead of being sent to an empty dropdown (owner: "make it clear and not confusing")
- 2026-09-21T18:03Z EVIDENCE: 2 correct — test_no_approver_configured_says_so.py 6/6; proved red on clean HEAD source (4 failed), tree restored
- 2026-09-21T18:03Z EVIDENCE: 3 works — blast radius green: 104 passed + 30 subtests across 13 suites
- 2026-09-21T18:03:40Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-21T18:03:40Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 13 extra test file(s) ⟂2d3ffee99479
- 2026-09-21T18:04:07Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-21T18:04:07Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 13 extra test file(s) ⟂2d3ffee99479
- 2026-09-21T18:04:08Z EVIDENCE: 6 behaves — family hunt: class=one message for two different situations. Both approver fences threw the; 4 call site(s) given verdicts, 6 same-root ⟂89f3246126b4
- 2026-09-21T18:04:10Z COMMIT: ab74a7904 fix(approval): say "no approver is set up" instead of "pick your manager" → review dispatched
- 2026-09-21T18:04:10Z COMPACT: context compacted — read the last NEXT above before continuing

LEARNING(gate): spec-gap -> family hunt sweeps CALL SITES only. Both spec-gaps in
  the 21 Sep range had one shape: a structurally identical sibling that does NOT
  call the changed symbol (Shift Request's own validate_approver/get_department_
  approvers pair; a 6th hand-threaded guard call site). Proposed gate: when a
  commit changes a routing/guard rule, also grep the function-NAME PATTERN
  (get_*_approvers, validate_approver, *_block_reason) across all modules and
  require the same same-root/ticket/not-affected verdict for each match.
  8th spec-gap row in tasks.csv with no gate. Raised by the retro, 21 Sep 2026.
NEXT: frappe-reviewer verdict on ab74a7904, then push + refresh docs/glass/HANDOFF.md.
- 2026-09-21T18:08:08Z PUSH: nz-glass @ ab74a7904
- 2026-09-21T18:08:17Z PUSH: nz-glass @ 2ecd6223b
- 2026-09-21T18:08:18Z COMMIT: 2ecd6223b docs(glass): handoff for the approver message fix → review dispatched

REPAIR: Remote Checkin Request routed by its own private copy of the approver
  rule — one hop, Department Approver as tier 2. The one request type the
  21 Sep ruling missed, because it calls none of the symbols that changed.
  Owner approved closing it ("sure"). resolve_approver now stamps chain[0];
  approval.DESIGNATED_APPROVER_DOCTYPES admits the rest of the chain to decide;
  _pending_for_approver_query admits them to the queue so a decidable request
  is never in nobody's list.
EVIDENCE: 2 — test_remote_checkin_routes_up_the_chain.py 6 RED on clean HEAD
  (grand-manager refused, department approver stamped), 11 green + 2 subtests.
EVIDENCE: 3 — blast radius green per file: approval_scoping_invariant 3,
  remote_checkin_request_hooks 25, two_approvers 3, selfie 4, company_api_scope
  31, api/test_approval 31, chain 15, shift chain 7, no-approver 6, self-approval
  13. Two pre-existing skips need a real bench. ruff clean.
EVIDENCE: 6 — family ledger .claude/plans/family.md, 11 call sites same-root,
  team.py's display-only tab gate ticketed.
NEXT: commit, review, push, refresh HANDOFF.
- 2026-09-21T18:22:33Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T18:25:07Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:25:07Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:25:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:25:31Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:25:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:25:48Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:25:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:25:59Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:26:37Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:26:37Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:26:41Z COMMIT: 0a0d0402c fix(remote-checkin): a remote punch routes up the employee's own chain → review+cross-app dispatched

LEARNING(gate): family-hunt sweeps production call sites of the CHANGED symbols only ->
  it misses test files that call the changed function directly (here
  hrms/overrides/test_remote_checkin_request_hooks.py pinned the removed
  Department Approver tier, and is bench-only so no local run catches it).
  Proposed gate: the family scan greps the changed function NAMES across
  test_*.py as well, and a bench-only test (FrappeTestCase) naming a changed
  function needs a verdict line like any other call site.
NEXT: push 0a0d0402c + the bench-test amendment, refresh docs/glass/HANDOFF.md.
- 2026-09-21T18:29:59Z COMMIT: 353ceb7d6 test(remote-checkin): the department tier is pinned as absent, not as winning → review+cross-app dispatched
- 2026-09-21T18:30:58Z PUSH: nz-glass @ 353ceb7d6
- 2026-09-21T18:31:16Z PUSH: nz-glass @ 1c36eeebc
- 2026-09-21T18:31:16Z COMMIT: 1c36eeebc docs(glass): handoff for the remote check-in routing fix → review dispatched
- 2026-09-21T18:43:17Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T18:54:22Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:54:27Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:54:31Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:54:34Z COMMIT: 1c36eeebc docs(glass): handoff for the remote check-in routing fix → review dispatched
- 2026-09-21T18:54:44Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:55:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:55:09Z COMMIT: ecc3b8d7b fix(pwa): one waiting word, and a rejected remote punch looks rejected → review+design dispatched

REPAIR: 21 Sep — one waiting word on screen; Remote Approvals joins the shared
  status rule; Employee Issue states get colour. Commit ecc3b8d7b.
EVIDENCE: 2 correct — frontend/src/utils/__tests__/requestStatus.test.js, 5 RED
  on HEAD before the change, 9 green after.
EVIDENCE: 3 works — 143 frontend tests green (utils + components), prettier
  clean on the three changed files.
LEARNING(fact): slice 4 of the Thread F plan (track_changes on Leave
  Application and Expense Claim, plus the guarded Property Setter patch) was
  already shipped this morning in f04526cea with test_who_approved_when.py. The
  audit that surfaced it (H-request-dates-backend.md H1) predates that commit.
NEXT: slices 5 and 6 of the request-status unification wait on the owner — the
  RequestPolicy table needs his ruling on backdating windows for Shift Request,
  Expense Claim, Attendance Request and Compensatory Leave (today: none at all),
  and the clock unification is its own change. Deploy ecc3b8d7b first.
NEXT: also open — .claude/plans/ticket-waiting-word-in-filters.md (the two list
  filters still offer the stored word; needs FormField Select to take
  {label, value} pairs first).
- 2026-09-21T18:56:48Z COMMIT: aea8da075 docs(plans): record what the waiting word left open → review dispatched
- 2026-09-21T18:56:48Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T18:58:56Z PUSH: nz-glass @ aea8da075
- 2026-09-21T18:59:20Z PUSH: nz-glass @ c1200e921
- 2026-09-21T18:59:20Z COMMIT: c1200e921 docs(glass): handoff for the one-waiting-word slice → review dispatched
- 2026-09-21T19:01:13Z PUSH: nz-glass @ 61b16f93e
- 2026-09-21T19:01:13Z COMMIT: 61b16f93e style(remote-approvals): the name gives ground on purpose, not by accident → review+design dispatched
- 2026-09-21T19:01:25Z PUSH: nz-glass @ 5cc2206f2
- 2026-09-21T19:01:25Z COMMIT: 5cc2206f2 docs(glass): point the handoff at the tip commit → review dispatched
- 2026-09-21T19:10:36Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T20:05:00Z EVIDENCE: rung 5 (looks right) — nadi-2.0-mockup-4.html rendered in Chromium at 320/390/1280, light+dark, 12 states captured, 0 console + 0 page errors; axe-core WCAG 2 A/AA + 2.1 + 2.2 AA = 0 violations across 13 states.
- 2026-09-21T20:05:00Z REPAIR: nine defects found by that pass and fixed — dev strip covering the app bar (assumed 38px, now measured), [hidden] losing to a class selector, focus ring drawn round <main>, tab labels colliding at 320px, calendar role="grid" without rows (now role="list"), and five AA contrast pairs (waiting chip, segmented control, caption on page bg, text+chips on sheet glass, three dark chips).
- 2026-09-21T20:05:00Z LEARNING(how): text laid on CHROME GLASS has no fixed backdrop, so token inks tuned for a white card fall under AA there. Any .sub/.eyebrow/.chip inside a sheet needs its own ink rule. Cheapest check is axe with the sheet OPEN — a closed-sheet pass reports nothing.
- 2026-09-21T20:05:00Z NEXT: owner reviews "Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html" (+ -notes.md); the folder is gitignored so neither file is committed. Thread F slice 5 still waits on the backdating ruling.
- 2026-09-21T19:28:50Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T19:44:50Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T20:45:00Z REPAIR: mockup 4 reworked onto nadi-2.0-mockup.html at the owner's preference — Inter Tight/Inter web fonts, 390x844 device on a dark stage with the mockup toolbar, blurred light field + four-layer liquid glass, 11 screens + 5 sheets, switchable Lime B. Done as a rebase, not a merge: mockup 1 became the file, then every a11y fix the old mockup 4 had earned was re-applied on top.
- 2026-09-21T20:45:00Z EVIDENCE: rung 5 (looks right) — axe-core WCAG 2 A/AA + 2.1 + 2.2 AA over 20 states (5 tabs, 5 secondary screens, 3 sheets, 4 dark, desktop, Lime B) = 0 violations; 12 Chromium screenshot states = 0 console + 0 page errors.
- 2026-09-21T20:45:00Z REPAIR: mockup 1's palette carried eleven AA failures the old mockup 4 did not — four pill inks, the quiet caption on two surfaces, the weekday header, the row chevron, the out-of-range day opacity, dark ink3, and black UA text on button-as-surface. Every replacement computed as a luminance ratio, not eyeballed (e.g. 3.84 -> 6.10, 2.84 -> 5.87, 1.17 -> inherit).
- 2026-09-21T20:45:00Z LEARNING(how): a <button> used as a SURFACE (button.panel / button.card) never inherits the app's ink — the .row reset only covers .row, so it keeps the UA's black and disappears on a dark surface at 1.17:1. It is invisible to a light-mode-only audit; only axe run in dark finds it.
- 2026-09-21T20:45:00Z LEARNING(how): a coloured pill ink tuned for a white card fails on its own 14-26% wash. Measure each pill ink against the wash it actually sits on, and give light mode its own value while dark falls back to the token.
- 2026-09-21T20:45:00Z NEXT: owner reviews the reworked "Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html" (+ rewritten -notes.md); the folder is gitignored (.gitignore:40) so neither file is committed — un-ignoring is his call. Thread F slice 5 still waits on the backdating ruling; deploy ecc3b8d7b..5cc2206f2 still pending.
- 2026-09-21T20:01:29Z COMPACT: context compacted — read the last NEXT above before continuing

2026-09-21T23:40:00Z REPAIR: mockup-4 reworked against 2026 standards — 13 findings, each an external rule plus a measured number in the file.
2026-09-21T23:40:00Z EVIDENCE: rung 5 (looks right) — tab bar inside the frame at 320/360/390/414 (was +117..+262px off-screen); axe 0 violations across phone screens, 4 request states, dark, desktop; every visible button >=44px; 19 screenshots, 0 console + 0 page errors.
2026-09-21T23:40:00Z LEARNING(fact): a flex child with no min-height:0 will not shrink below its content — that alone pushed an absolutely-positioned tab bar out of an overflow:hidden frame at EVERY width, not just the reported one. The user reported "missing on mobile"; measurement found it missing everywhere.
2026-09-21T23:40:00Z LEARNING(how): for "too much scrolling", measure screen depth before cutting content. Eight of eleven screens already fit one viewport; the real defect was two NESTED horizontal scrollers, which is a different fix from pagination.
2026-09-21T23:40:00Z DEAD END: axe reports target-size x13 on the desktop preview. It is the mockup's own 0.72 scale transform, not the layout — at real desktop size nothing is under 24px CSS. Not a finding.
2026-09-21T23:40:00Z NEXT: owner reviews the reworked "Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html" + notes; the folder is gitignored (.gitignore:40) so neither file is committed — un-ignoring is his call.
- 2026-09-21T20:44:24Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T21:15:48Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T21:44:34Z COMPACT: context compacted — read the last NEXT above before continuing

REPAIR: mockup 4 defect-family audit closed. 7 families found by measurement,
  all fixed: A contrast through glass (61 -> 0), B inert ellipsis on
  display:inline (7 -> 0), C home depth (1.59 -> 1.36 viewports), D sheet detent
  (226px top-edge swing -> 0), F tap targets (3 -> 0), G ragged column edge
  (259/338px -> clean), G2 ragged inner edge (12px pill spread -> clean),
  H text resting under floating chrome (12 -> 0).
EVIDENCE: rung 2. a2 NO LOW-CONTRAST TEXT over 1754 verified boxes, both themes,
  29 states, self-test 13.80:1. a3 no clipped text; sheet top=399 h=444 on all
  30 days. a5 ANIMATES 19 frames 482->0. a7 under 44px: none, clean at 8 widths
  320-1440. a8 COLUMN EDGE CLEAN + INNER EDGE CLEAN. a9 NO TEXT RESTS UNDER
  CHROME. Visual read of 10 screenshots, light and dark.
EVIDENCE: 6 probe defects found and fixed while closing the families, each
  recorded in .claude/plans/family-mockup4.md because each would have hidden a
  real defect later. The worst: offsetParent reports a collapsed <details> as
  visible, so three probes were measuring text nobody can see.
DEAD END: axe-core cannot answer contrast through backdrop-filter — it returns
  INCOMPLETE, never a violation. The earlier "0 violations" verdict was the tool
  declining to answer. Real-pixel sampling replaced it; notes file corrected.
NEXT: owner's word on two things before Phase 2 starts — (1) un-ignore
  "Nadi PWA UI UX 2.0" (.gitignore:40) so the mockup repairs can be committed,
  or leave it uncommitted; (2) confirm Mockup 4 is signed off as the visual
  contract, which is the gate he set for the full PWA 2.0 frontend build.
