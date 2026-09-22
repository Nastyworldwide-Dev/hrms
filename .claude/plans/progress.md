2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-22T08:54:52Z COMMIT: 88e3f58e7 fix(sheets): a sheet measured itself against a viewport the phone was not showing → review+design dispatched
- 2026-09-22T08:55:47Z PUSH: nz-glass @ 88e3f58e7

REPAIR: S6 — Home's request panel rendered EVERY request a person had; ten of
  them is ~620px, another whole screen past the thing they opened Home for.
  Now five rows and a "Show {N} more" that expands in place.
  Two decisions the plan did not make, both the owner's call, both recorded:
  FIVE, not three. Measured: a row is two lines plus py-3 either side, ~62px,
  so five is ~310px inside the ~440px small-phone budget. Three fits too and
  hides rows from people who would never have scrolled anyway.
  EXPAND, not "See all". Each tab MERGES six doctypes (leaves, claims, shift,
  attendance, OT, replacement leave) and there is no combined list route, so
  the plan's "See all (N) -> the existing route" had no target: it could only
  point at ONE type's screen and answer a tap about nine requests with a page
  showing three. Expanding is also this app's own idiom (TeamDashboard rows,
  SideNav rail). Told the owner before building; he chose consistency of
  MEANING over a control that misstates where it goes.
  The control is a plain text button, NOT GGhostButton: that is a glass
  surface and Home already spends 4 of its 6 (§15.1). Verified after: still
  4/6.
EVIDENCE: 2 correct — RequestPanel.cap.test.js RED first (5 of 6), 5 mutants
  killed (count = total instead of hidden; cap removed; tab watch removed;
  label loses its count; the cap leaks into RequestList, which the full-screen
  lists share). Suite 528 tests / 524 pass — the same 4 that fail at HEAD.
  Lint clean. Gates byte-identical to baseline: contrast 54/0, surfaces 46
  screens / 0 over, Home 4/6, tokens ok. Build clean.
NOTE: my first version put `activeRequests` above `historyRequests` and read
  it — the exact temporal-dead-zone defect this repo already has a gate for
  (script-setup-order.test.mjs, currently red on two OTHER files at HEAD).
  Caught by reading the declaration order back before running anything.
NEXT: S4-S7 are done. Re-measure the app (e2e/app-measure.mjs at 360x640) and
  re-bake Home's visual baselines; the recorded numbers predate the bottom-nav
  repair and understate every overflow by ~65px.
- 2026-09-22T09:28:13Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-22T09:28:20Z PUSH: nz-glass @ 70bffe660
- 2026-09-22T09:28:20Z COMMIT: 70bffe660 fix(home): the request panel printed every request a person had → review+design dispatched

REPAIR: design review of 70bffe660 — one CRITICAL, two WARNINGs, all real, all
  mine. (a) FOCUS: the control renders `v-if="hidden > 0"`, so activating it
  unmounts the element that had focus and focus falls back to <body> — a
  keyboard or screen-reader user presses Enter, rows appear, and they are
  returned to the top of the page having pressed a button that as far as they
  can tell did nothing. The list is now focusable by script and takes focus
  after nextTick. (b) ANNOUNCEMENT: rows appearing announce nothing, and the
  control that would have said so is the thing that just disappeared. A polite
  sr-only region carries the count; the button carries aria-expanded and
  aria-controls. (c) TOUCH TARGET: py-3 + text-sm computes to EXACTLY 44 — the
  §14 floor met by arithmetic, one utility from failing, and at 120% dynamic
  type the label grows while the padding does not. Now an explicit minimum, as
  §10.1 #3's list row guards the same floor.
NOTE: my "~62px per row, five = ~310px" was measured on MY REQUESTS only. A
  TEAM row carries a third line — ListItem renders an avatar and employee name
  under isTeamRequest — so own rows are ~70px (5 = ~348px) and team rows ~102px
  (5 = ~508px, past the small-phone budget on its own). Five stays and the cap
  is the same on all three tabs: the panel sits BELOW the anchor and is
  scrolled to either way, so what five buys is a BOUND, not a fit, and one cap
  is what a person can predict. The comment now says that instead of quoting a
  figure that covered one tab of three.
EVIDENCE: 2 correct — 4 new tests, each red first, 6 mutants killed (focus
  before the rows exist; no focus call; live region removed; minimum removed;
  tab reset keeps a stale announcement; tabindex dropped). Suite 534 / 530
  pass, the same 4 red at HEAD. Gates back to baseline exactly: lint 242/10,
  contrast 54/0, surfaces 46/0, Home still 4/6, tokens ok. Build clean.
NOTE: the floor went through three spellings before it was right. `min-h-[44px]`
  is a second copy of the number; `min-h-[var(--g-touch-target-min)]` still
  trips the lint gate, which counts EVERY bracketed utility as an arbitrary
  value and is right to. It is a named class (.g-list-more) resolving to the
  token. Two of the three lint items I then "fixed" were in my own test's
  PROSE — a comment naming the utility it forbids — which is the third time
  this class has appeared today.
LEARNING(gate): a rule that counts a token also counts the comment explaining
  it. Strip comments before counting (usage.mjs already does); until then,
  never write the forbidden spelling inside prose the gate reads.
NEXT: S4-S7 all done. Re-measure (e2e/app-measure.mjs at 360x640) and re-bake
  Home's baselines — the recorded numbers predate the bottom-nav repair and
  understate every overflow by ~65px.
- 2026-09-22T09:35:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-09-22T09:35:14Z PUSH: nz-glass @ a46848871
- 2026-09-22T09:35:14Z COMMIT: a46848871 fix(home): pressing "Show more" sent keyboard users back to nowhere → review+design dispatched
- 2026-09-22T09:41:51Z COMMIT: 0cd678fe4 docs(plans): the hook lines for the Show-more accessibility fix → review dispatched

REPAIR: pre-2.0 R1. Owner's checklist, sections 8 (XSS) and the two open spec
  decisions he answered. THE REAL DEFECT was the sanitiser: three templates
  hand a server string straight to v-html (Notifications, SopDetail,
  TicketDetail). None is exploitable today — Frappe sanitises Helpdesk's rich
  text, SOP content is HR-authored, notification bodies are server-built — and
  every one of those is a statement about the CURRENT backend, enforced
  nowhere on this side. src/utils/safeHtml.js is now the one door: an
  ALLOW-list (a blocklist is a list of the attacks somebody thought of), the
  browser's own parser inside a detached <template> (hand-written tag regexes
  are how sanitisers get bypassed), and a no-DOM branch that returns TEXT
  because SSR and every unit test take it.
  NOT DOMPurify: a dependency is right for untrusted third-party HTML and this
  is three internal fields with a known vocabulary. The marker is in the file.
NOTE: the iOS input-zoom "defect" WAS ALREADY FIXED and I started fixing it a
  second time. I re-derived it correctly from `.g-input`'s 12.5px
  --g-type-row-label-size, added a `field-input` token, rebuilt the CSS — and
  then found the real rule two thousand lines further down in
  glass-components.css, pinning 16px below every other input rule so source
  order wins. Reverted the whole duplicate (and had to restore glass.css: yarn
  tokens regenerates it and dropped S7's dvh comment). The audit that found it
  was right about the mechanism and wrong about the state, because NOTHING
  SAID IT WAS DONE — §19 still listed DECISION 3 as open.
EVIDENCE: 2 correct — two new test files, both RED first (3 of 5 and 3 of 5),
  5 mutants killed: allow <script> through the tag list; allow the style
  attribute; make the no-DOM branch return its input; unwire one call site;
  delete the zoom rule. Suite 544 / 540 pass, the same 4 red at HEAD. Lint
  clean. Gates at baseline exactly: lint 242/10, contrast 54/0, surfaces 46/0,
  tokens ok. Build clean.
NOTE: spec §19's five open decisions are now recorded with the owner's answers
  (2 NO tab · 3 fixed · 4 cannot name a device, so §15's budget is an
  ASSUMPTION not a measurement · 5 accepted and already applied · 6 this
  branch is official, frappe-ui stays at 0.1.105). Decision 5 needed no work:
  nothing in tokens.json is under 10px. Both facts are now pinned by tests
  rather than left to be re-derived.
LEARNING(gate): a fix with no test and no spec update is a fix that gets paid
  for twice. Both re-found items today (DECISION 3, DECISION 5) were DONE and
  unrecorded. When an audit finds a defect, grep for the fix before writing one.
NEXT: R2 — API contract. ~60 of 115 endpoints do not pin an HTTP method (no
  writer is GET-exposed today; verified), 15 carry no visible guard, and
  nothing checks that the endpoints the PWA calls still exist.
- 2026-09-22T10:16:32Z EVIDENCE: 2 correct — mapped tests green (bun ) for 10 file(s) ⟂f3b86cf4d3e6
- 2026-09-22T10:16:35Z COMMIT: 62f83eff8 fix(security): three screens wrote server HTML into the page unchecked → review+design dispatched

REPAIR: pre-2.0 R2 — the contract between the PWA and its OWN api layer.
  `hrms/api/` is the PWA's backend, not Desk: 117 endpoints whose only caller
  is frontend/src, with no compiler between the two sides. Three rules now
  hold, each pinned by hrms/tests/test_pwa_api_contract.py:
  (1) every `hrms.api.*` the frontend names resolves to a real endpoint — 84
  called, 117 defined, nothing missing;
  (2) every endpoint DECLARES its method. 76 did not. All 76 turned out to be
  reads (checked one by one, not assumed), so nothing was GET-exposed — but
  nothing stopped the next writer inheriting "any method" by default, and a
  write reachable by GET is a write a link can perform;
  (3) every endpoint guards, or is a NAMED open read with its reason in the
  file. The exemption list is short and is itself checked: an entry that
  writes, or that reads Employee, fails the test.
NOTE: my first guard scan said 28 of 115 were unguarded. Wrong — it read only
  the endpoint's own body and missed every delegation (`_decide`,
  `is_hr_operator`, `_get_visible_doc`, `_decision_access`). The real figure
  was 5, and of those four delegate to `get_employee()` from utils/identity,
  which resolves the CALLER's own employee and nobody else's — scoped by
  construction rather than by a check it could forget. The fifth,
  hr_contacts, is a DIRECTORY: it filters on the HR role rather than on the
  caller because every employee is meant to see who in HR to ask. That is now
  recorded as a decision instead of read as an omission.
NOTE: a second scan claimed 5 write endpoints were GET-reachable. Also wrong,
  same cause — the regex ran past each endpoint into the next function. All
  five are reads. Both scans were corrected by reading the actual bodies.
EVIDENCE: 2 correct — test RED first (2 of 4 failing, 76 unpinned + 5
  unguarded), green after. 3 mutants killed: an endpoint loses its pin; a new
  unguarded endpoint appears; an open read starts writing. ruff clean, 36
  files already formatted. The 76-line diff across 14 api files is decorators
  ONLY — verified by diffing every changed line against /methods=/.
NOTE: a `git checkout` to revert a mutant took the real method pins with it
  (same file). Caught by the test going red on a "clean" tree; re-pinned and
  re-verified. Restore a mutant from a COPY, never from git, when the file
  also carries uncommitted work.
EVIDENCE: 3 works — security review of R1's sanitiser: SECURE, not blocking,
  no bypass found. It traced the real mXSS gadget classes against the code —
  noscript's scripting-flag mismatch, RAWTEXT round-trip (textarea/title/xmp),
  SVG/MathML foreign-content revival, and the SVG `<a>` + `<animate>`
  attribute hijack that was a real DOMPurify CVE — and each is closed, mostly
  because UNWRAP removes the wrapper tag entirely so the serializer mismatch
  has nothing to attach to. Its one INFO is taken: `plaintext` now deletes
  whole rather than unwrapping (it has no closing tag and swallows every
  following sibling), and the delete-list is a named set with its own test.
NEXT: R3 — reliability. navigator.onLine appears nowhere (the offline banner
  has no trigger), skipWaiting() takes a new build over mid-form, and the
  double-submit guards need a sweep.
- 2026-09-22T10:22:36Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 22 file(s) ⟂16efdd472c5b
- 2026-09-22T10:22:36Z EVIDENCE: 3 works — blast radius green: 16 dependent(s), 11 extra test file(s) ⟂7ccc0c0a1133
