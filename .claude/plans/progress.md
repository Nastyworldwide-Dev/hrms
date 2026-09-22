2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
  tab routes now.
NOTE: two gates were silently stale and neither would have said so.
  coherence-rules.mjs still listed the OLD tab roots, and it skips without a
  running site, so nothing complained; e2e/screens.mjs did not know /requests
  existed, so every future measurement would have missed a tab root.
EVIDENCE: 2 correct — 7 tests red first (4 of 7), 4 mutants killed: wrong
  order; Calendar points elsewhere; More drops the routes it inherited; a
  sixth tab. Suite 592 / 588 pass, same 4 red at HEAD. Gates: lint 234/0,
  contrast 56/0, surfaces 47 screens (the new hub) / 0 over, tokens ok. Build
  clean.
NOTE: my own test read the bar's order from COMMENTS (stripped, so never
  matched), then from literal titles (only More has one), before resolving
  NAV_ITEMS[n] against the source list. Three attempts to read five names.
NEXT: 2.0 slice 1.3 — Home, now that the bar says what Home is for.
- 2026-09-22T12:15:28Z PUSH: nz-glass @ bb3796ebe
- 2026-09-22T12:15:28Z COMMIT: bb3796ebe feat(nav): the tab bar is Home, Calendar, Requests, Score, More → review+design dispatched
- 2026-09-22T14:23:10Z EVIDENCE: 2 correct — mapped tests green (bun ) for 13 file(s) ⟂884c4344e835

REPAIR: 2.0 slice 1.3 — Home. §3.1's order is check-in, what NEEDS YOU, then
  your requests. What shipped was an approvals banner, the check-in card,
  SEVEN QUICK LINKS, then the request panel.
  The quick links are the change. They were Home's answer to "how do I start a
  request?" — a question that now has a screen of its own one tap from
  anywhere (slice 0.1's Requests tab). Keeping them meant Home's LARGEST block
  existed to answer what the navigation answers, while the thing the plan puts
  in that slot — what needs the employee today — was one conditional banner.
  PendingApprovalsBanner is now a ROW inside NeedsYou. It answered exactly one
  question; the plan's row is wider (approvals, geofence reviews, issue
  replies, later SOPs and expiring certs) and as banners each new kind would
  be another conditional block above the fold with its own empty state. As
  rows in one bounded list, a new kind is a row. Bounded at three with "N
  more", the request panel's shape, because this is the list that spikes when
  an approver goes on leave.
  Its empty state is ABSENCE: a permanent "nothing needs you" row is wrong
  most of the time and costs the fold every day.
NOTE: the banner's two hard-won copy rules travelled with it and are now
  pinned against NeedsYou — no "tap to review" on a row that is already a
  button, and "REMOTE check-in(s)", because the count is
  remote_checkin.get_pending_count and an approver reading a bare "check-ins
  to approve" would take it for all of them and stop looking.
NOTE: two existing tests failed for the right reason and were re-aimed, not
  loosened: the skeleton-tile count read Home for the link count (the links
  moved), and the expenses-coin rule pointed at Home (same). Re-aiming the
  first found a REAL defect — GTileGrid's skeleton still defaulted to seven
  tiles while Requests passes six, so the panel would have jumped a row on
  load. That is the defect that test was written for, caught by moving it.
NOTE: the coin mutant survived TWICE before the assertion was right. A window
  ending at the label missed the icon on the same line; a line match missed it
  once the formatter wrapped the entry across five lines. It matches the whole
  ENTRY now, brace to label.
NOTE: `h-[17px] w-[17px]` is ELEVEN literals across SEVEN files. NeedsYou uses
  the named `.g-row-icon` instead; the other ten are a TICKET in family.md,
  not smuggled into a Home restructure.
EVIDENCE: 2 correct — 6 tests red first (4 of 6), 5 mutants killed (wrong
  order; quick links return to Home; needs-you unbounded; it renders when
  empty; a quick link lost in the move) plus 2 on the re-aimed tests. Suite
  598 / 594 pass, same 4 red at HEAD. Gates: lint 234/0, contrast 56/0,
  surfaces 47 / 0 over, tokens ok. Build clean.
NEXT: 2.0 slice 2.2 — OT claims read as money owed, not documents.
- 2026-09-22T14:23:17Z PUSH: nz-glass @ 2ebffe118
- 2026-09-22T14:23:17Z COMMIT: 2ebffe118 feat(home): Home is what is happening, what needs you, what you asked for → review+design dispatched
- 2026-09-22T14:27:07Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49

REPAIR: 2.0 slice 2.2 — overtime reads as what is owed, not as a document.
  An OT claim is the one request in this app ABOUT MONEY and the screens
  described it as paperwork: the history was "OT Request History" (a table),
  its filter offered "Compensation" (the field's label in Desk) with options
  "Overtime Pay" and "Replacement Leave", and a row read "1.5h overtime ·
  Overtime Pay".
  The row led with the INPUT. An employee knows how long they stayed; what
  they opened the screen to find out is whether it turned into money or into a
  day off. So the row leads with the outcome and carries the hours as the
  detail they belong to, beside the date.
  The two wire values are mapped EXPLICITLY rather than passed through __():
  "Overtime Pay" and "Replacement Leave" are the doctype's Select options and
  cannot change without a migration, so translating the raw value is exactly
  how the server's vocabulary reaches the screen — the same defect slice 1.2
  fixed on the shift chip. Naming them in a map also makes it visible here
  that there are only two.
  Filters: "Date worked" and "Paid or time off". The OPTIONS keep the server's
  spelling because the filter sends them as-is; only the label is the
  question the employee is actually asking.
NOTE: the forms needed nothing — slice 1.1's `noun` prop already gave them
  "overtime request" and "replacement leave claim".
EVIDENCE: 2 correct — 5 tests red first (4 of 5), 4 mutants killed: the title
  reverts to the doctype; the filter label reverts to Desk's; the row leads
  with hours again; the raw compensation is translated through. Suite 603 /
  599 pass — the same 4 red at HEAD, and one of them NAMES OT claims, so it
  was verified against a stashed tree rather than assumed. Gates: lint 234/0,
  contrast 56/0, surfaces 47/0, tokens ok. Build clean.
NEXT: 2.0 slice 2.1 — Attendance and clock-in history, then 4.1 (Approvals +
  Helpdesk) and D.1 (desktop).
- 2026-09-22T14:27:13Z PUSH: nz-glass @ be2e5f5a5
- 2026-09-22T14:27:13Z COMMIT: be2e5f5a5 fix(overtime): a claim about money read as a document → review+design dispatched
- 2026-09-22T14:30:55Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9

REPAIR: 2.0 slice 2.1 — attendance screens name the thing, not the table.
  Three were titled with a doctype: "Employee Checkin History", "Shift
  Assignment History", "Attendance Request History". An employee looking for
  the times they tapped in does not know what an Employee Checkin is, and
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
