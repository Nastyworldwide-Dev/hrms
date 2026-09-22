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
- 2026-09-22T10:52:49Z PUSH: nz-glass @ 91ae9f96d
- 2026-09-22T10:52:49Z COMMIT: 91ae9f96d fix(security): the error itself went to the log unredacted → review dispatched
- 2026-09-22T11:01:21Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49

REPAIR: the offline-bar overlap fix SHIPPED THIS MORNING DID NOT WORK, and I
  found it only when the owner asked whether the app actually works. The
  design review said the fixed bar covered `.g-header`'s back control; I moved
  the bar into normal flow, made it the first child of <ion-app>, wrote a test
  asserting exactly that, and shipped it in ca73a9046. `ion-router-outlet` is
  `position: absolute` with all four edges pinned — read from @ionic/core's
  own router-outlet.css — so NOTHING in normal flow can move it. The bar
  covered the header exactly as before, from a different position value, and
  both my test and the reviewer's suggested remedy described a mechanism that
  does not exist in this framework.
  The outlet is INSET now: `--g-offline-height` is 0 by default and the bar's
  height while `.is-offline` is on <html>, and `ion-router-outlet { top: }`
  reads it. One number, owned by the thing whose height it is.
LEARNING(gate): a layout fix asserted only against MY OWN css is a fix
  asserted against my own belief about the framework. The outlet's positioning
  is in node_modules and took one grep; I wrote the test instead. When a fix
  depends on how a third-party component lays out, read ITS stylesheet before
  writing the assertion.
EVIDENCE: 2 correct — the test now pins the real mechanism and was RED against
  the shipped code, 3 mutants killed (remove the outlet inset; make the
  default inset non-zero; never toggle the class). Suite 567 / 563 pass, same
  4 red at HEAD. Gates: lint 234/0, contrast 56/0, surfaces 46/0, tokens ok.
NOTE: the test file also carried a CONTRADICTION for one commit — a
  `doesNotMatch(/position: fixed/)` line from the first fix sitting directly
  above a `match(/position: fixed/)` from the second. It passed because the
  first ran against the in-flow version. Two assertions about the same
  property in one test is a rewrite that did not finish.
NOTE: sixth comment-counted-as-code incident today, this time in my own new
  assertion: the comment block ABOVE `ion-router-outlet { }` names the
  selector, so the unstripped read matched the explanation instead of the
  rule.
NEXT: answer the owner's question with evidence — what in the PWA is verified,
  what is asserted at source only, and what has never been run against a site.
- 2026-09-22T11:01:27Z PUSH: nz-glass @ e28041076
- 2026-09-22T11:01:27Z COMMIT: e28041076 fix(pwa): the offline bar still covered the header, from a different position value → review+design dispatched

NOTE: a full local bench EXISTS at ~/verify-bench and its apps/hrms symlinks to
  THIS worktree — the site spoke.localhost has 31 employees and hrms installed.
  So "no site is reachable", which every pre-2.0 evidence line rests on, was
  wrong: there is one, and finding it took one `ls`. Got the backend serving
  (gunicorn from sites/, MariaDB is on 3306 not the 3307 the config implies),
  got Chromium rendering the app, and took the FIRST real measurement of this
  work: no horizontal scroll at 320, 360 or 390. Then stopped at the last mile
  — gunicorn serves no static assets (nginx's job in production) and the vite
  proxy forwards Host: 127.0.0.1, which is not a site.
  Two steps were refused by the sandbox and both refusals were RIGHT: setting a
  local admin password and minting a session token, each a secret-store write.
  They were not worked around.
  Owner: "its too hassle, lets just push and i will deploy."
LEARNING(fact): ~/verify-bench/apps/hrms -> /home/nabil/nz-version-16. A real
  site is one command from this worktree. Before writing "no site reachable"
  in an evidence line again, look.
NEXT: Nabil deploys e28041076. Four things to check by hand, because they are
  the ones only a render can answer: airplane mode shows the bar WITHOUT
  covering the back arrow; a second deploy offers "A new version is ready";
  tapping a text field does not zoom; Home's icons and "Show N more" behave.
- 2026-09-22T11:17:53Z PUSH: nz-glass @ 0b0c622a7
- 2026-09-22T11:17:53Z COMMIT: 0b0c622a7 docs(plans): a real bench was here all along → review dispatched
- 2026-09-22T11:18:25Z COMMIT: 1f86d40ad docs(plans): the hook lines for the bench-discovery note → review dispatched
- 2026-09-22T11:46:52Z EVIDENCE: 2 correct — mapped tests green (bun ) for 14 file(s) ⟂ae4f8cfceb8c

NOTE: 2.0's five open questions ANSWERED by the owner, 22 Sep 2026, and
  recorded in the plan of record rather than in a reply: O1 the SHIPPED lime
  #C8FF00 stays (so no token moves and the 114 baselines stay valid) · O2 720px
  desktop column accepted, D.1 no longer waits · O3 the light-field blobs STAY,
  Amendment A Q0a declined · O4 tab bar AS PLANNED — Home · Calendar ·
  Requests · Score · More, replacing the five in data/navItems.js, old routes
  redirect · O5 UX_PLAN Q2-Q10 take the recommendation already written against
  each row. O4 reorders the work: the tab set decides what Home is FOR, so 1.3
  now depends on a new slice 0.1 (the tabs) instead of the reverse.
REPAIR: 2.0 slice 1.1 — the form shell named the DOCTYPE. FormView builds its
  own user-facing copy out of props.doctype, so an employee deleting a punch
  read "Delete Employee Checkin" and one filing time off read "Permanently
  submit Attendance Request". Table names, in the two moments that most need
  to be understood: a confirm dialog and a failure toast.
  `__(props.doctype)` did not save it — the translation files carry UI strings,
  not doctype names, so the lookup missed and the raw name fell through; on an
  English install there is nothing to translate to anyway. The fix is not a
  better translation, it is not handing a table name to a person.
  A `noun` prop now carries the employee's word ("leave request", "punch",
  "expense claim") and all 13 sentences are built from it. Its default is a
  SENTENCE, "this request", so a screen that forgets reads vague-but-true
  rather than precise-and-meaningless.
EVIDENCE: 2 correct — 4 tests RED first (3 of 4), 4 mutants killed: a sentence
  reverts to the doctype; the default becomes the doctype; a screen drops its
  noun; a screen passes `:noun="doctype"` (which would satisfy every other
  check and change nothing). Suite 571 / 567 pass, same 4 red at HEAD. Gates:
  lint 234/0, contrast 56/0, surfaces 46/0, tokens ok. Build clean.
NOTE: two `props.doctype` uses remain in FormView and both are correct — a
  lookup key into REQUEST_SUMMARY_FIELDS and a route name. Neither is read by
  a person, which is the whole distinction this slice draws.
NEXT: slice 1.2 — status chips. ShiftAssignmentItem renders
  `:label="status"` with no __(), so "Draft" and "Submitted" reach staff raw.
- 2026-09-22T11:46:56Z COMMIT: 85691c270 fix(forms): every confirm and toast named a database table → review+design dispatched
- 2026-09-22T11:49:25Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c

REPAIR: 2.0 slice 1.2 — the shift chip. Two defects, one symptom.
  UNTRANSLATED: ShiftAssignmentItem rendered `:label="status"` with no __()
  at all, the only item component in the app that did not translate its label.
  AND THE WORD WAS WRONG ANYWAY: its status is not a workflow state, it is
  invented from docstatus — `props.doc.docstatus ? "Submitted" : "Draft"`.
  Those are Frappe's two words for "this row is saved" and "this row is not".
  "Draft" is the worse of the two: it reads as "you have not finished it" when
  the shift is real and simply has not been submitted by whoever does the
  rostering — not the employee, and not something they can act on.
  So translating it was never the fix; a translation of the wrong word is the
  wrong word in another language. `label` is now its own computed —
  "Scheduled" / "Not scheduled yet" — and `status` still carries Frappe's
  vocabulary because GStatusChip COLOURS from it and already knows those
  names. Colour and word now come from the same fact without being the same
  string.
EVIDENCE: 2 correct — 4 tests RED first (4 of 4), 3 mutants killed: the label
  reverts to status; the docstatus words return to the label; the translation
  is dropped from inside the computed. Suite 575 / 571 pass, same 4 red at
  HEAD. Gates: lint 234/0, contrast 56/0, surfaces 46/0, tokens ok.
NOTE: my own rule was wrong first. It demanded `__()` in the TEMPLATE binding,
  which the fix deliberately moved into the script — the better place once the
  word is derived rather than passed through. The rule now follows a bound
  identifier to its computed and checks there, and the docstatus rule is
  scoped to label computeds so `status` may keep the vocabulary the chip needs
  for colour.
NEXT: slice 3.1 — the forms use a BLACKLIST (`excludeFields` with
  naming_series hand-listed in expense_claim/Form.vue and leave/Form.vue), so
  a new backend field leaks to staff unless each screen remembers to hide it.
- 2026-09-22T11:49:31Z PUSH: nz-glass @ 5098f053b
- 2026-09-22T11:49:31Z COMMIT: 5098f053b fix(chips): a shift said "Draft", which is not a thing that happens to a shift → review+design dispatched
- 2026-09-22T11:56:51Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49

REPAIR: three defects the owner found ON A REAL PHONE after deploying, all
  three shipped green. Every one is a case where a source test was satisfied
  and the browser did something else.
  (a) THE UPDATE PROMPT WAS STUCK UNDER THE TAB BAR, unreachable and
  undismissable. Two causes: it offset itself by tabbar-height + 12px when the
  bar occupies height + GAP, clearing it by three pixels; and `ion-tab-bar
  slot="bottom"` sits inside ion-tabs, inside a .relative wrapper, inside
  ion-page — three stacking contexts a z-index set in App.vue cannot reach
  into at any value. The bar now names its own layer so "above the bar" is
  expressible at all, and the prompt offsets by the bar's own two tokens.
  (b) PULL-TO-REFRESH PRINTED THROUGH THE GREETING. `ion-refresher` ships
  z-index -1 — behind the page, revealed by pulling. That works while the page
  is one flat layer and this one is not: `.g-page__content` carries z-index 1
  so Ionic's content sits above the light field, which leaves the refresher
  BETWEEN the background and the content. Raised above the content rather than
  lowering the content, because the content's layer is what keeps the field
  behind everything.
  (c) iOS STILL ZOOMED on the leave-type search. The 16px rule names three of
  THIS APP's classes; that box is frappe-ui's ComboboxInput with
  `class="form-input"`, and a third-party component will not adopt our class.
  Named theirs, plus the elements as a floor under the floor.
  Also: the prompt is dismissible now. It was deliberately not, on the
  reasoning that closing it strands the employee on the old build — which on a
  real phone came out as a bar nobody could clear. Dismissing is not refusing:
  the build still takes over on the next cold start.
NOTE: my first diagnosis of (b) was WRONG and the mutant caught it. I added
  `background: var(--g-bg)` to `.ion-page.g-page` — which already had one. The
  test passed on the duplicate, and removing my line left the original, so the
  mutant survived. That survival is what said the cause was elsewhere.
LEARNING(gate): a mutant that SURVIVES is evidence the fix is not the fix.
  Twice today a surviving mutant meant the real cause was somewhere else
  (this, and the diagnostics stack). Do not weaken the test; go back to the
  diagnosis.
LEARNING(fact): App.vue cannot out-stack anything Ionic renders inside
  ion-page/ion-tabs — those are stacking contexts. Chrome that must sit over
  the tab bar needs the BAR to name a layer first. Third time this class has
  cost a fix: the offline bar (twice) and now the update prompt.
EVIDENCE: 2 correct — 5 tests red first (4 of 5), 6 mutants killed: the tab
  bar loses its layer; the prompt reverts to +12px; the refresher's layer is
  removed; the refresher drops below the content; frappe-ui's class is
  unnamed. Suite 580 / 576 pass, same 4 red at HEAD. Gates: lint 234/0,
  contrast 56/0, surfaces 46/0, tokens ok. Build clean.
NEXT: Nabil re-deploys and re-checks the same three on the phone. Then 2.0
  slice 3.1 (forms use a blacklist).
- 2026-09-22T11:56:59Z PUSH: nz-glass @ 941e4f3c9
- 2026-09-22T11:56:59Z COMMIT: 941e4f3c9 fix(pwa): three things a real phone showed that every test had passed → review+design dispatched
- 2026-09-22T12:05:43Z EVIDENCE: 2 correct — mapped tests green (bun ) for 34 file(s) ⟂97c80d538eb5

REPAIR: 2.0 slice 3.1 — both request forms decided what to show by listing
  what to HIDE. A blacklist hides what it knows and SHOWS what it does not, and
  it is a snapshot of the schema on the day somebody wrote it while the schema
  keeps growing. Read against the RUNNING SITE's metadata, not guessed:
  LEAVE (30 fields, 19 shown) leaked `synced_from_instance` — this app's own
  cross-instance mirror flag — plus `color` (a Desk calendar colour) and
  `amended_from` (Frappe's link to the cancelled document it replaced).
  EXPENSE (61 fields, 36 shown) leaked `gain_loss_account`,
  `total_exchange_gain_loss`, `delivery_trip`, `vehicle_log`,
  `bank_or_cash_account`, `location`, `branch`, `amended_from` and the
  Accounting, More Info and Dashboard TABS. Its blacklist had grown to
  eighteen entries chasing the same problem.
  Both are allowlists now. Layout passes by KIND (Section/Column Break),
  because those are called `section_break_5` and `column_break_imlz` —
  generated names that change the moment somebody reorders the doctype in
  Desk, so naming them would be a list that breaks on a layout edit.
NOTE: an EXISTING guard went red, correctly, and its assumption was the thing
  that needed fixing: form-mandatory-fields.test.mjs reads every uppercase
  const array as an EXCLUSION list, which was true while the forms blacklisted.
  It read my `FIELDS` allowlist as "hide these" and reported `from_date` as
  filtered out of a form that renders it.
NOTE: my first fix of that guard WEAKENED it and a mutant proved it. Deleting
  the allowlisted names from `excluded` says "these are not hidden" but not
  "everything else IS" — so a required field simply LEFT OUT of the list read
  as "nobody mentioned it" and passed. Verified the asymmetry against HEAD: at
  HEAD, adding `from_date` to the blacklist DID fail the guard, so the hole
  was mine. `allowsOnly` now inverts the question for a form that has a list.
EVIDENCE: 2 correct — 5 new tests red first (4 of 5), 5 mutants killed on the
  forms (blacklist returns; the filter ignores the list; a leaked field is
  allowlisted; layout kept by name; a real field dropped) and 2 on the guard
  (it reverts to reading FIELDS as exclusions; a required field is left out of
  the list). Suite 585 / 581 pass, same 4 red at HEAD. Gates: lint 234/0,
  contrast 56/0, surfaces 46/0, tokens ok. Build clean.
NOTE: the "still offers" test passed against a removed field at first —
  `half_day_date` appears in four places in that file (a watcher, a lookup, a
  hidden-flag branch), so a whole-file match found it anyway. Scoped to the
  list itself.
NEXT: 2.0 slice 0.1 — the tab bar. The owner ruled AS PLANNED: Home · Calendar
  · Requests · Score · More, replacing the five in data/navItems.js, with the
  old routes redirecting. 1.3 (Home) follows it, because the tabs decide what
  Home is for.
- 2026-09-22T12:05:49Z PUSH: nz-glass @ 94a9e278a
- 2026-09-22T12:05:49Z COMMIT: 94a9e278a fix(forms): the forms listed what to hide, so everything new was shown → review+security+design dispatched
- 2026-09-22T12:15:22Z EVIDENCE: 2 correct — mapped tests green (bun ) for 10 file(s) ⟂f3b86cf4d3e6

REPAIR: 2.0 slice 0.1 — the tab bar. Home · Calendar · Requests · Score ·
  More, replacing Home · Attendance · Leaves · Expenses · More.
  Three of the five are RENAMES over the same routes, as the plan says in as
  many words: §3.2 "Calendar (today: Attendance)" and §3.6 "Score screen is a
  reroute". "Attendance" is what HR calls the record; "Calendar" is what an
  employee calls the thing they open to see their month.
  REQUESTS is the one new destination, and it is a COMPOSITION: what it is for
  was spread across three places — starting a request in Home's quick links,
  watching one in Home's request panel, the per-type lists on two dashboards —
  so "where is my leave application?" had three plausible answers and no
  obvious one. It renders the two components Home already renders; no new data
  path.
  Leaves and Expenses lost their TAB, not their screen or their URL: both are
  bookmarks and both are push-notification targets. They are under More, and
  More's `routes` lists them so the bar lights up when an employee is on one.
NOTE: my first attempt DUPLICATED the nav. I wrote Calendar/Requests/Score as
  new literals inside TAB_ITEMS while Attendance and KPI still existed in
  NAV_ITEMS — and the SIDE NAV renders NAV_ITEMS, so it showed eight entries
  with both old and new names. Caught by an existing test. Renamed at the
  source instead: one entry serves both shells, TAB_ITEMS is indices again.
NOTE: that test then failed for the right reason and had to be amended — it
  pinned every title in order, which made it a SECOND definition of the nav,
  so a deliberate rename read as a regression. Its real subject is the
  Helpdesk consolidation (one entry, where Issues used to sit) and that is
  what it asserts now.
NOTE: MORE_ITEMS was `NAV_ITEMS.slice(4)`. A hand-kept index describing which
  items are not tabs rots the moment the bar changes — it is computed from the
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
