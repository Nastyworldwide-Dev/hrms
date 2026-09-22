2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
CORRECTION: I cited "mockup-4 home = 723px, 0 overflow" as evidence the no-scroll
  goal was already proven. Wrong file. 2026-09-09-prototype-measure.json measures
  nadi-prototype.html (e2e/prototype-measure.mjs:12), not mockup-4. Withdrawn.
EVIDENCE: rung 1 — mockup-4 measured directly instead. It hardcodes
  .app{width:390px;height:844px;overflow:hidden} (line 124), so a fixed frame
  CANNOT show overflow and eyeballing it reports "no scroll" at any window size.
  Measured one screen at a time inside its own frame: s-home 912/774 = 138 over,
  s-appr 1030/774 = 256, s-leaveform 915/774 = 141, s-score 27, s-req 25; six
  screens fit. Frame released to real heights, home alone: 360x640 824 over,
  360x740 501, 360x800 347, 390x844 229, 414x896 138, 430x932 67. So "no scroll"
  is not proven anywhere yet — not in the app, not in the mockup.
CORRECTION: my first tap-target pass reported minTap 12-14px on mockup-4. It was
  measuring card DIVs matched by [class*=card]/[class*=row], not controls.
  Re-audited over button/a/[role=button]/input/select only: exactly ONE target
  under 24x24 (a 38x22 toggle track on s-leaveform). Mockup tap targets are
  otherwise WCAG 2.2 SC 2.5.8 clean. Withdrawn.
NOTE: latent bug found, NOT in scope for the Home work — glass.css:96
  --g-sheet-max-height: calc(100vh - 5rem) plus 9 more 100vh/88vh/80vh/70vh
  sites. 100vh is the LARGEST mobile viewport state, so sheets are cut off while
  browser chrome shows. dvh/svh have been Baseline Widely Available since Jun
  2025. Filed as its own slice (S7) with its own root cause.
PLAN: .claude/plans/current-plan.md written, tier risky — Home density (4 named
  causes, each with its own fix), the fold FORMULA (anchor block sized against
  the SMALLEST usable height ~440px at 360x640, elastic list allowed to scroll;
  invariant F1), and one icon library (recommend lucide-vue-next, feather
  REMOVED with it). 7 slices. Mockup sign-off required before S2.
NEXT: present the plan for approval — no code until the owner rules on it, and a
  measured frameless mockup is required before the QuickLinks grid slice.

REPAIR: S1 — Home spent its small-phone budget on air and said things twice.
  Three causes, one slice: (a) four panels at gap-8 = 96px of inter-panel air on
  a screen whose usable budget is ~440px at 360x640 -> gap-5; (b) CheckInPanel
  rendered an <h1> greeting while GAppHeader.vue:44 already renders the page h1,
  so every screen reader announced Home's title twice AND display-size type ate
  anchor height -> <p>, same words, same look, no structural claim;
  (c) PendingApprovalsBanner said "{0} remote check-in(s) awaiting your approval"
  + "Tap to review and decide." = 11 words for one count and one tap, on a
  GBanner that is already `interactive` -> "{0} check-in(s) to approve".
EVIDENCE: rung 2 — frontend/src/views/__tests__/home-fold-budget.test.js, 3
  tests, RED on all three before the edit (verified, not assumed). Mutation-
  checked: reintroducing the <h1> turns it red again and restoring it green.
  First draft of the h1 test matched its OWN explanatory comment (the comment
  names the tag it removed), so it stripped comments before asserting — a test
  its subject's prose can fail is not a test.
EVIDENCE: rung 3 — contrast gate 54 checked / 0 failures, gate tests 13/13,
  component+view tests 55/55, biome clean on all four files, production build
  green (188 asset chunks, Home/CheckInPanel/PendingApprovalsBanner all emitted).
- 2026-09-22T04:13:24Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-22T04:14:29Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-22T04:14:32Z COMMIT: 8e07bf701 fix(home): the fold is a budget, and Home overspent it → review+design dispatched
- 2026-09-22T04:15:05Z COMPACT: context compacted — read the last NEXT above before continuing

REPAIR: S1 review follow-up. The frappe reviewer's one Warning was right and I
  verified it at source before acting: the banner's count is
  hrms.api.remote_checkin.get_pending_count (data/remoteCheckin.js:21) and the
  row routes to RemoteApprovals only, so cutting "remote" left a bare
  "check-in(s) to approve" that reads as EVERY pending approval. An approver who
  believes that stops looking elsewhere — the one failure a visibility banner
  must not cause. Restored to "{0} remote check-in(s) to approve": five words,
  still less than half the original eleven. CLASS: a trim that removed a
  qualifier carrying scope, not prose. Brevity is a word budget, not a licence.
  Also took the design reviewer's DSN-06: .g-approvals__hint had no emitter left
  after S1, so the dead branch is gone from glass-components.css:931.
  .g-banner__hint stays — CheckInPanel.vue:74 still emits it.
EVIDENCE: 2 correct — new test "the approvals banner names the scope of the
  count it shows" RED before the edit (3 pass / 1 fail, verified), green after
  (4/4). Mutation-checked: re-cutting the scope word turns it red again, and the
  file was restored byte-identical (git diff --numstat 8/2, the intended edit).
EVIDENCE: 3 works — contrast 54 checked / 0 failures, gate tests 13/13,
  component+view tests 56/56, biome clean on all three touched files.
NOTE: both S1 reviewers cleared the commit (NEXT_ACTION: DEPLOY,
  VERDICT: DESIGN_APPROVED, zero Critical between them). Both nonetheless hit
  their 10-turn limit and returned nothing until nudged — a silent reviewer here
  was a truncated one, not a clean one. Their remaining SUGGESTIONs are NOT
  taken: the orphan-translation risk can only be settled against live Translation
  doctype rows (repo has no .csv/.po; lookup is exact-source-string via
  translationsPlugin.js), and converging content-column gaps onto one token
  (--g-stack-column, Home/Team gap-5 vs Leave/Attendance/KPI/Expense gap-8) is a
  five-view change that belongs to the owner, not to this slice.
EVIDENCE: rung 1 — S3 icon map measured against real Lucide (1848 icons, fetched
  from lucide-static). 36 feather names are actually rendered, NOT the 13 I
  recorded earlier: that count came from literal name="" only and missed the
  dynamic bindings, all three of which resolve to literals in the code
  (WorkflowActionSheet.vue:89/94 x/check; Home.vue link.icon = components).
  CORRECTION to the earlier inventory line. Coverage: 29 identical, 5 renamed
  (alert-triangle->triangle-alert, check-circle->circle-check,
  check-square->square-check, edit->pen-line, edit-2->pencil), and 2 with NO
  same-name target (filter, trash-2) that need a named substitute before S4 can
  claim parity. All 14 hand-rolled components have a Lucide target.
NEXT: commit this follow-up, then finish S3 as a committed doc (the 2 unmapped
  names get a decided substitute, not a guess) before S4 installs anything.
- 2026-09-22T04:21:43Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-22T04:21:47Z COMMIT: d6c82f17e fix(home): "remote" was scope, not prose → review+design dispatched

NOTE: d6c82f17e cleared by both reviewers — NEXT_ACTION: DEPLOY and
  VERDICT: DESIGN_APPROVED, zero Critical, zero Warning on design. The frappe
  reviewer INDEPENDENTLY verified at source what my fix rests on: get_pending_count
  (hrms/api/remote_checkin.py:365-372) counts Remote Checkin Request rows only,
  no union with Employee Checkin, so "remote" is factually correct and the bare
  string shipped in 8e07bf701 was the defect. I read the same lines myself before
  it reported. Its one Warning was that it never saw the test output (cut off by
  my deliver-now nudge) — re-run to close it: 4/4.
NOTE: reviewer truncation is now a pattern, not an incident — 3 of 4 agents this
  session hit the 10-turn limit and returned NOTHING until nudged, including one
  given an explicit 4-turn investigation budget in its prompt. A silent reviewer
  here means truncated, never clean, so the circuit rule ("silent reviewer gets
  one nudge, then counts as FIX_CRITICAL") is the right default and was applied.
LEARNING(how): nudge a truncated reviewer with "deliver NOW, zero further tool
  calls, mark anything unestablished as not-checked". All three nudged agents then
  returned a usable report WITH honest not-checked lines. Asking for the verdict
  without forbidding tools just burns the remaining turns.

REPAIR: S3 complete — docs/glass/plan/ICON-COVERAGE-MAP.md, a doc and no code,
  because S4 must not install anything until "does every icon have a target?" is
  answered. It does, with two names that needed a DECISION and now have one:
  filter -> funnel (not list-filter: three stacked lines is a different idea from
  the funnel users already learned) and trash-2 -> trash (trash-2 is not a Lucide
  name at all, only a back-compat alias, and two sibling tables already use plain
  trash for the same destructive action, so this unifies an existing split).
EVIDENCE: rung 1 — measured, not quoted: lucide-static fetched and counted at
  1848 icons; lucide-vue-next's published .d.ts confirms Filter/Trash2/
  AlertTriangle/CheckCircle/Edit/Edit2 still exist as ALIASES. S4 will not use
  them — an alias keeps a dead vocabulary alive in a codebase that just paid to
  replace it. 29 of 36 names identical, 5 mechanical renames, 2 decided above,
  and all 14 hand-rolled components have a target, so src/components/icons/ can
  go entirely.
NOTE: the 14 component->Lucide rows are JUDGEMENT, not measurement, and the doc
  says so: kanban for a project board and life-buoy for support change the
  drawing noticeably even where the meaning holds. Listed so the owner can review
  the change before it lands rather than discover it after.
NEXT: commit S3, then S2 (QuickLinks 8 full-width rows -> 4-across grid) — the
  largest single saving at ~274px, with a red tap-target test first at 44px.
  S4 stays blocked on its own revert condition: the real gzip delta, measured.
- 2026-09-22T04:24:37Z COMMIT: ac8890e81 docs(icons): every icon has a Lucide target, and two needed a decision → review dispatched
- 2026-09-22T04:28:41Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-22T04:40:00Z REPAIR: my icon inventory was wrong and a fresh-context
  verifier REFUTED it before S4 could act on it. I claimed "36 names across 28
  files, three dynamic sites" and attributed two dynamic bindings to
  RequestActionSheet.vue, which has none. Recount, scripted rather than eyeballed:
  40 distinct names across 28 files, FIVE dynamic binding sites —
  CheckInPanel.vue:54, ExpenseTaxesTable.vue:111, ExpensesTable.vue:119,
  WorkflowActionSheet.vue:33, Profile.vue:50. The four names every earlier count
  missed (book, file, user from Profile.vue's profileLinks literal, plus
  external-link) are all identical in Lucide, so the load-bearing conclusion
  survives: 33 identical + 5 renamed + 2 decided + 0 missing.
EVIDENCE: rung 1 — byte figures re-derived with feather's own toSvg() then gzip,
  and the methodology is now stated in the doc because it matters: all 287 icons
  are 106.2 KB raw / 11.2 KB gz and the 40 used names are 14.1 KB / 1.9 KB gz.
  My earlier 52.5/10.5 was wrong, and a raw read of dist/feather.js gives 159 KB
  because it measures a different thing. Projected delta restated honestly as
  "~9 KB gz from feather leaving, plus most of the 6.9 KB of hand-rolled SVG,
  minus whatever Lucide's 40 tree-shaken icons add back" — not the "-14 KB gz"
  I first wrote, which double-counted.
NOTE: the coverage map was already committed (ac8890e81) when the verifier
  refuted it. Correcting a shipped doc is cheaper than a shipped migration, which
  is the entire reason S3 is a doc and runs before S4.
LEARNING(how): an inventory I assemble by reading is an estimate. Three counts of
  the same 28 files gave 13, then 36, then 40. Only the scripted one is a count.
  Script the extraction, then have a fresh context try to refute it.
NEXT: S2 — QuickLinks 8 full-width rows -> 4-across g-cellgrid grid, the largest
  single saving at ~274px. The 5 red tests are written and the CSS is in place;
  QuickLinks.vue is the remaining edit.
- 2026-09-22T04:31:09Z COMMIT: 43fd4093c docs(icons): the inventory was an estimate three times, so I counted it → review dispatched
- 2026-09-22T05:10:00Z REPAIR: S2 — QuickLinks was seven full-width rows at
  ~350px on a phone whose whole usable height is ~440px (invariant F1). Now a
  4-across tile grid: two rows, ~120px with one-line labels and ~145px when they
  wrap. Saving ~206px, the largest single item in the fold budget.
  The panel itself became a primitive, GTileGrid, because the usage gate caught
  the first version building .g-glass inline inside QuickLinks. The gate was
  right: components/glass/** owns the surface class and everything else composes
  it, which is exactly how GListPanel, GStatPanel and GBalanceGrid are built.
EVIDENCE: rung 2 — 6 tests red first, then green, and every one mutation-checked.
  Two mutants initially SURVIVED and both were my fault: swapping
  g-cellgrid--quick for --balance (two columns, four rows, the whole saving gone)
  passed five green tests because nothing tied the component to the modifier;
  and the skeleton tile count was pinned to a comment rather than to Home. Both
  now have assertions that fail on the mutant. Full suite 74/74, surfaces gate
  Home 4/6 (the grid stayed ONE surface), contrast 54/0, biome clean, vite build
  clean.
NOTE: my own figures were wrong again and I caught it only by computing from the
  tokens. The comments and tests said "eight links, ~450px, saving 274px". Home
  passes SEVEN (baseQuickLinks is six plus one unconditional HR row) and the row
  height is 50px, not 56. Every stated number is now derived, and the seventh
  test reads the count out of Home.vue so adding a quick link fails the test
  instead of silently making the panel jump a row on load.
NOTE: design/gates/usage.mjs counted .g-glass inside COMMENTS, so a component
  documenting which primitive owns its surface scored a violation and the test
  enforcing the rule scored five for quoting the class it forbids. Same defect
  class the gate's own direct-import rule already fixed ("a comment naming the
  file is legitimate documentation") and the same class as the h1 test in
  home-fold-budget.test.js. Fixed by stripping comments before counting and
  exempting __tests__; verified the gate still catches a real inline .g-glass.
  It still reports views/helpdesk/TicketDetail.vue, which is pre-existing at
  HEAD and not mine — that exit 1 is unchanged by this commit, not introduced.
LEARNING(gate): unmeasured-count-in-prose -> assert the count against its source
  file, not against a comment (QuickLinks.grid.test.js test 6).
NEXT: re-bake Home's visual baselines, then S4 (lucide-vue-next migration) —
  carrying the reviewer's note to re-verify the Trash2 alias against the
  INSTALLED package version, not the published .d.ts.
- 2026-09-22T04:42:19Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-22T04:42:22Z COMMIT: 49a68f18f feat(home): seven quick links were eating four fifths of the fold → review+design dispatched
- 2026-09-22T05:35:00Z REPAIR: the CSS comment for the tile grid still asserted
  "eight rows, ~450px, ~176px" after the component comments and tests had been
  corrected to seven/~350px/~145px. Exactly the drift class this repo already
  has on record — a figure fixed in one place while the prose elsewhere keeps
  quoting the superseded value — and I found it only because I had just warned a
  reviewer to look for it. Fixed, with the old figures named so the correction
  is legible rather than silent.
EVIDENCE: rung 1 — three claims I had asserted but not checked are now checked
  and the check is written next to the rule: (1) LABELS at the smallest width,
  360px -> 328px panel / 4 = 82px tile = 74px of text, the longest label Home
  passes ("Request Attendance") needs two lines and its longest word is ~55px,
  so nothing clips and the line-clamp is a guard rather than a truncator;
  (2) DIVIDERS at SEVEN tiles, not eight — tile 5 opens row two and 5 % 4 == 1
  so it correctly takes no left border, and the absent eighth cell draws no
  dangling line because borders belong to cells; (3) FOCUS RING in dark —
  --g-shadow-focus-ring-inset is built from --g-ink and --g-brand, both
  redefined in the dark block, so outline:none is replaced by a ring that
  resolves per theme rather than by nothing (WCAG 2.4.7).
  Suite 74/74, contrast 54/0, biome clean, vite build clean.
NEXT: S4 — install lucide-vue-next, migrate 40 names across 28 files and delete
  the 14 hand-rolled icon components, REMOVING feather-icons in the same commit,
  and record the real gzip delta (revert if it is not negative). Carry the
  reviewer's note: verify the Trash2/Filter aliases against the INSTALLED
  package version, not the published .d.ts. Two reviews of 49a68f18f were still
  in flight at this line; read their verdicts before starting.
- 2026-09-22T04:45:32Z COMPACT: context compacted — read the last NEXT above before continuing

REPAIR: S2 review follow-up, two findings, both real. (a) The design reviewer
  found the precedent I had missed: .g-cellgrid--balance.g-cellgrid--odd spans
  its short last tile, and .g-cellgrid--quick has no equivalent, so seven tiles
  in four columns render [5][6][7][gap]. Its suggested fix is WRONG HERE and the
  reason is now written beside the rule: spanning at TWO columns fills a 50% hole
  for free, but at FOUR it pushes tile 7 onto a third row (+~72px on the one
  panel whose purpose was removing rows) and draws the conditional HR tile at 4x
  its siblings' width, signalling an importance it does not have. Recorded as a
  decision, which was the reviewer's own second option. (b) DSN-03 was a real
  gap: -webkit-line-clamp caps LINES, so a single word wider than the 74px column
  would overflow sideways rather than wrap — overflow-wrap: break-word added.
  The frappe reviewer's one Warning was the stale CSS comment already fixed in
  the working tree; it is in this commit.
EVIDENCE: 2 correct — new test "a label too long to break at a space still wraps
  instead of overflowing" RED before the rule existed (6 pass / 1 fail, verified
  by removing the declaration) and green after (7/7). Suite 63/63 across the
  component and view test files, gate self-tests 13/13, surfaces PASS (24 screens,
  0 over), contrast 54 checked / 0 failures, biome clean, vite build exit 0.
  usage.mjs still exits 1 on views/helpdesk/TicketDetail.vue only — pre-existing
  at HEAD, independently confirmed by the reviewer (the baseline has no diff in
  49a68f18f, the file is not in that commit, and decomment/EXEMPT can only ever
  REMOVE matches or EXCLUDE files, never manufacture a violation).
NOTE: the reviewer's own suite count was 62 and mine is 63 because this commit
  adds one test. Its NEXT_ACTION: FIX_CRITICAL was raised on the stale comment,
  which it correctly observed was already written but uncommitted in the tree.
LEARNING(how): a design finding can be correct about the ABSENCE and wrong about
  the remedy. The balance grid's span rule is right for two columns and costs a
  row at four. Check what the suggested fix does to the number the slice exists
  to reduce before taking it.
NEXT: S4 — install lucide-vue-next, migrate 40 names across 28 files, delete the
  14 hand-rolled icon components and REMOVE feather-icons in the same commit,
  recording the real gzip delta (revert if it is not negative). Verify the
  Trash2/Filter aliases against the INSTALLED package, not the published .d.ts.
- 2026-09-22T04:50:14Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-22T04:50:17Z COMMIT: 5b2486fca fix(home): a short last row is a decision, and a long word could clip → review+design dispatched
- 2026-09-22T04:51:33Z COMMIT: 478b041e7 docs(glass): the handoff still described an attendance hotfix → review dispatched

REPAIR: 5b2486fca review — one of the two findings was a FALSE CLAIM I wrote in
  the same commit that was supposed to be closing that exact class. The
  focus-ring comment said --g-shadow-focus-ring-inset "is built from --g-ink and
  --g-brand, both of which the dark block redefines". Checked: --g-ink is
  redefined (glass.css:36 -> :231, #0B0C10 -> #FFFFFF); --g-brand is defined
  ONCE at :root (glass.css:6) and never overridden. The ring is still correct in
  both themes, but for two different reasons — one half adapts, the other is a
  deliberately constant accent — and the comment now says that instead of
  asserting a symmetry that does not exist. Both reviewers also read "not\nN."
  in the surface-budget sentence as an unsubstituted placeholder; it was §15.1's
  own shorthand, but shorthand two readers decode wrongly is not shorthand, so
  it now reads "rather than one per tile".
EVIDENCE: 2 correct — the token claim is no longer prose. New test "the focus
  ring's two halves behave the way the comment says they do" asserts --g-ink is
  defined twice and --g-brand once, straight out of glass.css. Mutation-checked:
  adding a dark --g-brand turns it red (7/1) and removing it green (8/0), and
  glass.css was restored byte-identical (git diff --numstat empty).
EVIDENCE: 3 works — suite 64/64, gate self-tests 13/13, surfaces exit 0,
  contrast 54 checked / 0 failures, biome exit 0, vite build exit 0.
NOTE: also took DSN-06 (the label rule carried two comment blocks explaining the
  same fact one rule apart — merged into one covering height and width, since two
  copies of a rationale is the drift generator this slice exists to remove) and
  recorded the reviewer's third option for the short row (a :has() re-shape of
  row two) as CONSIDERED AND DECLINED rather than leaving it to be re-raised: it
  needs a second case for the six-tile no-HR set and the two would fall out of
  alignment with row one.
LEARNING(gate): a comment that asserts how a TOKEN behaves is a testable claim,
  not prose — assert it against the token file (QuickLinks.grid.test.js, "the
  focus ring's two halves"). Three figure-drift incidents in this slice were all
  prose nobody could fail.
NEXT: S4 — install lucide-vue-next, migrate 40 names across 28 files, delete the
  14 hand-rolled icon components and REMOVE feather-icons in the same commit,
  recording the real gzip delta (revert if it is not negative). Verify the
  Trash2/Filter aliases against the INSTALLED package, not the published .d.ts.
- 2026-09-22T04:55:32Z COMMIT: c61dd191d test(glass): pin the token claim a comment was making, and got wrong → review+design dispatched

NOTE: progress.md lost 99 lines again — SECOND occurrence this session of the
  same class. The file is append-only, so a commit showing "1 added, 100
  deleted" is not an edit of mine; another process rewrote it from a stale copy
  between my append and the commit. Caught by reading the numstat on a two-line
  comment commit (101 deletions on a change that touched three words) rather
  than by any gate. Rebuilt as HEAD~1 + the single hook line that was genuinely
  new; verified 1 added / 0 deleted against HEAD~1 before staging.
LEARNING(gate): append-only file + a commit whose numstat shows deletions = a
  concurrent overwrite, every time. Read --numstat on every commit that includes
  progress.md; the truncation is invisible in the message and in git status.
NEXT: S4 — install lucide-vue-next, migrate 40 names across 28 files, delete the
  14 hand-rolled icon components and REMOVE feather-icons in the same commit,
  recording the real gzip delta (revert if it is not negative). Verify the
  Trash2/Filter aliases against the INSTALLED package, not the published .d.ts.
