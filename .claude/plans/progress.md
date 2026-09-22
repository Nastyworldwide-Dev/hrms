2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-22T10:22:40Z COMMIT: fc5e8bf4a feat(api): the PWA and its own backend had no contract between them → review+security dispatched
- 2026-09-22T10:23:09Z PUSH: nz-glass @ fc5e8bf4a

REPAIR: pre-2.0 R3 — two things the app never told the employee.
  OFFLINE: `navigator.onLine` appeared NOWHERE in src/. The offline banner
  existed and only the design specimen ever drew it, so a phone that lost
  signal mid-shift looked exactly like a slow server — tap, nothing, spinner,
  tap again. Now composables/useOnline.js (ONE module-level ref: three
  components each holding their own listener is three answers that can
  disagree) and components/OfflineBanner.vue in App.vue, so every screen has
  it rather than one screen having it.
  UPDATES: `registerType: "autoUpdate"` plus `self.skipWaiting()` at module
  scope meant a new build activated and reloaded the page the moment it
  downloaded — mid-form, losing whatever was typed. Now "prompt": the build
  still downloads immediately and takes the page when the employee presses
  Reload. The worker waits for one SKIP_WAITING message from the page.
NOTE: neither bar is GBanner or .g-glass, on purpose. Both render in App.vue
  ABOVE every screen, so a glass surface there is a compositing layer on all
  forty-odd of them against a budget of six — and the surfaces gate walks
  views/ only, so it would never be counted. §15.3 exists for exactly that.
  Opaque bars cost nothing and read the same. Verified after: 46 screens, 0
  over.
NOTE: `navigator.onLine` is weaker than it reads and the file says so: FALSE
  is reliable, TRUE only means an interface exists — a captive-portal wifi
  reports true and cannot reach Frappe. So it EXPLAINS a failure the employee
  is already looking at; it never decides whether to attempt a request.
EVIDENCE: 2 correct — offline-and-updates.test.js RED first (7 of 7), 5
  mutants killed: autoUpdate returns; the worker seizes again; the message
  listener is renamed; the composable leaks its listeners; the banner shouts
  (role=alert). Suite 552 / 548 pass, same 4 red at HEAD. Lint 242/10,
  contrast 54/0, surfaces 46/0, tokens ok. Build clean, and BOTH halves
  verified IN the output: SKIP_WAITING in sw.js, registerSW in its own chunk.
NOTE: mutant F4 survived twice. `void 0 && window.removeEventListener(...)`
  keeps the call's TEXT, so an unanchored /removeEventListener/ matched a line
  that removes nothing. A source-level test cannot see reachability; what it
  can pin is the SHAPE, so the assertion is now anchored to the start of the
  line — an unconditional statement, not a guarded expression.
NOTE: R2's review (DEPLOY, no Critical) established something worth keeping:
  a bare `@frappe.whitelist()` allows ALL verbs, so pinning ["GET","POST"] was
  a NARROWING, not a widening. Its one real finding is taken: the contract
  test matched guard words inside DOCSTRINGS, so an endpoint whose only
  "approver" was in prose passed. Docstrings and comments are now blanked
  before matching — and that immediately caught a real one,
  get_current_employee_info, whose guard is one delegation further out
  (get_employee_info in utils/identity). Two new mutants cover it.
LEARNING(gate): four times today a rule counted the COMMENT that explains it —
  usage.mjs, the dvh unit, the sanitiser's v-html, the worker's skipWaiting.
  Strip comments before counting, in every gate, without waiting to be bitten.
NEXT: R4 — accessibility over forms (labels, errors tied to fields, focus
  traps) and observability (frontend error capture with the build id).
- 2026-09-22T10:30:38Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
