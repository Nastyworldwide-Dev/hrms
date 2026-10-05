2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
- 2026-09-30T06:50:52Z COMMIT: c18817c41 docs(handoff): alpha.24 done → review dispatched
EVIDENCE: 3 fresh.local supervisor locked to _Test Company: report in Nadi W0 A SAVED, self SAVED, stranger refused; Team roster lists You first; browser Assign x2 no errors
- 2026-09-30T08:59:01Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-30T08:59:01Z EVIDENCE: 3 works — blast radius green: 28 dependent(s), 16 extra test file(s) ⟂0ef7741de903
- 2026-09-30T08:59:04Z COMMIT: 7913dc781 fix(roster): a Shift Supervisor could not assign shifts to their own team → review dispatched
EVIDENCE: 2 team-roster-assign 3/3 (2 red before); browser: button reads 'Assign shift', first row 'You'
- 2026-09-30T08:59:55Z EVIDENCE: 2 correct — mapped tests green (bun ) for 1 file(s) ⟂447b403db931
- 2026-09-30T09:00:26Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-30T09:00:29Z COMMIT: a494357ca fix(team): the Assign shift button was a blank green pill → review+design dispatched
- 2026-09-30T09:01:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
EVIDENCE: 2 company-from-employee test red on HEAD (1 fail), green after
- 2026-09-30T09:01:33Z COMMIT: 729262e15 fix(roster): a supervisor's shift took its company from the browser → review dispatched
EVIDENCE: 2 pre-push — frontend suite 1579/1579; roster/fence stub tests OK
- 2026-09-30T09:07:19Z COMMIT: 2f1b7b8dd chore(release): 2.0.0-alpha.25 — Supervisors Roster Their Whole Team → review+deps dispatched
NEXT: owner deploys alpha.25; HR retests Assign for the supervisor; alpha.26 larger text on 'go'
- 2026-09-30T09:08:14Z COMMIT: b275fad44 docs(handoff): alpha.25 done → review dispatched
EVIDENCE: 3 fresh.local HR-EMP-00012 (record calendar only) resolves Nadi W0 2026, half day 0.5; HR-EMP-00003 (none) plain refusal; holiday tests 33 pass
- 2026-09-30T09:38:52Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T09:38:52Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 11 extra test file(s) ⟂e3a82f02d393
- 2026-09-30T09:38:55Z COMMIT: a234b66dc fix(holidays): leave was refused for anyone added after install → review dispatched
- 2026-09-30T09:39:43Z COMMIT: 66ed9b420 docs(readiness): tell HR the simpler way to give someone a calendar → review dispatched
- 2026-09-30T09:41:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T09:41:05Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 11 extra test file(s) ⟂e3a82f02d393
- 2026-09-30T09:41:08Z COMMIT: 3722a3ace fix(holidays): a split date range could add days to an empty start → review dispatched
- 2026-09-30T09:43:45Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T09:43:45Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 11 extra test file(s) ⟂e3a82f02d393
- 2026-09-30T09:43:46Z COMMIT: 1f3bfb3d3 fix(holidays): a range across two calendars counted holidays outside it → review dispatched
EVIDENCE: 2 pre-push — holiday/OT stub suites 74+ pass; fresh.local record-calendar employee resolves, half day 0.5
- 2026-09-30T09:45:28Z COMMIT: 8c191c356 chore(release): 2.0.0-alpha.26 — Leave Works for New Staff → review+deps dispatched
NEXT: owner deploys alpha.26; HR sets Nsty Holding Default Holiday List if blank; alpha.27 larger text on 'go'
- 2026-09-30T09:45:58Z COMMIT: 1b168a8c5 docs(handoff): alpha.26 done → review dispatched
- 2026-09-30T10:06:20Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
EVIDENCE: 3 fresh.local employee with allocation + past leave + no assignment: live resolver -> leave section omitted ("None allocated yet"); alpha.26 resolver with record calendar -> balance 7.0
- 2026-09-30T10:06:22Z COMMIT: 681545ac0 fix(requests): "None allocated yet" for someone with eight allocations → review+design dispatched
- 2026-09-30T10:08:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-30T10:08:11Z COMMIT: 25d4ed093 fix(requests): "pull down to try again" did not reload the balances → review+design dispatched
- 2026-09-30T10:15:19Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T10:15:19Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 11 extra test file(s) ⟂e3a82f02d393
- 2026-09-30T10:15:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T10:15:44Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 11 extra test file(s) ⟂e3a82f02d393
- 2026-09-30T10:15:49Z COMMIT: 51f319e17 fix(requests): "pull down to try again" did not reload the balances → review dispatched
DEAD END: commit 51f319e17 carries the Monthly Attendance Sheet record-calendar fallback (holiday_list.get_assigned_holiday_lists_to_employee_and_company + 5 tests) under the previous subject 'pull down to try again' — the command that wrote the new commit-msg was refused by a gate, so the old file was reused. Correct subject: fix(attendance): the monthly sheet showed no holidays for newer staff. Evidence: fresh.local Sep holidays [] -> [09-06, 09-16].
NEXT: owner answers the 3 decisions in docs/glass/plan/WORKING_DAY_MAP.md before any leave/payroll day-count change; 3 commits (balance msg, pull refresh, monthly sheet) wait for 'push'
- 2026-09-30T10:24:04Z COMMIT: 3de46d30e docs(plan): how Nadi decides a working day, and where the flows disagree → review+design dispatched
- 2026-09-30T10:25:24Z COMMIT: 4a8513bf0 docs(plan): state the upstream leave-count change as it is, not as intent → review+design dispatched
- 2026-09-30T10:43:39Z COMMIT: 88fd57169 test(requests): the pull-to-refresh guard names both reloads → review dispatched
EVIDENCE: 5 alpha.27 pre-push — frontend 1580/1580; iOS gate 9/9 0 findings
- 2026-09-30T11:01:48Z COMMIT: 5dbc1592f chore(release): 2.0.0-alpha.27 — Honest Leave Balances → review+deps dispatched
NEXT: write the rest-day rule plan (shift calendar first for leave and payroll, from deploy date; roster gap is not a day off; approved leave may still recount) and wait for owner approval
- 2026-09-30T11:06:42Z COMMIT: 7db2b35c3 docs(handoff): alpha.27 done → review dispatched
NEXT: owner approves docs/glass/plan/REST_DAY_RULE_PLAN.md; then step 0 (read-only Rest day differences report) ships alone
- 2026-09-30T11:08:06Z COMMIT: 745e30dd6 docs(plan): one rest-day rule for leave and payroll, from the deploy day → review dispatched
- 2026-09-30T11:09:57Z COMMIT: 7fe1dbc68 docs(plan): rest-day plan covers every payroll reader and defines "the shift" → review dispatched
- 2026-09-30T11:11:06Z COMMIT: 7912ba96a docs(plan): payroll consumers and the start-date patch spelled out → review dispatched
- 2026-09-30T11:17:24Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-09-30T11:17:26Z COMMIT: fedf16621 docs(plan): payroll consumers and the start-date patch spelled out → review+design dispatched
DEAD END: commit fedf16621 is the Rest Day Differences report (step 0: hrms/hr/report/rest_day_differences/*, tests) under the previous subject 'docs(plan): payroll consumers...' — the command that wrote the new commit-msg.txt was refused by the TDD gate, so the old file was reused. Second time today (first: 51f319e17). Correct subject: feat(reports): Rest Day Differences shows who a one-rule rest day would move. LEARNING(gate): stale commit-msg.txt after a refused command -> write commit-msg.txt and git commit in the SAME command, or have the pipeline clear commit-msg.txt after each successful commit.
- 2026-09-30T11:19:39Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T11:20:27Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T11:21:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-30T11:21:07Z EVIDENCE: 6 behaves — family hunt: class=a per-day lookup inside a per-employee loop in a report; 16 call site(s) given verdicts, 3 same-root ⟂bd4bcf991ec9
- 2026-09-30T11:21:07Z COMMIT: e0dae0e2f fix(reports): Rest Day Differences looked a calendar up per person per day → review dispatched
- 2026-09-30T11:23:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T11:23:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
EVIDENCE: 3 fresh.local mid-window Holiday List Assignment switch Sun->Sat: work dates Sun 04/11 Oct then Sat 17/24 Oct; 23 lookups, 0.05s
- 2026-09-30T11:24:10Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-30T11:24:11Z EVIDENCE: 6 behaves — family hunt: class=a cache that assumes an answer cannot change inside the window; 6 call site(s) given verdicts, 3 same-root ⟂c6bc03d262ad
- 2026-09-30T11:24:12Z COMMIT: 9cd034555 fix(reports): Rest Day Differences missed a calendar that changes mid-window → review dispatched
EVIDENCE: 3 fresh.local checkpoints in one query: same Sun/Sat split, 0.05s
- 2026-09-30T11:25:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-09-30T11:25:53Z COMMIT: 3e1e97c0f perf(reports): Rest Day Differences reads calendar changes in one query → review dispatched
EVIDENCE: 2 sw.test.js 10/10 (2 new red before); vite build OK, notificationclick in built sw.js
- 2026-10-01T06:32:23Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-01T06:33:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-01T06:33:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-01T06:33:51Z EVIDENCE: 6 behaves — family hunt: class=an event handler registered inside a try block that can fail first, so it is someti; 8 call site(s) given verdicts, 1 same-root ⟂737944510390
- 2026-10-01T06:33:52Z COMMIT: a5cdc1bc1 fix(pwa): tapping a notification did nothing when push failed to start → review+design dispatched
- 2026-10-01T06:37:31Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-01T06:37:35Z COMMIT: 51e6973dc fix(pwa): a notification tap could still do nothing on an uncontrolled window → review+design dispatched
- 2026-10-01T06:39:09Z COMPACT: context compacted — read the last NEXT above before continuing
DEAD END: none this step. Sign-in plan for non-HQ staff written (phone-number login = Frappe System Settings allow_login_using_mobile_number, user.py:835; SMS-code self reset = new code, needs SMS provider). sw tap fix 51e6973dc reviewed: no Critical (suggest try/catch around new URL).
NEXT: wait for owner: (1) "push" -> scripts/release.sh alpha.28 (Rest Day Differences + sw tap fix); (2) SMS provider name + "go phone sign-in"; (3) announcement name + login email; (4) HR leave-import intent + one row. Do NOT push the safety tag.
- 2026-10-01T06:42:36Z COMMIT: 5dcc9e8bb docs: record sign-in plan and pending owner decisions in progress → review dispatched
EVIDENCE: 2 bench fresh.local console: test_roster 12/12 green; old break_shift -> test_supervisor_removes_the_first_day ERROR (red); node team-roster-assign 5/5. Mutation probe escaped: bench-only FrappeTestCase, pytest cannot run it
- 2026-10-02T03:36:51Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-10-02T03:36:51Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-10-02T03:37:14Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-02T03:37:14Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-10-02T03:37:28Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-02T03:37:28Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-10-02T03:37:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-02T03:37:53Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-10-02T03:38:18Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-02T03:38:18Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-10-02T03:38:58Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-10-02T03:38:58Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-10-02T03:39:01Z COMMIT: b4e7adb81 feat(roster): supervisors change and remove their team's shifts in Nadi → review+design dispatched
- 2026-10-02T03:39:18Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-10-02T03:39:18Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-10-02T03:39:20Z COMMIT: d6f21438f fix(desk): Shift Supervisor got "No permission for Page" opening Nadi → review+cross-app dispatched
NEXT: wait for the 2 frappe-reviewer verdicts (.claude/tmp/review-roster-edit.md, review-nadi-tile.md). No Critical -> scripts/release.sh alpha.28 and push nz-glass (9 commits: Rest Day Differences, sw tap x2, docs, roster edit b4e7adb81, Nadi tile d6f21438f). Do NOT push the safety tag. After deploy: Fauzi refreshes Desk.
EVIDENCE: review b4e7adb81 no Critical (12/12 console, 5/5 node); calendar-day warning judged safe-direction, ticket-roster-py-refactor.md filed
- 2026-10-02T03:41:19Z COMMIT: dddcaa3ca chore(release): 2.0.0-alpha.28 — Supervisors Edit the Roster → review+deps dispatched
NEXT: owner ruling — plain staff clicking Desk Nadi still dead-end (hide the tile for non-HR/non-supervisor, or send them to /hrms PWA). alpha.28 pushed.
- 2026-10-02T03:41:55Z PUSH: nz-glass @ 08a7b8ba7
- 2026-10-02T03:41:55Z COMMIT: 08a7b8ba7 docs: handoff for alpha.28 → review dispatched
EVIDENCE: 3 fresh.local get_bootinfo+extend_bootinfo: plain Employee -> Nadi link /hrms, app_route /hrms; Shift Supervisor -> /desk/shift-&-attendance. test_desk_boot 3/3 (red first: module missing)
- 2026-10-02T03:46:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-02T03:46:59Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-10-02T03:47:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-02T03:47:06Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-10-02T03:47:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-02T03:47:21Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-10-02T03:47:22Z COMMIT: e770733ba feat(desk): plain staff who click Nadi on Desk land in the Nadi app → review+cross-app dispatched
EVIDENCE: review e770733ba no Critical/Warning; live p4 rerun plain->/hrms, sv->desk. NEXT: alpha.29 pushed; deploy, then a plain staff user clicks Desk Nadi -> lands in /hrms.
- 2026-10-02T03:48:44Z COMMIT: 77e5119ef chore(release): 2.0.0-alpha.29 — Nadi Opens the App for Staff → review+deps dispatched
- 2026-10-02T03:48:58Z PUSH: nz-glass @ 0032b8022
- 2026-10-02T03:48:58Z COMMIT: 0032b8022 docs: handoff for alpha.29 → review dispatched
EVIDENCE: 2 fresh.local test_roster 13/13 (HR User first-day change red before: PermissionError at cancel); node ShiftAssignmentDialog.test 3/3 (old dialog 2 red)
- 2026-10-02T07:33:20Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-10-02T07:33:23Z COMMIT: f8d7da809 fix(roster): HR could not change a shift on the Desk roster → review+design dispatched
EVIDENCE: 2 review follow-up f8d7da809: test_roster 14/14 fresh.local, dialog node 5/5; HR worked-day message no 'Ask HR'; shift+end-date edit refused not dropped; 'Changes <date> only' hint
- 2026-10-02T07:35:27Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-10-02T07:35:30Z COMMIT: b4d308942 fix(roster): a shift change no longer drops an end-date edit silently → review+design dispatched
NEXT: alpha.30 pushed; read .claude/tmp/review-hr-roster-2.md for b4d308942 and fix anything Critical.
- 2026-10-02T07:36:13Z COMMIT: c79232a46 chore(release): 2.0.0-alpha.30 — HR Can Change Shifts on the Roster → review+deps dispatched
EVIDENCE: 2 review b4d308942 warning: blank end date vs null on open-ended shift; dialog node 6/6
- 2026-10-02T07:36:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-02T07:37:02Z COMMIT: 9dbfb35af fix(roster): an open-ended shift could refuse a shift change by mistake → review+design dispatched
NEXT: deploy alpha.31 (HR Desk Roster update incl. open-ended shifts).
- 2026-10-02T07:37:34Z COMMIT: 2276c06a0 chore(release): 2.0.0-alpha.31 — Roster Fix for Open-Ended Shifts → review+deps dispatched
EVIDENCE: 3 fresh.local real _classify_day on HR-SHA-26-09-00030 2026-10-12: normal -> public_holiday (Day Type PH) -> off (Off Day); migrate fills existing rows 'None' (0 null of 20). test_roster_day_type 5/5 red first
EVIDENCE: test_ot_calculation 47/49 on fresh.local both before and after (test_ot_below_minimum_is_zero, test_ot_off_day_tiered_bands fail on HEAD too — pre-existing)
EVIDENCE: 2 test_ot_nonworking_hours + test_attendance_recovery 128 passed (same as HEAD); stub fakes answer the new Shift Assignment day_type read with [] (no roster)
- 2026-10-02T08:55:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-02T08:55:08Z EVIDENCE: 3 works — blast radius green: 17 dependent(s), 9 extra test file(s) ⟂f707328e3e9d
- 2026-10-02T08:55:11Z COMMIT: 8f463dccd feat(roster): a shift's Day Type decides what kind of day it is → review dispatched
EVIDENCE: 3 slice 2: test_roster 16/16 fresh.local (day_type split + refuse unknown); real save PH -> classify public_holiday, Off Day -> off (request cache cleared by queue_restamp); stub 133 passed; review 8f463dccd warnings fixed (request_cache + conflict log once per day)
- 2026-10-02T08:58:52Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-02T08:58:52Z EVIDENCE: 3 works — blast radius green: 22 dependent(s), 13 extra test file(s) ⟂57065ab3ea96
- 2026-10-02T08:58:56Z COMMIT: aa6afa294 feat(roster): assign and change a shift's Day Type through the roster API → review+cross-app dispatched
- 2026-10-02T09:01:02Z COMMIT: aa6afa294 feat(roster): assign and change a shift's Day Type through the roster API → review+cross-app dispatched
EVIDENCE: 2 slice 3 Desk dialog + month view Day Type: node 10/10 (4 new); test_roster 16/16; _valid_day_type returns None before the schema update (review aa6afa294 W1); W2 read-select: Frappe Cloud updates the schema during maintenance, accepted
- 2026-10-02T09:01:44Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 5 file(s) ⟂5d9cef17ceeb
- 2026-10-02T09:01:47Z COMMIT: b89f4791c feat(roster): HR sets the Day Type in the Desk Roster → review+design dispatched
EVIDENCE: 2 test_roster 17/17 fresh.local incl. repeating schedule carries Off Day to every created shift (review b89f4791c W: schedule path dropped day_type)
- 2026-10-02T09:02:56Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-02T09:03:00Z COMMIT: 8993f5f80 fix(roster): a repeating schedule dropped the Day Type HR chose → review dispatched
EVIDENCE: 3 slice 4 Nadi Team roster Day Type: frontend yarn test 1588/1588, vite build OK; team-roster-assign 8/8 (3 new)
- 2026-10-02T09:05:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-02T09:05:10Z COMMIT: 60610277c feat(team): supervisors set the Day Type in the Nadi Team roster → review+design dispatched
- 2026-10-02T09:05:58Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-02T09:06:04Z COMMIT: 7ad9678dc fix(team): a screen reader did not hear a day's Day Type → review+design dispatched
NEXT: alpha.32 pushed (Day Type). Deploy; HR sets one day PH and checks its OT price. Pre-existing: test_ot_calculation 2 red on HEAD.
- 2026-10-02T09:06:31Z COMMIT: 253fcef96 chore(release): 2.0.0-alpha.32 — Day Type on the Roster → review+deps dispatched
EVIDENCE: 3 fresh.local persona: Shift Supervisor lists only their report's Attendance + Employee Checkin, reads it, write False, create False, stranger False; plain employee unchanged; sidebar shows Attendance after patch (ran twice); other sidebar doctypes list 0 team rows. stub test_supervisor_team_view 6/6 red first
- 2026-10-02T09:43:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-02T09:43:10Z COMMIT: d425496e5 feat(desk): a Shift Supervisor sees their team's attendance and clock-ins → review dispatched
NEXT: alpha.33 pushed (supervisor team attendance view). Owner to confirm supervisors may see clock-in location/device fields.
- 2026-10-02T09:44:29Z COMMIT: 3022951d4 chore(release): 2.0.0-alpha.33 — Supervisors See Their Team's Attendance → review+deps dispatched
EVIDENCE: 2 test_roster 21/21 fresh.local; old delete_shift_schedule_assignment -> repeating-schedule delete ERROR (red); roster dialog node 12/12 incl. class guard (no frappe.client writes in roster/src; old dialog had 2); roster vite build OK
- 2026-10-03T03:19:03Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-10-03T03:19:14Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-10-03T03:19:37Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 9 file(s) ⟂79474414be21
- 2026-10-03T03:19:41Z COMMIT: bb6400b3a fix(roster): a Shift Supervisor was refused deleting or updating a shift → review+design dispatched
EVIDENCE: 2 review bb6400b3a W: supervisor whole-assignment delete/update/inactive/schedule-delete now refuse worked days (HR keeps power); test_roster 22/22; class guard widened (bulk_update, desk.form.save, .setValue., list .update.submit) 12/12
- 2026-10-03T03:22:38Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 4 file(s) ⟂bdfcc00ed624
- 2026-10-03T03:22:41Z COMMIT: 3759c2854 fix(roster): a supervisor could delete or cut a shift over worked days → review+design dispatched
NEXT: alpha.34 pushed (Fahmie roster delete/update). Open: clock-in location visible to supervisors — keep or hide.
- 2026-10-03T03:24:04Z COMMIT: 4b3b826bc chore(release): 2.0.0-alpha.34 — Supervisors Can Delete and Update Shifts → review+deps dispatched
- 2026-10-05 DEAD END: rostered punches "Not counted yet" (1-5 Oct) - no code regression found. The real hourly job marks Present on a local copy of shift "8.30AM - 5PM (PM&CK)"; marking/roster/Day Type tests green. Likely live Shift Type setup (Last Sync of Checkin stuck / Auto Update Last Sync off) - UNVERIFIED, needs live values.
- 2026-10-05 DEAD END: OT "0 h" on 3 Oct (shift 8:30-5, in 8:00, out 18:08) - stub test shows two silent-zero paths: minimum_overtime_minutes above the OT, and a punch missing shift_actual_end (ot_calculation.py _session_ot_slices gates on it though OT uses shift_end). Real cause unknown.
- 2026-10-05 PLAN: Approvals filter + bulk approve + table view + banner (no export, no gate): .claude/plans/current-plan.md (APPROVED line blank). Mockup: /home/nabil/mockups/mockup-approvals-table.html
NEXT: (1) get live Shift Type values (Enable Auto Attendance, Process Attendance After, Last Sync of Checkin, Auto Update Last Sync) or Error Log "Auto attendance failed for shift"; run attendance_day_audit.repair_attendance_days dry_run=1 for 1-5 Oct. (2) On owner "approved": red tests first for approval.check_many/decide_many, then build; fix mockup (check-in row in confirm sheet, clipped Approver line).
- 2026-10-05 PLAN A step 1 (server): hrms/api/roster.change_shift_from + hrms/utils/shift_change.plan_change. EVIDENCE: 2 correct - test_shift_change.py 13 green (red seen first: module missing, then every-day-beside-another test failed before its guard); probe on fresh.local as real calls: punched date refused and roster unchanged, 9-6->10-7 ends old 11 Oct and starts new 12 Oct, repeat is idempotent, Mon-Thu+Fri makes the right weekday split, non-HR refused. hrms/api/test_roster.py::TestHRChangesAShiftFromADate written but NOT run (bench run-tests is env-broken, see verify-bench note).
NEXT: Plan A step 2 = Desk dialog "Change shift from..." (mockup + owner sign-off first), then Plan B1 check_many/decide_many.
- 2026-10-05T07:17:13Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-05T07:17:13Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-05T07:17:15Z COMMIT: 12fff2dd5 feat(roster): HR can change a person's shift from a date → review dispatched
- 2026-10-05T07:19:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-05T07:19:54Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-05T07:19:56Z COMMIT: a0c3d9651 fix(roster): changing a shift from a date touched rows the old ERP owns → review dispatched
- 2026-10-05T07:22:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-05T07:22:05Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-05T07:22:08Z COMMIT: e0f1f31ea fix(roster): a shift change could mis-set the Day Type and miss a stamped punch → review dispatched
- 2026-10-05 PLAN A reviews: 12fff2dd5 + a0c3d9651 + e0f1f31ea reviewed, no Critical. Fixed: Day Type only from the ended assignment, shift_start punches count as worked, mirrored schedules left alone, malformed shifts refused plainly, mirrored assignments refused. Refactor ticket still owed: move change_shift_from's "what was worked" reads into hrms/utils/shift_change.py (roster.py is a hotspot).
- 2026-10-05 PLAN B step 1 (server): approval.check_many / decide_many (+ BULK_CAP 50). EVIDENCE: 2 correct - test_approval_bulk.py 15 green (red first: 14 failed, module functions missing). Real fresh.local probe: 2 of 3 leaves approved, the one with no balance left refused with the controller's words and stays Open, a missing request reported gone, repeat is a no-op. LIMIT: check_many judges each request alone, so two requests competing for one balance both read "ready"; decide_many then refuses the second truthfully.
NEXT: Plan A step 2 (Desk dialog "Change shift from...", mockup + sign-off first), Plan B step 2 (Approvals page: chips, select, banner, table, confirm sheet; fix mockup: remove check-in row, clipped Approver line). Nothing pushed.
- 2026-10-05T07:24:47Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-05T07:24:47Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T07:24:48Z COMMIT: f3f0a587a feat(approvals): approve many requests at once, each checked first → review dispatched
- 2026-10-05T07:28:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-10-05T07:28:29Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T07:28:39Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-05T07:28:39Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T07:28:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-05T07:28:59Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T07:30:30Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T07:30:30Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T07:30:33Z COMMIT: 225d95f41 fix(approvals): bulk approve could deadlock, hide a lost transaction, or skip the revision check → review dispatched
- 2026-10-05 PLAN B step 1 reviews: f3f0a587a + 225d95f41 reviewed, no Critical. Fixed: fixed lock order, abort on lost transaction (reuses offshift_punch_heal._lost_transaction, imported lazily), revision required, text-only names. Refactor tickets filed in ticket-roster-py-refactor.md (roster.py + approval.py). OPEN: day_remark after_commit callbacks of a rolled-back bulk item not confirmed to re-read state (ticket).
- 2026-10-05 MOCKUPS: /home/nabil/mockups/mockup-approvals-table.html (Check-in rows now 1x, never selectable) and /home/nabil/mockups/mockup-change-shift-from.html (new) await owner sign-off. Nothing pushed.
NEXT: owner signs off the two mockups, then Plan A step 2 (Desk dialog) and Plan B step 2 (Approvals page).
- 2026-10-05T07:32:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T07:32:44Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T07:32:47Z COMMIT: e44496ed5 fix(approvals): bulk approve crashed on non-text names and loaded attendance code on every request → review dispatched
- 2026-10-05 PLAN A step 2 (Desk dialog): hrms/public/js/change_shift_from.bundle.js, loaded at boot (hooks.py app_include_js), button "Change shift from..." under Actions on a submitted Shift Assignment, HR only. EVIDENCE: 2 correct - node tests 8 green (red first: file missing), hrms/tests/test_change_shift_screen.py 7 green, each of 5 breaks (endpoint renamed, GET, button for everyone, weekday spelling, not loaded) fails a test. 3 works - ran the dialog in a real browser with a faked frappe: preview reads "Until 2026-10-11: no change | From 2026-10-12: 10am-7pm (Mon, Tue, Wed, Thu); 10am-4pm (Fri) | No shift on: Saturday, Sunday."; three presses in one instant = one server call; payload matches the endpoint. NOT verified: bench build (node 22 here, frappe wants >=24, so `bench build` fails with or without this change; esbuild alone bundles the file, 8 KB, syntax ok) and the dialog inside real Desk.
OPEN: roster row-menu door (Vue roster app) not built; the form door is. Approvals page UI (Plan B step 2) not built.
- 2026-10-05T07:44:10Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 5 file(s) ⟂5d9cef17ceeb
- 2026-10-05T07:44:10Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-10-05T07:44:14Z COMMIT: 0c5327a15 feat(desk): HR can change a person's shift from a date on the Shift Assignment form → review+design+cross-app dispatched
- 2026-10-05T07:49:30Z EVIDENCE: 6 behaves — family hunt: class=a dialog that shows only what HR typed and swallows what the server said. The shift; 40 call site(s) given verdicts, 4 same-root ⟂b7295ee5c9cb
- 2026-10-05T07:49:49Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 7 file(s) ⟂85be7f79c548
- 2026-10-05T07:49:49Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-05T07:49:55Z EVIDENCE: 6 behaves — family hunt: class=a dialog that shows only what HR typed and swallows what the server said. The shift; 40 call site(s) given verdicts, 4 same-root ⟂b7295ee5c9cb
- 2026-10-05 PLAN A step 2 reviews of 0c5327a15 (frappe-reviewer: no Critical; cross-app: SAFE; design-reviewer: FIX_CRITICAL on a11y). FIXED: server refusal was never shown (frappe.messages.slice is not an array in v16 -> TypeError; now reads _server_messages), chips have aria-pressed + full weekday name + reason when disabled + focus kept, visible labels per shift, preview is a live region, errors role=alert, busy label "Changing...", shift labels carry their hours, translated "{0}, from {1}". NEW: hrms.api.roster.preview_shift_change (read-only, HR only) so the dialog names the one-day changes the date will drop and refuses a worked day as soon as the date is picked; change_shift_from and the preview share ONE read (_assignments_and_worked_days) and ONE rule (plan_change). EVIDENCE: 2 correct - 63 python + 15 node tests green (red first; 3 breaks each fail a test). 3 works - real fresh.local probe: preview and change agree (punched day refused in both; preview lists the removable assignment), non-HR refused; real browser run with a REAL-shaped frappe (messages is an object): refusal text reaches HR, focus stays on a toggled chip, 2nd-row chips named+disabled, preview aria-live. NOT verified: the dialog inside real Desk (bench build needs node >=24, here 22).
- 2026-10-05T07:49:56Z COMMIT: 7dd5e3aa8 fix(desk): the shift change dialog hid the server refusal and said nothing about what it drops → review+design dispatched
- 2026-10-05 PLAN A step 2 pass 3 (reviews of 7dd5e3aa8: frappe-reviewer no Critical, design pass 2 FIX_WARNINGS). FIXED: live regions are in the dialog from the start and only their text changes; ask_server drops an answer still on its way on EVERY path (cleared date, removed shift), a failed preview redraws; shift list that fails or is empty says so; focus goes to a new shift row; "A day can be on one shift only." hint; the form door formats the date. EVIDENCE: 3 works - real-browser run: late reply after a cleared date does NOT repaint the old refusal; failed preview shows the local preview only; 11 python + 15 node tests green, each of 3 breaks fails a test. LEFT (deliberate, noted): chips are btn-sm (24-28px, matches mockup; Desk admin tool); no 7-day grid in the preview; no remove-row button; HR-with-User-Permission preview test.
- 2026-10-05 PROVE-RED escape used (PIPELINE_SKIP_PROVE_RED=1, once, for the "repaint a refusal for a cleared date" fix): the gate re-ran the UNCHANGED change_shift_from.bundle.test.js against HEAD (green by construction) and reported my 4 new tests as green-before. Run by hand against HEAD's bundle, test_change_shift_screen.py goes 4 failed / 7 passed (the 4 new tests are exactly the red ones); against the fix 11 passed. LEARNING(gate): a fix whose new tests are Python-only is blamed for the mapped JS file's old tests -> prove-red should judge only the files this commit changes.
- 2026-10-05 PLAN B step 2 (Approvals page): frontend/src/utils/approvalBulk.js (pure: chips, ageing, ticks, select-all, itemsFor, afterApprove), Approvals.vue (banner, type chips, Select mode, per-request ticks, sticky "Approve N" bar, confirm sheet "N ready / N will be refused"), tests approvals-bulk.test.js (15) + approvals-bulk-page.test.js (14). EVIDENCE: 2 correct - 45 node tests green across the 5 approvals suites; 7 page breaks + 6 helper breaks each fail a test. 3 works - ran the REAL page (vite dev + stubbed API) in a 390px browser: banner "7 waiting. Oldest since 17 Aug.", chips, Overtime filter narrows groups to 2, Select all ticks 6 of 7 and the check-in row is NOT tickable, sticky bar "6 selected / Approve 6", confirm sheet "4 ready / 2 will be refused" with the reason, Approve 4 -> decide_many called ONCE with the ready ones and the revision, toast "4 approved". Caught on the way: two `const selected` (renamed ticked), the empty-state v-else hung on the wrong element (now v-if="!rows.length"), a chip colour token that did not exist (--g-ground -> --g-bg).
NOT BUILT: the desktop Table view (columns, sort, search) - HR's "datatable"; select mode + chips work on desktop too. NOT verified: inside the real app against the real server; dark theme; 320 px reflow.
- 2026-10-05T08:02:27Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-05T08:02:35Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-10-05T08:03:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-05T08:03:12Z COMMIT: 5943dfa58 feat(approvals): the bookkeeping for filtering and approving many requests → review+design dispatched
- 2026-10-05T08:03:26Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-05T08:03:30Z COMMIT: 83a7113e8 feat(approvals): filter by type and approve many requests at once → review+design dispatched
- 2026-10-05 PLAN B step 2 fix found while the reviewers ran: ages and the banner used the UTC date (new Date().toISOString().slice(0,10)), so an approver at UTC+8 between midnight and 8 am saw every wait one day short (verified: a request really 1 day old read 1 vs 2 by the site calendar). Now siteToday(new Date(), siteTimeZone()) (new, tested: KL 23:30Z -> next day; bad zone falls back). 49 node tests green; the page test fails if the UTC date comes back.
- 2026-10-05T08:05:46Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-05T08:05:50Z COMMIT: 6e0415333 fix(approvals): a wait read one day short for an approver before 8 am in Malaysia → review+design dispatched
- 2026-10-05 PLAN B reviews of the Approvals page (frappe-reviewer: 1 CRITICAL; design: FIX_WARNINGS, 5 warnings). CRITICAL FIXED (server): check_many handed back the server's FRESH `modified`, so a request the employee edited after the approver's list loaded would go through for dates the approver never saw (the check only covered check -> approve). Now it compares the revision the approver SAW and refuses a mismatch as "changed"; ready rows keep the approver's revision. EVIDENCE: 21 python tests (red first: 2 failed), 2 breaks each fail a test; real fresh.local probe: a leave edited after the list loaded is refused "changed" at the check AND by decide() if sent anyway; the other two behave as before.
OPEN from the reviews (page): ticks outlive the filter and Other-teams rows can be ticked unseen (Select all runs over visibleRows incl. Other teams) -> scope pickable/itemsFor to Yours + the filter and clear ticks on a filter change; sticky bar vs tab bar + safe area; age badge contrast (3 of 4 below 4.5:1); in-sheet failure state with retry; "nothing tickable" hint for Check-ins; dismiss while working. Desktop Table view (searchRows/sortRows done + tested, UI not built).
- 2026-10-05T08:08:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-05T08:08:29Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T08:08:34Z COMMIT: b5dd26acb fix(approvals): bulk approve could approve dates the approver never saw → review dispatched
- 2026-10-05T08:11:32Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-05T08:11:36Z COMMIT: 2c5d0ce57 fix(approvals): Select all ticked requests nobody could see → review+design dispatched
- 2026-10-05 PLAN B page fixes after the reviews (frappe-reviewer + design): Select all / Approve now cover only what the approver can SEE ticked (Yours, not check-ins) and follow the filter (keepVisible drops ticks no longer shown; itemsFor runs over visibleRows); a filter with nothing tickable says "These are approved one by one"; a failed check/approve stays IN the sheet with "Nothing was approved. Your ticks are kept." + Try again (no vanishing toast); closing the sheet while the server is approving is ignored; age badge tint 14% -> 8% (3 of 4 cases were under 4.5:1); "Select all in this filter" -> "Select all shown". EVIDENCE: 63 node tests green; 4 page breaks each fail a test. NOT YET DONE: sticky bar vs the floating tab bar + safe-area (needs a look in the real app), the desktop Table view UI (searchRows/sortRows exist, tested), in-app dark theme and 320px check.
- 2026-10-05 PLAN B DSN-2 (design pass 1): the sticky "Approve N" bar used bottom:0, which sticks to the scrollport edge the floating tab bar overlays, with no safe area. Now bottom: max(var(--padding-bottom,0px), env(safe-area-inset-bottom,0px)) (ion-content's own tab-bar reservation, theme/glass-components.css:66-72) and the page gets 88px of padding while the bar shows. Tests pin both (red first). NOT verified by eye on a device/in the real app (Approvals is a tab child at router/index.js:190, so the tab bar is present); iOS safe area + the 320px check still need a look.
- 2026-10-05T08:13:51Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T08:13:53Z COMMIT: 49b360546 fix(approvals): the Approve bar sat under the tab bar → review+design dispatched
- 2026-10-05 PLAN B review round 3 (frappe-reviewer: no Critical; design pass 2: FIX_WARNINGS). FIXED: (1) the sheet cannot be closed under a working request - the refusal now lives in GModal (new `dismissible` prop: Close button + scrim + Ionic gestures/Escape via can-dismiss) because ignoring did-dismiss in the handler leaves is-open true after Ionic closed the overlay; (2) a failed APPROVE no longer says "Nothing was approved" (decide_many may have got some through): its own phase "We could not confirm what was approved. The list is reloading." and the reload is wrapped; (3) age badge: measured 8% tint = 4.37/4.20 on --g-bg, plain ink = 4.86/4.83 -> no tint; (4) dead `retry` field removed; (5) the sticky bar sits above the tab-bar reservation + safe area. EVIDENCE: 170 node tests green incl. every glass test; 4 breaks (modal closable, Ionic gesture, Close/scrim, wrong failure text) each fail a test; vite build compiles. STILL OPEN: i18n (__(chip.label) is dynamic - add literals), a one-line "N approved one by one" for hidden rows in select mode, desktop Table view UI, 320px/dark/iOS look, the bar's margin/radius on desktop (design suggested).
- 2026-10-05T08:16:01Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-05T08:16:06Z COMMIT: 987a14819 fix(approvals): the Approve sheet could be closed under a working request → review+design dispatched
- 2026-10-05 REVIEW 987a14819 final (frappe-reviewer): no Critical. WARNING for the owner: the Approve sheet cannot be closed while "working", with no timeout, so a request that never returns leaves no way out. Recommended: after ~20 s allow close + "Taking long?" hint. Not built.
- 2026-10-05T08:35:17Z PUSH: nz-glass @ af05c1670
- 2026-10-05T09:03:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-05T09:03:59Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-05T09:04:06Z COMMIT: 473d9cf11 fix(auth): the next person on a shared phone kept getting the last person's pushes → review+security+design dispatched
- 2026-10-05 AUTHZ HUNT (3 hunters + my own probes; reports in /tmp/hunt/*.md). OWNER RULINGS TODAY: (1) H1 System Manager must NOT approve/reject check-ins outside the area: "HR only"; (2) H2 leave reason: "approvers yes, others no". FIXED H1: _is_routed_approver now uses HR_SEE_ALL_ROLES (not System Manager), and validate_inherited_checkout no longer keeps its own System-Manager list (uses may_decide). PROVEN on fresh.local before/after: an admin-only login was ADMITTED by remote_checkin._ensure_approver for another company's check-in, now REFUSED; an admin who also holds HR Manager keeps the right. Tests: 13 + 4 green (red first). AU-1 (push token after logout) fixed in 473d9cf11.
STILL OPEN from the hunt: H2 leave reason to managers who are not approvers (ruled, not built; get_leave_applications api/__init__.py:1116 + matrix wording); H3 finalize on an undecided request: NOT REPRODUCED (own employee is refused at the read gate; named approver is refused by each controller's on_submit status check, all 7 doctypes checked) - downgraded to a hardening note; M1 report_half_transitioned selects `company` from Compensatory Leave Request (no such column) -> 500 for HR; M3 appraisal raw identity (Desk only); M5 upload_base64_file attached_to_field client-supplied; L4 get_leave_approver raw compare; AU-2..5 session UX; M1/M2 flows: rejection REASON missing from the employee's notification, no approver told when the approver field is blank; stale tests fixed below.
- 2026-10-05T09:15:42Z EVIDENCE: 6 behaves — family hunt: class=a decision gate that names System Manager next to the HR roles, so an admin-only lo; 5 call site(s) given verdicts, 2 same-root ⟂101f7acbc7fc
- 2026-10-05T09:17:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-05T09:17:17Z EVIDENCE: 3 works — blast radius green: 17 dependent(s), 14 extra test file(s) ⟂37afa90f943c
- 2026-10-05T09:17:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-05T09:17:34Z EVIDENCE: 3 works — blast radius green: 17 dependent(s), 14 extra test file(s) ⟂37afa90f943c
- 2026-10-05T09:17:48Z EVIDENCE: 6 behaves — family hunt: class=a decision gate that names System Manager next to the HR roles, so an admin-only lo; 6 call site(s) given verdicts, 1 same-root ⟂419e55a601b8
- 2026-10-05T09:18:33Z COMMIT: 9623902c1 test: two OT tests went stale and no longer tested what they say → review dispatched
- 2026-10-05T09:18:55Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-05T09:18:55Z EVIDENCE: 3 works — blast radius green: 17 dependent(s), 14 extra test file(s) ⟂37afa90f943c
- 2026-10-05T09:18:59Z EVIDENCE: 6 behaves — family hunt: class=a decision gate that names System Manager next to the HR roles, so an admin-only lo; 6 call site(s) given verdicts, 1 same-root ⟂419e55a601b8
- 2026-10-05T09:19:04Z COMMIT: 3faf00848 fix(approvals): a System Manager could decide any company's check-in outside the area → review dispatched
- 2026-10-05 H2 (leave reason) BUILT per the owner ruling "approvers yes, others no": new approval.may_read_leave_reason(doc, user) = the employee, an approver on the request's LINE (get_designated_approvers: the named approver, the reports_to manager, and each level up to HR Settings' approval_levels, default 2), or HR inside its company fence; NOT a System Manager alone, NOT someone past the levels. Asked by BOTH doors: get_leave_applications (reason blanked) and the Approvals page row. NOTE for the owner: the direct reports_to manager IS on the line by the 21 and 29 Sep rulings, so he still reads the reason (the 13 Sep audit said "manager never"; the access matrix now says what the code does). PROVEN on fresh.local (probe_h2e): employee/named approver/level-2 approver read it; a person past level 2 and a stranger are refused (the list endpoint itself refuses them). 9 + 31 tests green (red first), ACCESS-MATRIX updated.
- 2026-10-05T09:24:48Z EVIDENCE: 6 behaves — family hunt: class=a private field sent to everyone who can open the record. The leave REASON (Leave A; 8 call site(s) given verdicts, 3 same-root ⟂e237a6a149e5
- 2026-10-05T09:25:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-05T09:25:02Z EVIDENCE: 3 works — blast radius green: 15 dependent(s), 13 extra test file(s) ⟂08f9e39b63c4
- 2026-10-05T09:25:04Z EVIDENCE: 6 behaves — family hunt: class=a private field sent to everyone who can open the record. The leave REASON (Leave A; 8 call site(s) given verdicts, 3 same-root ⟂e237a6a149e5
- 2026-10-05T09:25:05Z COMMIT: a5fc9433f fix(requests): a person past the approval line could read a leave reason → review dispatched
- 2026-10-05T09:26:04Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-10-05T09:26:04Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 11 extra test file(s) ⟂e3a82f02d393
