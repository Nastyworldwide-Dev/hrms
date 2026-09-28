2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
REPAIR: bbc69c614 update-prompt fallback timer; ad540b28c "(s)" wording -> countOf (13 sites)
EVIDENCE: 2 frontend 990/990 after ad540b28c
NEXT: review bbc69c614..ad540b28c together once an agent slot frees (3 executors running: live leave balance, grouped approvals, rest-day OT)
- 2026-09-23T10:57:04Z EVIDENCE: 2 correct — mapped tests green (bun ) for 10 file(s) ⟂f3b86cf4d3e6
- 2026-09-23T10:57:07Z COMMIT: 57eba0006 fix(words): departments showed as "Production - NW0A" → review+design dispatched
NEXT: batch review bbc69c614..57eba0006 (3 small frontend commits) when an agent slot frees
- 2026-09-23T10:58:37Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-23T10:58:41Z COMMIT: b91698cef fix(layout): short pages scrolled for nothing under the tab bar → review+design dispatched
NEXT: batch review bbc69c614..b91698cef (4 small frontend commits) when an agent slot frees
- 2026-09-23T11:00:00Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
NEXT: batch review bbc69c614..HEAD (5 small frontend commits)
- 2026-09-23T11:00:06Z COMMIT: 2711d83f6 fix(lists): team requests had a second home beside Approvals → review+design dispatched
- 2026-09-23T11:01:28Z COMMIT: d92780f40 docs(access): who sees and does what in Nadi, as the code stands → review dispatched
REPAIR: b91698cef double tab-bar padding; 2711d83f6 team tabs off lists; d92780f40 ACCESS-MATRIX.md (docs)
EVIDENCE: 2 leave balance slice: test_approver_sees_the_balance_approve_uses 7/7, test_approval 37/37, comp_leave 16/16, decision_access_properties 1/1; test_a_decision_is_always_recordable 11 pass + 3 Shift fails that are red on clean HEAD (skip-tests used for that reason)
- 2026-09-23T11:04:16Z COMMIT: bece07866 test(shift): three shift-request tests failed on a missing name, not a rule → review dispatched
REPAIR: 14a27160e live leave balance (slice A); bece07866 shift test lift missing names
FINDING: 15 backend test files fail when run alone (/tmp/perfile.out) — ALL also fail at alpha.3 7f6449fb8, so none is an alpha.4 regression. Families: stale tests after rulings (reject-needs-reason, announcements audience, SOP/company fence). Triage each: stale test vs real defect.
- 2026-09-23T11:11:32Z EVIDENCE: 2 correct — mapped tests green (bun ) for 10 file(s) ⟂f3b86cf4d3e6
- 2026-09-23T11:11:34Z COMMIT: d83acb1b1 feat(header): the Nadi mark leads every tab page; the date moves into Today → review+design dispatched
- 2026-09-23T11:12:59Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-09-23T11:13:04Z COMMIT: 470867da6 fix(words): Home would say "2 attendance fixs to approve" → review+design dispatched
EVIDENCE: 3 rest-day OT: fresh.local probe Sun 13:37 outside 15:00-23:30 stamped shift, offshift 0; test_restday_offshift_ot 7/7; checkin_shift_stamp 6, offshift_punch_heal 40, checkin_override 14; test_ot_nonworking_hours 1 fail pre-existing at 7f6449fb8 (skip-tests reason)
- 2026-09-23T11:14:46Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T11:14:49Z COMMIT: d3d588a08 fix(header): a screen reader said "Nadi" twice on Home → review+design dispatched
REPAIR: 470867da6 plurals from server; 5f9cb5d33 rest-day OT (slice C); d83acb1b1 header mark; d3d588a08 header a11y + dead CSS
- 2026-09-23T11:16:34Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-09-23T11:16:38Z COMMIT: d3d588a08 fix(header): a screen reader said "Nadi" twice on Home → review+design dispatched
- 2026-09-23T11:17:03Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-09-23T11:17:07Z COMMIT: 44d886d0d feat(reports): HR can see who has no shift, so no overtime goes uncounted → review dispatched
REPAIR: 44d886d0d Staff Without A Shift report
REVIEW 5f9cb5d33: reviewer FIX_CRITICAL was process-only — tests were run pre-commit (7/7 + 60 related), overtime_type exists on Shift Assignment json. Real side effect: rest-day off-window punch now gets a shift, so geofence applies (lenient -> Remote Checkin Request; strict -> refused) where before it silent-allowed "No Shift". Matches "check in as normal"; FLAG for owner in HANDOFF.
- 2026-09-23T11:22:46Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 9 file(s) ⟂79474414be21
- 2026-09-23T11:22:46Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T11:22:50Z COMMIT: b12fd210f feat(approvals): the queue is grouped — Yours, then Other teams → review+design dispatched
REPAIR: b12fd210f grouped Approvals (slice B + page), Home counts yours only
- 2026-09-23T11:24:53Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-23T11:24:57Z COMMIT: c49b731c1 fix(home): blocks vanished when empty, so Home read as broken → review+design dispatched
- 2026-09-23T11:25:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
REPAIR: c49b731c1 Home never-empty; fix Approvals Other-teams heading
- 2026-09-23T11:25:20Z COMMIT: 30c11bfb0 fix(approvals): screen readers could not find "Other teams" by heading → review+design dispatched
- 2026-09-23T11:27:18Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T11:27:21Z COMMIT: 2d10eb07b feat(requests): Annual and Medical on top, every balance one tap away → review+design dispatched
REPAIR: 2d10eb07b Requests R2 balances (pinned 2 + All balances sheet). NEXT: Requests one-screen (last 5 + See all), Calendar key R1, Score R3, sheet words P1-5, notifications P1-6
- 2026-09-23T11:28:31Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T11:28:33Z COMMIT: 41ab5256c fix(requests): "Show more" poured out every request at once → review+design dispatched
- 2026-09-23T11:29:48Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T11:29:51Z COMMIT: 0c80f1f15 fix(calendar): the key changed from month to month → review dispatched
REPAIR: 41ab5256c Requests paged 20; 0c80f1f15 calendar full key. QUEUED REVIEW: 2d10eb07b..0c80f1f15
- 2026-09-23T11:31:11Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T11:31:14Z COMMIT: 42bd5b17c fix(score): no review said who scores you twice → review+design dispatched
- 2026-09-23T11:31:40Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-23T11:31:43Z COMMIT: a1911f88e fix(requests): "Annual" was never pinned on a site that calls it Privilege → review+design dispatched
- 2026-09-23T11:32:08Z COMMIT: a711e6555 test(fence): two test files had gone stale behind real code changes → review dispatched
- 2026-09-23T11:32:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-23T11:32:59Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T11:33:03Z COMMIT: 5da924b1e fix(dates): announcements and leave expiry used the server's day → review dispatched
REPAIR: 42bd5b17c Score R3; a1911f88e pin privilege/earned + v-show; a711e6555 stale fence/allowance tests; 5da924b1e employee clock in announcements + requests_summary
OWNER DECISIONS PENDING (access/permission, report-only): A5 announcements get_reach/get_outstanding read Employee without company fence (fenced HR sees other companies' names) announcements.py:_audience_employees, get_outstanding; A6 shift_assignment.json System Manager permlevel-1 row with no level-0 row (ba5ddce9d) — may abort migrate.
- 2026-09-23T11:35:12Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-23T11:35:15Z COMMIT: 19e77c1fd fix(sheets): the approval sheet said "Leave Application", an ID and "Open" → review+design dispatched
- 2026-09-23T11:36:05Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 3 file(s) ⟂892bfc303afb
- 2026-09-23T11:36:11Z COMMIT: eca50e974 refactor(requests): drop the flag paging replaced; look the employee up once → review+design dispatched
EVIDENCE: 3 re-ran review EXECUTE for 2d10eb07b..eca50e974 myself (reviewer skipped it): ruff clean; api_clean_errors 10, company_fence 42, attendance_allowance 13, approvals_list 28, live balance 7, restday OT 7, staff_without_shift 6, plurals 3, decision_recordable 14; frontend 1038/1038
- 2026-09-23T11:38:08Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 9 file(s) ⟂79474414be21
- 2026-09-23T11:38:08Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-23T11:38:12Z COMMIT: bf646a4b9 feat(calendar): Travel, Training and Open request on the calendar → review+design dispatched
REPAIR: 19e77c1fd sheet plain words; eca50e974 cleanup; bf646a4b9 calendar Travel/Training/Open. NEXT: notifications P1-6, check-in camera dark P1-5, sweep remaining 8 stale tests, then release
- 2026-09-23T11:39:51Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T11:39:54Z COMMIT: 48eb45aba fix(notifications): a system notice showed a grey "?" as its sender → review+design dispatched
- 2026-09-23T11:43:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-23T11:43:54Z COMMIT: 367c95d8c fix(checkin): the camera box was a white slab in dark mode → review+security+design dispatched
REPAIR: 48eb45aba notifications; 367c95d8c camera dark + Approvals flattened (gates all OK); stale tests batch 2 committed
OWNER DECISIONS PENDING (report-only, access/security): A7 local HR_ROLES copies in restamp.py:48, attendance_fix_day.py:65, attendance_master_edit.py:73 (same values today, drift risk); A8 api-contract gate does not count get_current_employee( as a guard (calendar.get_month_flags, now.get_now, request_counts) — no leak today.
STILL RED pre-existing: test_pwa_resource_states (2), test_selfie_is_private_and_attached (1), utils/test_timezone (2) — not reached.
- 2026-09-23T11:44:25Z COMMIT: 187d65217 test: five more test files had gone stale behind deliberate changes → review dispatched
- 2026-09-23T12:03:21Z COMMIT: 5fe5cb7b1 chore(release): 2.0.0-alpha.4 — approvals grouped, rest-day OT, sheets fixed → review+deps dispatched
FINDING: utils/test_timezone red only under the bench-free stub (frappe.utils.get_datetime_in_timezone not stubbed -> MagicMock); code is a 2-line mirror of frappe now_datetime. Needs real bench or a stub entry; not a product defect.
EVIDENCE: 3 alpha.4 release: frontend 1045/1045; design gates lint/usage/contrast/surfaces/tokens/scale/motion OK (a11y/visual/coherence need served audit); e2e sheet-closes, sheet-is-tappable, sheet-leaves-with-page, nav-motion, critical-paths, reflow-320, kpi-back, back-race(ITER=1) green on the alpha.4 build
NEXT: owner deploys v2.0.0-alpha.4; then owner decisions A5-A8 in HANDOFF; P1-1 Home one-screen + P1-2 Requests one-screen still open
- 2026-09-23T12:08:03Z COMMIT: 6f6733e1b docs(release): alpha.4 handoff and tag note → review dispatched
RULING 23 Sep (owner "b" then "ok"): hold deploy; build Home one-screen (Today, NEWS moved up under Today, This week, Coming up, Waiting on you, never-empty) + Requests one-screen (New request, balances line, Needs attention, last 5 + See all) + check-in/out reminders (15 min after shift start if not in; 30 min after shift end if still in; opt-out switch on You, default on; no manager copy; friendly short tone; only people with a shift that day). One deploy after.
- 2026-09-23T12:34:10Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-23T12:34:10Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 0 extra test file(s) ⟂91e50812f2cb
- 2026-09-23T12:34:33Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-23T12:34:33Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 0 extra test file(s) ⟂91e50812f2cb
- 2026-09-23T12:35:12Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-23T12:35:12Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 0 extra test file(s) ⟂91e50812f2cb
- 2026-09-23T12:35:47Z PLAN: approved 7530b57748ee — # Check-in / check-out reminders (alpha.4)
- 2026-09-23T12:35:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-23T12:35:53Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 0 extra test file(s) ⟂91e50812f2cb
- 2026-09-23T12:35:56Z COMMIT: 50403096f feat(reminders): a nudge when you forget to check in or out → review+design+cross-app dispatched
- 2026-09-23T12:38:24Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 12 file(s) ⟂0fefc010db80
- 2026-09-23T12:38:24Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T12:38:28Z COMMIT: 2a6e8baa1 feat(home): one screen — Today, News, This week, Coming up, Needs you → review+design dispatched
- 2026-09-23T12:40:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 10 file(s) ⟂f3b86cf4d3e6
- 2026-09-23T12:40:21Z COMMIT: ca6a6b9d9 feat(requests): one screen — New request, balances line, last 5, See all → review+design dispatched
- 2026-09-23T12:41:11Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-23T12:41:13Z COMMIT: d090a4897 fix(reminders): one failed reminder could cancel everyone else's → review dispatched
- 2026-09-23T12:47:43Z EVIDENCE: 2 correct — mapped tests green (bun ) for 12 file(s) ⟂1127c68211d5
- 2026-09-23T12:47:46Z COMMIT: 805bb5738 fix(home): Home ran over its six glass surfaces; the header lost its right side → review+design dispatched
EVIDENCE: 3 alpha.4 final: frontend 1070/1070; gates all OK (surfaces 0 over); e2e 23 passed 4 skipped on final build; backend touched files green; ruff hrms/ clean
- 2026-09-23T12:50:03Z COMMIT: 8c41e4a8d chore(progress): alpha.4 final evidence → review dispatched
- 2026-09-23T13:35:14Z COMPACT: context compacted — read the last NEXT above before continuing
NEXT: alpha.5 plan written (docs/glass/plan/NADI_2.0.0-alpha.5_PLAN.md); waiting on Nabil's go + 2 answers (sketch first? notification wording PWA-only?)
- 2026-09-23T14:01:33Z COMMIT: 412622e70 docs(plan): alpha.5 proposal — whole app on one shell, glass on chrome only → review dispatched
NEXT: waiting on Nabil: 'go' on alpha5-review.html + 4 conflicts (H1,H4,C4,H3)
- 2026-09-23T14:51:15Z PLAN: approved 75c9b8b6d304 — # Nadi 2.0.0-alpha.5 — whole app, one design (owner "go till finish", 23 Sep 2026)
PLAN: alpha.5 go from owner 23 Sep (sleeping; complete to deploy-ready). Conflicts as recommended.
- 2026-09-23T14:53:50Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 14 file(s) ⟂e8a8a521fe15
- 2026-09-23T14:53:50Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 15 extra test file(s) ⟂33c05d5d9756
- 2026-09-23T14:53:53Z COMMIT: 894cec929 fix(time): the PWA read every server time on Dubai's clock → review+design dispatched
EVIDENCE: 2 S1 894cec929 — pytest test_pwa_boot_timezone 2/2, yarn test 1070/1070, ruff clean (run by advisor; reviewer hit turn limit)
- 2026-09-23T14:56:45Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-09-23T14:56:48Z COMMIT: 92e6ec6b6 test(time): boot zone test no longer asserts an unreachable None → review dispatched
- 2026-09-23T15:02:56Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-23T15:02:59Z COMMIT: 2a6366232 fix(glass): the frost sat on the content, not on the controls → review+design dispatched
EVIDENCE: 3 S3 glass-chrome-only 3/3, gates OK (contrast on glass-fill ≥4.5 both themes); design review FIX_WARNINGS = served a11y/visual not run -> covered by S10 served walk
- 2026-09-23T15:10:57Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 15 file(s) ⟂4dfab182ad5c
- 2026-09-23T15:10:57Z EVIDENCE: 3 works — blast radius green: 10 dependent(s), 11 extra test file(s) ⟂bffee3af90b2
- 2026-09-23T15:11:01Z COMMIT: 2564a835a fix(attendance): today read as "no attendance"; Calendar left it blank → review+design dispatched
- 2026-09-23T15:14:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-23T15:14:02Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 2 extra test file(s) ⟂ce54683ec640
EVIDENCE: 3 S2 2564a835a + overnight fix — worked_one_rule 9/9, home 12/12, calendar_kinds 15/15, frontend 1091 (+1 known unwired), gates OK; review DEPLOY (overnight warning fixed)
- 2026-09-23T15:14:05Z COMMIT: 914145e1c fix(attendance): a night shift across midnight never counted as worked → review dispatched
- 2026-09-23T15:14:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-23T15:14:59Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 2 extra test file(s) ⟂ce54683ec640
- 2026-09-23T15:15:02Z COMMIT: 914145e1c fix(attendance): a night shift across midnight never counted as worked → review dispatched
- 2026-09-23T15:15:16Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-23T15:15:16Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 2 extra test file(s) ⟂ce54683ec640
- 2026-09-23T15:15:18Z COMMIT: 3b205b47c fix(attendance): a check-out days later made a forgotten day look worked → review dispatched
EVIDENCE: 6 review a40d806 FIX_CRITICAL refuted — 'open' is read only as open_today (calendar.py:409, calendarDayState.js:10); past forgotten check-outs surface via the lone-IN Fix path, not punch_days. worked_days 10/10, home 12/12, calendar 15/15.
- 2026-09-23T15:22:10Z EVIDENCE: 2 correct — mapped tests green (bun ) for 18 file(s) ⟂8670267188cb
- 2026-09-23T15:22:13Z COMMIT: e223cad2c fix(shell): screens outside the tabs still wore the old Frappe header → review+design dispatched
- 2026-09-23T15:23:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 18 file(s) ⟂8670267188cb
- 2026-09-23T15:23:49Z COMMIT: e61bf5e29 fix(forms): every form still drew its fields with the old Frappe kit → review+design dispatched
- 2026-09-23T15:28:29Z EVIDENCE: 2 correct — mapped tests green (bun ) for 14 file(s) ⟂ae4f8cfceb8c
- 2026-09-23T15:28:32Z COMMIT: 7ceb369d6 fix(words): hours as decimals, IN/OUT, a date field losing its seconds → review+design dispatched
EVIDENCE: 3 S4 e223cad2c review DEPLOY; S6 e61bf5e29 review FIX_WARNINGS (seconds) -> fixed in wording commit; wording commit 1114/1114
- 2026-09-23T15:30:32Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T15:30:34Z COMMIT: 01c83997b fix(words): zero hours left "Absent ." and " overtime" → review+design dispatched
EVIDENCE: 2 zero-hour guard 1115/1115 (red first); small follow-up to reviewed 7ceb369d6 — covered by the S10 final review; hotspot ticket filed
- 2026-09-23T15:41:09Z EVIDENCE: 2 correct — mapped tests green (bun ) for 27 file(s) ⟂b60f9a35b391
- 2026-09-23T15:41:12Z COMMIT: 5dfa3ebc9 fix(sheets): every sheet drew its own head, or none → review+design dispatched
- 2026-09-23T15:44:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 189 file(s) ⟂c16a4ac47bb7
- 2026-09-23T15:44:45Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T15:44:49Z COMMIT: bb0b5db0f fix(help,notifications): drowning in ids, full names and 3-line rows → review+design dispatched
EVIDENCE: 3 S8 review DEPLOY; v-html gap closed by advisor (Notifications/Help: none; remaining 3 via safeHtml); tel/mailto vue-bound. Ticket: notificationLine reads English issue sentences; non-en site falls back to id-stripped sentence (upgrade: build issue messages structurally server-side).
- 2026-09-23T15:53:21Z EVIDENCE: 2 correct — mapped tests green (bun ) for 191 file(s) ⟂71065483d73f
- 2026-09-23T15:53:24Z COMMIT: 36a6a7668 fix(states): screens said "nothing" when they meant "still loading" → review+design dispatched
EVIDENCE: 3 S7 review DEPLOY (KPI markup-only confirmed; approve never danger; pending blocks double submit). S5 review DEPLOY.
- 2026-09-23T16:04:23Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 175 file(s) ⟂f3657a42e8f5
- 2026-09-23T16:04:23Z EVIDENCE: 3 works — blast radius green: 8 dependent(s), 8 extra test file(s) ⟂895605e4b558
- 2026-09-23T16:04:27Z COMMIT: 569648a51 fix(calendar,forms): Claim offered twice; forms showed table names → review+design dispatched
- 2026-09-23T16:06:18Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-23T16:06:18Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
EVIDENCE: 3 S9 review DEPLOY; approver warning fixed (8/8); formTitle covers all 7 FormView doctypes; leave ?date= new-doc only (Form.vue:49)
- 2026-09-23T16:06:21Z COMMIT: edc7eec61 fix(calendar): "Claim waiting with" could name a disabled approver → review dispatched
- 2026-09-23T16:18:27Z COMMIT: 4e7411442 fix(forms): every open request still showed its raw id in the header → review+design dispatched
EVIDENCE: 6 release review 8c41e4a8d..HEAD FIX_CRITICAL (unverified risks) refuted by advisor: FormView imports ErrorMessage/Dropdown/Dialog (FormView.vue:375-383), <Button> global (main.js:65), You->Approvals (Profile.vue:206); backend 47/47 + ruff clean; frontend 1168/1168; gates OK
EVIDENCE: 5 served gates on the alpha.5 build: a11y OK (76 screen-themes, 0 new), visual OK (0 differ), coherence OK (38 screens, 0 violations); e2e sheet specs 8/8; PIPELINE_SKIP_TESTS for coherence.spec.js (Playwright spec, not a bun test)
- 2026-09-23T17:19:35Z COMMIT: 07bb1249d chore(release): 2.0.0-alpha.5 — one design across the whole app → review+deps dispatched
NEXT: deploy 2.0.0-alpha.5 (Nabil); nothing else pending
- 2026-09-23T17:20:15Z COMMIT: fd503ed1f docs(handoff): alpha.5 done — deploy only → review dispatched
- 2026-09-24T01:45:27Z COMPACT: context compacted — read the last NEXT above before continuing

NEXT: alpha.6 — research (Apple HIG iOS 26 + UX writing), audit the PWA against it, triage the 8 screenshot defects, then plan with evidence before code.
EVIDENCE: 5 alpha6 controls measured live (e2e probe, /tmp/alpha6/controls.json): form fields radius 0 (FormView.vue:1023) vs pickers 12px/44px
NEXT: alpha.6 plan written (docs/glass/plan/NADI_2.0.0-alpha.6_PLAN.md) — waiting on owner answers to its 4 questions, then slices A→E
RULING (owner 24 Sep): Q1 yes — requests say "Send to {name}" not Save. Q2 delegated to Claude. Q3 not sideways scroll: pages that should only move vertically can be dragged freely sideways (Time off seen). Q4 unsure, delegated. Owner asks: 360 audit vs iOS 26 Liquid Glass (Apple only, no Material), per page purpose/contents/actions, checklist + violations, native feel, no jargon.
DECISION (delegated Q2): section headings grey (Footnote, secondary) — COLOR/WWDC25 219: tint only the primary action.
DECISION (delegated Q4): hide Expense posting_date from employees — each Expense Claim Detail row has its own expense_date; posting_date is an accounting date, defaults to today.
EVIDENCE: 5 Time off sideways drag = WebKit native date input ignores width:100% unless appearance:none + min-width:0 (not reproducible in Chromium); fix in .g-datefield input.
EVIDENCE: 3 journey_every_request.py on fresh.local 24 Sep: 87 checks 0 fail — 5 staff-filed types + routing (chain/HR/double-decide/remote) + CLR approver side
RULING (owner 24 Sep): frontend adapts to the existing backend; never change backend to make the PWA work. Desk config gaps are reported, not patched.
NEXT: UI journeys (Playwright, staff+approver taps) then Desk-field→PWA display map, then alpha.6 slices
EVIDENCE: 3 alpha6-journey.mjs 24 Sep: staff files Time off/Fix a day/Shift change/Expense via real forms, approver decides each via Approvals UI — 8/8, server state verified
EVIDENCE: 5 approval sheet shows "Fri 18 Sep" under title after 45f1d5efb (screenshot /tmp/alpha6/journey/13)
FINDING: expense approval sheet shows Posting Date, Total Taxes and Charges, Total Advance Amount, Status Draft + Approval Waiting (two statuses) — alpha6 slice B/C
FINDING: readiness gaps not checked: expense type account (2), company payable account (3), leave period (5), shift OT tab (4 partial) — readiness.py collect_facts
NEXT: overtime + readiness gaps + alpha6 slice A (shift truth, empty sections, approver names, WebKit date width)
EVIDENCE: 3 phase A done 24 Sep: A0 45f1d5efb A2 shift default A3 temporal inputs A4 empty sections A5 approver names A6 expense sheet A7 readiness — frontend 1195/1195, journey 10/10
NEXT: phase B — B1 one field style (FormView.vue:1023 radius-0 override first)
EVIDENCE: 3 phase B done 24 Sep: grouped forms, you settings, new request sheet, iOS type ramp + grey headers, one button height, sheet close leading — frontend 1215/1215, gates OK, journey 10/10 after B1
NEXT: phase C — C1 words gate, C2 Send to {name}, C3 overtime list, C4 long lists, C5 underlined links
- 2026-09-24T04:46:15Z COMPACT: context compacted — read the last NEXT above before continuing
EVIDENCE: 3 motion/sheet e2e 25 Sep: nav-motion 3/3, sheet-closes 5/5, sheet-is-tappable 3/3, sheet-leaves-with-page 3/3 green; back-race failed once under 15-spec load, then passed standalone at BACK_RACE_ITER=7 (full 7 rounds) — contention, not a regression
EVIDENCE: 3 alpha6-sheets.mjs 25 Sep: 9/9 reachable sheets clean (close leading, titled, no jargon/email/heavy/overflow, closes)
NEXT: phase E — E1 whole-app audit to 0, E2 journeys, E3 coverage list, E4 gates + tag v2.0.0-alpha.6
EVIDENCE: 4 v2.0.0-alpha.6 tagged a3b02ead0, pushed; served gates a11y/coherence OK, visual re-baselined 0 differ; audit 205 views clean; journeys 87/87 + 10/10
NEXT: owner deploys 2.0.0-alpha.6; after deploy check Home shift line, Time off on iPhone, one approval
EVIDENCE: 5 WebKit 26.5 runs locally WITHOUT sudo (24 Sep): webkit-ubuntu-24.04 build + apt-get download deps unpacked to ~/.local/webkit-deps, symlinked into minibrowser-*/sys/lib. iPhone 15 Pro emulation: Time off page 393 wide, no sideways scroll, date fields 223/233px.
FINDING: WebKit shows an "Install Nadi" lime banner (frappe-ui Popover, InstallPrompt.vue) over forms in Safari — alpha7 item.
FINDING: WebKit renders empty date inputs as blank (no value pill) and switch attribute unsupported in this WPE build (desktop UA).
FINDING: WebKit (Safari engine) 25 Sep: InstallPrompt.vue iOS banner white-on-lime contrast 1.18, covers every page in Safari; frappe-ui tailwind plugin sets html font-family InterVar before -apple-system (buttons/body render Inter); sheets 10/10 open in WebKit.
NEXT: when /tmp/alpha7/wk-audit/audit.jsonl completes, compare with /tmp/alpha6/shots3 (chromium), add a "Safari-only findings" section to docs/glass/plan/NADI_2.0.0-alpha.7_PLAN.md, report to owner; then await "go" for alpha.7 phase 0 (live defects).
EVIDENCE: 5 WebKit whole-app audit 205 views = chromium on every measure; sheets 10/10; Safari-only: install banner contrast 1.18, InterVar before system font — plan §11
NEXT: await owner "go" for alpha.7 phase 0 (live defects 0.1–0.11)
RULING (owner 25 Sep): Q2 coloured icon tiles YES; "go till finish", owner deploys.
- 2026-09-24T10:02:49Z COMPACT: context compacted — read the last NEXT above before continuing
NEXT: alpha.7 Phase 1 (frame + colour) — plan §5 / task #2; Phase 0 done (e7a0e86c9 ceafa03e2 576014ab6 437442e7f pushed)
NEXT: alpha.7 Phase 2 Home (plan §3 + §10.3 order: title, Announcements first, Today card, week, Needs you); Phase 1 done c2c163d70 (title collapse -> Phase 6)
NEXT: alpha.7 Phase 3 lists/forms/details (§5.3-5.5); Phase 2 done a22a4681f
NEXT: alpha.7 Phase 4 controls (native switch, toasts->banners, alerts); Phase 3 done bd9ed9b52
NEXT: alpha.7 Phase 5 announcements (§4 + §10.1); Phase 4 done 5a1ed0192
NEXT: alpha.7 Phase 6 (badge, wake lock, title collapse, dynamic type; offline check-in RULED OUT by owner 'never ever offline checks in'); Phase 5 done e71c8b29b
NEXT: alpha.7 Phase 7 prove (audit x2 engines, journeys, sheets, served gates, backend, server journey) + release
NEXT: owner deploys alpha.7 (v2.0.0-alpha.7); then Search ruling for alpha.8
NEXT: owner deploys nz-glass head (446b77b9f+); confirm live attendance for the two On Duty rows
NEXT: owner deploys nz-glass head; defect-family report docs/glass/audit/2026-09-25-defect-families.md
NEXT: owner deploys nz-glass head; confirm lag on iPhone; answer Desk 2-decimal display
- 2026-09-25T07:29:08Z COMPACT: context compacted — read the last NEXT above before continuing
EVIDENCE: 3 scroll-and-shift-audit 0/36 cold+warm; sheet-shift-audit 0/10; yarn test 1330+9 pass; gates OK (visual re-baselined d261bb7c4)
NEXT: alpha.9 D10/D11 — name not ID and no Company on own requests
EVIDENCE: 3 design/gates/ios.mjs OK (pages 0, sheets 0, page moves 0, sheet moves 0); yarn test 1356 pass; scale/lint/surfaces/tokens OK
NEXT: owner deploys nz-glass; then Search who-finds-whom ruling
NEXT: owner deploys nz-glass (alpha.8 r3 + alpha.9 + OT hours 1.50); then the Search who-finds-whom ruling
EVIDENCE: 4 bench probes (rolled back): AM half clears late at mid+5, keeps at mid+20; no-session refused; approver reads "Half day · AM"; Fix a day 09-18 -> Present 9h
NEXT: owner deploys nz-glass (alpha.8 r3 + alpha.9 + OT 1.50 + half-day AM/PM + Fix a day hours)
EVIDENCE: 3 ios gate 0/0/0/0; yarn test 1373 pass; bench probes: after-shift OT 1.0 -> 5.0 h via real approval hook; own approver saved over a sent higher-up; midnight button Check out at 00:01/01:01/03:00/05:59
NEXT: owner deploys nz-glass (2.0.0-alpha.10); HR works the Missed Check-outs After Midnight report
- 2026-09-26T02:56:22Z COMPACT: context compacted — read the last NEXT above before continuing
NEXT: alpha.11 pushed (tag v2.0.0-alpha.11); owner deploys; next asks come from the owner
NEXT: alpha.12 released (v2.0.0-alpha.12, GitHub Release); owner deploys; carried: Ionic core size, notifications grouping, request timeline, Calendar month summary
NEXT: alpha.13 planned (docs/glass/plan/NADI_2.0.0-alpha.13_PLAN.md); waiting on R5-R7 rulings
NEXT: alpha.13 slices 1-4 committed + pushed (timeline f33f82806, calendar 01aea95b8, notifications ff69c6bc1, perf 97f34aa77); slice 5 mockup mockups/mockup-nadi-a13-feedback.html awaits owner sign-off; then ios gate + re-baseline + release.sh
NEXT: alpha.13 released (v2.0.0-alpha.13); owner deploys; carried: Ionic core per-component imports for first paint < 5 s
- 2026-09-27T09:34:13Z COMPACT: context compacted — read the last NEXT above before continuing
NEXT: alpha.14 plan rev 2 written (docs/glass/plan/NADI_2.0.0-alpha.14_PLAN.md); wait for owner rulings R10-R13, then slice 0 (installed-iPhone gate profile)
NEXT: owner to choose — HR answers ROSTER_FACTS_NEEDED.md questions, or ship read-only Roster Patterns report; meanwhile start slice 0 (installed-iPhone gate profile)
EVIDENCE: 3 roster_patterns — 25 tests green; fresh.local migrate: report + links idx 15/19, card count 7; HR 22 rows, nadi.w0.employee refused
NEXT: after owner deploys, read Roster Patterns on live to design roster; meanwhile slice 0 (installed-iPhone gate profile)
EVIDENCE: 3 slice0 — device journey red on HEAD (J1 x5 after Back, J2 x29), green after c2ae0aa07 + 1dcc97700 (31 stops, 0); yarn test 1450/1450
NEXT: S1 — clear the nadi-pages cache on logout / user change
EVIDENCE: 3 S1 26dee5f1b — Chromium: nadi-pages held /hrms/home before logout, only a Guest page after. S2 1c802b294 — bench: GET 403, POST no CSRF 400, POST+CSRF handled
NEXT: slice 4 — check-ins row (B), long values stack (F), truncation (J), number spinner (I)
EVIDENCE: 3 slice4 — 398d149af check-in time at chevron (342/354); 996bc885f long manager name under label; 8d914bd50 picker whole + no spinner; yarn test 1464/1464; page-audit 402/1280, sheet, ios all 0
NEXT: slice 5 — check-in sheet (A): plain title, photo preview, quiet coordinates; every attachment previews
EVIDENCE: 3 slice5 — 27e4f4c9a check-in sheet (photo 480px loaded, stranger/guest 403, ZZAUDIT punch cleaned); e6c05c3d2 attachments preview (PDF mark + image thumb), ticket picks kept; yarn test 1477/1477
NEXT: slice 6 — G (no Add a file on decided), H (status out of bar), K (one empty state), L (Score tint bar), M, N, O (Your team group), P (version + release name, no date)
DEAD END: states-audit /settings O2 once (27 Sep), green on 2 reruns — timing flake, not a regression; watch it
EVIDENCE: 3 slice6a — b56499be9 version+name no date (You: 'Nadi 2.0.0-alpha.13'); ad5b63574 decided files read-only; 9635038cc status out of bar + reason sized; 380f306db balance only while writing; yarn test 1485/1485, page-audit 402 0, states 0 (1 flake /settings, 2 reruns green)
NEXT: slice 6b — K one empty state, L Score tint bar, N plain words (Fix a day, password rule), O 'Your team' group on More
DEAD END: committed 1334108aa before the full suite finished — api-contract went red; fixed next commit. Run yarn test BEFORE commit, not in the same command
EVIDENCE: 3 slice6b — a7eda6117 empty lists one voice + New in place; 5cb26c4d1 Score row; 1334108aa+cf857cb25 password rule live (bench policy on/off) + Fix a day words; b32f6880b Your team group; yarn test 1497/1497
NEXT: mockups E (balance strip) + calendar Me|Team -> owner sign-off; meanwhile S4 endpoint/CSRF sweep
EVIDENCE: 4 release v2.0.0-alpha.14 12e4084f3 tagged + GitHub Release; ios gate 8/8 at 0; states 0 on release build
NEXT: owner deploys alpha.14; then build balance strip + Team calendar on sign-off; design roster from live Roster Patterns
DEAD END: OT Hours prefill to 2 decimals (formatHoursCap) broke tests/ot-request-state 'storage-precision caps survive' — the claim must hold the exact proven figure (d58fa94af). Reverted; decide together with the rest-day rounding ruling (Q2)
NEXT: owner rules Q2 (rest-day OT exact vs half-hour bands); then fix the Hours display in the same slice
- 2026-09-28T02:04:15Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-28T02:04:27Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-28T02:05:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 9 file(s) ⟂0e91782f6c7d
- 2026-09-28T02:08:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-28T02:08:58Z COMMIT: 946ca6c55 chore(lint): en dashes in two docstrings, ruff's pyupgrade on its test → review dispatched
- 2026-09-28T02:09:48Z EVIDENCE: 2 correct — mapped tests green (bun ) for 9 file(s) ⟂0e91782f6c7d
- 2026-09-28T02:09:52Z COMMIT: 8009391fe fix(pwa): pull-to-refresh and infinite scroll never actually ran → review+design dispatched
- 2026-09-28T02:12:37Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-28T02:17:29Z COMMIT: 2b173f731 fix(pwa): drop nativeEl()'s wrapper fallback in GPullRefresh → review dispatched
- 2026-09-28T02:19:30Z PUSH: nz-glass @ 2b173f731
- 2026-09-28T02:50:51Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-28T02:50:51Z EVIDENCE: 3 works — blast radius green: 10 dependent(s), 8 extra test file(s) ⟂6837c933cc25
- 2026-09-28T02:50:55Z COMMIT: f56e7cc04 fix(calendar): team line said "not in yet" for people already in → review+design dispatched
- 2026-09-28T02:56:48Z EVIDENCE: 2 correct — mapped tests green (bun ) for 12 file(s) ⟂1127c68211d5
- 2026-09-28T02:56:53Z COMMIT: f7886d7c2 feat(calendar): the day sheet shows your team, by name → review+design dispatched
- 2026-09-28T02:59:02Z COMMIT: 98379a3f7 fix(calendar): "See all" and "Open team roster" read as one list → review dispatched
- 2026-09-28T03:04:40Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-28T03:04:40Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 2 extra test file(s) ⟂a5801cfef452
- 2026-09-28T03:05:30Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-28T03:05:31Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 2 extra test file(s) ⟂a5801cfef452
- 2026-09-28T03:05:34Z COMMIT: 38f6087ba feat(ot): OT Request report shows when it was approved and if it's paid → review+design dispatched
- 2026-09-28T03:07:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-28T03:08:04Z COMMIT: 87527bfde feat(more): TruTrip shortcut for business travel → review+design dispatched
- 2026-09-28T03:10:09Z COMMIT: b2c591dd7 fix(ot): Approved On can't be planted, Payment works on custom-perm sites → review dispatched
- 2026-09-28T03:30:41Z EVIDENCE: 2 correct — mapped tests green (bun ) for 17 file(s) ⟂da5fdd6c5fcd
- 2026-09-28T03:30:41Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-28T03:30:55Z COMMIT: b2f020a62 fix(pwa): "A new version is ready" kept appearing with nothing new → review+design dispatched
- 2026-09-28T03:34:30Z COMMIT: 6621d7bd9 fix(pwa): "A new version is ready" kept appearing with nothing new → review+design dispatched
- 2026-09-28T03:35:16Z COMMIT: 7b48b8fa5 chore(release): 2.0.0-alpha.15 — Your Team on the Calendar → review+deps dispatched
- 2026-09-28T03:37:03Z COMMIT: 67fb9d62d docs(handoff): alpha.15 done → review dispatched
- 2026-09-28T03:37:04Z EVIDENCE: 2 correct — mapped tests green (bun ) for 161 file(s) ⟂526748ab8aba
- 2026-09-28T03:37:36Z EVIDENCE: 2 correct — mapped tests green (bun ) for 161 file(s) ⟂526748ab8aba
- 2026-09-28T03:38:23Z EVIDENCE: 2 correct — mapped tests green (bun ) for 161 file(s) ⟂526748ab8aba
2026-09-28T03:45Z EVIDENCE: 4 works here — alpha.15 released (tag v2.0.0-alpha.15, 67fb9d62d pushed); calendar parity probe PASS on spoke.localhost, update bar 3 loads clear / dismiss sticks on fresh.local
2026-09-28T03:45Z NEXT: multi-site check-in (HR) — plan in .claude/plans/current-plan.md awaits owner go-ahead; on yes, slice 1 = employee_sites()/evaluate_sites() in hrms/utils/geofence.py with red tests first, then check the hub sync does not overwrite the new Employee fields
