2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed

CORRECTION: the REPAIR line above paraphrased three numbers from
  family-mockup4.md instead of copying them, and the paraphrase drifted. Caught
  by the reviewer on 3fe415b8e. The ledger is the measurement; these are the
  real figures:
  - CLASS C home depth: 1.63 -> 1.39 viewports (not "1.59 -> 1.36"). 1264px of
    content in a 774px viewport before, 1072px after.
  - CLASS D sheet swing: tops at 418/488/444/600 = 182px swing (not "226px").
    After: top=399 h=444 on every day, swing 0.
  - The 44px tap-target family is CLASS E in the ledger, not "F". There is no
    CLASS F. Letters in family-mockup4.md are A B C D E G H G2.
EVIDENCE: rung 2, re-run after the CLASS G2 pill fix landed, so these verdicts
  cover the current mockup rather than the state at the time of the commit:
  a2 NO LOW-CONTRAST TEXT (1754 boxes, self-test 13.80:1 both themes) ·
  a3 no clipped text, sheet top=399 h=444 all four probe days ·
  a8 COLUMN EDGE CLEAN + INNER EDGE CLEAN · a9 NO TEXT RESTS UNDER CHROME.
LEARNING(gate): numbers paraphrased from a sibling ledger drift -> when a commit
  adds both a family-*.md and a progress.md summary of it, copy the figures,
  do not restate them.
- 2026-09-21T22:19:09Z COMMIT: 09f08df05 docs(plans): the audit summary quoted its own ledger wrong → review dispatched
- 2026-09-21T22:19:27Z COMPACT: context compacted — read the last NEXT above before continuing

CORRECTION: the correction above has the same flaw it was written to fix, one
  level up. It says "the ledger is the measurement; these are the real figures"
  and then cites "1.39 viewports / 1072px" for CLASS C — a figure the ledger
  does not contain. family-mockup4.md:47 records only the BEFORE state (1264px
  in a 774px viewport = 1.63); classes A-E carry no FIX line, so no after-value
  was ever written there. The number itself is real, but its source is a probe
  run, not the ledger, and quoting a probe under a sentence that promises a
  ledger is how the first drift happened.
  - CLASS C after-state: s:home 1.39 viewports (1072px / 774px). SOURCE:
    frontend/_audit/a3.mjs section C, re-run 21 Sep 2026. Not in the ledger.
  - CLASS D after-state: top=399 h=444 swing 0. SOURCE: a3.mjs section D, days
    2/8/16/24 — the four days that probe opens, not all 30. The "all 30 days"
    figure on the EVIDENCE line above came from a separate earlier sweep; the
    two are different runs and the later one is narrower.
  - "7 families" on the REPAIR line is wrong: the same line lists eight
    (A B C D E G G2 H) and the ledger documents eight. Read it as 8.
LEARNING(gate): a correction block is not exempt from the rule it enforces ->
  every figure gets a source token (ledger line, or probe file + section) in
  the same sentence, and "the ledger says" is only written above numbers that
  are literally in the ledger.
- 2026-09-21T22:24:21Z COMMIT: b3eab04d4 docs(plans): the correction broke its own rule → review dispatched
- 2026-09-21T22:24:51Z COMMIT: f9f907943 docs(glass): the handoff pointed two commits back → review dispatched

CORRECTION: third time, same class, one level up again. The bullet above says
  the REPAIR line "lists eight (A B C D E G G2 H)". It does not. Line 232
  literally reads "F tap targets (3 -> 0)". What I printed was the CORRECTED
  set with the F already silently swapped to E, inside a sentence that promises
  a transcription. Literal content of line 229-234: A B C D F G G2 H — eight
  entries, and the F among them is the letter the first correction fixed.
  So: the count is 8, not 7, and the sixth letter as written is F and should
  be read as E. Both statements, separately, instead of one blended one.
STOP: this is the third correction in a row and every one of them had the same
  shape — a paraphrase wearing the clothes of a quote. The rule is not "be more
  careful". It is mechanical:
LEARNING(gate): quoting another line means copying its bytes. If a quoted
  figure or letter needs correcting, the corrected value goes in a SEPARATE
  sentence after the quote, never inside it. A sentence may carry a quote or a
  correction, not both.
- 2026-09-21T22:27:00Z COMMIT: 950e3813c docs(plans): a corrected quote is not a quote → review dispatched
- 2026-09-21T22:30:02Z COMMIT: 49131862f chore(audit): commit the probes the handoff tells people to run → review dispatched
- 2026-09-21T22:30:13Z COMMIT: 5c1c90fbd docs(glass): the handoff can now name files that exist → review dispatched

DEAD END: this file lost 106 lines out of its own middle. Noticed when a read
  at offset 229 said "the file has 207 lines" — it had been 312. The tail was
  intact and hook lines were still appending to it, and the only lines the
  working copy held that HEAD did not were the three COMMIT lines written after
  the last commit. So something trimmed the history of an APPEND-ONLY file
  while leaving both ends looking healthy, which is the worst possible shape:
  nothing errors, and the loss is invisible unless you count.
  What went missing was 21 Sep 07:00-11:00 — the Release 1/2/3 PLAN, COMMIT and
  PUSH lines. Not mine to lose: that is the record of what shipped.
  Recovered from HEAD (the commit was never truncated) and the three newer hook
  lines re-appended. Verified: 312 + 3 = 315, and `comm` shows nothing from the
  truncated copy absent from the restored one.
  Cause not established. I did not edit those lines; every write I made this
  session was a >> append. Candidates: a concurrent writer, or a hook that
  rewrites rather than appends. Not chased further because the data is back and
  guessing at a culprit would be its own kind of drift.
LEARNING(gate): an append-only file needs a length floor. Before any write,
  assert the line count is >= the count in HEAD; a file that has shrunk since
  its last commit has lost something, and no append should land on top of a
  loss and bury it.
- 2026-09-21T22:32:22Z COMMIT: c11bdc513 fix(plans): the append-only ledger had lost its own middle → review dispatched
- 2026-09-21T22:32:51Z COMMIT: 0fb2298e9 docs(glass): say what commit: means, so it stops drifting → review dispatched
- 2026-09-21T22:33:15Z COMPACT: context compacted — read the last NEXT above before continuing

CORRECTION: the DEAD END above ("this file lost 106 lines out of its own
  middle", "cause not established", "candidates: a concurrent writer, or a hook
  that rewrites rather than appends") named the right suspect and then stopped
  one step short of reading it. The cause IS a hook, it is not a defect, and it
  is documented in the function's own comment: cs_progress() in
  humanless-pipeline/core/hooks/lib/commit-scope.sh:198 ends with
      if [ "$n" -gt 300 ]; then { head -4 "$f"; tail -200 "$f"; } > "$f.tmp" ...
  Past 300 lines it keeps the first 4 and the last 200 and DROPS THE MIDDLE.
  312 -> 204, plus the appends that followed = the 206 I measured. Proven, not
  inferred: head-4 + tail-200 of HEAD, diffed against the working copy, leaves
  exactly the three hook lines written after the trim.
  So my "recovery" in c11bdc513 restored 315 lines into a file capped at 300,
  and the next COMMIT hook re-trimmed it within minutes. I did not lose the
  history a second time; I re-created a condition the cap exists to handle.
  The comment two lines above the cap says "capped so it cannot rot into a
  wall". I had read the ledger's contract as "append-only" from its header and
  never opened the writer.
LEARNING(gate): the length floor I proposed last hour is WRONG and is withdrawn
  before it was ever built — it would have fired on every trim forever, which is
  exactly what it did to me on its first manual use. An append-only file with a
  cap is not append-only; it is a RING. Before calling a file's shape a defect,
  read the code that writes it. The real protection is the one that already
  exists: git. HEAD holds the untrimmed history, the trim only ever touches the
  working copy, and nothing was ever actually lost.
LEARNING(fact): .claude/plans/progress.md is capped at 300 lines by cs_progress
  (head -4 + tail -200). Long-lived records do NOT belong in it — they belong in
  a plans/*.md file that nothing trims. The progress file is the state NOW.

2026-09-21T23:05:00Z REPAIR: phase 2 section 1 (ground truth) done as a
  read-only pass over the real frontend — 45 routes, 42 glass components, 8
  gates, 115 baselines, generated tokens. Written to
  .claude/plans/phase2-ground-truth.md, which is not trimmed.
2026-09-21T23:05:00Z DEAD END: the mockup and the app do not agree on what the
  five tabs ARE. Mockup: Home/Calendar/Requests/Score/More. App
  (frontend/src/data/navItems.js): Home/Attendance/Leaves/Expenses/More. That is
  an information-architecture change, not a restyle — one Calendar absorbing
  attendance+roster+claims, one Requests absorbing six doctype lists each with
  its own my/team permission surface. Not mine to pick: the brief authorises
  frontend work, and merging six permissioned lists is a product decision.
2026-09-21T23:05:00Z NEXT: three questions open with the owner, all blocking
  phase 2 — (1) un-ignore "Nadi PWA UI UX 2.0" (.gitignore:40); (2) is mockup 4
  signed off as the visual contract; (3) is mockup 4 a VISUAL contract (tokens,
  depth, motion, component shapes on the screens that exist) or an
  INFORMATION-ARCHITECTURE contract (these five tabs, these merged screens).
  Section 3 token work can start without an answer; section 2 per-screen work
  cannot, because it names three screens this app does not have.
- 2026-09-21T22:39:53Z COMMIT: af7593f79 fix(plans): the ledger was not losing lines, it is a ring buffer → review dispatched
- 2026-09-21T22:40:27Z COMMIT: 1c98ca521 docs(glass): the commit: convention now states its own precondition → review dispatched
- 2026-09-21T22:41:20Z COMMIT: 83d844dc2 docs(plans): ground truth says how each number was counted → review dispatched
- 2026-09-21T22:43:12Z COMMIT: 449d81478 docs(glass): files: says which commit its paths are in → review dispatched
- 2026-09-21T22:45:23Z COMMIT: 3f1143f22 fix(plans): the ground-truth file had three wrong numbers and a command that would not paste → review dispatched
- 2026-09-21T22:45:57Z COMMIT: 9469e033d docs(glass): commit: names a range, because the work was a range → review dispatched
- 2026-09-21T22:46:16Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T22:54:40Z COMMIT: 237eeb07b docs(plans): the grep note stated a rule that is only true of this pattern → review dispatched
- 2026-09-21T22:54:54Z COMMIT: 4a071aa78 docs(plans): section 3 has no design system to author, only two to reconcile → review+security dispatched
REPAIR: section 3 of the implementation brief is not "author a design system".
  Measured: 53 of the mockup's 62 --g-* names already exist shipped, and the
  overwhelming majority carry identical values. The job is reconciling two
  systems that overlap, and it is nearly done. Landed as
  .claude/plans/phase2-token-delta.md (4a071aa78).
EVIDENCE: rung 2 — node design/gates/contrast.mjs, read-only, 54 checks 0
  failures, ink-muted over blob 4.54-4.56 both themes. This is what shows the
  shipped app fixed family-mockup4 CLASS A by blob PLACEMENT, not by a thicker
  veil, so the mockup's --g-glass-fill .56 -> .86 buys taste and not
  correctness. Under review (237eeb07b^..HEAD).
DEAD END: I diffed the mockup against frontend/src/theme/glass.variables.css
  and got zero overlap, then nearly wrote that up as a finding. That file is
  output 3 of build-tokens.mjs and holds five --ion-* variables. glass.css is
  output 1 and is the --g-* file. A "zero overlap" between two systems that
  visibly share a prefix is not a finding, it is a wrong input file.
NOTE: the commit hook asked for a security-reviewer on 4a071aa78. Not spawned:
  both commits are one markdown file each, which CLAUDE.md's own rule exempts
  (docs commits touching <=2 files), and a security review of prose has no
  target. Recorded rather than silently skipped.
NEXT: owner's word on FOUR now, not three — un-ignore the mockup folder? is
  mockup 4 signed off? visual contract or information-architecture contract?
  and: adopt the mockup's --g-glass-fill .86 (thicker glass, both themes)
  against tokens.json's own "do not correct (spec 6)" note?
- 2026-09-21T22:56:00Z COMMIT: 95d098cc2 docs(plans): record the token measurement, and the wrong file it started on → review dispatched
- 2026-09-21T22:57:29Z COMMIT: 86cb48ab2 docs(plans): "5 of 53" added a dark-theme result to a light-theme total → review+security dispatched
- 2026-09-21T22:58:13Z COMMIT: aacd7c179 chore(design): the token figures had no way to be re-derived → review+security dispatched
- 2026-09-21T22:59:29Z COMMIT: efecccb98 docs(plans): 880px does not "re-run the gate", it FAILS it → review+security dispatched
- 2026-09-21T23:00:26Z COMMIT: 59e20f697 fix(gates): the lg: contrast proof could not see the token it proves → review dispatched
- 2026-09-21T23:00:54Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T23:09:54Z COMMIT: 1aacc7529 fix(gates): "this was the one literal" was wrong — there were four → review dispatched
- 2026-09-21T23:10:58Z COMMIT: 69a8dbb29 docs(plans): the gate defect this file reports is now fixed → review+security dispatched
- REPAIR: "this was the one literal" (59e20f697) was refuted by reviewing its own
  claim by name instead of from memory. contrast.mjs held FOUR copied tokens, not
  one: column, gutter: 15, const GUTTER = 15, VIEWPORT {w:390,h:844}. CLASS: a
  proof that keeps its own copy of a token proves the geometry the app USED to
  have. Fixed in 1aacc7529; px() now takes a group.
- EVIDENCE: rung 2 — node --test design/gates/*.test.mjs 7/7; contrast 54 checked
  0 failures. Perturbation proves the inputs are live, not decorative:
  screen-gutter 15->60px moves the gate 54 -> 42 checks; content-column-lg
  720->880px gives 57/1 with the documented 4.31 blob-B failure, from tokens.json
  ALONE with no gate edit. tokens.json restored, git status clean each time.
- NOTE: layout.viewport-width is currently INERT (390->320px moves no ratio).
  My first mechanism for this was WRONG and a reviewer refuted it: I wrote "blob
  B's centre is inside the column, dx=0". The probe that produced dx=0 had
  stripped the minus sign off blob-b-right (-163px), so it computed a different
  blob than the gate does. Real distance is 73px at EVERY width, against a
  cutoff of r*0.7=73.5 — outside the column, not inside.
  The true reason is algebraic, and stronger: blob B is right-anchored, so
  cx = W - right - r, and the right clamp boundary is also W - GUTTER. The two
  W terms cancel: dist = GUTTER - right - r = 73, for ANY width, while the
  right-clamp branch stays active. Blobs A and C are left-anchored and never
  reference W at all. So the input is inert by construction, not by coincidence
  — but that is contingent on blob-b-right/-size/screen-gutter, NOT guaranteed
  against edits to those three. Read from the token for that reason.
- NOTE: all three blobs sit within ~1px of their alpha cutoff (A 80.0 vs 80.5,
  B 73.0 vs 73.5, C 62.0 vs 63.0), i.e. contributing 0.6-1.6% of peak. That is
  the §3.3 PLACEMENT mechanism working as designed — blobs held just clear of
  the column — but the margin is thin enough that a few px of blob movement
  turns a 4.5x pass into a fail. Pre-existing, unchanged by this work, worth
  knowing before anyone moves a blob.
- NOTE: lint 242/9 and usage 2/1 are UNCHANGED with and without the gate diff
  (verified by stashing it). Pre-existing, not introduced by this work.
- DEAD END: two frappe-reviewers in a row burned all 10 turns gathering and
  reported nothing. Resuming with already-verified command output and an explicit
  "spend your turns on judgement, report by turn 4" budget is what got a usable
  pass. A reviewer that has to re-run the commands has no turns left to think.
- NEXT: owner's word on FOUR, unchanged and still blocking — un-ignore the mockup
  folder (.gitignore:40)? is Mockup 4 signed off? visual contract or information-
  architecture contract? adopt --g-glass-fill .86 against tokens.json's own "do
  not correct (spec 6)" note? Phase 2 section 2 cannot start without #3. 25
  commits unpushed on nz-glass; no push authorisation given.
- 2026-09-21T23:11:29Z COMMIT: 7948be9ab chore(plans): record the four copied tokens and the reviewer budget → review dispatched
- 2026-09-21T23:11:52Z COMMIT: f6d148172 docs(glass): the handoff named a file set from before this session's work → review dispatched
- 2026-09-21T23:12:11Z COMMIT: 7705661ce chore(plans): the ring trimmed 115 lines, as designed → review dispatched
- 2026-09-21T23:16:13Z COMMIT: 166a20a67 fix(gates): px() accepted anything parseFloat would guess at → review dispatched
- 2026-09-21T23:19:37Z COMPACT: context compacted — read the last NEXT above before continuing
- REPAIR: the px() guard added in 166a20a67 was narrower than its own commit
  message implied. It validated the reads that went THROUGH px() and left three
  raw parseFloat calls beside it — including layout.content-column-lg, the very
  token whose copied literal (59e20f697) started this chain. A reviewer named
  one of the three; grepping by name instead of trusting the report found the
  other two in the lg: block. CLASS: a guard is only as wide as its call sites,
  and "I added validation" is not the same claim as "every read is validated".
- EVIDENCE: rung 2 — new test proved RED on HEAD's own source (5 pass/1 fail,
  the failure naming all three sites by expression), GREEN after: 9/9 tests,
  contrast 54 checked 0 failures. Guard reach proven by perturbation: pointing
  content-column-lg at "calc(100% - 30px)" now exits 1 naming that token and
  emits NO GATE_RESULT, so the runner reports FAIL rather than a silent pass.
  tokens.json restored, git status clean.
- 2026-09-21T23:24:07Z COMMIT: 166a20a67 fix(gates): px() accepted anything parseFloat would guess at → review dispatched
- 2026-09-21T23:24:23Z COMMIT: a51daf3fa fix(gates): the parseFloat guard did not cover three of its own call sites → review dispatched
- REPAIR: fifth instance of the same class, and the first that is not a token.
  contrast.mjs LG.scale {a:.32,b:.29,c:.25} said "matching glass-components.css"
  — a file whose own header says HAND-AUTHORED, holding width:32vw/29vw/25vw as
  literals under @media(min-width:1024px). The gate kept a copy of a number with
  no token behind it, so editing the CSS would leave the lg: proof green and
  proving the old geometry. CLASS unchanged: a proof that reads a copy of its
  input. Found by tracing a literal to its source instead of believing the
  comment that named one.
- EVIDENCE: rung 2 — new test asserts the gate's MODEL against the CSS's
  DECLARATION in both halves (scale vs vw width; the derived (offset/size)*scale
  origin vs the CSS's own -25.04/-22.51/-19.03vw, agreeing to 0.003vw). Proven
  red twice by perturbing the CSS: width 29->34vw and right -22.51->-18.00vw each
  fail with the drift named. 10/10 tests, contrast 54/0. CSS restored, clean.
- NOTE: my first version of that assertion was itself wrong — assert.equal(0.29
  * 100, 29) fails, because 0.29*100 is 28.999999999999996. Tolerance, not
  equality: the assertion is about the app's geometry, not about IEEE 754.
- NOTE: reviewer on a51daf3fa returned DEPLOY, no Critical/Warning. Its two
  Suggestions: blob-opacity (lines 167/246) is read raw and used arithmetically
  with no validator — same shape as px() but a different value class (number,
  not px string), pre-existing, NOT fixed here; and the test's comment-stripper
  only handles full-line //, which can only ever cause a false RED, never hide a
  real call. Both recorded rather than silently carried.
- 2026-09-21T23:28:03Z COMMIT: 6a9b01d9e fix(gates): the lg: blob model was a copy of hand-written CSS → review dispatched
- CORRECTION: the commit message on 6a9b01d9e says the derivation "lands within
  0.003vw" of the CSS. Measured from the tokens: deltas are a 0.0035, b 0.0005,
  c 0.0022 — max 0.0035, so the claim is false as written by 0.0005vw. The code
  is unaffected (tolerance is 0.005vw and every delta clears it); the SENTENCE
  was wrong. Caught by verifying my own claim numerically instead of restating
  it. Same class as the three progress.md correction blocks above: a figure
  quoted from memory rather than from the measurement.
  Corrected in the test's comment, which is where it will be read.
- EVIDENCE: rung 2 — 0.005vw = 0.0512px at 1024 and 0.0960px at 1920; a real
  1px drift at the 1024 breakpoint is 0.0977vw, ~20x the tolerance, so the
  tolerance is tight enough to catch anything that matters and is exactly the
  CSS's own 2dp rounding granularity. Media-block capture verified independently:
  the regex finds 5 blocks at min-width:1024px, and ALL three blob rules sit in
  block 1 with the other four capturing none — no truncation, no vacuous pass.
- NOTE: swept every sibling gate for the same copied-CSS-literal class. Only
  coherence.mjs holds a unit literal ("0px", a radius comparison, not a copy of
  a CSS declaration). No other gate models CSS geometry. The class is closed in
  design/gates/ as far as unit literals go.
- 2026-09-21T23:29:23Z COMMIT: 838018826 fix(gates): "within 0.003vw" was 0.0035vw → review dispatched
- NEXT: owner's word on FOUR, unchanged and still blocking — un-ignore the
  mockup folder (.gitignore:40)? is Mockup 4 signed off? visual contract or
  information-architecture contract? adopt --g-glass-fill .86 against
  tokens.json's own "do not correct (spec 6)" note? Phase 2 section 2 cannot
  start without #3. ~32 commits unpushed on nz-glass; no push authorisation
  given. Open reviewer Suggestion carried, not actioned: blob-opacity
  (contrast.mjs:167,246) read raw and used arithmetically with no validator —
  pre-existing, different value class (number not px string).
- 2026-09-21T23:29:51Z COMMIT: 7873ee6f6 docs(glass): the handoff described a file set two sessions old → review dispatched
- NOTE: reviewer on 6a9b01d9e returned DEPLOY. Its Warning was the 0.003 vs
  0.0035vw claim I had already corrected in 838018826 — and it recomputed the
  deltas independently from tokens.json, matching all three (a .0035 b .0005
  c .0022). Independent agreement, not an echo.
  Its Suggestion — route the test's parseFloat through px() too — is NOT
  actionable and is now documented in place rather than left looking like an
  oversight. px() cannot be imported: contrast.mjs has ZERO exports and no
  main-guard, so `import("./contrast.mjs")` runs the whole gate and calls
  process.exit(), taking the test runner with it (verified: the import printed
  the gate's own PASS lines). Fixing that means restructuring the gate for
  testability — a bigger change than the tidy it buys.
  Its safety argument checked out though: pointing blob-a-size at a calc() makes
  the test go RED (6 pass/1 fail), because NaN fails every comparison. Degrades
  loudly, never vacuously.
LEARNING(fact): design/gates/contrast.mjs is not importable — no exports, no
  main-guard, process.exit() at module scope. A source-grep test is the only
  seam available for it. Any future "just import the helper" suggestion against
  this file is blocked on giving it exports first.
