2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-22T10:30:45Z PUSH: nz-glass @ 796d015c4
- 2026-09-22T10:30:45Z COMMIT: 796d015c4 fix(pwa): the app never said it was offline, and updated without asking → review+design dispatched

REPAIR: design review of 796d015c4 — two CRITICALs, both real, both mine.
  (a) OVERLAP: the offline bar was `position: fixed; top: 0`, and `.g-header`
  is TRANSPARENT and sits in NORMAL FLOW — its own comment says content never
  scrolls under it, an assumption the bar broke. So the bar landed on the back
  control: the employee is told they have no connection in the same moment
  they lose the way out of the screen. It is in flow now and FIRST in
  <ion-app>, so it pushes the outlet down for exactly as long as it shows.
  Found independently here and by the reviewer, same reasoning.
  (b) CONTRAST: --g-bg on --g-warn-ink measured 4.36:1 in light against the
  4.5 floor. warn-ink is a TEXT colour for glass; using it as a FILL was the
  error. New --g-warn-fill: 6.33 light, 6.32 dark.
NOTE: the contrast GATE could not have caught it. Every pair it knew was
  ink-on-glass or ink-on-tint; a solid themed fill had no shape in the table,
  so the gate passed 54/54 while a real failure shipped. It has a "solid"
  branch now, and the pair is listed. Verified by re-introducing #B45309:
  FAIL light 4.36, exactly the number the review computed by hand.
NOTE: the tokens gate then refused warn-fill for collapsing onto warn-ink in
  dark — two names, one value, so a swap between them would be invisible. It
  is right. Dark is #D97706 now, distinct and still 6.32.
NOTE: S7's dvh fix WAS SILENTLY REVERTED and had been for two commits. It was
  hand-patched into src/theme/glass.css, which is GENERATED from
  design/tokens.json — so every `yarn tokens` since put `100vh` back, and
  today's run did it twice while I watched the diff and restored the comment
  instead of the cause. The token now carries `fallback` and the builder emits
  two declarations. The behaviour test passed throughout, because it reads the
  generated file and I had just restored it by hand.
LEARNING(gate): never hand-edit a generated file. If a fix belongs in
  glass.css it belongs in design/tokens.json, and if the generator cannot say
  it, teach the generator.
LEARNING(gate): FIVE separate times today a rule counted the COMMENT that
  explains it. lint.mjs now strips comments before counting, as usage.mjs
  already did — and the total fell 242 -> 234, so eight recorded "violations"
  in this app were never violations. Baseline rewritten: 234 total, 0 new.
EVIDENCE: 2 correct — 2 new tests (the bar takes its own room; the prompt
  clears the tab bar), both red first. Suite 554 / 550 pass, same 4 red at
  HEAD. Gates: lint 234/0 (first clean run this session), contrast 56/0,
  surfaces 46/0, tokens ok. Build clean.
NEXT: R4 — accessibility over forms (labels, errors tied to fields, focus
  traps) and observability (frontend error capture carrying the build id).
- 2026-09-22T10:39:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 12 file(s) ⟂1127c68211d5
- 2026-09-22T10:39:13Z PUSH: nz-glass @ ca73a9046
- 2026-09-22T10:39:13Z COMMIT: ca73a9046 fix(pwa): the offline bar covered the back button and failed contrast → review+security+design dispatched

REPAIR: pre-2.0 R4 — forms that explain themselves, failures somebody can
  investigate. The audit expected far more than it found: GInput and GTextarea
  already wrap their control in a <label>, already set aria-invalid, already
  render the error in a live region, and GModal already carries the focus trap
  the raw ion-modal lacks. Most of checklist §4 and §5 was built. Two were not.
  (a) THE ERROR WAS NOT LINKED TO THE FIELD. aria-invalid says THAT it is
  wrong; only aria-describedby says what. A screen reader announced "Reason,
  invalid, edit text" while the sentence explaining it sat in a live region
  already read and moved past. Both fields now carry a per-INSTANCE id from
  Vue's own useId — shared ids would make the second invalid field on a form
  describe the first one's error.
  (b) NOTHING RECORDED A FAILURE. utils/diagnostics.js attaches the three
  seams a browser offers (window.error, unhandledrejection, Vue's
  errorHandler), carries a build stamp, and redacts before writing.
NOTE: deliberately NOT a telemetry vendor. The server is Frappe and already
  has an Error Log; a dependency, an egress path and a data-protection
  question in exchange for a dashboard nobody would open is a bad trade for
  forty employees. The reason is in the file so the next person does not add
  one by default.
NOTE: redaction is enforced in the reporter, not by asking callers to be
  careful — password, token, api_key, session, salary, ctc, bank, nric,
  passport, matched loosely at any depth, because a list of exact field names
  ages badly. And report() swallows its own failure: a reporter that throws
  inside an error handler takes the page down AND loses what it was reporting.
EVIDENCE: 2 correct — 7 tests RED first (7 of 7), 5 mutants killed. THREE
  survived the first round and all three for the same reason: the test read
  the SOURCE for a word instead of exercising the behaviour. A shared
  `const errorId = "field-error"` still contains "errorId"; a `redact` that is
  never called still puts the word in the file; a reporter with no try/catch
  still has the word "catch" elsewhere. Rewritten to import the module, stub
  console.error, and assert on what is actually written — including that
  redaction keeps the SHAPE (the key is still named, a non-sensitive value
  survives) rather than being a synonym for silence.
NOTE: the build stamp broke two checks that were right to break: eslint's
  no-undef and tests/no-undefined-identifiers.test.mjs both flagged
  __APP_BUILD__, which exists only after vite's `define` substitutes it.
  Declared as a readonly global in .eslintrc.cjs. Verified in the OUTPUT, not
  the source: the bundle carries the literal "2026-09-22 10:46".
EVIDENCE: 3 works — suite 561 / 557 pass, the same 4 red at HEAD. Gates:
  lint 234/0, contrast 56/0, surfaces 46/0, tokens ok. Build clean.
NEXT: R5 — re-measure. The harness and the source-level checks ship; the
  numbers wait on a reachable site (owner: "if site is inaccessible its okay").
- 2026-09-22T10:47:54Z EVIDENCE: 2 correct — mapped tests green (bun ) for 8 file(s) ⟂514b00a817f9
- 2026-09-22T10:47:54Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-22T10:48:00Z PUSH: nz-glass @ b7a23bc7c
- 2026-09-22T10:48:00Z COMMIT: b7a23bc7c feat(pwa): a field's error was never announced with the field, and nothing recorded a failure → review+design dispatched

REPAIR: security review of b7a23bc7c — FIX_CRITICAL, blocking, two findings,
  both right and both mine.
  (a) THE ERROR WENT TO THE LOG RAW. redact() ran on `detail` only, and the
  file's own header claimed redaction was "enforced HERE". In this app a
  failure arrives from Frappe as an Error whose MESSAGE embeds the server's
  sentence ("Basic Salary must be positive, got 4500") and whose response
  hangs off it as a property — so the commonest error shape was the one shape
  that bypassed the filter completely. redact() now runs on the error too,
  with an `instanceof Error` branch because Object.entries on an Error returns
  {} (message and name are not enumerable).
  (b) DEPTH FAILED OPEN. Past four levels the value was returned RAW, so the
  one case the limit exists for — a body nested deeper than expected — was the
  case it stopped protecting. It returns "[too deep]" now.
  Also added: value-SHAPE matching. Key matching only works when the caller
  named the field, and `{ data: { value: <bank account> } }` defeats it
  entirely — the reviewer's example. Long opaque tokens, 10-19 digit numbers,
  addresses and NRICs are refused on sight whatever key they sit under.
NOTE: my FIRST fix reintroduced the leak. I kept the stack unredacted "because
  it is file names and line numbers" — but a stack's first line IS the message,
  so the sentence went straight back into the log next to the redacted object.
  Caught by the test I had just written. Only the frames are logged now
  (indented `at ` / `@` lines, true of both V8 and Firefox), which keeps the
  one thing that says WHERE without the one thing that says what.
EVIDENCE: 2 correct — 2 tests red first, 5 mutants killed: log the error raw;
  make depth fail open; log the full stack instead of the frames; drop the
  Error branch; remove shape matching. Verified by exercising the module:
  sk-live-1, 1234567890 and the salary sentence all absent, frames present.
REPAIR: pre-2.0 R5 — the honest half. No site is reachable, so the NUMBERS
  wait (owner: "if site is inaccessible its okay"). What shipped instead:
  tests/narrow-viewport.test.mjs, the first check in this repo at the
  checklist's 320px floor — nothing may demand more width than the narrowest
  phone has, and the app shell never absorbs a too-wide child sideways. And
  docs/glass/audit/2026-09-09-app-measure.json now says IN ITS OWN DATA that
  it must not be graded against: all 36 screens record tabH 0, captured before
  the nav repair, so every overflow in it is ~65px too small. The 2.0 plan
  rests on those numbers and a reader could pick the file up without knowing.
NOTE: the width rule was wrong twice before it was right. `min-width: 1024px`
  inside an @media query is the OPPOSITE of a demand — it means "once the
  screen is this wide" — and every breakpoint in the app tripped it. Then
  `--width: 480px` and `--g-viewport-width: 390px` tripped it, both custom
  properties rather than declarations, both legitimate. The rule now blanks
  media conditions and requires a bare `width:`.
EVIDENCE: 3 works — suite 567 / 563 pass, the same 4 red at HEAD. Gates: lint
  234/0, contrast 56/0, surfaces 46/0, tokens ok. Build clean.
NEXT: pre-2.0 R1-R5 are done. The measurement is the one thing outstanding and
  it needs a reachable site: `W=320 H=640 node e2e/app-measure.mjs`.
- 2026-09-22T10:52:42Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-09-22T10:52:42Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
