2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
- 2026-09-28T04:01:39Z EVIDENCE: 3 works — blast radius green: 37 dependent(s), 23 extra test file(s) ⟂27ae31fb0871
- 2026-09-28T04:01:43Z COMMIT: 342e8ed58 fix(geofence): only HR can set someone's other sites; sync leaves them → review+deps dispatched
- 2026-09-28T04:02:29Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-28T04:02:35Z COMMIT: c00dd370e feat(checkin): the check-in screen shows the site you are actually at → review+design dispatched
- 2026-09-28T04:06:51Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-28T04:06:55Z COMMIT: 82c6e2dba fix(checkin): a site with no pin could be shown as the nearest → review dispatched
2026-09-28T04:45Z DEFERRED (owner, 28 Sep 2026): staff lockdown — Employee Self Service keeps Desk write on own Employee (Shift Location, Default Shift, Holiday List, Roster Managed) and delete on own requests because User Type saves re-grant it over staff_perm_lockdown; owner said yes to locking, then deferred. Multi-site fields are already permlevel 1 (HR only).
- 2026-09-28T05:03:44Z PLAN: approved 0cec142e1997 — # Plan — 28 Sep 2026: check in at more than one site (HR request)
- 2026-09-28T05:03:47Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9
- 2026-09-28T05:03:51Z COMMIT: 6a7e9341f fix(sheets): scrolling inside a sheet moved or closed the sheet → review+design dispatched
- 2026-09-28T05:17:49Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-28T05:17:54Z COMMIT: 430ebae46 fix(pwa): closing a request sheet threw inside the file preview → review+design dispatched
- 2026-09-28T05:18:09Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-28T05:18:13Z COMMIT: a77af51d5 fix(sheets): sheet content sat 3 px in, head rules fought, no keyboard scroll → review+design dispatched
- 2026-09-28T06:10:56Z COMMIT: d5b513081 chore(release): 2.0.0-alpha.16 — Steady Sheets and More Than One Site → review+deps dispatched
- 2026-09-28T06:12:14Z COMMIT: e00844f3d docs(handoff): alpha.16 done → review dispatched
- 2026-09-28T10:25:56Z PLAN: approved d14698ebb4f2 — # Plan — 28 Sep 2026: check in at more than one site (HR request)
- 2026-09-28T10:26:05Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 12 file(s) ⟂0fefc010db80
- 2026-09-28T10:26:05Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 6 extra test file(s) ⟂3652c40d4b9b
- 2026-09-28T10:26:09Z COMMIT: 401002df3 feat(home): Today shows when you came in and when you can leave → review+design dispatched
- 2026-09-28T10:34:03Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-28T10:34:03Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-28T10:34:11Z COMMIT: b0811eab8 fix(pwa): the update bar still came back on phones with a push relay → review dispatched
- 2026-09-28T11:18:49Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-28T11:26:02Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-28T11:26:07Z COMMIT: 13a5c511d fix(forms): hours on a sent request showed as 10.026111111 → review+design dispatched
- 2026-09-28T11:30:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-09-28T11:30:32Z COMMIT: 9fcbb79a6 test(ot): the reject-without-attachment test broke on Approved On → review dispatched
- 2026-09-28T11:30:52Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-28T11:30:52Z EVIDENCE: 3 works — blast radius green: 12 dependent(s), 11 extra test file(s) ⟂4b2afcdac5fd
- 2026-09-28T11:30:55Z COMMIT: 4bcce526c fix(leave): a half day off could not be approved on a day worked → review dispatched
- 2026-09-28T11:33:22Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-28T11:33:22Z EVIDENCE: 3 works — blast radius green: 12 dependent(s), 11 extra test file(s) ⟂4b2afcdac5fd
- 2026-09-28T11:33:25Z COMMIT: afd8b4503 fix(leave): the half-day fix missed saves that don't send the date → review dispatched
- 2026-09-28T11:52:15Z COMMIT: 46391957a chore(release): 2.0.0-alpha.17 — When You Can Leave → review+deps dispatched
- 2026-09-28T11:52:29Z PUSH: nz-glass @ 46391957a
- 2026-09-28T11:52:51Z PUSH: nz-glass @ c9dd97366
- 2026-09-28T11:52:51Z COMMIT: c9dd97366 docs(handoff): alpha.17 done → review dispatched
EVIDENCE: 3 alpha.17 — iOS gate 9/9 clean; fresh.local probes: half-day on Present -> Half Day, 20->19.5; no-date API save -> Half Day; HEAD refused both
NEXT: owner deploys alpha.17; Amy retests 29 Sep; then OT rates + roster Day Type once the rulings come back
- 2026-09-28T14:45:38Z PLAN: approved e94d0c8d5737 — # OT rates from the deploy date (owner rulings 28 Sep 2026)
- 2026-09-28T14:48:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-09-28T14:48:54Z COMMIT: 08d5f6f01 test(ot): three claim-capacity tests broke on Approved On → review dispatched
- 2026-09-28T14:54:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-28T14:54:08Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 18 extra test file(s) ⟂73a15faed7f1
- 2026-09-28T14:54:11Z COMMIT: 59d56d877 feat(ot): HR's new OT rates start on the deploy day, old days keep theirs → review dispatched
EVIDENCE: 3 OT dated rates — test_ot_rates_from_a_date 20 green (red on HEAD); every test_ot_* file green; fresh.local migrate + probe: pre-date PH10h RM300/off6h RM100/rest40m counts, deploy day+ RM220/RM120/40m no/55m yes; patch rerun no-op
NEXT: money review of the dated-OT-rates commit; then changelog + alpha.18 bump + release (after a clean review)
- 2026-09-28T14:57:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-28T14:57:53Z EVIDENCE: 3 works — blast radius green: 16 dependent(s), 8 extra test file(s) ⟂0fc2d17debed
- 2026-09-28T14:58:23Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-28T14:58:23Z EVIDENCE: 3 works — blast radius green: 16 dependent(s), 8 extra test file(s) ⟂0fc2d17debed
- 2026-09-28T14:58:42Z PLAN: approved e94d0c8d5737 — # OT rates from the deploy date (owner rulings 28 Sep 2026)
- 2026-09-28T14:58:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-28T14:58:50Z EVIDENCE: 3 works — blast radius green: 16 dependent(s), 8 extra test file(s) ⟂0fc2d17debed
- 2026-09-28T14:58:53Z COMMIT: ee5a974c0 fix(ot): an old day could still be priced at today's rates by mistake → review dispatched
- 2026-09-28T15:00:43Z COMMIT: ebf5701a1 test(ot): a shift with no overtime rates prices nothing and does not fail → review dispatched
- 2026-09-28T15:01:00Z PUSH: nz-glass @ 3873cdcf6
- 2026-09-28T15:01:00Z COMMIT: 3873cdcf6 chore(release): 2.0.0-alpha.18 — New Overtime Rates → review+deps dispatched
NEXT: owner deploys alpha.17 + alpha.18 together; after deploy check Shift Type OT rates show the dated rows; Amy retests 29 Sep
- 2026-09-28T15:01:21Z PUSH: nz-glass @ 6239be175
- 2026-09-28T15:01:21Z COMMIT: 6239be175 docs(handoff): alpha.18 done → review dispatched
- 2026-09-29T03:18:19Z PLAN: approved d24861845f8a — # alpha.19 — Team inside the Calendar, and approvers guided (owner, 29 Sep 2026)
- 2026-09-29T03:24:09Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-29T03:24:15Z COMMIT: 817230d33 fix(calendar): the day sheet said 6 and listed 5, and showed the team 3x → review+design dispatched
- 2026-09-29T03:36:01Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 7 file(s) ⟂85be7f79c548
- 2026-09-29T03:36:01Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 7 extra test file(s) ⟂d4b7f357f1bc
- 2026-09-29T03:36:07Z COMMIT: ee5192fa5 feat(calendar): a team lead sees how many of their team were off each day → review+design dispatched
- 2026-09-29T03:41:26Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-29T03:41:26Z EVIDENCE: 3 works — blast radius green: 11 dependent(s), 8 extra test file(s) ⟂2fe864bb96a3
- 2026-09-29T03:41:31Z COMMIT: 8b6bc1284 feat(approvals): an approver is told why before Approve, never after → review dispatched
- 2026-09-29T03:45:00Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-29T03:45:07Z COMMIT: 4582d3c84 feat(approvals): the approver sees why before pressing, not an error after → review+design dispatched
- 2026-09-29T03:45:40Z COMMIT: cf7ed8730 docs(approvals): say the dry run restores only the decision field → review dispatched
EVIDENCE: 3 alpha.19 slices — 817230d33 team once (Playwright: one heading, counts match), ee5192fa5 grid N off (manager 30 lines light+dark, staff 0, tiles 44px), 8b6bc1284 approver dry run (fresh.local: worked day -> [Rejected]+worked_day, 0 writes, 0 after-commit, real approve after ok; review no Critical), 4582d3c84 guidance note (Playwright: note + Reject only, 0 error toasts)
NEXT: read design-review verdict (agent a6c79b7da70e1d703) + iOS gate /tmp/ios_a19.out; fix any Critical; then CHANGELOG alpha.19 'Team in the Calendar and Guided Approvals' + package.json bump + scripts/release.sh + HANDOFF
- 2026-09-29T03:48:04Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-29T03:48:08Z COMMIT: ac9e864ae fix(calendar): a two-digit "off" count could widen a tile on a small phone → review+design dispatched
NEXT: wait for iOS gate /tmp/ios_a19.out (task b7fgc9gmq); if clean -> CHANGELOG alpha.19 'Team in the Calendar and Guided Approvals' + package.json bump + push + scripts/release.sh + HANDOFF.md. Design review FIX_WARNINGS handled (320px cap 9f…; contrast of leave/absent ink 4.56/4.54 on record, no change)
- 2026-09-29T04:02:52Z PUSH: nz-glass @ 32a5e86e1
- 2026-09-29T04:02:52Z COMMIT: 32a5e86e1 chore(release): 2.0.0-alpha.19 — Team in the Calendar and Guided Approvals → review+deps dispatched
NEXT: owner deploys alpha.17 + 18 + 19; then filer-side guidance (reuse _approve_would_refuse), roster Day Type (needs Desk screen name), balance strip (owner picks 1 of 3)
- 2026-09-29T04:03:10Z PUSH: nz-glass @ 5b4d55bdb
- 2026-09-29T04:03:11Z COMMIT: 5b4d55bdb docs(handoff): alpha.19 done → review dispatched
NEXT: alpha.20 per docs/glass/plan/NADI_2.0.0-alpha.20_PLAN.md — wait for owner: + (title bar) vs FAB, and go; then slice 1 (approval chain red test)
- 2026-09-29T04:55:42Z PUSH: nz-glass @ 1e96e3a96
- 2026-09-29T04:55:43Z COMMIT: 1e96e3a96 docs(plan): alpha.20 — approval chain, reminders, calmer Requests and Home → review dispatched
- 2026-09-29T05:06:14Z PUSH: nz-glass @ 3afeb5fc1
- 2026-09-29T05:06:14Z COMMIT: 3afeb5fc1 docs: how we work on Nadi 2.0 — the standard, in one place → review dispatched
- 2026-09-29T06:09:08Z PLAN: approved 298d26855ed6 — # alpha.20 plan (copy of docs/glass/plan/NADI_2.0.0-alpha.20_PLAN.md)
- 2026-09-29T06:25:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-29T06:25:36Z EVIDENCE: 3 works — blast radius green: 34 dependent(s), 22 extra test file(s) ⟂f542f42c1843
- 2026-09-29T06:25:40Z COMMIT: b98d3cdff fix(approvals): a manager was shown Approve, then refused → review dispatched
- 2026-09-29T06:27:22Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-29T06:27:22Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 14 extra test file(s) ⟂37e898c3addf
- 2026-09-29T06:27:26Z COMMIT: 5a67eca19 feat(settings): HR sets approval levels and reminder days in Desk → review+deps dispatched
- 2026-09-29T06:33:24Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-29T06:33:24Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 14 extra test file(s) ⟂37e898c3addf
- 2026-09-29T06:33:38Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-29T06:33:38Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 14 extra test file(s) ⟂37e898c3addf
- 2026-09-29T06:34:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-29T06:34:05Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 14 extra test file(s) ⟂37e898c3addf
- 2026-09-29T06:34:14Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-29T06:34:14Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 14 extra test file(s) ⟂37e898c3addf
- 2026-09-29T06:34:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-29T06:34:32Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 14 extra test file(s) ⟂37e898c3addf
- 2026-09-29T06:34:38Z COMMIT: ff2011c5c feat(settings): HR sets approval levels and reminder days in Desk → review dispatched
- 2026-09-29T06:34:57Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-29T06:34:57Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-29T06:35:22Z PLAN: approved 298d26855ed6 — # alpha.20 plan (copy of docs/glass/plan/NADI_2.0.0-alpha.20_PLAN.md)
- 2026-09-29T06:35:25Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-29T06:35:25Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-29T06:35:31Z COMMIT: 8b40b27c6 feat(approvals): approvers get a morning reminder, the backup only later → review+cross-app dispatched
- 2026-09-29T06:35:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-09-29T06:36:09Z COMMIT: 3321bccff test(approvals): the approval line reads a request but never edits it → review dispatched
- 2026-09-29T06:45:41Z EVIDENCE: 2 correct — mapped tests green (bun ) for 11 file(s) ⟂4c8e69619202
- 2026-09-29T06:45:47Z PLAN: approved 298d26855ed6 — # alpha.20 plan (copy of docs/glass/plan/NADI_2.0.0-alpha.20_PLAN.md)
- 2026-09-29T06:45:49Z COMMIT: ccbbe61e7 feat(requests): "+" in the title bar and leave balances as two numbers → review+design dispatched
- 2026-09-29T06:52:39Z PLAN: approved 298d26855ed6 — # alpha.20 plan (copy of docs/glass/plan/NADI_2.0.0-alpha.20_PLAN.md)
- 2026-09-29T06:52:40Z EVIDENCE: 2 correct — mapped tests green (bun ) for 11 file(s) ⟂4c8e69619202
- 2026-09-29T06:52:45Z COMMIT: f0a8f7998 feat(home): approvers see their queue on the Requests tab, Home stays quiet → review+security+design dispatched
- 2026-09-29T06:55:33Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-29T06:55:44Z COMMIT: ea9b0e8da fix(design): badge contrast headroom, a lone balance spans the row → review+security+design dispatched
- 2026-09-29T08:12:02Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9
- 2026-09-29T08:12:27Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9
- 2026-09-29T08:13:06Z PLAN: approved 298d26855ed6 — # alpha.20 plan (copy of docs/glass/plan/NADI_2.0.0-alpha.20_PLAN.md)
- 2026-09-29T08:13:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9
- 2026-09-29T08:13:12Z COMMIT: 2295b1f61 fix(home): the page jumped when an approver's queue arrived → review+design dispatched
- 2026-09-29T08:18:22Z PUSH: nz-glass @ ecfb1b60f
- 2026-09-29T08:18:22Z COMMIT: ecfb1b60f chore(release): 2.0.0-alpha.20 — Approval Line and a Calmer Home → review+deps dispatched
EVIDENCE: 4 alpha.20 — iOS gate 9/9 clean after jump fixes; fresh.local: reports_to manager approves expense+leave (was refused), line read-only (write refused), reminders delivered to owner+backup, badge 1 for manager / none for staff
NEXT: owner deploys alpha.17–20; alpha.21 per plan (undo withdraw, guide the filer, larger text)
- 2026-09-29T08:19:00Z PUSH: nz-glass @ a7f6f1ee3
- 2026-09-29T08:19:00Z COMMIT: a7f6f1ee3 docs(handoff): alpha.20 done → review dispatched
- 2026-09-29T08:25:42Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-29T08:25:48Z PUSH: nz-glass @ 11ac31d65
- 2026-09-29T08:25:48Z COMMIT: 11ac31d65 test: a stand-in document that refuses what a real one refuses → review dispatched
- 2026-09-29T08:45:36Z PLAN: approved 3a2d4a5e3ef1 — # alpha.21 plan (owner "go", 29 Sep 2026) — from docs/glass/plan/NADI_2.0.0-alpha.20_PLAN.md "Next
- 2026-09-29T08:45:41Z EVIDENCE: 2 correct — mapped tests green (bun ) for 11 file(s) ⟂4c8e69619202
- 2026-09-29T08:45:41Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-29T08:45:44Z COMMIT: f8b533e8d feat(requests): withdrawing a request is instant, with Undo → review+design dispatched
- 2026-09-29T08:49:07Z PLAN: approved 3a2d4a5e3ef1 — # alpha.21 plan (owner "go", 29 Sep 2026) — from docs/glass/plan/NADI_2.0.0-alpha.20_PLAN.md "Next
- 2026-09-29T08:49:14Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-09-29T08:49:19Z COMMIT: b540341bf feat(leave): you are told before Send when your leave would be refused → review+design dispatched
- 2026-09-29T09:43:58Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-29T09:44:02Z COMMIT: 378543412 fix(expenses): the page jumped 69 pt when the summary arrived → review+design dispatched
- 2026-09-29T09:44:20Z PUSH: nz-glass @ 68dc48b9c
- 2026-09-29T09:44:20Z COMMIT: 68dc48b9c chore(release): 2.0.0-alpha.21 — Undo and a Warning Before Send → review+deps dispatched
EVIDENCE: 4 alpha.21 — iOS gate 9/9 (scroll-and-shift 0 x3 after the Expense claims fix); fresh.local: Undo keeps / timeout withdraws; worked day caught before Send, nothing saved
NEXT: owner deploys alpha.17–21; alpha.22 = larger text (Dynamic Type via -apple-system-body; all font sizes to rem; ios gate at 200%)
- 2026-09-29T09:44:40Z PUSH: nz-glass @ 571046bdc
- 2026-09-29T09:44:41Z COMMIT: 571046bdc docs(handoff): alpha.21 done → review dispatched
- 2026-09-29T09:59:35Z COMPACT: context compacted — read the last NEXT above before continuing
NEXT: Fahmie roster access — owner to approve: Shift Supervisor on Shift & Attendance workspace + read on Branch/Designation (patch); attendance report for supervisors is a Reports-fencing decision
- 2026-09-29T10:45:45Z PLAN: approved ccc253034b67 — # Shift Supervisor can open the roster (Fahmie, 29 Sep 2026)
EVIDENCE: 3 fresh.local Shift Supervisor — /desk/shift-&-attendance getpage 403 before patch, none after; /hr/roster get_list 403x2 before, none after
- 2026-09-29T10:45:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-29T10:45:57Z COMMIT: 622b97917 fix(roster): a Shift Supervisor could not open the roster → review dispatched
DEAD END: frappe-reviewer on 622b97917 silent after one nudge (10-turn limit) — counts as FIX_CRITICAL, no deploy; re-review in the batch review with a larger budget
EVIDENCE: 3 fresh.local Shift Supervisor — Shift Assignment visible 0 -> 6 (team), insert_shift report OK, stranger PermissionError
- 2026-09-29T10:57:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-29T10:57:51Z COMMIT: e85839d28 fix(roster): a Shift Supervisor saw none of their team's shifts → review dispatched
NEXT: ticket-one-my-team-rule.md (review warning, not blocking)
- 2026-09-29T11:02:04Z PLAN: approved b0168fb4f2a4 — # Shift Supervisor can open the roster (Fahmie, 29 Sep 2026)
EVIDENCE: 3 fresh.local Monthly Attendance Sheet _Test Company — admin 7 employees, Shift Supervisor 0 (only own team), no role PermissionError; patch ran twice clean
- 2026-09-29T11:02:12Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-29T11:02:12Z EVIDENCE: 3 works — blast radius green: 12 dependent(s), 11 extra test file(s) ⟂4b2afcdac5fd
- 2026-09-29T11:02:16Z COMMIT: 3e9d43be0 fix(attendance): a Shift Supervisor could not report their team → review dispatched
NEXT: owner to say ship (release/push) for 622b97917 e85839d28 3e9d43be0; minor: workspace Attendance Count chart says 'Please select company.' for a user with no default company
- 2026-09-30T04:04:05Z COMMIT: 96cc2f87f chore(release): 2.0.0-alpha.22 — Shift Supervisors Can Roster Their Team → review+deps dispatched
EVIDENCE: 2 pre-push batch — 12 stub test files OK (roster/report/fence/workspace + importers), ruff clean
NEXT: owner deploys alpha.22 on Frappe Cloud, then Fahmie checks Desk Shift & Attendance + roster + Monthly Attendance Sheet
- 2026-09-30T04:05:10Z COMMIT: 772add72f docs(handoff): alpha.22 done → review dispatched
NEXT: owner deploys alpha.22 on Frappe Cloud; Fahmie checks Desk Shift & Attendance, roster (team shifts + add), Monthly Attendance Sheet (team only); then alpha.23 larger text on owner 'go'
- 2026-09-30T04:06:29Z COMMIT: d5e151cb7 chore(progress): alpha.22 evidence, next step and team-rule ticket → review dispatched
- 2026-09-30T04:41:30Z PLAN: approved 28937b8d3127 — # alpha.23 — theme choice back, no update popup (owner, 30 Sep 2026)
- 2026-09-30T04:41:34Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
EVIDENCE: 2 theme — theme-choice-in-you 4/4 red on HEAD, green after; 25/25 across theme/You/boot tests
- 2026-09-30T04:41:36Z COMMIT: 7d7b1b5c2 fix(you): theme switching was missing → review+design dispatched
EVIDENCE: 2 update popup — update-applies-quietly red (2 fail) before, 4/4 after; full frontend suite 1576/1576; vite build OK
- 2026-09-30T04:45:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 16 file(s) ⟂80a763f10cf1
- 2026-09-30T04:45:08Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-30T04:45:09Z COMMIT: 02d69dfec fix(pwa): remove the "A new version is ready" popup → review+design dispatched
EVIDENCE: 5 desktop 1440 light+dark — home/requests/calendar/you/leaves: sidenav on, 672 column centred, no h-scroll; You shows Appearance (Automatic) in dark
EVIDENCE: 5 iOS gate 9/9 OK, 0 findings (phone + desktop 1280, light + dark, installed-iPhone journey) on fresh.local with the alpha.23 bundle
- 2026-09-30T05:15:08Z COMMIT: fb6dc5745 chore(release): 2.0.0-alpha.23 — Choose Light or Dark Again → review+deps dispatched
NEXT: owner deploys alpha.23; then alpha.24 larger text on owner 'go'
- 2026-09-30T05:15:34Z COMMIT: d86508c67 docs(handoff): alpha.23 done → review dispatched
- 2026-09-30T05:16:24Z COMMIT: 8a641484a docs(handoff): name the alpha.23 release commit → review dispatched
EVIDENCE: 3 fresh.local Approva User — employee apps [] -> ['approva'] with role -> [] removed; patch twice clean; test_app_links 7/7 (1 red before)
- 2026-09-30T06:49:11Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-30T06:49:11Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-30T06:49:13Z COMMIT: ddaa02b12 feat(apps): an "Approva User" role that opens Approva and nothing else → review dispatched
- 2026-09-30T06:50:21Z COMMIT: 699adbb7f chore(release): 2.0.0-alpha.24 — Approva for Anyone Who Needs It → review+deps dispatched
NEXT: owner deploys alpha.24; give Approva User in Desk to whoever needs Approva; alpha.25 larger text on 'go'
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
