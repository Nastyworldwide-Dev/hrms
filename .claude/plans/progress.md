2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-10T03:13:52Z COMMIT: 7173539cd chore(plans): progress and next step for the 10 Sep defect batch → review dispatched
- 2026-09-10T03:24:35Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-10T03:24:40Z COMMIT: f6528e423 fix(attendance): a check-out closes its own session on every path, not only for two-shift staff → review dispatched
- 2026-09-10T03:25:52Z COMMIT: 93cf975ae docs(audit): the complete check-in edge-case set, measured not reasoned → review dispatched
- 2026-09-10T03:35:03Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-10T03:35:03Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-10T03:35:09Z COMMIT: 6e2d4ab3e feat(attendance): an early arrival is presence, and the paid hours start at the shift → review dispatched
- 2026-09-10T03:36:52Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-10T03:36:57Z COMMIT: 0cc503069 fix(attendance): trim the early arrival once, so a break cannot be taken off it twice → review dispatched
- 2026-09-10T03:45:45Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-10T03:52:16Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-10T03:52:16Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 4 extra test file(s) ⟂ec40e5b3a4bb
- 2026-09-10T03:52:19Z COMMIT: 894e758d0 fix(attendance): a punch keeps its shift's overtime type, so early arrivals still earn OT → review+cross-app dispatched
- 2026-09-10T03:53:55Z COMMIT: d08702051 docs(audit): what the check-in pipeline is actually connected to → review dispatched
- 2026-09-10T04:09:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-09-10T04:09:09Z COMMIT: a2f4ee3b8 test(attendance): cover the resolver line only a two-shift employee can reach → review dispatched
- 2026-09-10T04:15:09Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-09-10T04:15:11Z COMMIT: 50bec0dd7 test(attendance): pin the candidate the two-shift case is actually asserting on → review dispatched
- 2026-09-10T04:15:18Z PUSH: nz-glass @ 50bec0dd7
- 2026-09-10T04:15:31Z PUSH: nz-glass @ 6ca713aff
- 2026-09-10T04:15:31Z COMMIT: 6ca713aff docs: handoff for the overtime-type batch → review dispatched
- 2026-09-10T04:39:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-09-10T04:39:49Z PUSH: nz-glass @ 80860da47
- 2026-09-10T04:39:49Z COMMIT: 80860da47 docs(test): name the forgotten-check-out case for what it asserts → review dispatched
- 2026-09-10T06:55:58Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-10T06:56:31Z PLAN: approved 66d76f8e7dbe — # PLAN — the attendance causes still uncovered (10 Sep 2026)
- 2026-09-10T06:56:35Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-10T06:56:39Z COMMIT: 94afecfa9 fix(pwa): stop waiting forever on a browser that will never send a location → review+design dispatched
- 2026-09-10T07:01:01Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-10T07:01:06Z PUSH: nz-glass @ dcfbf669f
- 2026-09-10T07:01:07Z COMMIT: dcfbf669f fix(pwa): tell the truth about which way the location failed → review+design dispatched
- 2026-09-10T07:05:40Z PLAN: approved d2aa5705cc5c — # PLAN — the attendance causes still uncovered (10 Sep 2026)
- 2026-09-10T07:06:33Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-10T07:06:39Z PUSH: nz-glass @ 1b6fd02dc
- 2026-09-10T07:06:39Z COMMIT: 1b6fd02dc fix(pwa): the location banner's severity follows the coordinates, not the error → review+design dispatched
- 2026-09-10T07:14:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-09-10T07:14:48Z COMMIT: e42e0bf7c fix(pwa): put the reset where the commit said it was, and pin the muted banner → review+design dispatched
- 2026-09-10T07:14:54Z PUSH: nz-glass @ e42e0bf7c
- 2026-09-10T07:19:20Z PUSH: nz-glass @ 231392219
- 2026-09-10T07:19:21Z COMMIT: 231392219 test(pwa): name the banner, not just its tone, in the muted-arm test → review dispatched
- 2026-09-10T07:19:44Z PUSH: nz-glass @ 2d3a7b3c6
- 2026-09-10T07:19:44Z COMMIT: 2d3a7b3c6 docs: handoff for the location-stall batch → review dispatched
- 2026-09-10T07:25:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-10T07:25:57Z COMMIT: 2d3a7b3c6 docs: handoff for the location-stall batch → review dispatched
- 2026-09-10T07:27:54Z EVIDENCE: 3 works — scripts/smoke.sh on fresh.local: migrate clean, patches.txt fully applied, deciding-status columns live in the schema ⟂62ddd9a606da
- 2026-09-10T07:28:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-10T07:28:07Z COMMIT: 2d3a7b3c6 docs: handoff for the location-stall batch → review dispatched
- 2026-09-10T07:28:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-10T07:28:45Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-10T07:29:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-10T07:29:05Z COMMIT: be4f5639b fix(hr): show the status that decides something, not the one that decides nothing → review dispatched
- 2026-09-10T07:29:11Z PUSH: nz-glass @ be4f5639b
- 2026-09-10T07:30:22Z EVIDENCE: 3 works — scripts/smoke.sh on fresh.local: migrate clean, patches.txt fully applied, deciding-status columns live in the schema ⟂62ddd9a606da

PLAN: Nadi PWA UX 2.0 — amendment A written (docs/glass/plan/NADI_2.0_AMENDMENT_A_LIQUID_GLASS.md).
  Cause: the 8 Sep plan's decision Q0 retires Liquid Glass; Nabil's instruction is to KEEP and
  apply it properly. Evidence that Q0 indicted placement, not material: .g-glass (the CONTENT card
  class, 26 files) carries backdrop-filter blur(20px) at glass-components.css:320-325, over a
  three-blob colour field (field.* in design/tokens.json, GLightField.vue:32-34); tokens.json's own
  track-solid description already records muted text at 3.41:1 dark / 4.14:1 light on glass, below AA.
  Amendment: Q0 splits into Q0a (retire blob field + blur on content — YES) and Q0b (retire glass —
  REVERSED). Adds U16 glass-is-chrome-only, U17 reachability (absent from the plan entirely),
  U18 readability floor. Moves accessibility from phase 4 to required gates + new slice 0.8
  (design/gates/a11y.mjs is advisory today with 20 accepted violations baselined).
  Splits slice 0.6 into 0.6a readability/grid (Q0-independent) and 0.6b material (Q0-blocked).
NEXT: Nabil answers the five questions in amendment §A6. No code until then.
- 2026-09-10T07:59:27Z COMMIT: 8c902d849 docs(nadi): reverse the decision that would have retired Liquid Glass → review dispatched
NEXT: Nabil answers the five yes/no questions in docs/glass/plan/NADI_2.0_AMENDMENT_A_LIQUID_GLASS.md
  section A6 (Q0a retire blob field+content blur; Q0b KEEP Liquid Glass on the six chrome surfaces;
  U17 reachability; a11y promoted to a required gate now; mockup of the amended look before code).
  No Nadi 2.0 code until then. Q1-Q10 in the original plan remain open and were not re-asked.
- 2026-09-10T08:00:36Z COMMIT: f352558d6 docs: record the next step for the Nadi 2.0 amendment → review dispatched
REPAIR: amendment A corrected after frappe-reviewer on 8c902d849 (2 Critical + 3 Warning, all class:spec).
  CORRECTION to my earlier progress line and to commit 8c902d849's message: the a11y baseline is
  30 nodes (16 route:theme entries / 8 routes; label 16, aria-allowed-attr 8, button-name 2,
  aria-dialog-name 2, target-size 2) — NOT 20. Verified by tallying design/a11y-baseline.json.
  CORRECTION: design/gates/{a11y,contrast}.mjs are NOT advisory — both exit 1 on failure and
  glass-gates.yml runs them on push+PR. The real holes: (a) a11y is render-time and exits 0 with
  status:skip when CI has no served site + AUDIT_PW, so it has never been measured in CI;
  (b) no branch protection on nz-glass (gh api -> 404), so a red job blocks no merge;
  (c) a11y.mjs --update-baseline makes "frozen baseline" unenforceable.
  CORRECTION (mine AND the reviewer's): ion-tab-bar.g-tabbar (glass-components.css:172-190) DOES
  carry the full glass material incl. both fallbacks. There are exactly 4 backdrop-filter sites in
  frontend/src: tabbar + .g-sidenav (chrome, correct) and .g-glass + .g-glass-ghost (content, wrong).
  So "flat chrome, frosted content" was wrong; the tab bar is U16's reference implementation.
  U16 widened to seven surfaces (.g-sidenav added, §20.2/§15.3 net-zero). A6 gains Q6: Nabil enables
  branch protection, the only thing that makes any gate blocking.
EVIDENCE: 2 (verified) — python tally of design/a11y-baseline.json = 30 nodes; contrast.mjs:251
  process.exit(failures?1:0) green 54/0; a11y.mjs:111 exit 1; grep of backdrop-filter across frontend/src = 4 sites.
LEARNING(fact): in this repo "advisory gate" is always wrong — the gates enforce by exit code. The two
  real escape hatches are the render-time SKIP without a served site (only --strict makes it fatal) and
  the absent branch protection on nz-glass.
LEARNING(how): design/a11y-baseline.json is keyed route:theme, so every violation is stored twice;
  any count must sum node values across both themes or it understates the work by half.
NEXT: Nabil answers the SIX questions in docs/glass/plan/NADI_2.0_AMENDMENT_A_LIQUID_GLASS.md §A6.
  No Nadi 2.0 code until then.
- 2026-09-10T11:25:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-10T11:25:32Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 4 extra test file(s) ⟂c68dc5c03ea4
- 2026-09-10T11:25:35Z COMMIT: cf4cb2fe4 fix(attendance): a typed correction takes the unpaid break off, like the job does → review dispatched
2026-09-10T09:20Z COMMIT: 2fc1db148 fix(ot) round before the minimum; cf4cb2fe4 fix(attendance) typed correction deducts the break.
  EVIDENCE: 2 correct — red proved for both (ImportError on ot_minutes_qualify; TypeError on the third arg), then 6/6 and 24/24 green.
  EVIDENCE: 3 works — bench hrms.tests.test_ot_nonworking_hours 17/17; bench-free suite diffed against a 174-failure baseline, no new failures;
    reviewer independently killed 4 mutants (raw-compare and always-true on the helper, raw-compare at both gate call sites).
  EVIDENCE: 6 behaves — frappe-reviewer on 2fc1db148: NEXT_ACTION DEPLOY, no Critical. Property sweep over min_minutes 1..180 x 1..720 min:
    the OLD gate produced 435 "qualifies but pays 0" mismatches, the NEW gate produces 0. Double-rounding proven idempotent.
TICKET: refactor hrms/utils/ot_calculation.py — split the policy ladder (round/qualify/cap) from the pricing and capacity-replay layers.
  Hotspot, 18 fixes/90d, 950 lines. Cause of the churn: day classification, band pricing, capacity replay and monthly-cap accounting all live
  in one module, so every policy change touches the same file. This commit reduced pressure slightly (two duplicated inline gate expressions
  collapsed into one named rule) but did not address the cause.
TICKET: break-aware OT window — hrms/utils/ot_calculation.py has zero break awareness (grep 'break' -> only Python keywords). Harmless while
  every configured break sits inside the normal shift; a break configured to overlap the OT window would be paid as overtime. Needs Nabil's
  ruling because it changes money; today's figures do not move.
DEAD END: `git stash push -u -- <paths>` then `git stash apply <sha>` in this worktree silently REVERTED an already-committed file
  (hrms/utils/ot_calculation.py, back to the pre-fix body) and truncated .claude/plans/progress.md from 321 to 211 lines. Caught by reading
  `git diff --stat` before committing; recovered with `git checkout HEAD -- <both paths>`. Class: STASH-IN-SHARED-WORKTREE. Do not use stash to
  take a baseline measurement here — commit first and measure against the parent commit instead.
NEXT: Nabil rules on the OT backfill (below); then doors and permissions — OT Request menu link, Employee permlevel-1 rows,
  HR User on Overtime Type, HR Manager on Overtime Slip.
DECISION NEEDED: the rounding fix changes what Attendance.ot_hours SHOULD hold for every historical weekday in the 50-59 minute band.
  The record still reads 0 while get_claimable_ot_summary recomputes from punches and offers the day as 1.0 h — record and claim card disagree
  on the employee's screen. The only remedy is recompute_ot_backfill, which rewrites SUBMITTED rows in a range with no financial-dependency
  guard (current-plan.md risk 5c). NOT run and NOT patched in: mass-rewriting submitted pay rows needs Nabil's explicit word for that exact range.
- 2026-09-10T11:29:57Z COMMIT: 7020a4f87 test(patches): make the masters test runnable and give it something to fail on → review dispatched
2026-09-10T09:35Z REPAIR: review of cf4cb2fe4 (frappe-reviewer, NEXT_ACTION DEPLOY, no Critical) found a SECOND live member of the same
  class, larger than the one fixed. The hourly job applies three rules to produce working_hours — unpaid break, unpaid early arrival
  (paid_intervals_from, shift_type.py:551), and hours-from-worked-intervals-not-span. cf4cb2fe4 unified the break only.
  Verified: shift 09:00-18:00, punch in 07:30 out 18:00 -> job writes 8.00h. HR corrects the out time by five minutes -> typed path
  recomputes 07:30-18:05 = 10.58h less 60m = 9.58h against the job's 8.08h. +1.50h to payroll per correction, permanent because
  on_update_after_submit (attendance.py:396-398) sets auto_attendance = 0 so the job never revisits the row.
  Recorded in .claude/plans/family.md as the second live member; NOT patched (class: spec -> ruling first).
  EVIDENCE: 6 behaves — reviewer killed both wiring mutants independently (each call site turned a different test red), and probed the two
  likeliest wrong answers: a fixed break the employee punched out for is NOT double-deducted (job 8.00h vs typed 8.00h), and an overnight
  Thu 22:00 -> Fri 06:00 correctly takes 0 break minutes while Fri 08:00 -> Sat 02:00 takes the 105-minute Friday prayer break.
TICKET: one paid-hours rule shared by both writers — extract "paid hours for these times on this shift" so shift_type._process and the typed
  correction path cannot diverge again. Closes the early-arrival divergence above AND the attendance.py hotspot obligation (10 fixes/90d) in
  one move. Blocked on the decision below.
DECISION NEEDED: does an HR correction re-apply the early-arrival rule (hours start at shift start), or is the span HR typed authoritative?
  HR ruled on the job's behaviour only, 10 Sep 2026: "early clock in didnt counted as paid".
NEXT: Nabil rules on (a) the OT backfill range and (b) early arrival on typed corrections. Meanwhile: doors and permissions —
  OT Request menu link, Employee permlevel-1 rows, HR User on Overtime Type, HR Manager on Overtime Slip.
- 2026-09-10T11:34:22Z COMMIT: 143fc391c docs(plans): the paid-hours class has a second live member, larger than the first → review dispatched
- 2026-09-11T03:14:42Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:14:42Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-11T03:14:46Z COMMIT: 33d286691 fix(perms): restore restricted-field permission rows on every migrate, not once → review+cross-app dispatched
- 2026-09-11T03:21:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:21:44Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:21:57Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:21:57Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:22:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:22:17Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:22:23Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:22:23Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:22:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:22:50Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:22:54Z COMMIT: 6032d0749 fix(hr): two select comparisons matched values their fields never declared → review dispatched
- 2026-09-11T03:25:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-11T03:25:12Z COMMIT: 861d9be54 fix(perms): a restored permlevel row has to write, not only read → review dispatched
- 2026-09-11T03:34:10Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-11T03:34:14Z COMMIT: 4c181eeb3 fix(perms): keep the guard inside the doctypes the lockdown owns → review dispatched
- 2026-09-11T03:39:43Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-11T03:39:47Z COMMIT: 239ad87b5 feat(hr): restrict bank, IBAN and passport on Employee, reversibly → review dispatched
2026-09-11T03:40Z COMMIT: 33d286691 -> 4c181eeb3 permlevel guard (3 iterations, 2 of them fixing defects review found in my own work);
  6032d0749 two dead select branches + a class gate; 239ad87b5 reversible sensitive-field lock.
  EVIDENCE: 3 works — every permission claim grounded on the verify bench, not by reading rows: the write defect was proved with a real
  HR Manager doc.save() reading back 0 (red) then 1 (green); the sensitive lock was proved BOTH directions, 0->1 on migrate with the box
  ticked and 1->0 on the migrate after unticking it.
REPAIR: my first permlevel guard granted read without write, so the checkbox rendered and every tick was silently reverted — WORSE than the
  missing row, because HR would believe the grant landed. Caught by review. Second defect found while fixing it: the guard keyed on row
  EXISTENCE, so a read-only row stayed read-only for ever. Third: unfiltered doctype scan + rows_needing_write had no level-0 gate, so one
  permlevel-1 Custom Field on Appraisal would have granted HR write on appraisee_comments / appraisee_agreement / appraisee_sign_date —
  the employee's own sign-off, read-only for HR by design. Not live; closed anyway. Scope is now GUARDED_DOCTYPES, pinned equal to the
  lockdown patch's L1_HR_DOCTYPES by test.
LEARNING(fact): frappe.permissions.add_permission grants READ only. Without update_permission_property(..., "write", 1) the field renders and
  Document.reset_values_if_no_permlevel_access reverts every edit with no error. Proving the ROWS are right is not proving a SAVE persists.
LEARNING(fact): Frappe does not apply a new field's `default` to an EXISTING Single — HR Settings read 0 straight after the migrate that
  introduced the field, indistinguishable from a deliberate untick. A defaulted setting needs a one-time patch, written only when the field
  has never been stored so an existing choice survives.
LEARNING(how): the shared git stash is unsafe in this worktree — `git stash push -- <paths>` then `apply` silently reverted an already-committed
  file and truncated progress.md by 110 lines. Measure a baseline against the parent COMMIT, never by stashing.
TICKET: refactor hrms/utils/ot_calculation.py (18 fixes/90d) — split the policy ladder from pricing and capacity replay.
TICKET: one shared paid-hours rule for both writers (attendance hotspot, 10 fixes/90d) — closes the early-arrival divergence too.
NEXT: (1) sweep 4 finding #20 — Shift Request approval builds a Shift Assignment with NO shift_location, and employee_checkin.py returns early
  when no assignment has one, so anyone approved that way checks in from anywhere with the geofence silently off. Verify, then fix.
  (2) Nabil rules on the OT backfill range and on early arrival for typed corrections. (3) OT Request Desk menu link + the 4 select-only
  permission rows + HR Manager on Overtime Slip.
- 2026-09-11T03:40:19Z COMMIT: 7d7326508 docs(plans): evidence, three self-inflicted repairs, and the stash dead end → review dispatched
- 2026-09-11T03:43:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-11T03:43:09Z COMMIT: 5e61fc7ff fix(perms): one discovery source, one warning per loop, and a loud conversion → review dispatched
2026-09-11T03:45Z CIRCUIT: hrms/utils/permlevel_guard.py has taken FOUR fix: commits in a row with no push
  (33d286691 -> 4c181eeb3 -> 861d9be54 -> 5e61fc7ff). Per CLAUDE.md that opens the circuit: no more reviewers on this file,
  park it, ask a human. Parked. Each fix was found by the review of the one before it, and each was real — read without write,
  row-existence not row-capability, an unscoped scan that could have granted HR write on an employee's own appraisal sign-off,
  and a log line I said I had moved when I had copied it. The file is converging (three different LAYERS, not the same line
  three times) but four rounds on one file is the signal the rule exists for.
TICKET: hrms/utils/permlevel_guard.py now holds two responsibilities — granting permission ROWS (ensure_permlevel_rows) and
  setting field PERMLEVELS (apply_sensitive_field_lock). Split when a fifth change lands. Also: the source-contract tests assert
  on literal source text and file ordering (.index()); they are the right tool for a wiring defect and the most brittle thing in
  the file — any rename breaks them with a confusing message.
NEXT: NOT more work on permlevel_guard.py. Next is sweep-4 finding #20 (Shift Request approval creates a Shift Assignment with no
  shift_location, and employee_checkin returns early when no assignment has one -> geofence silently off for anyone approved that
  way). Verify first, then fix. Nabil still owes a ruling on the OT backfill range and on early arrival for typed corrections.
