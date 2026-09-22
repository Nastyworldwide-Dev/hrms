2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
  container is UNCAPPED — expense_claim/Dashboard.vue:5 is
  `lg:grid lg:grid-cols-[1fr_1.2fr] lg:p-7` with no max-width, inside
  BaseLayout's `lg:max-w-none lg:mx-0`. There the blobs DO reach the text box:
  browser-measured alpha 0.019/0.023/0.032 at 1440px and 0.060/0.065/0.089 at
  1920px, putting dark --ink-muted at 4.42 and 4.07 against the 4.5 floor
  (light 4.44 at 1920 on blob C). The gate prints all 24 lg: combinations as
  "ZERO alpha" clear. So the gate is not merely pessimistic about a wide
  column — it is OPTIMISTIC about this view, in the direction that hides a real
  sub-AA cell. CLASS: a gate proving geometry the app does not draw — the same
  class contrast.mjs's own comments and contrast-column.test.mjs exist to
  catch, and contrast-column.test.mjs asserts NOTHING about alignment or blob
  anchoring, so nothing went red when the app centred.
  Exposed call site: .g-chip--muted (glass-components.css:755) is
  `background: transparent` + `color: var(--g-ink-muted)` with its own recorded
  margin 4.56/4.58 — about 0.06 of headroom, so any blob alpha takes it under.
  It renders on that screen via ExpenseClaimItem.vue:22 -> GStatusChip.
  NOT FIXED HERE. Fixing it is a code change to a shipped view or to the gate,
  neither of which is what was asked, and the right fix depends on O3 (do the
  blobs stay?), still OPEN. Recorded for the owner's queue.
- EVIDENCE: rung 1+2 — contrast 54 checked 0 failures exit 0, 13/13 tests, both
  before and after. No token, no shipped CSS and no view changed; the only new
  file is a probe nothing imports.
- 2026-09-22T02:09:24Z COMMIT: 801c8fadd docs(design): the lg: contrast gate models geometry the app never draws → review dispatched
- NOTE: skipped frappe-reviewer + retro on 801c8fadd — docs/evidence, 2 files
  (one probe nothing imports, plus the ledger), zero Python/Frappe/doctype
  surface, exempted per this repo's own chore/docs/style <=2-files rule, same as
  36b5baacb, 078698b5b, 9c4df8ac3, d62bddd53, e56319358, 54b4b7b77. The
  adversarial verifier already did the substantive review of this commit's
  content, and its refutation is what the commit records.
- 2026-09-22T02:10:00Z COMMIT: 0c23be5f9 chore(plans): record the reviewer exemption for the gate-model evidence → review dispatched
- 2026-09-22T02:10:11Z PUSH: nz-glass @ 0c23be5f9

REPAIR: Fix attendance was dead on every day it exists for. `fresh_state` read
  `day_plan`'s REFUSAL as an ABSENCE and pre-ticked every counted punch, so the
  dialog refused its own opening state ("ticked: 3 IN, 1 OUT") and Save & rebuild
  deleted nothing, rebuilt nothing and re-shifted nothing.
EVIDENCE: 2 (correct) — red proved on HEAD before the fix: 2 failed in
  hrms/tests/test_fix_day_unreadable_day.py, 3 failed (11/12/13) in
  hrms/public/js/fix_day.bundle.test.js. Green after: 77 passed across
  test_fix_day_unreadable_day / test_fix_day_rebuilds_a_day / test_fix_day_screen.
EVIDENCE: 3 (works) — the real dialog driven end to end in a vm sandbox over
  Adam Daniel's actual 18 Aug: pre-ticked 0 of 4, the next-morning punch shown as
  "07:38 19 Aug", and after HR ticks the true night pair the save sends
  pairs=[{in:C,out:D,shift:"7PM - 3.30AM"}] delete=[A,B]. Before the fix the same
  day could not reach a saveable state at all.
NOTE: hrms/public/js/fix_day.bundle.test.js tests 1-3,6-8,10 were ALREADY red on
  HEAD (stale: they assert the six pre-21-Sep buttons the one-button rewrite
  removed). Not touched here. 5 tests in test_attendance_fix_day_save_day.py are
  likewise red on HEAD, verified identical by stashing this change.
NEXT: Nabil deploys; then re-open Adam Daniel 18 Aug and confirm the dialog opens
  with nothing ticked and the reason shown. The stale JS/py suites above want a
  separate pass.
- 2026-09-22T02:50:34Z COMPACT: context compacted — read the last NEXT above before continuing
REPAIR: hrms/public/js/fix_day.bundle.test.js tests 1-10 re-aimed at the shipped one-button
  screen. They asserted run()/dedupe/claim_tap/relabel/show_change — removed by the 21 Sep
  rewrite and pinned as gone by test_fix_day_screen.py — so they had been red on HEAD ever
  since. Each kept as the INCIDENT it was written for, against what shipped.
EVIDENCE: 2 correct — node --test fix_day.bundle.test.js 13 pass 0 fail (was 6/7).
EVIDENCE: 2 correct — mutation check: 6 of 7 rewritten assertions go red when the behaviour
  they name is broken (the 7th is a doesNotMatch guard, which cannot); bundle restored identical.
NOTE: the stale-test repair widens this hotfix beyond the defect. Kept visible, not folded in:
  the commit gate refuses a red suite and the project rule is "write the test or split", not stash.
NEXT: commit the hotfix + test repair, push, write docs/glass/HANDOFF.md.
- 2026-09-22T02:56:54Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-09-22T02:56:54Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 1 extra test file(s) ⟂878a988d4e57
- 2026-09-22T02:56:57Z COMMIT: a531bd3d4 fix(fix-attendance): a refused day is not an unknown day → review dispatched
- 2026-09-22 NOTE: Desk token snapshot + the two attendance plan files were untracked/unstaged
  across the hotfix. They are the design contract this fix was built against, not scratch —
  committed as docs so the next session reads the same spec. .claude/brag/ is self-ignored.
NEXT: read the frappe-reviewer verdict on a531bd3d4; if DEPLOY, push nz-glass and write
  docs/glass/HANDOFF.md; if FIX_CRITICAL, fix and re-commit (review re-triggers).
- 2026-09-22T02:58:29Z COMMIT: 8b7496492 docs(plans): the attendance spec the Fix Attendance work is built against → review+security+design dispatched
- 2026-09-22T03:01:22Z COMMIT: 5e84d51fb docs(design): the Desk pills fail AA because Desk's pills fail AA → review+security+design dispatched
- 2026-09-22 REPAIR: two assertions from the hotfix matched whole-file `src`, so they pinned the
  CONSUMER only. Blanking `day_label` in fresh_state, or stubbing the summary's refusal branch,
  left all 13 green — the wire was untested, and it is the wire this hotfix exists to fix.
  Found by the reviewer's independent mutation re-derivation, not by mine: my 6-of-7 claim was
  wrong (it was 4 of 7). Both now scoped to their method slice and pinned at the producer.
- 2026-09-22 EVIDENCE: 2 correct — 4 mutants now bite where 2 did not: blank day_label producer,
  drop the producer line, stub `const why =`, drop `why` from the render. Bundle restored clean.
LEARNING(how): in fix_day.bundle.test.js the source-asserted tests slice per method
  (src.indexOf("tap_html(row) {")). An assertion matched against whole-file `src` silently stops
  pinning the producer->consumer wire. Match a name that occurs ONCE in the slice (the assignment
  `const why = ...`), never the bare field name — it recurs and survives the mutation.
NEXT: push nz-glass, then write docs/glass/HANDOFF.md.
- 2026-09-22T03:03:25Z COMMIT: 9aae23f42 test(fix-attendance): pin the wire, not just the consumer → review dispatched
- 2026-09-22T03:04:18Z COMMIT: f844ae9bd docs(plans): G13 has no test, and the split ticket has no date → review dispatched
- 2026-09-22T03:04:31Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-22T03:08:35Z COMMIT: 7950344fd docs(design): the contrast note was wrong — only green fails → review+security+design dispatched
- 2026-09-22 REPAIR: the 5e84d51fb contrast annotation understated every ratio (by 0.4-0.8) and
  called orange a WCAG failure at 4.22 when it passes at 4.92. Recomputed from the committed
  hexes: blue 4.58 / orange 4.92 / red 5.70 pass, green 3.58 is the ONLY pill that fails.
  Greys stand (500 2.85, 600 4.17 fail; 700 7.81 passes). Committed 7950344fd.
  EVIDENCE: 2 correct - WCAG 2.1 relative luminance recomputed independently before editing;
  the design reviewer's figures and mine agree to 2 dp on all 10 pairs.
- 2026-09-22 NOTE: a reviewer left mutant (c) applied in the working tree (`const why = ""` in
  fix_day.bundle.js). Caught by `git diff` before the commit, restored, suite re-run 13/13 on a
  clean bundle. A mutation reviewer edits the real file - check the tree after every one.
LEARNING(gate): a subagent's mutation test can leave the source mutated -> before every commit,
  `git diff --numstat` the files the reviewer touched, never just `git status`.
- 2026-09-22 NOTE: the f844ae9bd reviewer returned FIX_CRITICAL, but its Critical is "implement
  the G13 test" - which is what the ticket asks the OWNER to schedule. It independently confirmed
  the ticket's claim (G13 unreferenced anywhere in hrms/) and found no other unreferenced guard.
  A filed ticket is not a defect in the commit that files it; no code change taken.
  It also found test_attendance_endgame.py:153 "agrees with nightly" asserts state MARKS only,
  not day CONTENT - a name/behaviour mismatch worth recording on the G13 ticket.
NEXT: land the design reviewer's verdict on 7950344fd, then push nz-glass and write
  docs/glass/HANDOFF.md.
- 2026-09-22T03:09:29Z COMMIT: 4ffa311f1 docs(plans): G13's absence confirmed, and the test that hid it → review dispatched
- 2026-09-22T03:13:16Z COMMIT: ecb213981 test(fix-attendance): six tests red since 21 Sep, none of them a defect → review dispatched
- 2026-09-22T03:15:33Z PUSH: nz-glass @ ecb213981
- 2026-09-22T03:15:59Z PUSH: nz-glass @ f4a6c1de4
- 2026-09-22T03:15:59Z COMMIT: f4a6c1de4 docs(handoff): the unreadable-day hotfix, pushed → review dispatched
- 2026-09-22 REPAIR: six tests had been red since 21 Sep and none was a defect. Five were a stale
  3-unpack after 04e7bb62e gave the rebuild stub a 4th element; one armed `_financial` when
  Save & rebuild runs requests_ok=True and reads `_paid_day`; one asserted on `show_change`,
  removed by the one-button rewrite 9e5232647. Re-aimed at result_html. Committed ecb213981.
  EVIDENCE: 2 correct - the paid-day guard driven through the seam save_day actually uses still
  refuses ("This day is already paid... (SAL-0001)"); 3 mutants bite (stop filtering held
  verdicts / drop verdict.detail / financial=None). 43 green across the three files.
  Reviewer confirmed at source: the Salary Slip leg of _repair_financial_dependency is
  unconditional, so the seam change silenced nothing.
- 2026-09-22 PUSH: 0c23be5f9..f4a6c1de4 nz-glass (9 commits). docs/glass/HANDOFF.md written.
NEXT: Nabil deploys on Frappe Cloud; then open Adam Daniel 18 Aug in Fix attendance and confirm
  four punches listed, none ticked, the engine's reason shown, and Save & rebuild enabled once
  the true pair is ticked. The UI itself was never browser-verified here (no dev site reachable).
- 2026-09-22T03:16:17Z PUSH: nz-glass @ cfc78998e
- 2026-09-22T03:16:17Z COMMIT: cfc78998e docs(plans): progress through the push → review dispatched
- 2026-09-22 NOTE: retro on 0c23be5f9..ecb213981 counted SHOTS: 3, extra shots 9aae23f42
  (oracle-gap: assertions scoped to the whole bundle, not the method) and 7950344fd. It filed the
  second as 'spec-gap', which would make spec-gap x7 and aim the next gate at specs. It is not a
  spec gap: the spec was fine, the arithmetic was mine and I published it unchecked. Class is
  unverified-figure. The gate that would have caught it is cheap and worth having either way:
  any commit whose message or diff states a contrast ratio recomputes it from the committed hexes
  before the commit stands. Both extra shots were caught by a reviewer, not by me.
NEXT: Nabil deploys on Frappe Cloud; then open Adam Daniel 18 Aug in Fix attendance and confirm
  four punches listed, none ticked, the engine's reason shown.
- 2026-09-22T03:17:47Z PUSH: nz-glass @ fe2638b16
- 2026-09-22T03:17:47Z COMMIT: fe2638b16 docs(plans): the retro's second shot was not a spec gap → review dispatched
- 2026-09-22T03:22:48Z COMPACT: context compacted — read the last NEXT above before continuing

EVIDENCE: rung 1 — Home density + icon inventory measured 22 Sep. Shipped Home
  1382px content / 844 fold / 538 overflow at 390x844 for TEN tap targets
  (docs/glass/audit/2026-09-09-app-measure.json). That file records tabH:0 on all
  36 screens — measured BEFORE the bottom nav repair (3d4fa0dfe) — so every fold
  is ~64-73px too generous. Directionally right, precisely wrong; must be re-run.
EVIDENCE: rung 1 — icons: feather-icons 4.29.2 already a dep; frappe-ui's
  FeatherIcon does `import feather from 'feather-icons'` (namespace), so all 287
  icons ship (52.5 KB raw / 10.5 KB gz) while only 13 names are used across 6
  files (1.6 KB / 0.6 KB gz). Cannot tree-shake: Object.keys(feather.icons) runs
  at module scope for the prop validator. Plus 14 hand-rolled components
  (263 lines / 6.9 KB) and 34 inline <svg> in 29 .vue files. 0 ion-icon.
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
