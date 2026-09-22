2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-22T08:47:25Z COMMIT: 1bcb41e1a refactor(icons): four views drew their own arrow, and it had already drifted → review+design dispatched

REPAIR: S7 — a sheet sized against 100vh runs its confirm button off the
  bottom of a phone, because 100vh is the viewport with the address bar
  RETRACTED and the bar is showing most of the time. The token now declares
  dvh with the vh line kept above it as the fallback (a browser that cannot
  read dvh drops that declaration entirely and would have no height at all),
  and the three views that hardcoded the same calc use the token instead.
  Five sites, not the ten the plan said.
REPAIR: two design-review findings on bed29bbee, both real, both mine.
  (a) WEIGHT: all fourteen hand-rolled components drew at stroke-width 1.5 and
  Lucide defaults to 2 — a third heavier on every nav tab, side-nav item and
  Home quick link. Its defaultAttributes are module-internal and not exported,
  so main.js has nothing to assign; every icon does carry a `lucide` class, so
  the weight is set once in CSS beside §9's own. 1.5, not §9's 1.55: that is
  the line this set already drew at, and matching §9 exactly is a different
  change (a 24-grid glyph at 1.55 is not a 16-grid glyph at 1.55).
  (b) PICTOGRAM: ExpenseIcon was NOT a Lucide glyph. It drew a dollar COIN on
  a "-1 -1 28 28" viewBox, from Streamline — its group id is that library's
  slug — and I shipped it as Lucide's Receipt, a torn-paper receipt. A
  different picture for the same idea, in a commit whose whole claim was that
  only the source changed. Now CircleDollarSign, the coin the app had.
  I checked the other thirteen the same way: six carry Lucide's own
  `class="lucide lucide-*"` marker and seven draw its geometry on its 24-grid.
  ExpenseIcon was the only one.
EVIDENCE: 2 correct — sheet-height-dvh.test.mjs RED first (2 of 3), 4 mutants
  killed (drop the fallback; put the fallback after dvh; leak dvh onto a glass
  surface; a view reverts to the raw calc). Two new icon tests, each red
  first. Suite 522 tests / 518 pass — the same 4 that fail at HEAD. Lint
  clean. Gates byte-identical to baseline: contrast 54/0, surfaces 46/0,
  tokens ok. Build clean, total JS gz 1127671.
NOTE: two of my own test rules were wrong before the code was, same class both
  times — a rule that counts a unit also counts the COMMENT explaining it.
  Fixed by stripping /* */, // and <!-- --> before counting; the last of those
  was found by a Vue comment in Home.vue. And `/\bdvh\b/` never matched
  `50dvh` at all: there is no word boundary between a digit and a letter, so
  the leak mutant survived a rule whose author could not see the hole.
LEARNING(gate): a CSS length is a number glued to its unit — match
  /\d(?:dvh|svh|lvh)\b/, never /\bdvh\b/. A mutant that adds the forbidden
  unit is the only thing that finds this.
NEXT: S6 — RequestPanel capped at 3 rows + "See all (N)".
- 2026-09-22T08:54:48Z EVIDENCE: 2 correct — mapped tests green (bun ) for 11 file(s) ⟂4c8e69619202
