2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
  killed, including the shipped bug itself (dismissal not remembered).
DEAD END: a time-based cooldown for the update prompt. An update is a SPECIFIC
  build — it stops mattering when a newer one lands, so a 30-day silence would
  hide an urgent fix. Keyed on the worker's __WB_REVISION__ instead.
NEXT: audit the shipped screens against mockup 4 and write the gap list.
- 2026-09-23T01:42:14Z PUSH: nz-glass @ c0c11341a
- 2026-09-23T01:42:14Z COMMIT: c0c11341a fix(update): dismissing the new-version bar did not dismiss anything → review+design dispatched
- 2026-09-23T01:50:54Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 25 file(s) ⟂7d6596642304

EVIDENCE: rung 2 (correct) — "with whom, since when" on request rows: 809/809 tests
  green, ruff clean. Two mutants killed (a row dropping the line; `pending`
  hardcoded, which would show "with Hafiz" under an Approved chip — that one
  SURVIVED the first version of the test and the assertion was strengthened).
EVIDENCE: rung 3 (works) — approver_name reaches the leave payload on
  spoke.localhost (2 rows, both named). Falls back to the login when the User row
  carries no full name, which is the fallback working.
FINDING: mockup 4 gap list written to docs/glass/audit/2026-09-23-mockup4-gap.md.
  Headline: the app follows mockup 4's SHELL and not its CONTENT — six of its
  blocks need data this app does not compute. Ranked by visible impact; items 1-3
  are copy over data we already have.
NEXT: mockup 4 gaps 2 and 3 — split Requests into waiting/finished, add filter chips.
- 2026-09-23T01:51:01Z PUSH: nz-glass @ 04162c0d3
- 2026-09-23T01:51:01Z COMMIT: 04162c0d3 feat(requests): "Waiting" never said who it was waiting on → review+design dispatched
- 2026-09-23T01:56:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 18 file(s) ⟂8670267188cb

EVIDENCE: rung 2 (correct) — Requests filter chips + waiting/finished split:
  814/814 tests green, 7 static gates green. Mutants killed: a chip losing its
  44px floor (mockup 4's own audit found its chips at 33px), chips claiming
  role="tab", the filter surviving a tab change.
DEAD END: counting each chip by swapping filter.value and restoring it. A side
  effect inside a computed — eslint refused it, and it would have flickered the
  rendered list through three filters on every recount. `matches(request, key)`
  takes the key instead.
DEAD END: the cap test matching "the first <button> in the file". The filter
  chips are buttons and come first in the template, so it silently started
  measuring a chip. Anchored on .g-list-more now.
NEXT: mockup 4 gap #4 — the claimable-money row on Home (the number already
  exists in requests_summary).
- 2026-09-23T01:56:55Z PUSH: nz-glass @ 3938741a6
- 2026-09-23T01:56:55Z COMMIT: 3938741a6 feat(requests): one undivided list became two piles and four filters → review+design dispatched
- 2026-09-23T01:57:16Z PUSH: nz-glass @ e6eb026cb
- 2026-09-23T01:57:16Z COMMIT: e6eb026cb docs(glass): the handoff and the mockup 4 gap list → review dispatched
- 2026-09-23T02:13:35Z NEXT: glass work unchanged; stop-hook fix aa4052f sits unpushed on humanless-pipeline fix/commit-gate-scope
- 2026-09-23T02:22:48Z COMPACT: context compacted — read the last NEXT above before continuing
NEXT: owner reviews docs/glass/plan/pages/00-sheets-and-transitions.md + 02-home.md; then plan page 3 (Requests). No code until approved.
EVIDENCE: 1 recollection — gates 7 pass/3 skip, 814/814 tests, eslint 0; checklist 16 pass/7 partial/27 fail (docs/glass/audit/2026-09-23-recollection.md)
DEAD END: helper agents invented a blob ruling (D4) and passed orientation without evidence; corrected by hand
NEXT: owner picks version scheme + approves step 0 foundation; then write pages/00-foundation.md
EVIDENCE: 2 FLOW-1 confirmed in code — expense_claim/Form.vue FIELDS allowlist (from 94a9e278a) lacks "taxes"; tabs lastField:"taxes" -> FormView findIndex -1 -> empty tab. LIVE DEFECT on deployed 2.0: nobody can file an expense.
EVIDENCE: 2 verified pages-audit criticals — PAGE-1 main.js beforeEach treats any userResource.reload() failure as logged-out (offline nav -> Login); PAGE-2 announcements/List.vue ResourceError + GEmptyState both render on error; PAGE-3 HRIssueBoard.vue:58 + TeamDashboard.vue:100 clickable divs (keyboard cannot reach). All CONFIRMED in code.
EVIDENCE: 3 audit merged — docs/glass/audit/2026-09-23-AUDIT-PLAN.md: 92 findings, 13 P0 (all verified in code), F-1..F-15 foundation, 10 page plans
NEXT: owner rules on 5 questions in AUDIT-PLAN.md, then build alpha.2 = P0-1..13
NEXT: owner answered the 5 decisions (team line compressed on Calendar -> Team page; reword everything; shift pattern yes; HR reply + goals later). Waiting on "go P0".
- 2026-09-23T04:59:44Z COMMIT: 6195d0977 docs(glass): audit of the whole PWA and the plan it produced → review dispatched
- 2026-09-23T05:01:09Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T05:01:13Z COMMIT: 986a46e56 fix(forms): a tab whose last field was filtered out rendered empty → review+design dispatched
- 2026-09-23T05:02:22Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:02:25Z COMMIT: bf9d0fb3b fix(glass): a comment closed early and deleted the tab-bar reservation → review+design dispatched
- 2026-09-23T05:04:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:04:20Z COMMIT: a16a354ef fix(forms): a missing middle tab boundary still emptied the later tabs → review dispatched
- 2026-09-23T05:14:12Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-23T05:14:12Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T05:14:15Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-23T05:14:15Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T05:14:18Z COMMIT: 76367b0fd fix(sheets): a sheet outlived its page and froze the next one → review+design dispatched
- 2026-09-23T05:16:04Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:16:04Z EVIDENCE: 3 works — blast radius green: 22 dependent(s), 10 extra test file(s) ⟂87c743b7274b
- 2026-09-23T05:16:07Z COMMIT: 221503d09 fix(privacy): an employee's record stayed on the phone after logout → review dispatched
- 2026-09-23T05:18:05Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T05:18:05Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-23T05:18:08Z COMMIT: 9fb28a77b fix(session): changing page offline threw people onto the Login screen → review+security dispatched
- 2026-09-23T05:20:12Z COMMIT: fedb09a20 fix(sheets): a sheet closed after Back left the previous page frozen → review+design dispatched
- 2026-09-23T05:20:36Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T05:20:39Z COMMIT: 6a3f0c968 fix(checkin): check in still opened the camera and confirmed offline → review+design dispatched
- 2026-09-23T05:21:18Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:21:21Z COMMIT: 9eca99cf5 fix(announcements): the board said "could not load" and "nothing here" at once → review+design dispatched
- 2026-09-23T05:23:39Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T05:23:39Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-23T05:23:42Z COMMIT: d3c812188 fix(session): offline, a failed employee read froze every navigation → review dispatched
- 2026-09-23T05:23:58Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-23T05:24:00Z COMMIT: f813eee26 fix(checkin): the remote and late check-out dialogs still sent offline → review+design dispatched
- 2026-09-23T05:25:49Z EVIDENCE: 2 correct — mapped tests green (bun ) for 13 file(s) ⟂884c4344e835
- 2026-09-23T05:25:51Z COMMIT: d2c7bd636 fix(a11y): rows you could tap could not be opened from a keyboard → review+design dispatched
- 2026-09-23T05:26:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:26:20Z COMMIT: d7bda3a9b fix(sheets): a keyboard-opened sheet drew the browser outline, not the app ring → review+design dispatched
- 2026-09-23T05:28:53Z COMMIT: d7bda3a9b fix(sheets): a keyboard-opened sheet drew the browser outline, not the app ring → review+design dispatched
- 2026-09-23T05:29:02Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:29:05Z COMMIT: 5eaf85485 fix(sheets): a keyboard-opened sheet drew the browser outline, not the app ring → review+design dispatched
- 2026-09-23T05:29:19Z COMMIT: 5cf0c12f3 fix(glass): at 320px with large text the calendar and balances scrolled sideways → review+design dispatched
- 2026-09-23T05:32:33Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 5 file(s) ⟂5d9cef17ceeb
- 2026-09-23T05:32:33Z EVIDENCE: 3 works — blast radius green: 8 dependent(s), 6 extra test file(s) ⟂51e98e473e5f
- 2026-09-23T05:32:36Z COMMIT: da51cd501 fix(approvals): a rejection gave the employee no reason → review+design dispatched
- 2026-09-23T05:34:34Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-23T05:34:37Z COMMIT: 964cc96f3 fix(home): "1 leave request to approve" opened an empty list → review+design dispatched
- 2026-09-23T05:35:05Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-23T05:35:08Z COMMIT: 5f1fee8b8 fix(approvals): a disabled Reject gave no hint that a reason was needed → review+design dispatched
- 2026-09-23T05:37:41Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 7 file(s) ⟂85be7f79c548
- 2026-09-23T05:37:41Z EVIDENCE: 3 works — blast radius green: 8 dependent(s), 6 extra test file(s) ⟂51e98e473e5f
- 2026-09-23T05:37:44Z COMMIT: 996532e0b fix(approvals): Reject in Desk would have failed, and the reason check ran first → review dispatched
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
