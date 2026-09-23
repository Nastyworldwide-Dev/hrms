2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
  "Shift Assignment" is the TABLE that stores a roster line — the word is
  "shifts". Now "Your check-ins", "Your shifts", "Your attendance requests".
  And the dashboard carried the SAME defect slice 2.2 had just fixed one
  screen over: `__(claimableOt.data.compensation)`, translating the server's
  own Select value, so "Overtime Pay" reached the screen because the
  translation files do not contain it. Mapped explicitly, same two values, and
  a test now scans every attendance screen and every component for
  `__(compensation|workflow_state|docstatus)` so the class cannot reappear.
NOTE: the layout work §3.2 describes for these screens — the day sheet, the
  missing-punch flag, travel and training dots — is marked N in the plan: it
  needs backend that does not exist. Building it is a FEATURE, and §7 puts
  features out of 2.0's scope. This slice is the wording, which is what the
  §6 row actually asks for ("plain labels; no doctype words").
NOTE: the fix exposed a real runtime bug that only the lint gate could see.
  `__` is a TEMPLATE-only global (main.js:141, app.config.globalProperties) —
  Vue resolves it in markup, and this file had never needed it in the script
  because every previous call was in the template. A computed that builds a
  word does need the real function, and `no-undef` said so. Injected.
EVIDENCE: 2 correct — 5 tests red first (4 of 5), 4 mutants killed: a title
  reverts to the doctype; the raw compensation is translated; the shifts title
  says "Assignment"; the outcome mapping is dropped. Suite 608 / 604 pass,
  same 4 red at HEAD. Gates: lint 234/0, contrast 56/0, surfaces 47/0, tokens
  ok. Build clean.
NEXT: 2.0 slice 4.1 — Approvals and the Helpdesk hub. Then D.1 (desktop).
- 2026-09-22T14:31:11Z PUSH: nz-glass @ 1e4e07f51
- 2026-09-22T14:31:11Z COMMIT: 1e4e07f51 fix(attendance): three screens were titled with the name of a table → review+design dispatched
- 2026-09-22T14:36:57Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c

REPAIR: 2.0 slice 4.1 — approvals say whose turn it is. The tabs were
  "Pending" and "History", and "Pending" never said pending on WHOM: both
  lists on that screen hold pending things and only one is waiting on the
  person reading it. Now "Waiting on you" / "Decided by you" (§3.5's own
  words), plus the count above the rows — an approver wants to know whether
  this is a two-minute job before they start reading.
  KEY AND LABEL ARE DIFFERENT THINGS and conflating them is why the tabs still
  said "Pending": the string is compared in the template
  (`activeTab === 'History'`) and carried in the deep link a decided request's
  notification uses (`?tab=History`). GSegmented already takes { key, label },
  so the key is untouched and only the label is the employee's word.
NOTE: §3.5 also asks for a UNIFIED queue over a new
  `approval.list_pending_for_user`. The plan marks it N (new backend) and §7
  puts new backend out of 2.0's scope, so that is its own piece of work. This
  slice is what §6's row asks for.
NOTE: my first placement of the count was wrong twice in one edit — it landed
  in the HISTORY branch (the anchor matched the first occurrence) counting the
  PENDING list, and it sat between `v-else-if` and `v-else`, which breaks the
  chain. It shares the v-else with the rows now.
NOTE: two of my own assertions were too loose and mutants proved it. The count
  check matched a `.length` in a `v-if`, which is a render decision and not a
  number anybody reads; and the "Remote survives" check matched the word
  anywhere in a file that contains it eight times, so renaming the HEADING
  passed. Both are scoped now — a number in a sentence, and the <h2>.
EVIDENCE: 2 correct — 5 tests red first (3 of 5 after the count check was
  tightened), 4 mutants killed: labels revert; the key is translated (which
  would break the deep link); the count is removed; "Remote" leaves the title.
  Suite 613 / 609 pass, same 4 red at HEAD. Gates: lint 234/0, contrast 56/0,
  surfaces 47/0, tokens ok. Build clean — the template change was verified by
  compiling, not only by reading.
NEXT: D.1 — desktop. O2 answered (720px), so the token is signed off rather
  than provisional. The 1440 baselines it asks for need a reachable site.
- 2026-09-22T14:37:04Z PUSH: nz-glass @ 2e3c01175
- 2026-09-22T14:37:04Z COMMIT: 2e3c01175 fix(approvals): "Pending" never said pending on whom → review+design dispatched
- 2026-09-22T14:40:25Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8

REPAIR: 2.0 slice D.1 — desktop. Mostly VERIFICATION, and that is the finding:
  the shell was built in phase 4 and slice 0.1's tab change reached it BY
  ITSELF, because SideNav reads the same TAB_ITEMS and MORE_ITEMS the phone
  bar reads. That is now pinned — a future edit giving the desktop its own
  copy would let the two drift on the surface fewest people look at, and the
  drift would survive for months.
  Two real changes. (a) The 720px token still described itself as "a starting
  value, expected to be tuned on device". The owner signed it off, so it says
  that instead: a token that reads as unfinished invites the question to be
  re-opened by whoever meets it next. (b) §20.2's own text still named the
  PRE-2.0 side-nav order (HOME · ATTEND · LEAVE · PAY, then KPI, Issues,
  SOPs, Expenses) — the spec describing a bar that no longer exists.
NOTE: my own rule caught my own prose. The first rewrite of the token's
  description explained the history using the words "expected to be tuned",
  which is exactly what the test forbids. Reworded.
NOTE: `yarn tokens` regenerated glass.css and the dvh fallback SURVIVED — the
  generator-level fix from earlier today held, where the hand-patch had been
  silently reverted twice.
EVIDENCE: 2 correct — 5 tests, 1 red first (four already held, which is the
  slice's point), 4 mutants killed: the token calls itself provisional again;
  the side nav keeps its own list; the tab bar is visible at lg:; the width
  changes. Suite 618 / 614 pass, same 4 red at HEAD all day. Gates: lint
  234/0, contrast 56/0, surfaces 47 screens / 0 over, tokens ok. Build clean.

=== 2.0 COMPLETE, 22 Sep 2026 ===
All eight slices shipped: 0.1 tabs · 1.1 form copy · 1.2 chips · 1.3 Home ·
2.1 attendance · 2.2 overtime · 3.1 form allowlists · 4.1 approvals · D.1
desktop. Status table with commit shas is in the plan of record §6.
NOT BUILT, deliberately, each because the plan marks it new backend and §7
puts that out of scope: the unified approval queue, the attendance day sheet
and missing-punch flag, travel and training rows, the leave ledger breakdown.
OWED, both needing a reachable site: the 1440 visual baselines D.1 asks for,
and every measured number in the 2026-09-09 audit (tabH 0 on all 36 screens,
now marked stale in its own data).
NEXT: Nabil deploys. Pre-2.0 and 2.0 are both on nz-glass, unreleased.
- 2026-09-22T14:41:29Z COMMIT: 082fbbeeb docs(glass): the handoff still described the attendance repair → review dispatched
- 2026-09-22T14:54:57Z PUSH: nz-glass @ 082fbbeeb
- 2026-09-22T14:54:58Z COMMIT: 082fbbeeb docs(glass): the handoff still described the attendance repair → review dispatched
- 2026-09-22T14:55:18Z EVIDENCE: 2 correct — mapped tests green (bun ) for 18 file(s) ⟂8670267188cb
- 2026-09-22T14:55:21Z COMMIT: b46d8ea83 chore(home): remove a dead translator binding, guard against dead links → review+design dispatched
- 2026-09-22T14:55:30Z PUSH: nz-glass @ b46d8ea83
- 2026-09-22T14:55:42Z COMMIT: 37932ced9 docs(plans): hook lines for the post-2.0 audit → review dispatched
- 2026-09-22T15:38:46Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-22T15:43:55Z COMMIT: 243d480f6 docs(plan): name why 2.0 looked unchanged, and what a real revamp is → review dispatched
- 2026-09-22T15:44:03Z PUSH: nz-glass @ 243d480f6
- 2026-09-22T15:50:26Z PUSH: nz-glass @ 2b7b595b4
- 2026-09-22T15:50:26Z COMMIT: 2b7b595b4 docs(plan): the owner's rulings, and the fence the revamp must not widen → review dispatched
- 2026-09-22T15:58:36Z PUSH: nz-glass @ fb6472af2
- 2026-09-22T15:58:36Z COMMIT: fb6472af2 docs(plan): the ten dimensions the revamp plan was missing → review dispatched
- 2026-09-22T16:04:15Z PUSH: nz-glass @ a9e98528b
- 2026-09-22T16:04:15Z COMMIT: a9e98528b docs(plan): offline check-in is deleted, not deferred, and four more gaps → review dispatched
- 2026-09-22T16:09:46Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-22T16:09:49Z COMMIT: fb315beae fix(nav): a tab and the screen it opens disagreed about what the screen is → review+design dispatched
- 2026-09-22T16:13:15Z EVIDENCE: 2 correct — mapped tests green (bun ) for 23 file(s) ⟂0e43e1303bdf
- 2026-09-22T16:13:36Z EVIDENCE: 2 correct — mapped tests green (bun ) for 9 file(s) ⟂0e91782f6c7d
- 2026-09-22T16:13:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 9 file(s) ⟂0e91782f6c7d
- 2026-09-22T16:26:37Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9
- 2026-09-22T16:26:40Z COMMIT: 56806afef refactor(design): a 4pt grid and one modular type ramp, with a gate → review+security+design dispatched
- 2026-09-22T16:26:51Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-22T16:26:54Z COMMIT: ce4de0c9f refactor(helpdesk): a chat thread cost one glass surface per message → review+design dispatched
- 2026-09-22T16:27:03Z PUSH: nz-glass @ ce4de0c9f
- 2026-09-22T16:32:56Z EVIDENCE: 2 correct — mapped tests green (bun ) for 41 file(s) ⟂3e88cfe6592f
- 2026-09-22T16:32:58Z COMMIT: 86408c934 refactor(design): 103 hand-picked sizes became four scales → review+security+design dispatched
- 2026-09-22T16:33:06Z PUSH: nz-glass @ 86408c934
- 2026-09-22T16:40:51Z COMMIT: 5a645c720 chore(kpi): pin the fence before the revamp goes near it → review dispatched
- 2026-09-22T16:41:04Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 3 file(s) ⟂892bfc303afb
- 2026-09-22T16:41:06Z COMMIT: 1be1c4d81 feat(score): the empty screen was the screen, and it was never built → review+design dispatched
- 2026-09-22T16:41:13Z PUSH: nz-glass @ 1be1c4d81
- 2026-09-22T16:43:51Z COMMIT: f4ebcee0c refactor(design): the stylesheet was 96 values off the grid the tokens sit on → review+design dispatched
- 2026-09-22T16:43:58Z PUSH: nz-glass @ f4ebcee0c
- 2026-09-22T16:50:35Z EVIDENCE: 2 correct — mapped tests green (bun ) for 9 file(s) ⟂0e91782f6c7d
- 2026-09-22T16:50:37Z COMMIT: 0c8447068 feat(motion): reduced motion was honoured in 4 components out of ninety → review+security+design dispatched
- 2026-09-22T16:50:46Z PUSH: nz-glass @ 0c8447068
- 2026-09-22T16:56:16Z EVIDENCE: 2 correct — mapped tests green (bun ) for 22 file(s) ⟂7b381fd64ee9
- 2026-09-22T16:56:16Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-22T16:56:49Z EVIDENCE: 2 correct — mapped tests green (bun ) for 23 file(s) ⟂0e43e1303bdf
- 2026-09-22T16:56:49Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-22T16:57:14Z EVIDENCE: 2 correct — mapped tests green (bun ) for 23 file(s) ⟂0e43e1303bdf
- 2026-09-22T16:57:14Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-22T16:57:27Z EVIDENCE: 2 correct — mapped tests green (bun ) for 23 file(s) ⟂0e43e1303bdf
- 2026-09-22T16:57:27Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-22T16:57:30Z COMMIT: a334190b3 feat(a11y): every confirmation and every failure was silent to a screen reader → review+design dispatched
- 2026-09-22T16:57:40Z PUSH: nz-glass @ a334190b3
- 2026-09-22T16:59:23Z PUSH: nz-glass @ 8f365e67d
- 2026-09-22T16:59:23Z COMMIT: 8f365e67d test(responsive): no layout in this app had ever been checked at 320px → review+security+design dispatched
- 2026-09-22T17:02:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 20 file(s) ⟂9f33a174e0f9
- 2026-09-22T17:02:22Z PUSH: nz-glass @ a0aa92b30
- 2026-09-22T17:02:22Z COMMIT: a0aa92b30 feat(a11y): type ignored the reader's text size entirely → review+security+design dispatched
- 2026-09-22T17:14:00Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 34 file(s) ⟂ecbbf0369341
- 2026-09-22T17:14:28Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 34 file(s) ⟂ecbbf0369341
- 2026-09-22T17:14:41Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 20 file(s) ⟂ca85ac4a0141
- 2026-09-22T17:14:58Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 20 file(s) ⟂ca85ac4a0141
- 2026-09-22T17:15:22Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 20 file(s) ⟂ca85ac4a0141
- 2026-09-22T17:15:26Z COMMIT: 96c0925a7 feat(announcements): the feature 2.0 was asked for and could not build → review+design dispatched
- 2026-09-22T17:15:35Z PUSH: nz-glass @ 96c0925a7

EVIDENCE: rung 2 (correct) — announcements: 690/690 frontend tests green (yarn test),
  ruff clean across hrms/, and the audience fence exercised as a pure function over
  10 cases with 3 deliberate mutants (blank target opens the gate, unknown audience
  opens the gate, Department compares to company) — all 3 killed, file restored.
EVIDENCE: rung 3 (works) — announcements exercised END TO END on spoke.localhost
  (verify-bench, real data, 30 active employees). Verified: a Department notice
  reached reader A and was refused to reader B; the refusal left NO read row;
  expired and unpublished notices reached nobody; opening a card twice recorded one
  reading; acknowledge wrote acknowledged=1 with a timestamp; acknowledging a notice
  that never asked was refused; the pin is exclusive (first unpinned on second pin);
  deleting an announcement removed its read rows. Script: /tmp/ann_e2e.py, output
  "ALL CHECKS PASSED".
EVIDENCE: rung 3 (works) — both doctypes install cleanly on spoke.localhost via
  import_file_by_path; HR Announcement and HR Announcement Read both exist after.
DEAD END: audience_value as a Dynamic Link. Frappe resolves a Dynamic Link's target
  in _validate_links(), which runs BEFORE run_before_save_methods() — so neither
  validate() nor before_validate() can populate a derived target in time. Both were
  tried on the bench and both threw "Audience DocType must be set first". Now a
  plain Data name with our own existence check.
NEXT: patch to install the two announcement doctypes on deploy (a migrate that fails
  earlier must not leave endpoints with no tables), then B3 home.needs_you.
- 2026-09-22T17:16:56Z COMMIT: 36413e436 chore(announcements): install the board's doctypes explicitly on release → review dispatched
- 2026-09-22T17:17:05Z PUSH: nz-glass @ 36413e436
- 2026-09-22T17:22:46Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 21 file(s) ⟂d2611f29f8fb
- 2026-09-22T17:22:49Z COMMIT: 9f6fea7ab feat(home): "Needs you" showed one kind of work out of seven → review+design dispatched
- 2026-09-22T17:22:58Z PUSH: nz-glass @ 9f6fea7ab
- 2026-09-22T17:29:14Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 22 file(s) ⟂16efdd472c5b

EVIDENCE: rung 2 (correct) — requests_summary: 715/715 frontend tests green, ruff clean.
EVIDENCE: rung 3 (works) — exercised on spoke.localhost. An active employee with a real
  allocation returned balance 7.0 of 10.0 with expires_on 2026-12-31 and expiring_soon
  false (100 days out, past the 45-day horizon). All four sections answered for five
  different employees. Section independence proven by breaking _overtime on the live
  site: "overtime" was ABSENT from the payload, not zero, and leave/expenses/attendance
  all survived.
DEAD END: reading `to_date` from get_leave_balance_map. The map emits from_date and NOT
  to_date, so expires_on was always None and expiring_soon could never fire. The end
  date comes from Leave Allocation now, earliest first.
NEXT: Calendar (C2/C3) — month dots, then the day sheet.
- 2026-09-22T17:29:17Z COMMIT: 7824b9649 feat(requests): the numbers were on a different screen from the decision → review+design dispatched
- 2026-09-22T17:29:25Z PUSH: nz-glass @ 7824b9649
- 2026-09-22T17:39:27Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 25 file(s) ⟂7d6596642304
- 2026-09-22T17:39:27Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-22T17:39:53Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-22T17:39:53Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-22T17:40:18Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-22T17:40:18Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-22T17:40:21Z COMMIT: bc896836f feat(calendar): dates carry dots, and one tap carries the words → review+design dispatched
- 2026-09-22T17:40:29Z PUSH: nz-glass @ bc896836f
- 2026-09-22T17:44:20Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 19 file(s) ⟂9e4269db1302

EVIDENCE: rung 2 (correct) — team entitlement: 736/736 frontend tests green, ruff clean.
  Two mutants killed: entitled hardcoded True, and `!entitled` instead of `=== false`
  (which would flash the refusal at every manager on every load).
EVIDENCE: rung 3 (works) — three personas on spoke.localhost now give three answers:
  manager entitled=True members=1; non-manager entitled=False members=0; ex-manager
  (reports removed, still an approver) entitled=True members=0.
DEAD END: testing `if not team_of` for "has no team". `team_of` falls back to the
  caller's own employee id, so that branch only fires for somebody with NO Employee
  record — every ordinary employee came back entitled=True and was told their team
  was quiet today. Caught on the bench; `is_approver()` is the honest test and it is
  the app's existing definition.
NEXT: D3 — Helpdesk counts, SOP search, Profile grouping.
- 2026-09-22T17:44:26Z PUSH: nz-glass @ b8c3fc900
- 2026-09-22T17:44:26Z COMMIT: b8c3fc900 fix(team): an employee with no team was told their team was quiet → review+design dispatched
- 2026-09-22T17:53:05Z EVIDENCE: 2 correct — mapped tests green (bun ) for 22 file(s) ⟂7b381fd64ee9

EVIDENCE: rung 2 (correct) — D3 (helpdesk counts, profile groups): 749/749 frontend
  tests green, all 7 static gates green. Two mutants on the approver gate (removed,
  and re-gated on the count) both KILLED.
DEAD END: importing src/data/supportCounts.js directly in a node test. The module
  uses Vite's `@/` alias, which node does not resolve; the pure parts are evaluated
  in isolation with the resource stubs passed as FUNCTION PARAMETERS (a `new Function`
  body sees its own arguments, not the closure it was built in).
NEXT: SOP search-first (the last D3 piece), then the deploy note.
- 2026-09-22T17:53:10Z PUSH: nz-glass @ d0e98da13
- 2026-09-22T17:53:10Z COMMIT: d0e98da13 feat(support): the pills never said whether anything was behind them → review+design dispatched
- 2026-09-22T17:56:42Z EVIDENCE: 2 correct — mapped tests green (bun ) for 17 file(s) ⟂da5fdd6c5fcd
- 2026-09-22T17:56:48Z PUSH: nz-glass @ f4373af50
- 2026-09-22T17:56:48Z COMMIT: f4373af50 feat(sop): the library re-grouped itself between every keystroke → review+design dispatched
- 2026-09-22T18:01:30Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 22 file(s) ⟂16efdd472c5b
- 2026-09-22T18:01:30Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 3 extra test file(s) ⟂f95945b27b3b
- 2026-09-22T18:01:36Z PUSH: nz-glass @ cd8144e7c
- 2026-09-22T18:01:36Z COMMIT: cd8144e7c feat(home): the first line made the reader do arithmetic → review+design dispatched
- 2026-09-22T18:02:03Z PUSH: nz-glass @ 9d9798ff8
- 2026-09-22T18:02:03Z COMMIT: 9d9798ff8 docs(glass): the handoff still described the night before → review dispatched
- 2026-09-23T00:45:30Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 36 file(s) ⟂8bd154a716de
- 2026-09-23T00:45:30Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 4 extra test file(s) ⟂ec40e5b3a4bb
- 2026-09-23T00:45:55Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 22 file(s) ⟂16efdd472c5b
- 2026-09-23T00:45:55Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 4 extra test file(s) ⟂ec40e5b3a4bb
- 2026-09-23T00:46:17Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 22 file(s) ⟂16efdd472c5b
- 2026-09-23T00:46:17Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 4 extra test file(s) ⟂ec40e5b3a4bb
- 2026-09-23T00:46:20Z COMMIT: 460c42e66 fix(pwa): six defects from the 23 September deploy → review+security+design dispatched
- 2026-09-23T00:46:29Z PUSH: nz-glass @ 460c42e66

EVIDENCE: rung 2 (correct) — announcement reach: 784/784 frontend tests green,
  ruff clean across hrms/.
EVIDENCE: rung 3 (works) — reach verified on spoke.localhost: a Policy with
  acknowledge_required over 30 active employees read 0 of 30, then 2 of 30 after
  two employees opened it, then 1 confirmed; "who has not confirmed" listed 29 by
  name; an employee calling get_reach was refused (PermissionError).
FINDING (not a defect): Needs You is empty on the owner's account because nothing
  routes to it — 4 Leave Applications are pending on the site and that employee
  approves none of them. The endpoint is correct.
NEXT: verify the deployed screens against the plan one more time, then hand over.
- 2026-09-23T00:49:24Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 19 file(s) ⟂7da499605f72
- 2026-09-23T00:49:24Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-23T00:49:30Z PUSH: nz-glass @ b54d66f2f
- 2026-09-23T00:49:30Z COMMIT: b54d66f2f feat(announcements): HR published into silence → review dispatched

EVIDENCE: rung 2 (correct) — tab label fixed in px: 787/787 tests green, 7 static
  gates green. Mutants killed: 12px and 11px sizes (both overflow at 320px), the
  rem conversion applied to the tab label.
DEAD END: emitting the tab label in rem. Type went to rem yesterday for WCAG
  1.4.4, and at 120% text a rem-sized label overflows its slot — the
  "CALENDARREQUESTS" collision returns for exactly the people who raised their
  text size. One named exemption; everything a person READS still scales.
- 2026-09-23T00:51:56Z EVIDENCE: 2 correct — mapped tests green (bun ) for 21 file(s) ⟂f710e4a84ebd
- 2026-09-23T00:52:02Z PUSH: nz-glass @ c230f53c0
- 2026-09-23T00:52:02Z COMMIT: c230f53c0 fix(tabbar): raising your text size brought the collision back → review+security+design dispatched

EVIDENCE: rung 2 (correct) — error branches on Home's blocks: 789/789 tests green.
  Both mutants killed (each error branch disabled).
FINDING: swept every component for the self-hiding class that produced the Now-bar
  defect. Two more found (Announcements, RequestBalances rendered nothing on a
  FAILED read, identical to rendering nothing on an empty one). The rest — the
  calendar, the forms, the avatars — are correct: each has its four states or is
  deliberately absent.
- 2026-09-23T00:55:23Z EVIDENCE: 2 correct — mapped tests green (bun ) for 20 file(s) ⟂9f33a174e0f9
- 2026-09-23T00:55:29Z PUSH: nz-glass @ 4fa619563
- 2026-09-23T00:55:29Z COMMIT: 4fa619563 fix(home): a broken read looked exactly like having nothing → review+design dispatched
- 2026-09-23T00:56:07Z PUSH: nz-glass @ 1843005e4
- 2026-09-23T00:56:07Z COMMIT: 1843005e4 docs(glass): the handoff described the deploy that was just criticised → review dispatched
- 2026-09-23T01:42:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 19 file(s) ⟂145f4e2461a4

EVIDENCE: rung 2 (correct) — update prompt: 802/802 tests green. Three mutants
  killed, including the shipped bug itself (dismissal not remembered).
DEAD END: a time-based cooldown for the update prompt. An update is a SPECIFIC
  build — it stops mattering when a newer one lands, so a 30-day silence would
  hide an urgent fix. Keyed on the worker's __WB_REVISION__ instead.
NEXT: audit the shipped screens against mockup 4 and write the gap list.
