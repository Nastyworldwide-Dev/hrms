2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
2026-09-08T17:56Z DEAD END: standalone bench-free harness files (test_write_block, test_report_scope_filters, test_offboarding, ...) replace sys.modules["frappe"] at import or run time; in the gate's shared pytest session that broke later setUps. Fixed at the source for the two that blocked commits; new tests on the sync harness pin runner.frappe. Class: TEST-MODULE-CONTAMINATION — a conftest-level guard (restore sys.modules after each module) is the gate to propose.
2026-09-08T17:56Z NOTE: per the user ("review later"), NO reviewers were spawned for the batch 2 commits after 7cf3ebcb1; the post-commit hooks asked for frappe/design/cross-app reviews on each — run them in one pass before deploy. Agents: user-run script /tmp/claude-1009/-home-nabil-nz-version-16/f5651527-5a03-4dbb-9e4b-3209c3820cd2/scratchpad/agents-sonnet-high-2026-09-08.sh pins every agent to sonnet/high (scouts haiku/low).
2026-09-08T17:56Z NEXT: (1) reviews for batch 2 (14 fix commits from 807765415 to cd00c19a7); (2) HR answers -> rest-day rule Q1-Q3, four-month window, "punched, pending"/September repair after D4; (3) report family hunt (plan item 5) and the remaining notification rows N01-N04, N09; (4) Nabil pushes nz-glass + deploys (patches: gate_hr_desktop_icons..., grant_hr_read_on_pwa_notification).
- 2026-09-08T17:56:05Z COMMIT: 4915632e5 chore(plans): batch 2 rows 5-9 landed; ledgers, handoff and next steps → review dispatched
- 2026-09-08T18:03:31Z PUSH: nz-glass @ d27f028c9
- 2026-09-08T18:03:31Z COMMIT: d27f028c9 chore(plans): progress lines from the batch 2 commit gates → review dispatched
- 2026-09-08T18:34:01Z PUSH: nz-glass @ 550771c6f
- 2026-09-08T18:34:02Z COMMIT: 550771c6f test: give every test module the session's frappe back after it runs → review dispatched
2026-09-08T18:52Z PLAN: Nadi PWA UX 2.0 reviewed -> docs/glass/plan/NADI_2.0_UX_PLAN.md (UX contract U1-U12, gap ledger, 8 mapping corrections, decisions Q1-Q10, phases 0-4 ~55 slices). Prototype folder is gitignored by the user; the plan cites it by path.
2026-09-08T18:52Z NEXT: Nabil answers Q1-Q3 (tab bar, approve-all, one issue system) -> record in docs/glass/decisions/, then phase 0.3 mockup + 0.4 gates; batch-2 reviews and the earlier NEXT items stay open in parallel.
- 2026-09-08T18:53:01Z COMMIT: 602502d24 docs(plan): Nadi PWA UX 2.0 review, contract, gap ledger and slice plan → review dispatched
2026-09-08T18:54Z NEXT: Nabil answers Q1-Q3 from docs/glass/plan/NADI_2.0_UX_PLAN.md section 5 (tab bar, approve-all, one issue system) -> record in docs/glass/decisions/; then phase 0.3 mockup + 0.4 gates. Frappe-reviewer on 602502d24 was dispatched (docs commit); batch-2 reviews still owed.
- 2026-09-08T18:54:33Z COMMIT: d2e496ff1 chore(plans): NEXT line after the UX 2.0 plan commit → review dispatched
- 2026-09-08T18:56:59Z COMMIT: 1bb783490 docs(plan): name both company-fence helpers in the U12 gate row → review dispatched
- 2026-09-09T02:40:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-09T02:40:29Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 2 extra test file(s) ⟂f40f7b7fcc28
- 2026-09-09T02:40:58Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-09T02:40:58Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 2 extra test file(s) ⟂f40f7b7fcc28
- 2026-09-09T02:41:53Z PLAN: approved 4cc8131a5e9b — # Proper fixes v2 — reconciled with Codex's 8 Sep audit
- 2026-09-09T02:42:00Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-09T02:42:00Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 2 extra test file(s) ⟂f40f7b7fcc28
- 2026-09-09T02:42:03Z COMMIT: 1feffe5a7 fix(push): re-register with the relay when the stored credentials are another site's → review+cross-app dispatched
- 2026-09-09T02:46:40Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 13 file(s) ⟂ad7bb4cb625b
- 2026-09-09T02:46:40Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 5 extra test file(s) ⟂b91eb133f40c
- 2026-09-09T02:46:43Z COMMIT: 527680d56 feat(attendance): a Shift Location can be marked free so punches anywhere record without approval → review+design dispatched
- 2026-09-09T02:47:38Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T02:47:38Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 2 extra test file(s) ⟂ce54683ec640
- 2026-09-09T02:47:41Z COMMIT: c5d5b84c7 chore(push): say when the relay refusal cannot be recognised; complete the family ledger → review dispatched
2026-09-09T02:48Z REPAIR: stabilisation pair landed locally (no push): 1feffe5a7 push relay self-heal (cloned site carried nasty-live's relay credentials; reviewer DEPLOY), 527680d56 Free Location tick box on Shift Location (review pending), c5d5b84c7 chore follow-up. Reviewer for c5d5b84c7 skipped: docstring + ledger only, same code already reviewed DEPLOY.
2026-09-09T02:48Z EVIDENCE: 3 works — geofence suites 56 pass; push suites 8 pass; readiness 27 pass; frontend node 243 pass (4 pre-existing failures in pushNotifications.test.js: Node navigator getter, not in diff); eslint clean; fixture-gate clean.
2026-09-09T02:48Z NEXT: (1) read the Free Location review verdict, fix any Critical; (2) Nabil: push nz-glass + deploy (bench migrate adds Shift Location.is_free_location; hooks change needs the restart FC does); after deploy open the PWA once as any user so subscribe re-registers verifica-live with the relay, then confirm no nasty-live@notification.frappe in the error log; (3) Nabil: rotate nasty-live's relay key/secret (they are in the pasted log) by clearing Push Notification Settings api_key/api_secret there; (4) HR: tick Free Location on the Sales Shift Location; (5) then back to the 2.0 plan decisions Q1-Q3.
- 2026-09-09T02:48:16Z COMMIT: 2a628f6f4 chore(plans): stabilisation pair landed; next steps for deploy and rotation → review dispatched
- 2026-09-09T02:51:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-09T02:51:53Z COMMIT: 5e98e8235 chore(attendance): prettier on the free-location lines; say the phone still records where they were → review+design dispatched
2026-09-09T02:52Z REPAIR: 5e98e8235 closes the Free Location review's FIX_WARNINGS (prettier on 3 frontend files; HR description now says the phone still records where they were). Reviews for 5e98e8235 dispatched (frappe + design). Follow-ups NOT done, recorded here: docs/glass/diagnose_checkin_area.py still advises coordinates for a free location; readiness test is source-shaped, a collect_facts case with a free location would be the behaviour check; 7 pre-existing prettier errors in frontend push test files (frappe-push-notification.test.js, pushNotifications.test.js) make npm run lint red.
- 2026-09-09T02:52:19Z COMMIT: adbae859c chore(plans): Free Location follow-ups recorded → review dispatched
- 2026-09-09T02:57:13Z PUSH: nz-glass @ adbae859c
2026-09-09T03:11Z PLAN: NADI_2.0_SURFACE_MAP.md written from measurements (prototype 36 screens + 5 sheets; shipped 36 routes on fresh.local, bundle rebuilt 03:02): grid 4/8, component snap table, scroll budget (Home 1382 vs 723, Calendar 1362 vs 791, Requests 1301 vs 637, Notifications 1366 vs 508), surface verdicts for all routes/sheets, redundancy census (265 spacing classes, 39 arbitrary, 9 row components, 13 inline status labels), gates U13-U15. Plan gains Q0 (prototype material becomes the spec), 0.6 token re-tune, 0.7 kit.
2026-09-09T03:11Z NEXT: Nabil answers Q0 (look), Q1-Q3; deploy + PWA open for the relay; then phase 0.2 spec addendum §17/§18 and 0.4 gates (U13 app-measure, U14 census, U15 row/pill grep) — both scripts already in frontend/e2e.
- 2026-09-09T03:12:00Z COMMIT: 077077027 docs(plan): 2.0 surface map — grid, scroll budget and redundancy census from measurements → review dispatched
- 2026-09-09T03:12:24Z PUSH: nz-glass @ 077077027
- 2026-09-09T03:12:40Z PUSH: nz-glass @ c1a1c92dc
- 2026-09-09T03:12:40Z COMMIT: c1a1c92dc chore(plans): progress line from the surface-map commit gate → review dispatched
- 2026-09-09T03:16:08Z PUSH: nz-glass @ 34e8555d9
- 2026-09-09T03:16:08Z COMMIT: 34e8555d9 chore(plan): say the prototype file is untracked; declare its page globals for lint → review dispatched
- 2026-09-09T03:37:59Z PLAN: approved 884bd9128883 — # Proper fixes v2 — reconciled with Codex's 8 Sep audit
- 2026-09-09T03:40:57Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 12 file(s) ⟂59cca907033f
- 2026-09-09T03:40:59Z COMMIT: 3e01a73ab feat(attendance): every punch keeps the location evidence the fence decided on → review dispatched
- 2026-09-09T03:50:13Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T03:50:16Z COMMIT: ffce088ec fix(attendance): a punch waiting for approval is presence, not absence → review dispatched
- 2026-09-09T03:50:51Z PUSH: nz-glass @ ffce088ec
2026-09-09T03:51Z REPAIR: LIVE INCIDENT (Nabil 9 Sep): attendance Absent/Half Day for many after the 8 Sep deploy. Cause: ae0028f30 applied overtime eligibility (pending punch = no evidence) to attendance marking; out-of-radius (pending) check-ins produced no attendance and the absent-marker wrote provisional Absents; pending lunch returns split First/Last spans into Half Day. Fix ffce088ec: counts_for_attendance (pending counts; rejected/offshift/skipped do not); overtime unchanged. Red test hrms/tests/test_pending_punch_attendance.py reproduced all three symptoms on HEAD~1. Pushed.
2026-09-09T03:51Z EVIDENCE: 3 works — 225 attendance tests green; reproduction red before, green after.
2026-09-09T03:51Z NEXT: (1) Nabil deploys ffce088ec (plus 3e01a73ab evidence fields: migrate adds columns); the next hourly run replaces provisional Absents whose punches were never linked; Half Day rows with linked punches are updated through get_existing_half_day_attendance — verify on one employee after the run; (2) mitigation meanwhile: approvers clear pending Remote Checkin Requests; (3) OPEN follow-ups: rebuild the day on rejection under the financial guard; drawer permission state + fix quality (S2, not started); geofence drift diagnosis needs one week of evidence rows; ask Nabil whether the China site is in mainland China (GCJ-02 offset); (4) reviewer verdict for ffce088ec pending.
- 2026-09-09T03:51:17Z PUSH: nz-glass @ 7abd2066f
- 2026-09-09T03:51:17Z COMMIT: 7abd2066f chore(plans): incident record, next steps and handoff for the attendance fix → review dispatched
- 2026-09-09T03:59:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-09T03:59:48Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 3 extra test file(s) ⟂f95945b27b3b
- 2026-09-09T03:59:51Z COMMIT: fcb604535 fix(attendance): rebuild a day already marked from half its punches instead of colliding → review dispatched
2026-09-09T04:00Z REPAIR: fcb604535 rebuild-a-marked-day (reviewer Critical on ffce088ec): a day marked from its approved punches only would collide with the re-read pending punch and skip it forever; now merged from linked + re-read punches, kept if unchanged, cancelled + re-marked if different (automation-owned, unmirrored rows only). Pushed. DEPLOY ffce088ec AND fcb604535 TOGETHER — ffce088ec alone poisons the leftover punches on the first hourly run.
2026-09-09T04:00Z EVIDENCE: 3 works — 229 attendance tests green; test_pending_punch_attendance 10/10 (4 new: merge + hand-down, keep-or-replace).
- 2026-09-09T04:00:26Z PUSH: nz-glass @ fcb604535
- 2026-09-09T04:06:25Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T04:06:25Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 3 extra test file(s) ⟂f95945b27b3b
- 2026-09-09T04:06:28Z COMMIT: 2b01825d2 fix(attendance): never rebuild a leave record; find a shift-less row; keep linked punches whole → review dispatched
2026-09-09T04:07Z REPAIR: 2b01825d2 (reviewer Critical on fcb604535): the rebuild lookup matched leave rows converted in place from an auto-Absent (they keep auto_attendance=1) and would have cancelled HR's leave; now excludes leave_type set / modify_half_day_status=1 / On Leave; finds shift-NULL rows on a second look; a refused rebuild skip-stamps only newly read punches. Pushed. DEPLOY SET: ffce088ec + fcb604535 + 2b01825d2 together (plus 3e01a73ab evidence fields).
2026-09-09T04:07Z EVIDENCE: 3 works — 232 attendance tests green; test_pending_punch_attendance 13/13.
2026-09-09T04:07Z NEXT: (1) reviewer verdict on 2b01825d2; (2) Nabil deploys the set and checks one employee's September after the first hourly run (an Absent-with-OUT-linked day and a Half Day day); (3) S2 drawer permission state; (4) rebuild-on-rejection ticket; (5) China site question (GCJ-02).
- 2026-09-09T04:07:09Z PUSH: nz-glass @ 35e1cf543
- 2026-09-09T04:07:09Z COMMIT: 35e1cf543 chore(plans): deploy set for the attendance incident; handoff → review dispatched
- 2026-09-09T04:16:09Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T04:16:09Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 6 extra test file(s) ⟂3652c40d4b9b
- 2026-09-09T04:16:12Z COMMIT: ade4e3903 fix(sync): after cutover a pull never touches Attendance or Employee Checkin → review dispatched
- 2026-09-09T04:16:53Z PUSH: nz-glass @ ade4e3903
- 2026-09-09T04:19:47Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-09T04:19:47Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 2 extra test file(s) ⟂ce54683ec640
- 2026-09-09T04:20:22Z COMMIT: ed8e16d09 fix(attendance): give the two Overtime section breaks distinct names → review dispatched
- 2026-09-09T04:20:58Z PUSH: nz-glass @ ed8e16d09
- 2026-09-09T04:23:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T04:23:06Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 2 extra test file(s) ⟂ce54683ec640
- 2026-09-09T04:23:08Z COMMIT: 57efe03c4 feat(attendance): a Shift Location pinned from a Chinese map is stored where phones report it → review dispatched
- 2026-09-09T04:23:33Z PUSH: nz-glass @ 57efe03c4
- 2026-09-09T04:24:01Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-09T04:24:04Z COMMIT: 50626a942 fix(sync): parity grades only the doctypes a pull still brings after cutover → review dispatched
2026-09-09T04:24Z REPAIR: August/all-employees cause found: a pull UPDATES mirrored Attendance rows in place with the source's view; after cutover the source has no punches and marks everyone Absent; 'Sync Employee Data' copied that over. ade4e3903 holds Attendance + Employee Checkin back from any pull on an unlocked instance; 50626a942 keeps parity honest about it. Also landed: ee7ac60ef + ed8e16d09 HR in/out editing on Attendance (allow_on_submit, validation, hours + OT recompute, comment); 57efe03c4 GCJ-02/BD-09 -> WGS-84 on Shift Location (China site drift). All pushed.
2026-09-09T04:24Z NEXT: (1) reviewer verdicts on ee7ac60ef/ed8e16d09, 57efe03c4, 50626a942; (2) Nabil: confirm in Desk — HRMS Sync Run list for September runs; Attendance list (August, Absent) columns Synced From Instance / Auto Attendance / Created On; Employee Checkin list (August) Skip Auto Attendance = 1; (3) if confirmed, propose the historical repair under Nabil's word: release mirrored Attendance rows for dates after cutover where local punches exist, unskip the punches the duplicate check stamped, let the hourly job re-mark; (4) HR: set Coordinates Read From on the China Shift Location and save; (5) S2 drawer permission state; Attendance vs Punches report; rebuild-on-rejection.
- 2026-09-09T04:24:28Z PUSH: nz-glass @ 50626a942
- 2026-09-09T04:25:30Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T04:25:30Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 2 extra test file(s) ⟂ce54683ec640
- 2026-09-09T04:25:32Z COMMIT: 9cb5c86e7 fix(attendance): check typed times only, never the hourly job's own rows → review dispatched
- 2026-09-09T04:25:58Z PUSH: nz-glass @ 9cb5c86e7
- 2026-09-09T04:27:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-09T04:27:21Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T04:29:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T04:29:48Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 2 extra test file(s) ⟂ce54683ec640
- 2026-09-09T04:58:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T04:58:21Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 3 extra test file(s) ⟂f95945b27b3b
- 2026-09-09T05:07:15Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T05:07:15Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 3 extra test file(s) ⟂f95945b27b3b
- 2026-09-09T05:11:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
2026-09-09T05:11Z REPAIR: 781096bb3 swallowed get_start_and_end_dates + get_marked_attendance_dates_between (would have broken every hourly run); reviewer caught it before deploy; restored in 19d602aea. NEVER DEPLOY 781096bb3 alone. Deploy set = nz-glass HEAD.
- 2026-09-09T07:06Z REPAIR: cause of vanished punches found in code — runner._write_row let a source overwrite an UNSTAMPED local Employee Checkin sharing its autoname (owner/creation kept, content replaced, stamped; job then ignores it). Guard: IDENTITY_FIELDS + identity-aware plan_cross_instance_write (test_contested_rows red→green). Recovery module + report next.
- 2026-09-09T07:07:14Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T07:07:14Z EVIDENCE: 3 works — blast radius green: 8 dependent(s), 5 extra test file(s) ⟂5cb759d393f4
- 2026-09-09T07:11:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T07:11:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T07:14Z REPAIR: ccb224c38 guard, a5313c6f1 checkin_recovery (17 tests, mutation-checked), edbfc2427 Checkin Provenance Audit report (4 tests); audit doc docs/glass/audit/2026-09-09-checkin-loss-audit.md. Pipeline hooks under /opt/humanless-pipeline unreadable: gates and plan-approve did not run; reviewer spawned by hand.
- 2026-09-09T07:14Z NEXT: read the reviewer verdict on ccb224c38/a5313c6f1/edbfc2427, fix Criticals, push nz-glass; Nabil deploys, runs the report + Recover, one hourly run; then build R5 (release mirrored Attendance rows + un-skip punches) on his word.
- 2026-09-09T07:20Z EVIDENCE: 6 behaves — reviewer on ccb224c38 DEPLOY, edbfc2427 DEPLOY, a5313c6f1 FIX (Critical: sync operator with an Employee link classified overwritten on every mirrored insert; Important: Employee filter on the shown employee). Both fixed with red tests (20 tests green); JS month_start default + escape_html minors fixed.
- 2026-09-09T07:20:40Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-09T07:20:40Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T07:20Z NEXT: Nabil deploys nz-glass HEAD; runs Checkin Provenance Audit (Overwritten, from 1 Aug) then Recover; one hourly run; reports back his 4 Sep / 3 Sep rows and the HRMS Sync Run source. Then R5 patch (release mirrored Attendance rows after cutover where local punches exist + un-skip Duplicate/Overlap-stamped punches) on his explicit word.
- 2026-09-09T07:59Z REPAIR: claims — root cause of 'cannot pull GL from ERP': hub companies are shells with the Standard chart, Account never crosses; Expense Claim Type needs an account per company or every PWA claim save throws. Built account_shells (Pull → GL Accounts), regrouped instance buttons into Pull/Checks/Danger, PWA offers only configured types.
- 2026-09-09T07:59:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T07:59:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T08:06:04Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-09T08:06:04Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-09T08:08:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T08:13:25Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-09T08:13:25Z EVIDENCE: 3 works — blast radius green: 10 dependent(s), 9 extra test file(s) ⟂f62d0a5f62e7
- 2026-09-09T08:15Z NEXT: reviewer verdict on d2cc3dd10/686e4aa0d/bc76cf89b → fix Criticals → push nz-glass; Nabil deploys, runs Pull → GL Accounts, configures Expense Claim Types + expense approvers, tests one claim of each kind; then rulings Q1–Q6 in docs/glass/audit/2026-09-09-claims-audit.md.
- 2026-09-09T08:22:28Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T08:22:28Z EVIDENCE: 3 works — blast radius green: 8 dependent(s), 6 extra test file(s) ⟂51e98e473e5f
- 2026-09-09T08:22Z EVIDENCE: 6 behaves — reviewer: d2cc3dd10 FIX (is_paid guard skipped the payable default on paid claims) → 9b6e21803; 686e4aa0d DEPLOY; bc76cf89b DEPLOY. Pushed.
- 2026-09-09T08:44:18Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T08:44:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T08:45:51Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-09T08:45:51Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T08:50:49Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-09T08:50:49Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T08:51Z REPAIR: 7 Sep 'punched, still Absent' = lifecycle debris (skip stamps from the old Duplicate handler, dead links); attendance_day_audit module + Attendance Day Audit report with Repair button (ecf4134b3, 1d9f8d8ab, 759e70ef6 + reviewer fixes). Reviewer: Critical window bug fixed; repair carries only offending punches.
- 2026-09-09T08:51Z NEXT: push; Nabil deploys, opens Attendance Day Audit for 7–9 Sep, reads verdicts, presses Repair, waits one hourly run; reports his 7 Sep row. Then R5 (mirrored Attendance release) on his word; claims rulings Q1–Q6.
- 2026-09-09T09:06:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-09T09:06:36Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 6 extra test file(s) ⟂014423447a0e
- 2026-09-09T09:07Z REPAIR: HR corrections undone by the job (Amend copies auto_attendance=1; after-submit edit kept it) + no publish + Desk manual check-in refused + punches beside HR row re-read hourly → cf4c4692a (14 tests). Reviewer running.
- 2026-09-09T09:13Z EVIDENCE: 6 behaves — reviewer on cf4c4692a DEPLOY (no Critical/Important); minor: integration rows without device_id must not read as Manual Entry → flags.integration_entry.
- 2026-09-09T09:13:24Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-09T09:13:24Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 3 extra test file(s) ⟂f95945b27b3b
- 2026-09-09T09:51:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T09:51:34Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T09:51Z LIVE: Checkin Provenance Audit on Verifica: Overwritten 199 · Mirrored 3821 · Local 368 · plan insert 195 skip 4; source Nasty-Live; 3–4 Sep attendance rows are mirrored (R5 needed); neighbour-type rule added before Recover.
- 2026-09-09T10:02:09Z PLAN: approved bb53bcd6444e — # Proper fixes v2 — reconciled with Codex's 8 Sep audit
- 2026-09-09T10:02:19Z COMMIT: 9938fc1a5 chore(sync): the GL pull's ceiling admits a real group chart; per-company preview → review dispatched
- 2026-09-09T10:07:49Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T10:07:53Z COMMIT: 1b5beb6a5 refactor(sync): the GL pull creates its accounts in the background and notifies the operator → review dispatched
- 2026-09-09T10:08Z REPAIR: GL pull refused live (4,629 accounts > cap 500) → cap 10,000 (9938fc1a5); reviewer: NestedSet inserts would time out a web request → creation moved to a long-queue job with Desk notification (1b5beb6a5). Ticket: refactor hrms_erp_instance.js dialog builders into one module (hotspot, 8 fixes/90d).
- 2026-09-09T10:08:27Z COMMIT: b86de91dc chore(plans): GL pull ceiling and background job → review dispatched
- 2026-09-09T10:15:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T10:15:42Z COMMIT: 44d3a08ef refactor(sync): the GL pull job reports honestly — a running job, a timeout, counts from the loop → review dispatched
- 2026-09-09T10:18:31Z PLAN: approved 1e2c00f64ede — # Proper fixes v2 — reconciled with Codex's 8 Sep audit
- 2026-09-09T10:18:42Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-09T10:18:42Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-09T10:18:47Z COMMIT: 8fa1c097e feat(expense): HR's eleven claim types wired to their GL account in every company → review dispatched
- 2026-09-09T10:19Z REPAIR: HR's claim-type→GL sheet carried into hrms/utils/expense_claim_type_mapping.py (11 types, applied on deploy + after every GL pull); GL job reporting fixed (running job, timeout, per-company counts) 44d3a08ef; mapping 8fa1c097e. Slash in a type name verified OK on fresh.local.
- 2026-09-09T10:19:26Z COMMIT: dd994af84 docs: handoff for the claim-type mapping and queued GL pull → review dispatched
- 2026-09-09T10:21:35Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T10:21:41Z COMMIT: cfc137441 refactor(sync): the GL pull brings only the accounts HR's claim types point at → review dispatched
- 2026-09-09T11:16:36Z COMMIT: c5ce6f99a docs(audit): shift flip, Half Day everywhere, GL pull failures, Desk sorting — causes and plan → review dispatched
- 2026-09-09T11:40:38Z PLAN: approved 290b5479d0d3 — # Proper fixes v2 — reconciled with Codex's 8 Sep audit
- 2026-09-09T11:43:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-09T11:43:21Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-09T11:43:25Z COMMIT: 4727b4b63 fix(attendance): a punch belongs to the shift it was worked in, and a shift change ends the old one → review+cross-app dispatched
- 2026-09-09T11:45:27Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-09-09T11:45:32Z COMMIT: 497e619e7 fix(desk): HR's attendance lists read in the order the day happened → review dispatched
- 2026-09-09T11:47:11Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T11:47:17Z COMMIT: 5ff14adbb fix(desk): clear the saved sort so HR actually gets the new list order → review dispatched
- 2026-09-09T11:48:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T11:48:20Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T11:48:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T11:48:37Z COMMIT: 7e66adaa5 fix(desk): drop the cached copy of the saved sort as well → review dispatched
- 2026-09-09T11:51:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-09T11:51:18Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-09T11:51:22Z COMMIT: 7291940bf fix(attendance): the Day Audit finds the days whose punches were split across two shifts → review dispatched
- 2026-09-09T11:52Z REPAIR: shift flip root cause (closest-START pick + superseded assignment never ended) → hrms/utils/shift_resolution.py + on_submit supersede hook (4727b4b63); Desk lists sorted by Time/Attendance Date with shift columns, filters and counted/not-counted indicators (497e619e7) + saved-sort reset patch incl. Redis (5ff14adbb, 7e66adaa5); Day Audit names split-shift days and re-resolves them (7291940bf). GL ledger-parent + spelling fix pending commit.
- 2026-09-09T11:52:40Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-09T11:52:40Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T11:52:55Z COMMIT: db39bac2a fix(attendance): the split-shift verdict and its repair, the half 7291940bf left behind → review dispatched
- 2026-09-09T11:53:19Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T11:53:19Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-09T11:53:30Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T11:53:30Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-09T11:53:47Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T11:53:47Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-09T11:54:11Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-09T11:54:11Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-09T11:54:14Z COMMIT: 60167be47 fix(sync): a GL parent that is a ledger here falls back to the root group → review dispatched
- 2026-09-09T11:58:06Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 9 file(s) ⟂79474414be21
- 2026-09-09T11:58:39Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 9 file(s) ⟂79474414be21
- 2026-09-09T11:58:43Z COMMIT: d6c5873de fix(desk): the list reset keeps every other preference, and clears the saved columns too → review dispatched
- 2026-09-09T12:01:01Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 4 file(s) ⟂bdfcc00ed624
- 2026-09-09T12:01:01Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T12:01:07Z COMMIT: 5095377f4 fix(attendance): the shift repair cannot strand a day, and it says what it does → review dispatched
- 2026-09-09T12:02:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T12:02:44Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T12:02:49Z COMMIT: de269bd8d fix(attendance): clear the link before re-resolving, or the shift repair does nothing → review dispatched
- 2026-09-09T12:09:10Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 5 file(s) ⟂5d9cef17ceeb
- 2026-09-09T12:09:10Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 5 extra test file(s) ⟂2da7a836b075
- 2026-09-09T12:09:16Z COMMIT: 6016009c4 fix(attendance): name the real cause of a split day instead of repairing it forever → review+cross-app dispatched
- 2026-09-09T12:10Z EVIDENCE: 6 behaves — reviews on the Desk/shift batch: Critical (Redis hash flush) and Critical (fetch_shift no-op) both fixed and re-verified; 3 warnings closed in 6016009c4. Suites: 31 day-audit, 11 list, 10 sort-reset, all green on fresh.local too.
- 2026-09-09T12:10:21Z COMMIT: 465a5ae98 docs(audit): what shipped for the shift flip, the lists and the GL pull → review dispatched
- 2026-09-09T12:15:15Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-09T12:15:15Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-09T12:15:20Z COMMIT: d1ea992d4 fix(attendance): bound the assignment query, and tell the truth about the ceiling → review dispatched
- 2026-09-09T12:16Z NEXT: Nabil deploys d1ea992d4; Pull GL Accounts; Attendance Day Audit 1-10 Sep (HR ends duplicate assignments first, then Repair); one hourly run; report his 3/4/7 Sep rows. Then: August decision, source-site shutdown confirmation, claim rulings Q1-Q6.
- 2026-09-09T12:16:18Z COMMIT: 80c785744 docs: handoff for the shift and Desk batch → review dispatched
- 2026-09-09T12:19:28Z COMMIT: ac40ef311 chore(attendance): the day audit's docstring, guard and test class say what is true → review dispatched
- 2026-09-10T03:03:55Z COMMIT: 16fa438af fix(attendance): repair the split day even while both assignments are still active → review dispatched
- 2026-09-10T03:06:16Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-10T03:06:16Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-10T03:06:28Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-10T03:06:28Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-10T03:06:31Z COMMIT: ea3e66a41 fix(expense): say why a claim type has no account instead of counting it → review dispatched
- 2026-09-10T03:08:10Z COMMIT: d3421c288 fix(pwa): one forgotten check-out no longer asks you to check in forever → review+security+design dispatched
- 2026-09-10T03:09:15Z COMMIT: df061a33b docs(audit): the check-in pipeline and what each step feeds → review dispatched
- 2026-09-10T03:09Z REPAIR: three live defects traced and fixed after the deploy — (1) PWA stuck on "Check In": the abandoned flag of the OLDEST unresolved session was applied to the NEWEST log (d3421c288, proven red on shipped code); (2) some employees still Half Day because my own two-active-assignments guard refused the repair for exactly the broken population — removed, convergence proven on fresh.local, loop now impossible via the no-change guard (16fa438af); (3) two claim types unconfigured because the mapped GL name exists as a GROUP heading, not a ledger — the reason is now named per type and company (ea3e66a41). Pipeline map: docs/glass/audit/2026-09-10-checkin-pipeline-map.md.
- 2026-09-10T03:09Z NEXT: Nabil deploys df061a33b, then (a) Attendance Day Audit 1-10 Sep -> Repair -> one hourly run -> confirm his 3/4/7 Sep read Present; (b) check the PWA button after a fresh check-in; (c) Pull -> GL Accounts and read the bell for the two named types (pick a ledger under the group); (d) HR ends the superseded shift assignments. Then: August decision, source-site shutdown confirmation, claim rulings Q1-Q6.
- 2026-09-10T03:13:09Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 7 file(s) ⟂85be7f79c548
- 2026-09-10T03:13:09Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-10T03:13:15Z COMMIT: d26582aec fix(attendance): check the whole day before rewriting any of it, and drop a dead filter → review+security+design dispatched
- 2026-09-10T03:13Z EVIDENCE: 6 behaves — reviews on the three fixes: all DEPLOY, no Critical. Five warnings closed in d26582aec, incl. a half-applied shift repair that could unify a day onto the superseded shift (whole-day readability check now) and a dead Verdict filter option that would have read as 'nobody has duplicate assignments'.
- 2026-09-10T03:13Z NEXT: Nabil deploys d26582aec, then (a) Attendance Day Audit 1-10 Sep -> Repair -> one hourly run -> confirm 3/4/7 Sep read Present; (b) PWA button after a fresh check-in; (c) Pull -> GL Accounts, read the bell for the two named types; (d) HR ends the superseded shift assignments. Open: August decision, source-site shutdown, claim rulings Q1-Q6.
