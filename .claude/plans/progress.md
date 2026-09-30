2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-28T03:45:58Z COMMIT: 5fd86c729 docs(plans): multi-site check-in plan awaits the owner; alpha.15 plan kept → review dispatched
- 2026-09-28T03:47:45Z PLAN: approved 803a1d91149e — # Plan — 28 Sep 2026: check in at more than one site (HR request)
- 2026-09-28T03:55:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 19 file(s) ⟂7da499605f72
- 2026-09-28T03:55:54Z EVIDENCE: 3 works — blast radius green: 30 dependent(s), 21 extra test file(s) ⟂a971136cf53f
- 2026-09-28T03:55:58Z COMMIT: df282a764 feat(geofence): HR can let a person check in at more than one site → review+deps dispatched
- 2026-09-28T04:01:39Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
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
