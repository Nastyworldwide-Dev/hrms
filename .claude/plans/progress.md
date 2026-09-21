2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
  remote_checkin_request_hooks 25, two_approvers 3, selfie 4, company_api_scope
  31, api/test_approval 31, chain 15, shift chain 7, no-approver 6, self-approval
  13. Two pre-existing skips need a real bench. ruff clean.
EVIDENCE: 6 — family ledger .claude/plans/family.md, 11 call sites same-root,
  team.py's display-only tab gate ticketed.
NEXT: commit, review, push, refresh HANDOFF.
- 2026-09-21T18:22:33Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T18:25:07Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:25:07Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:25:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:25:31Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:25:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:25:48Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:25:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:25:59Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:26:37Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-21T18:26:37Z EVIDENCE: 3 works — blast radius green: 23 dependent(s), 20 extra test file(s) ⟂d5cc3dd5241d
- 2026-09-21T18:26:41Z COMMIT: 0a0d0402c fix(remote-checkin): a remote punch routes up the employee's own chain → review+cross-app dispatched

LEARNING(gate): family-hunt sweeps production call sites of the CHANGED symbols only ->
  it misses test files that call the changed function directly (here
  hrms/overrides/test_remote_checkin_request_hooks.py pinned the removed
  Department Approver tier, and is bench-only so no local run catches it).
  Proposed gate: the family scan greps the changed function NAMES across
  test_*.py as well, and a bench-only test (FrappeTestCase) naming a changed
  function needs a verdict line like any other call site.
NEXT: push 0a0d0402c + the bench-test amendment, refresh docs/glass/HANDOFF.md.
- 2026-09-21T18:29:59Z COMMIT: 353ceb7d6 test(remote-checkin): the department tier is pinned as absent, not as winning → review+cross-app dispatched
- 2026-09-21T18:30:58Z PUSH: nz-glass @ 353ceb7d6
- 2026-09-21T18:31:16Z PUSH: nz-glass @ 1c36eeebc
- 2026-09-21T18:31:16Z COMMIT: 1c36eeebc docs(glass): handoff for the remote check-in routing fix → review dispatched
- 2026-09-21T18:43:17Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T18:54:22Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:54:27Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:54:31Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:54:34Z COMMIT: 1c36eeebc docs(glass): handoff for the remote check-in routing fix → review dispatched
- 2026-09-21T18:54:44Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:55:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-21T18:55:09Z COMMIT: ecc3b8d7b fix(pwa): one waiting word, and a rejected remote punch looks rejected → review+design dispatched

REPAIR: 21 Sep — one waiting word on screen; Remote Approvals joins the shared
  status rule; Employee Issue states get colour. Commit ecc3b8d7b.
EVIDENCE: 2 correct — frontend/src/utils/__tests__/requestStatus.test.js, 5 RED
  on HEAD before the change, 9 green after.
EVIDENCE: 3 works — 143 frontend tests green (utils + components), prettier
  clean on the three changed files.
LEARNING(fact): slice 4 of the Thread F plan (track_changes on Leave
  Application and Expense Claim, plus the guarded Property Setter patch) was
  already shipped this morning in f04526cea with test_who_approved_when.py. The
  audit that surfaced it (H-request-dates-backend.md H1) predates that commit.
NEXT: slices 5 and 6 of the request-status unification wait on the owner — the
  RequestPolicy table needs his ruling on backdating windows for Shift Request,
  Expense Claim, Attendance Request and Compensatory Leave (today: none at all),
  and the clock unification is its own change. Deploy ecc3b8d7b first.
NEXT: also open — .claude/plans/ticket-waiting-word-in-filters.md (the two list
  filters still offer the stored word; needs FormField Select to take
  {label, value} pairs first).
- 2026-09-21T18:56:48Z COMMIT: aea8da075 docs(plans): record what the waiting word left open → review dispatched
- 2026-09-21T18:56:48Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T18:58:56Z PUSH: nz-glass @ aea8da075
- 2026-09-21T18:59:20Z PUSH: nz-glass @ c1200e921
- 2026-09-21T18:59:20Z COMMIT: c1200e921 docs(glass): handoff for the one-waiting-word slice → review dispatched
- 2026-09-21T19:01:13Z PUSH: nz-glass @ 61b16f93e
- 2026-09-21T19:01:13Z COMMIT: 61b16f93e style(remote-approvals): the name gives ground on purpose, not by accident → review+design dispatched
- 2026-09-21T19:01:25Z PUSH: nz-glass @ 5cc2206f2
- 2026-09-21T19:01:25Z COMMIT: 5cc2206f2 docs(glass): point the handoff at the tip commit → review dispatched
- 2026-09-21T19:10:36Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T20:05:00Z EVIDENCE: rung 5 (looks right) — nadi-2.0-mockup-4.html rendered in Chromium at 320/390/1280, light+dark, 12 states captured, 0 console + 0 page errors; axe-core WCAG 2 A/AA + 2.1 + 2.2 AA = 0 violations across 13 states.
- 2026-09-21T20:05:00Z REPAIR: nine defects found by that pass and fixed — dev strip covering the app bar (assumed 38px, now measured), [hidden] losing to a class selector, focus ring drawn round <main>, tab labels colliding at 320px, calendar role="grid" without rows (now role="list"), and five AA contrast pairs (waiting chip, segmented control, caption on page bg, text+chips on sheet glass, three dark chips).
- 2026-09-21T20:05:00Z LEARNING(how): text laid on CHROME GLASS has no fixed backdrop, so token inks tuned for a white card fall under AA there. Any .sub/.eyebrow/.chip inside a sheet needs its own ink rule. Cheapest check is axe with the sheet OPEN — a closed-sheet pass reports nothing.
- 2026-09-21T20:05:00Z NEXT: owner reviews "Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html" (+ -notes.md); the folder is gitignored so neither file is committed. Thread F slice 5 still waits on the backdating ruling.
- 2026-09-21T19:28:50Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T19:44:50Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T20:45:00Z REPAIR: mockup 4 reworked onto nadi-2.0-mockup.html at the owner's preference — Inter Tight/Inter web fonts, 390x844 device on a dark stage with the mockup toolbar, blurred light field + four-layer liquid glass, 11 screens + 5 sheets, switchable Lime B. Done as a rebase, not a merge: mockup 1 became the file, then every a11y fix the old mockup 4 had earned was re-applied on top.
- 2026-09-21T20:45:00Z EVIDENCE: rung 5 (looks right) — axe-core WCAG 2 A/AA + 2.1 + 2.2 AA over 20 states (5 tabs, 5 secondary screens, 3 sheets, 4 dark, desktop, Lime B) = 0 violations; 12 Chromium screenshot states = 0 console + 0 page errors.
- 2026-09-21T20:45:00Z REPAIR: mockup 1's palette carried eleven AA failures the old mockup 4 did not — four pill inks, the quiet caption on two surfaces, the weekday header, the row chevron, the out-of-range day opacity, dark ink3, and black UA text on button-as-surface. Every replacement computed as a luminance ratio, not eyeballed (e.g. 3.84 -> 6.10, 2.84 -> 5.87, 1.17 -> inherit).
- 2026-09-21T20:45:00Z LEARNING(how): a <button> used as a SURFACE (button.panel / button.card) never inherits the app's ink — the .row reset only covers .row, so it keeps the UA's black and disappears on a dark surface at 1.17:1. It is invisible to a light-mode-only audit; only axe run in dark finds it.
- 2026-09-21T20:45:00Z LEARNING(how): a coloured pill ink tuned for a white card fails on its own 14-26% wash. Measure each pill ink against the wash it actually sits on, and give light mode its own value while dark falls back to the token.
- 2026-09-21T20:45:00Z NEXT: owner reviews the reworked "Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html" (+ rewritten -notes.md); the folder is gitignored (.gitignore:40) so neither file is committed — un-ignoring is his call. Thread F slice 5 still waits on the backdating ruling; deploy ecc3b8d7b..5cc2206f2 still pending.
- 2026-09-21T20:01:29Z COMPACT: context compacted — read the last NEXT above before continuing

2026-09-21T23:40:00Z REPAIR: mockup-4 reworked against 2026 standards — 13 findings, each an external rule plus a measured number in the file.
2026-09-21T23:40:00Z EVIDENCE: rung 5 (looks right) — tab bar inside the frame at 320/360/390/414 (was +117..+262px off-screen); axe 0 violations across phone screens, 4 request states, dark, desktop; every visible button >=44px; 19 screenshots, 0 console + 0 page errors.
2026-09-21T23:40:00Z LEARNING(fact): a flex child with no min-height:0 will not shrink below its content — that alone pushed an absolutely-positioned tab bar out of an overflow:hidden frame at EVERY width, not just the reported one. The user reported "missing on mobile"; measurement found it missing everywhere.
2026-09-21T23:40:00Z LEARNING(how): for "too much scrolling", measure screen depth before cutting content. Eight of eleven screens already fit one viewport; the real defect was two NESTED horizontal scrollers, which is a different fix from pagination.
2026-09-21T23:40:00Z DEAD END: axe reports target-size x13 on the desktop preview. It is the mockup's own 0.72 scale transform, not the layout — at real desktop size nothing is under 24px CSS. Not a finding.
2026-09-21T23:40:00Z NEXT: owner reviews the reworked "Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html" + notes; the folder is gitignored (.gitignore:40) so neither file is committed — un-ignoring is his call.
- 2026-09-21T20:44:24Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T21:15:48Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T21:44:34Z COMPACT: context compacted — read the last NEXT above before continuing

REPAIR: mockup 4 defect-family audit closed. 7 families found by measurement,
  all fixed: A contrast through glass (61 -> 0), B inert ellipsis on
  display:inline (7 -> 0), C home depth (1.59 -> 1.36 viewports), D sheet detent
  (226px top-edge swing -> 0), F tap targets (3 -> 0), G ragged column edge
  (259/338px -> clean), G2 ragged inner edge (12px pill spread -> clean),
  H text resting under floating chrome (12 -> 0).
EVIDENCE: rung 2. a2 NO LOW-CONTRAST TEXT over 1754 verified boxes, both themes,
  29 states, self-test 13.80:1. a3 no clipped text; sheet top=399 h=444 on all
  30 days. a5 ANIMATES 19 frames 482->0. a7 under 44px: none, clean at 8 widths
  320-1440. a8 COLUMN EDGE CLEAN + INNER EDGE CLEAN. a9 NO TEXT RESTS UNDER
  CHROME. Visual read of 10 screenshots, light and dark.
EVIDENCE: 6 probe defects found and fixed while closing the families, each
  recorded in .claude/plans/family-mockup4.md because each would have hidden a
  real defect later. The worst: offsetParent reports a collapsed <details> as
  visible, so three probes were measuring text nobody can see.
DEAD END: axe-core cannot answer contrast through backdrop-filter — it returns
  INCOMPLETE, never a violation. The earlier "0 violations" verdict was the tool
  declining to answer. Real-pixel sampling replaced it; notes file corrected.
NEXT: owner's word on two things before Phase 2 starts — (1) un-ignore
  "Nadi PWA UI UX 2.0" (.gitignore:40) so the mockup repairs can be committed,
  or leave it uncommitted; (2) confirm Mockup 4 is signed off as the visual
  contract, which is the gate he set for the full PWA 2.0 frontend build.
- 2026-09-21T22:12:27Z COMMIT: 3fe415b8e docs(glass): what the mockup-4 audit found, and why the last one missed it → review dispatched
- 2026-09-21T22:12:56Z COMMIT: a0412dbb1 docs(glass): point the handoff at the audit commit → review dispatched

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
