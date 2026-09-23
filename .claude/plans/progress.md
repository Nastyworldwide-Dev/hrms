2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
- 2026-09-23T05:40:43Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-09-23T05:40:43Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-23T05:40:46Z COMMIT: 7bfda8858 fix(requests): the filter chips counted only the newest ten requests → review+design dispatched
- 2026-09-23T05:42:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T05:42:17Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-23T05:42:21Z COMMIT: 53ecc2bf3 test: three older suites still pinned the shapes today's fixes replaced → review dispatched
EVIDENCE: 2 P0-1..P0-13 committed (986a46e56..53ecc2bf3), each with a red-first test; frontend 872/872; approval suites 53 pass; live probes on fresh.local (reject reason, request counts, stuck sheet 3x3, reflow 5/5)
NEXT: P1-A foundation — F-1 blobs first, then F-3 portrait, F-2 version, F-4 motion, F-8/F-9 words
- 2026-09-23T05:46:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 20 file(s) ⟂9f33a174e0f9
- 2026-09-23T05:46:53Z COMMIT: 53ecc2bf3 test: three older suites still pinned the shapes today's fixes replaced → review dispatched
- 2026-09-23T05:47:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 20 file(s) ⟂9f33a174e0f9
- 2026-09-23T05:47:10Z COMMIT: eab1ab4de refactor(glass): remove the background blobs → review+security+design dispatched
- 2026-09-23T05:48:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T05:48:06Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-23T05:48:09Z COMMIT: 14682bc3e feat(pwa): lock the installed app to portrait on phones only → review dispatched
- 2026-09-23T05:49:30Z COMMIT: 763e02c92 feat(pwa): the app has a version, shown on You, with a changelog → review+design+deps dispatched
- 2026-09-23T05:50:11Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:50:15Z COMMIT: 8431e095c fix(sheets): drop a redundant pointer-focus rule the lint gate flagged → review+design dispatched
- 2026-09-23T05:53:36Z COMMIT: 41dab817e feat(motion): the right page transition on each device → review+design dispatched
EVIDENCE: 3 P1-A done so far: F-1 blobs (eab1ab4de), F-2 version 2.0.0-alpha.2 + CHANGELOG (763e02c92), F-3 portrait on phones (14682bc3e), F-4 motion per device (41dab817e, measured live)
NEXT: F-6 one error pattern (no raw server text, no double report), then F-8/F-9 words (sentence case, no caps, glossary), F-10 emoji/arrow/glow, F-11 fonts, F-12 CLS, F-13 tab labels, F-14 gates, F-15 role names
- 2026-09-23T05:54:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:54:59Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-09-23T05:55:02Z COMMIT: a3fe4b4a4 fix(errors): employees saw the server's raw permission sentence → review dispatched
- 2026-09-23T05:56:23Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-23T05:56:25Z COMMIT: 03b588737 refactor(glass): no greeting, no emoji, no arrows on actions, no glowing button → review+design dispatched
- 2026-09-23T05:57:55Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:57:55Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-09-23T05:57:59Z COMMIT: 8186e130d fix(errors): the load toast promised a pull-to-refresh that forms lack → review dispatched
- 2026-09-23T05:58:19Z COMMIT: 2990a116d fix(glass): the flat button's rims were raw colours, and its old glow token lingered → review+security+design dispatched
- 2026-09-23T06:00:23Z EVIDENCE: 2 correct — mapped tests green (bun ) for 44 file(s) ⟂624cc9eba258
- 2026-09-23T06:00:27Z COMMIT: e14a0d20c refactor(words): sentence case for every label, and one word per thing → review+design dispatched
EVIDENCE: 3 P1-A: F-6 errors (a3fe4b4a4, 8186e130d), F-8/F-9 words (e14a0d20c, sentence-case guard), F-10 decoration (03b588737, 2990a116d); frontend 896/896
NEXT: F-11 fonts (download Inter once), F-12 CLS, F-13 tab labels scale, F-15 role names out of Apps group, F-5 desktop sheets centred; then P1-B pages (Approvals+Requests first)
- 2026-09-23T06:02:13Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-23T06:02:22Z COMMIT: 07c51e2fa perf(fonts): Inter downloaded twice on every page → review+design dispatched
- 2026-09-23T06:05:18Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T06:05:21Z COMMIT: 1cdd9ff56 feat(home): Home shows what is true now and what waits on you, nothing else → review+design dispatched
- 2026-09-23T06:06:07Z COMMIT: 2818f671b refactor(words): two leftovers the sweeps missed → review+design dispatched
- 2026-09-23T06:06:18Z COMMIT: 9a3f97267 docs(glass): tab labels at large text need a design ruling → review dispatched
- 2026-09-23T06:07:25Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T06:07:36Z COMMIT: 3171fe30f fix(home): pulling down on Home refreshed lists Home no longer shows → review+design dispatched
EVIDENCE: 3 F-11 fonts 07c51e2fa (2 files/302 kB on Home), Home plan 1cdd9ff56 + 3171fe30f, words 2818f671b; frontend 906/906
NEXT: Calendar plan slice (01-calendar.md: absent style D1, today ring D6, legend only-occurring C6, two dots B1, day sheet one action, cuts D7-D9, hours as time D11, In/Out D12); F-13 needs owner ruling
- 2026-09-23T06:08:19Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T06:08:22Z COMMIT: 6f5835b0f fix(home): pulling down left the check-ins-to-approve count stale → review+design dispatched
- 2026-09-23T06:10:56Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T06:10:59Z COMMIT: 6f5835b0f fix(home): pulling down left the check-ins-to-approve count stale → review+design dispatched
- 2026-09-23T06:11:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T06:11:12Z COMMIT: 19d8e0b1b feat(calendar): the month, readable at a glance, with nothing repeated → review dispatched
- 2026-09-23T06:11:29Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9
- 2026-09-23T06:11:32Z COMMIT: e6e31cdaf feat(calendar): the month, readable at a glance, with nothing repeated → review+design dispatched
- 2026-09-23T06:14:23Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9
- 2026-09-23T06:14:26Z COMMIT: d9db1a0a0 feat(calendar): a day sheet that shows the day and the one thing it needs → review+design dispatched
- 2026-09-23T06:15:26Z COMMIT: 8f16f87ed fix(calendar): an absent day's numeral was below contrast in light mode → review+design dispatched
- 2026-09-23T06:15:55Z COMMIT: 24deded5a fix(calendar): the absent legend key still showed a fill the day no longer has → review+design dispatched
EVIDENCE: 3 Calendar plan: page+grid e6e31cdaf, day sheet + ?date= d9db1a0a0, absent contrast 8f16f87ed/24deded5a (contrast gate 20/20); frontend 924/924
NEXT: Requests page slice (audit-flows 4A): one New request button + type sheet (replaces 6 tiles), compact balances, cut unmarked-days row, rejected reason inline (get_rejection_reason); then Approvals page; F-5 desktop sheets
- 2026-09-23T06:19:25Z EVIDENCE: 2 correct — mapped tests green (bun ) for 9 file(s) ⟂0e91782f6c7d
- 2026-09-23T06:19:28Z COMMIT: 503b799c3 feat(requests): one New request button instead of six tiles → review+design dispatched
- 2026-09-23T06:19:55Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T06:19:58Z COMMIT: bc635174c fix(calendar): an absent today lost its outline to the today ring → review+design dispatched
EVIDENCE: 3 Requests one-button 503b799c3 (QuickLinks+GTileGrid deleted), absent-today bc635174c; frontend 920/920
NEXT: Approvals page (audit-flows 4B) = biggest remaining P1; then More/You per audit-pages 4; F-5 desktop sheets; HANDOFF + push at the end
- 2026-09-23T06:22:15Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T06:22:18Z COMMIT: 015901d24 fix(calendar): the today ring hid the half-day outline too; give today its own channel → review+design dispatched
- 2026-09-23T06:24:35Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 7 file(s) ⟂85be7f79c548
- 2026-09-23T06:24:39Z COMMIT: be4b81edf feat(approvals): one page for everything waiting on your decision → review+design dispatched
- 2026-09-23T06:24:57Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T06:25:00Z COMMIT: f0d953b41 fix(calendar): the today ring was too faint on a worked day → review+design dispatched
- 2026-09-23T06:25:01Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-23T06:30:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-23T06:30:56Z COMMIT: 459a9516e fix(approvals): an admin-only login saw every team's requests → review dispatched
- 2026-09-23T06:31:19Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T06:31:22Z COMMIT: b16b13f76 fix(approvals): a time-off-in-lieu row broke the sheet that decides it → review+design dispatched
- 2026-09-23T06:32:41Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T06:32:44Z COMMIT: 670893f15 fix(calendar): today was hard to see on half, leave and rest days too → review+design dispatched
- 2026-09-23T06:33:53Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 2 file(s) ⟂b55372be3803
- 2026-09-23T06:33:53Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 7 extra test file(s) ⟂d4b7f357f1bc
- 2026-09-23T06:33:56Z COMMIT: eaccb32bd test(approvals): pin the field map to the list the server really walks → review dispatched
- 2026-09-23T06:39:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-23T06:39:49Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-23T06:39:51Z COMMIT: 9204e9802 fix(checkin): a refused check-in outside the area said nothing about why → review dispatched
- 2026-09-23T06:44:25Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-23T06:44:25Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 4 extra test file(s) ⟂c68dc5c03ea4
- 2026-09-23T06:44:27Z COMMIT: 042edbe97 fix(checkin): Desk could still refuse a check-in without saying why → review dispatched
- 2026-09-23T06:47:03Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 22 file(s) ⟂16efdd472c5b
- 2026-09-23T06:47:07Z COMMIT: 52cc288ef feat(approvals): check-ins outside the area are decided with everything else → review+design dispatched
- 2026-09-23T06:51:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 11 file(s) ⟂4c8e69619202
- 2026-09-23T06:51:09Z COMMIT: 40133f8f3 feat(more): More holds only what no tab owns → review+design dispatched
- 2026-09-23T06:52:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T06:52:14Z COMMIT: e5cf10675 fix(approvals): a check-in's time read "Invalid Date" in its sheet → review+design dispatched
- 2026-09-23T06:55:40Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T06:55:43Z COMMIT: 7a09a90e5 fix(more): the holiday sheet could ask for nobody's holidays → review+design dispatched
- 2026-09-23T06:59:01Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 13 file(s) ⟂ad7bb4cb625b
- 2026-09-23T06:59:01Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-23T06:59:04Z COMMIT: 6288d058c feat(overtime): no banked overtime anywhere in the app → review+design dispatched
- 2026-09-23T07:03:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 11 file(s) ⟂4c8e69619202
- 2026-09-23T07:03:09Z COMMIT: 518a541e7 feat(you): who I am and how the app behaves, on one page → review+design dispatched
- 2026-09-23T07:06:37Z EVIDENCE: 2 correct — mapped tests green (bun ) for 17 file(s) ⟂da5fdd6c5fcd
- 2026-09-23T07:06:40Z COMMIT: fa429e100 refactor(type): no block capitals anywhere; spacing to match → review+security+design dispatched
- 2026-09-23T07:07:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-23T07:07:44Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-23T07:07:47Z COMMIT: 8fc7dbe6a fix(calendar): a missing announcement board blanked every employee's month → review dispatched
- 2026-09-23T07:08:28Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T07:08:30Z COMMIT: 01070b16d fix(you): the rework dropped two details and the "turned off" note → review+design dispatched
- 2026-09-23T07:11:38Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-23T07:11:38Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-23T07:11:40Z COMMIT: 3ce68a42e fix(calendar): the day sheet's "team" was everyone routed to you → review dispatched
- 2026-09-23T07:13:43Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-23T07:13:46Z COMMIT: 391ccefbb feat(calendar): one team line in the day sheet, opening Team on that day → review+design dispatched
- 2026-09-23T07:17:28Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T07:17:31Z COMMIT: 4e4af7332 fix(calendar): the team line and the Team page named one person twice → review dispatched
- 2026-09-23T07:19:15Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-23T07:19:18Z COMMIT: 474d12d34 feat(requests): what you already answered, in plain words → review+design dispatched
- 2026-09-23T07:20:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-23T07:20:09Z COMMIT: 3b0e65320 fix(requests): one missing request type blanked every filter count → review dispatched
- 2026-09-23T07:22:08Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-23T07:22:08Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T07:22:15Z COMMIT: 29d655127 refactor(apps): the server decides which sibling apps you are offered → review+design dispatched
- 2026-09-23T07:23:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-23T07:23:59Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T07:24:02Z COMMIT: f0cd01580 fix(approvals): your request could hide behind 50 older ones for others → review dispatched
- 2026-09-23T07:24:49Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-23T07:24:49Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T07:24:53Z COMMIT: 9840e2f89 perf(approvals): Home stops reading once it can say "20+" → review dispatched
- 2026-09-23T07:28:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T07:28:20Z COMMIT: 25479308e fix(sheets): on desktop a sheet hugged the bottom and left the nav live → review+design dispatched
- 2026-09-23T07:29:33Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-23T07:29:33Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T07:29:36Z COMMIT: b1d195fca fix(approvals): a scan that gave up was reported as "20+" → review dispatched
- 2026-09-23T07:32:39Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T07:32:44Z COMMIT: 111402a6d fix(requests): the page jumped when the balances arrived → review+design dispatched
- 2026-09-23T07:33:30Z COMMIT: 7ad5db300 docs(changelog): 2.0.0-alpha.2 — approvals, pages, and fixes since → review dispatched

EVIDENCE: 3 frontend 955/955 (yarn test), backend touched files green (approvals_list 16, app_links 5, request_counts 4, calendar soft 2, team 3, remote reject 6, remote request 10), design gates green (lint 119), live fresh.local checks: approvals list=Home per persona, team line -> /team?date, desktop sheet centred, Requests CLS 0.391 -> 0.058.
DEAD END: bench run-tests still broken (py3.14/orjson); verified per-file with stubs + live read-only probes.
NEXT: Nabil deploys nz-glass to Frappe Cloud; then F-13 tab-label ruling, OT form "Replacement Leave" option ruling (no banked OT policy), desktop drag-to-dismiss on centred sheets, per-list Team tabs cut.
- 2026-09-23T07:34:10Z COMMIT: 76240e245 docs(handoff): 2.0.0-alpha.2 ready to deploy → review dispatched
NEXT: push nz-glass after the CLS review (111402a6d) returns clean; Nabil deploys 2.0.0-alpha.2 on Frappe Cloud.
- 2026-09-23T07:34:31Z COMMIT: 0c6b45ffe chore(progress): next step recorded → review dispatched
- 2026-09-23T07:36:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T07:36:09Z COMMIT: b88f52ba5 fix(requests): a screen reader heard nothing while balances loaded → review+design dispatched
- 2026-09-23T07:36:32Z COMMIT: 5a4de55fd docs(handoff): latest commit and follow-ups → review dispatched
- 2026-09-23T07:37:48Z PUSH: nz-glass @ 5a4de55fd
- 2026-09-23T07:37:57Z PUSH: nz-glass @ 5a4de55fd
- 2026-09-23T07:38:54Z EVIDENCE: 3 works — scripts/smoke.sh on fresh.local: migrate clean, patches.txt fully applied, deciding-status columns live in the schema ⟂62ddd9a606da
DEAD END: 07:37 PUSH lines were refused pushes (release gate wanted tag v2.0.0-alpha.2), yet reset the evidence window; rung 2 for b88f52ba5 is at 07:36:06, full suite 957/957, rung 3 smoke at 07:38:54.
NEXT: Nabil deploys nz-glass (tag v2.0.0-alpha.2) on Frappe Cloud.
- 2026-09-23T07:39:24Z COMMIT: 3649de39e chore(progress): push evidence and next step → review dispatched
- 2026-09-23T07:44:52Z COMMIT: b55fe916b docs(glass): tab labels fit at 200% text now; F-13 needs no ruling → review dispatched
- 2026-09-23T08:40:47Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T08:40:50Z COMMIT: 7f6449fb8 fix(sheets): nothing inside an open sheet could be tapped → review+design dispatched
- 2026-09-23T08:41:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T08:41:10Z COMMIT: 1526e13bb fix(update): Reload on "A new version is ready" did nothing → review+design dispatched
- 2026-09-23T08:42:00Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T08:42:04Z COMMIT: 3b68f2cfe test(e2e): a sheet takes taps; page-motion ignores loading pulses → review dispatched
- 2026-09-23T08:42:10Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T08:42:13Z COMMIT: db0c599c6 fix(refresh): "Refreshing..." sat on top of the page with nobody pulling → review+design dispatched
- 2026-09-23T08:42:56Z COMMIT: eb0057205 chore(release): 2.0.0-alpha.3 hotfix — sheets tappable, reload works, refresh text hidden → review+deps dispatched
- 2026-09-23T08:43:20Z EVIDENCE: 3 works — scripts/smoke.sh on fresh.local: migrate clean, patches.txt fully applied, deciding-status columns live in the schema ⟂62ddd9a606da
- 2026-09-23T08:43:42Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T08:43:54Z COMMIT: 610614dd0 fix(update): a build that cannot take over was offered on every load → review+design dispatched
EVIDENCE: 3 hotfix alpha.3 — frontend 964/964, smoke pass, live fresh.local: sheet takes taps at 390 and 1280, day sheet button taps, sheet-leaves-with-page 3/3.
NEXT: Nabil deploys v2.0.0-alpha.3 hotfix; then alpha.4 plan (pages redesign + access matrix).
- 2026-09-23T08:44:29Z COMMIT: a3e83868a chore(progress): hotfix evidence → review dispatched
- 2026-09-23T08:49:30Z COMMIT: 81c21724a docs(plan): 2.0.0-alpha.4 plan for owner approval → review dispatched
- 2026-09-23T08:58:29Z COMMIT: 72dda5432 docs(plan): alpha.4 plan adds the 23 Sep live audit → review dispatched
- 2026-09-23T09:08:47Z COMMIT: 61381ddec docs(plan): alpha.4 grouped by priority, owner rulings R1-R4 in → review dispatched
- 2026-09-23T09:23:21Z COMMIT: fbc003fd4 docs(plan): alpha.4 element-by-element spec; Nadi mark in the header → review dispatched
- 2026-09-23T09:27:42Z EVIDENCE: 2 correct — mapped tests green (bun ) for 10 file(s) ⟂f3b86cf4d3e6
- 2026-09-23T09:27:46Z COMMIT: 1344b7cb7 fix(help): Help threw an error every time it opened → review+design dispatched
- 2026-09-23T09:28:49Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T09:28:52Z COMMIT: 30e6f96e0 fix(calendar): shift times read "9:00:" with a stray colon → review+design dispatched
- 2026-09-23T09:31:18Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T09:31:22Z COMMIT: e16828c1d fix(requests): money on Requests showed a currency code, not "RM" → review+design dispatched
- 2026-09-23T09:31:35Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-23T09:31:38Z COMMIT: 01ef697c0 fix(calendar): one shift-time format on Home, day sheet and Team → review dispatched
- 2026-09-23T09:33:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T09:33:55Z COMMIT: 8aea169f0 fix(you): "Your details" showed five rows with no label → review+design dispatched
- 2026-09-23T09:35:37Z COMMIT: 5c3d2bcd8 fix(calendar): the day sheet said "No shift" on a day you worked → review dispatched
- 2026-09-23T09:36:37Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-23T09:36:37Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-23T09:36:40Z COMMIT: 4063f95a1 fix(calendar): a night shift's morning check-out named the wrong day → review dispatched
- 2026-09-23T09:36:42Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-23T09:38:49Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T09:38:53Z COMMIT: 747fca364 fix(you): "Preferred email" never showed in Your details → review+design dispatched
- 2026-09-23T09:42:36Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T09:42:40Z COMMIT: e522bada8 fix(refresh): "Refreshing…" stuck after the first pull → review+design dispatched
- 2026-09-23T09:54:13Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-23T09:54:18Z COMMIT: eed4728f0 fix(sheets): tapping the dim area did not close the sheet → review+design dispatched
- 2026-09-23T09:57:13Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T09:57:16Z COMMIT: cb219b2c6 fix(sheets): Back right after opening a sheet left it over the next page → review+design dispatched
- 2026-09-23T10:01:55Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T10:01:57Z COMMIT: 92b2b6695 fix(sheets): the only way to close a sheet was to drag it down → review+design dispatched
REPAIR: alpha.4 P0 — 4063f95a1 night-shift day sheet; 747fca364 Preferred email field (prefered_email); e522bada8 refresh label; eed4728f0 scrim tap closes; cb219b2c6 Back mid-open; 15dd47210 sheet gate e2e; 92b2b6695 sheet Close (X)
EVIDENCE: 3 frontend 987/987; sheet e2e 11/11 (sheet-closes red 4/5 on 4063f95a1); pull probe second pull reads "Pull to refresh"
DEAD END: Vue <Teleport to="ion-app"> for the scrim — Ionic moves ion-modal, render throws nextSibling of null; scrim now hand-built (utils/sheetScrim.js)
NEXT: P0-9 held for owner ruling — no-shift day: server accepts a punch (rest-day work), so hiding Check in could block rest-day OT; then seed data, access matrix draft, sketches
- 2026-09-23T10:07:36Z COMMIT: 1604a7f53 docs(plan): P0-9 ruled (check in as normal); off-shift OT finding → review dispatched
PLAN: owner "go" 23 Sep evening — all 23 alpha.4 steps autonomously, push + tag, owner only deploys. No live-data repair, no access-rule change, no deploy.
- 2026-09-23T10:52:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T10:53:02Z COMMIT: bbc69c614 fix(update): a successful update was remembered as a failed one → review+design dispatched
- 2026-09-23T10:55:21Z EVIDENCE: 2 correct — mapped tests green (bun ) for 12 file(s) ⟂1127c68211d5
- 2026-09-23T10:55:21Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T10:55:24Z COMMIT: ad540b28c fix(words): counts read "1 leave request(s)" instead of "1 leave request" → review+design dispatched
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
