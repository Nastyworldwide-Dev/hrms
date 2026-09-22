2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-22T06:21:44Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-22T06:37:33Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-22T06:47:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-22T06:47:32Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 4 extra test file(s) ⟂c68dc5c03ea4
- 2026-09-22T06:48:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-22T06:48:08Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 4 extra test file(s) ⟂c68dc5c03ea4
- 2026-09-22T06:48:11Z COMMIT: 86f324f4b fix(checkin): a night shift's grace was swallowing the next morning's IN → review dispatched
- 2026-09-22T06:52:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-22T06:52:32Z COMMIT: 16cdf6a68 feat(checkin): repair the punches the grace fix cannot reach by itself → review dispatched
- 2026-09-22T06:52:50Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-22T07:01:02Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-09-22T07:01:05Z COMMIT: ecf4ac9b8 fix(fix-day): a two-row day had no way out of itself → review dispatched
- 2026-09-22T07:03:11Z COMPACT: context compacted — read the last NEXT above before continuing

REPAIR: two defects in my OWN Move door (ecf4ac9b8), found before the review
  landed. (a) `move_one` wiped `this.state` entirely. Both days DID change on
  the server, but `visited()` reads that same object, so the wipe also dropped
  HR's unsaved ticks on every OTHER day of a multi-day walk and the next Save &
  rebuild would have saved fewer days than HR had walked, silently. It now
  deletes exactly the days the server's `answer.after.days` names, plus the
  current one. (b) the Move dialog's Date field defaulted to the punch's CLOCK
  date. What a Move rewrites is the SHIFT day, and for a night shift's
  after-midnight OUT they differ by one — so the screen opened BECAUSE a shift
  day is wrong would have offered the wrong value as its default. `tap_view`
  already sends `shift_start`; `fresh_state` carries it and the field uses it.
EVIDENCE: 2 correct — two new node tests, each RED first, 4 mutants killed
  (restore the whole wipe; ignore the server's day list; drop shift_start from
  fresh_state; default to row.time). Suite 45 node / 0 fail, test_fix_day_screen
  21/21, test_restamp 15/15, test_shift_resolution 85/85,
  test_grace_restamp_repair 11/11, ruff + biome clean.
NOTE: the frappe review of ecf4ac9b8 came back NEXT_ACTION: DEPLOY, no Critical.
  It independently verified move_tap's server guards (_require_hr, _tap refuses
  a mirrored tap, _lock_and_guard still fences the arrival day) and judged the
  amended test_fix_day_screen assertion honest rather than loosened — it adds a
  STRICTER pin (save_day has exactly one call site) alongside the new entry. Its
  two open notes: the `.catch` in move_one shows the server's sentence through
  fd_call, same as save_one (checked, no change needed); and fix_day.bundle.js
  is a 10-fix/90d hotspot that now needs a consolidation ticket — filed in
  family.md against the day-cache, which is what both defects above were.
LEARNING(gate): progress.md lost 116 lines a THIRD time this session, same
  concurrent-overwrite class as e2f01419f. `git diff --numstat` on an
  append-only file is the only thing that has ever caught it. Rebuild as
  `git show HEAD:<file>` + the genuinely new tail; never `git add` the tree copy.
NEXT: push nz-glass (86f324f4b, 16cdf6a68, ecf4ac9b8 + this), write
  docs/glass/HANDOFF.md, and hand over. Nabil deploys — bench migrate runs the
  one-time grace re-stamp repair patch on its own.

EVIDENCE: 3 works — frappe review of c16453e48 came back clean, no Critical, no
  Warning. It verified at source the one thing the fix rests on: move_tap builds
  `days = sorted({_tap_day(row), target_day})` and _finish returns exactly those
  in `after.days`, so nothing the server rebuilt can be missing from the list
  the screen invalidates. Its suggestion is taken here: the trailing
  `delete this.state[this.date]` is marked a safety net, not a second rule.
NEXT: hand over. Post-check: Norazmi 11 Aug shows ONE Attendance row with the
  morning IN on its own shift, and the Fix dialog offers Move.
- 2026-09-22T07:06:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-22T07:06:19Z COMMIT: c16453e48 fix(fix-day): a Move was throwing away days it had not changed → review dispatched
- 2026-09-22T07:06:45Z PUSH: nz-glass @ c16453e48
- 2026-09-22T07:08:40Z PUSH: nz-glass @ 9efb942fc
- 2026-09-22T07:08:40Z COMMIT: 9efb942fc docs(glass): the handoff still described last week's Home slice → review dispatched
- 2026-09-22T07:45:00Z COMPACT: context compacted — read the last NEXT above before continuing

REPAIR: the shipped grace repair would barely have touched Nabil's data — two
  filters excluded almost all of it: only MULTI-shift employees were selected,
  and `restamp` skipped every punch the old ERP sent, which is the whole
  1 Aug - 4 Sep window. The owner then found the real shape of the defect in
  the shift's own config: "7PM - 3.30AM" was 19:30-07:00 with a 120-minute
  check-out grace, so it accepted punches until 09:00 and swallowed day-shift
  staff's morning INs. Shift Assignment, filtered: 2 of 2. His rule: "if the
  fix on X isnt Y or Z then X should revert to its original shift."
  So the WHO is a definition, not a heuristic — a punch on a guarded shift
  whose employee is not one of its two owners is wrong whatever produced it.
  hrms/utils/wrong_shift_repair.py + its patch. Two powers granted for this one
  job and passed explicitly: `mirrored_ok` (ERP punches in scope — his word for
  this exact change) and `authoritative` (a day HR keyed BY HAND on top of a
  lying stamp is rebuilt, option B, 22 Sep). Money is never waived.
EVIDENCE: 2 correct — 22 new tests, 9 mutants killed: drop mirrored_ok; drop
  authoritative; select by shift_start instead of the clock; stop excluding the
  two owners; flip the mirrored default to True; drop the write-side fence;
  stop passing authority to the re-mark; collapse the job id; unforce
  inline=False. restamp 15/15, grace 11/11, day_remark 35/35, fix_day_screen
  21/21, ruff + format clean.
EVIDENCE: 3 works — blast radius green on every importer of restamp/day_remark:
  attendance_recovery, day_remark_retires_an_emptied_day, offshift_punch_heal,
  day_remark_hooks, erp_backfill_copy, attendance_fix_day_writes_no_hours.
  test_hr_asked_for_this_day needs a real bench (imports frappe) and fails the
  same way at HEAD — unchanged by this commit.
NOTE: two stale assertions elsewhere were amended rather than loosened. The
  grace repair's mirrored test now pins the stronger fact (the guardrail is the
  DEFAULT, and that job holds no grant); test_day_remark's job-id test still
  passes because the plain id kept its old shape — only an authority-carrying
  job gets a suffix, so a job queued before this deploy still deduplicates.
NEXT: Nabil deploys. Order: this repair first, THEN save the corrected shift
  times (19:00-03:30) — the "Unmarked Check-in Logs Found" refusal clears once
  the stray punches are gone and their days re-marked. Then cut the check-out
  grace from 120.
- 2026-09-22T08:04:38Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-22T08:04:38Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 14 extra test file(s) ⟂5ba32964af47
- 2026-09-22T08:05:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-22T08:05:08Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 14 extra test file(s) ⟂5ba32964af47
- 2026-09-22T08:05:11Z COMMIT: 6e07c61cb fix(attendance): a shift belonging to two people was holding everyone's punches → review dispatched
- 2026-09-22T08:05:43Z PUSH: nz-glass @ 6e07c61cb
- 2026-09-22T08:06:09Z PUSH: nz-glass @ 6ee0f6ea7
- 2026-09-22T08:06:09Z COMMIT: 6ee0f6ea7 docs(glass): the handoff still described the Move slice → review dispatched

REPAIR: the frappe review of 6e07c61cb came back DEPLOY, no Critical, 284
  tests green across 9 suites. Its one Warning was real and is fixed here: the
  two owners are a module constant, the job runs on Nabil's schedule rather
  than at commit time, and a third person legitimately assigned that shift in
  between would have had their punches reverted — the job committing the very
  defect it exists to repair. `roster_drifted` now REFUSES the shift and logs
  what changed rather than repairing against a stale list. Fewer owners than
  the constant is not drift: the missing name is simply never selected.
EVIDENCE: 2 correct — 3 new tests, 4 mutants killed: remove the check; warn but
  continue anyway; make the difference symmetric so a DEPARTED owner also
  refuses; count draft/cancelled assignments as ownership. Suite 25/25,
  restamp 15/15, grace 11/11, day_remark 35/35, attendance_recovery and
  fix_day_screen green, ruff clean.
NOTE: mutant N3 SURVIVED its first run and the survival was a lie — a stale
  __pycache__ entry (same size, same second, so the timestamp check missed the
  edit) meant three runs scored the ORIGINAL file. Caught by reproducing the
  case standalone and reading the source line back. Every mutation run here now
  clears __pycache__ first. The test was genuinely weak too: it asserted an
  empty RESULT, which a refusal also returns, so it now asserts the punches
  were READ.
LEARNING(gate): a mutation run must clear __pycache__ between mutants — a
  same-size, same-second edit is invisible to Python's timestamp invalidation,
  and a surviving mutant is then indistinguishable from a killed one.
NEXT: Nabil deploys. Order: repair first, THEN save the corrected shift times
  (19:00-03:30), then cut the check-out grace from 120.
- 2026-09-22T08:09:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-22T08:09:57Z PUSH: nz-glass @ 29d56b08f
- 2026-09-22T08:09:58Z COMMIT: 29d56b08f fix(attendance): the repair trusted an owner list that could go stale → review dispatched

NOTE: second review (29d56b08f) came back DEPLOY, no Critical, 86 tests green.
  Its one Warning asked me to confirm why `roster_drifted` refuses the WHOLE
  shift rather than just excluding the drifted name — and one premise in it is
  wrong, which is why the answer is now in the docstring rather than in a reply
  nobody will read. It reasoned that an extra assignee "would only ever be
  excluded, same as a legitimate owner", so treating them as an owner is free.
  It is not: a STRAY assignment is what stamped these punches to the wrong
  shift in the first place, so reading ownership back out of the roster lets
  the defect grant itself an exemption and skip somebody who should be
  repaired. The constant is the only reading of ownership taken while a human
  was looking at the list. Refusing costs the two real owners nothing — their
  punches on their own shift are correct by definition and this job never
  touches them. What it defers is everyone else, until a human reads the log.
LEARNING(how): when a reviewer asks "is this the intended trade?", the answer
  belongs next to the rule, not in a reply — the next reader will have the same
  question and no transcript.
NEXT: Nabil deploys. Order: repair first, THEN save the corrected shift times
  (19:00-03:30), then cut the check-out grace from 120.
- 2026-09-22T08:11:37Z PUSH: nz-glass @ eb3e63b83
- 2026-09-22T08:11:37Z COMMIT: eb3e63b83 docs(attendance): say why a drifted roster refuses the whole shift → review dispatched

REPAIR: S4 — one icon library. 43 feather names across 27 files migrated to
  lucide-vue-next, the three prop-driven sites converted by hand (Profile's
  link list, WorkflowActionSheet's transition icon, FileUploaderView's
  multi-line tag), and components/icons/ deleted: all fourteen were Lucide
  glyphs pasted by hand, a copy of a library maintained by nobody.
EVIDENCE: 2 correct — icons.one-library.test.js RED first (3 of 5 failing),
  green after. Suite 512 pass / 4 fail, and those same 4 fail at HEAD
  (verified by stashing): named-export, temporal-dead-zone, claimed-days,
  request-chips. Lint clean. Gates: contrast 54 checked / 0 failures,
  surfaces 46 screens / 0 over, tokens ok. usage and lint counters are
  byte-identical to HEAD — measured, not assumed.
NOTE: S4's stated revert condition COULD NOT BE MET and the plan's premise was
  wrong. `feather-icons` is a dependency of frappe-ui, not of this app, and
  frappe-ui's own Button imports FeatherIcon — the Button main.js registers
  globally and 27 files render. So feather ships whatever we do. Measured on
  real production builds: total JS gz 1121112 -> 1128339, +7.0 KB. The icon
  map projected -9 KB from "feather leaving"; it was measuring feather as ours.
  Reported to the owner BEFORE writing code, with three options; he chose to
  proceed for the vocabulary, not the size. The failed condition is recorded in
  the test file's own header so the next reader cannot mistake this for a win.
NOTE: the icon sweep found 43 rendered names, not the 40 the map recorded. The
  map's own count had already been corrected twice. Every one of the 43 has a
  Lucide target — verified against the INSTALLED package, not its published
  types, which was the reviewer's carry-over note from S3.
NOTE: one test failed that was mine — sidenav-app-links-a11y pinned
  `<ExternalLinkIcon`. Amended to the new tag, not loosened: the RULE it
  protects (the arrow takes the muted ink token, so a decoration does not
  compete with the label beside it) is unchanged and still asserted.
NEXT: S5 — the 29 inline <svg>, triaged first; several are not icons (a
  progress ring, an upload target) and must not be converted.

REPAIR: S5 — no page draws its own copy of a library icon. TRIAGED first, as
  the icon map required, and the triage is most of the slice: of 20 inline
  <svg>, THREE are drawings (GProgressRing's bound arc, KpiDetail's plotted
  chart, SideNav's brand mark), ELEVEN are the SPEC'S OWN §9 icon set — a
  16-grid at stroke 1.55 carried by .g-icon, which the spec says in as many
  words no public set matches — and FOUR were pasted copies of Lucide's
  arrow-right on a 24-grid at stroke 2, one drawn at 16px and three at 17px.
  Only those four were converted. The plan called this "34 inline svg across
  29 files"; the real figure is 20 across 15, and the great majority must NOT
  be touched.
EVIDENCE: 2 correct — icons.no-pasted-glyphs.test.js RED first (2 of 3), green
  after. Suite 519 tests / 515 pass, and the 4 failures are the same ones that
  fail at HEAD. Lint clean. Gates byte-identical to the S4 baseline: contrast
  54/0, surfaces 46 screens / 0 over, tokens ok, usage and lint counters
  unchanged. Build clean; total JS gz 1128339 -> 1127855 (-484 B).
NOTE: my own test was wrong before the code was. It asserted every §9 glyph is
  a 16-grid; GSelfiePanel's face is 24, and §9's own sentence allows exactly
  that — "16 x 16 viewBox (24 x 24 for the selfie face only)". Written in as
  the spec's exception, matched on the face's own geometry, so a SECOND
  24-grid glyph still fails the test rather than the rule being loosened.
NOTE: the working tree was silently reverted to pre-S4 mid-slice — the icons/
  directory back, every call site un-migrated, and that revert STAGED. Cause
  found: the review subagent ran a git checkout of HEAD~1 in the shared
  worktree to verify my "these 4 tests also fail at HEAD" claim, and its turn
  limit ended it before it checked back out. Recovered by `git reset` (the
  commit itself was intact), deleting the resurrected files after confirming
  they were byte-identical to HEAD~1, and redoing the four conversions.
LEARNING(gate): a review subagent must be told read-only git ONLY (git show,
  git diff A..B). A worktree is shared state; a reviewer that checks out a
  different commit to verify a claim silently reverts whoever is working in it.
NEXT: S6 — RequestPanel capped at 3 rows + "See all (N)". Then S7, 100vh ->
  dvh across the 5 sites (the plan says 10; measured, it is 5).
