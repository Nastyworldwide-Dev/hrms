2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
- 2026-09-11T03:43:37Z COMMIT: 15793c95e docs(plans): circuit open on permlevel_guard.py after four fixes, parked → review dispatched
2026-09-11T03:55Z EVIDENCE: 3 works (partial) — sensitive-field lock, bench probe with savepoint + rollback.
  PROVEN: apply_sensitive_field_lock moves all eight fields 0 -> 1 and 1 -> 0 with the HR Settings box; the client-facing read
  paths enforce permissions (frappe.client.get and frappe.get_list both raise PermissionError for a user without Employee read);
  raw frappe.get_doc does NOT mask permlevel fields, which is correct Frappe design — masking lives at frappe/client.py:115 and
  frappe/handler.py:318, i.e. every path a Desk form, the REST API or the PWA actually uses. A server-internal get_doc is not a leak.
  NOT PROVEN: that a user holding the Employee role sees a COLLEAGUE's bank/IBAN/passport masked rather than refused. The probe
  could not attach the Employee role to a throwaway user (frappe.get_roles kept returning ['All','Desk User','Guest'] after
  add_roles), so the one scenario that distinguishes "masked" from "refused outright" is still untested. hrms also fences Employee
  reads by row (identity.own_employees), so the likely answer is "refused before masking matters" — likely is not proven.
  The security-reviewer spawned for exactly this question hit its turn limit after 113k tokens without reporting; per CLAUDE.md a
  silent reviewer counts as FIX_CRITICAL, so: NO DEPLOY of the PII lock until this one scenario is grounded.
NEXT: ground the remaining PII scenario (throwaway user WITH the Employee role and a linked Employee record, read a colleague via
  frappe.client.get) before the lock is deployed. Then sweep-4 #20, the geofence bypass via Shift Request. Nabil still owes the OT
  backfill range and the early-arrival ruling.
- 2026-09-11T03:52:42Z COMMIT: 8dfc21d28 docs(plans): what the PII probe proved, and the one thing it did not → review dispatched
- 2026-09-11T04:00:41Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-11T04:00:41Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 4 extra test file(s) ⟂c68dc5c03ea4
- 2026-09-11T04:00:44Z COMMIT: 19c939278 fix(attendance): a typed correction stops paying for an early clock-in → review dispatched
- 2026-09-11T04:03:10Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-11T04:03:10Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 4 extra test file(s) ⟂ec40e5b3a4bb
- 2026-09-11T04:03:14Z COMMIT: 2a62b77af fix(ot): repair the discarded overtime, inside the filing window and behind a guard → review dispatched
- 2026-09-11T04:14:41Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-11T04:14:41Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 4 extra test file(s) ⟂ec40e5b3a4bb
- 2026-09-11T04:14:45Z COMMIT: 59d6d3e07 fix(attendance): repair the hours the early-arrival fix only fixed forward → review dispatched
- 2026-09-11T04:22:38Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T04:22:38Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-11T04:22:42Z COMMIT: 8bac74c72 fix(sync): the GL pull now says why a claim type has no account → review dispatched
- 2026-09-11T04:27:24Z COMMIT: f83c201dd fix(attendance): the hours and overtime repairs recur, so HR never edits a record → review+cross-app dispatched
- 2026-09-11T04:33:30Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T04:33:30Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-11T04:33:34Z COMMIT: 275c0f6f5 fix(sync): the GL pull finds an account whose name is spelled differently → review dispatched
- 2026-09-11T06:26:57Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 4 file(s) ⟂bdfcc00ed624
- 2026-09-11T06:27:03Z COMMIT: 1ce408778 feat(pwa): an empty claim list says why, instead of a blank date picker → review+design dispatched
- 2026-09-11T06:30:19Z PUSH: nz-glass @ 1ce408778
2026-09-11T06:35Z PUSH: nz-glass be4f5639b..1ce408778 (24 commits) on Nabil's explicit word ("sure go on push all").
  Context that matters: Nabil had deployed be4f563 believing it was the latest — it was the session's STARTING commit, so every
  "still same" result today (the GL pull dialog, the missing tick box, nothing-to-claim in the PWA) was the UNFIXED build. I had
  said "nothing pushed" each time without making clear that pushing was the blocking step. Say it plainly next time.
NEXT: Nabil deploys 1ce408778, then: (a) Employee > Overview shows "Eligible for Overtime Pay" under Years of Service and a tick
  STICKS; (b) Pull -> GL Accounts reports the claim-type reasons and names the skipped account; (c) a new OT Request lists claimable
  days or says why there are none; (d) the two repairs report in the deploy log. Then sweep-4 #20, the geofence bypass.
- 2026-09-11T06:55:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-11T06:55:08Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-09-11T06:55:15Z PUSH: nz-glass @ 54327f689
- 2026-09-11T06:55:15Z COMMIT: 54327f689 fix(sync): a claim type may name more than one spelling of its GL account → review dispatched
- 2026-09-11 EVIDENCE: 2 correct — Team KPI probe on fresh.local (savepoint, rolled back): 10/10 PASS —
  non-CEO refused (can_view_team_kpi False + PermissionError), CEO sees both employees, department filter
  narrows rows AND the average, departments carry the company suffix as expected.
- 2026-09-11 EVIDENCE: 1 builds — `yarn build` green (75 modules), ruff + eslint clean on the touched files.
NEXT: Nabil deploys, then on the CEO's login: More -> "KPI" -> the [My KPI | Team KPI] strip appears,
  Team KPI lists scores and the Department selector filters them. On any other login the KPI page must look
  exactly as before (no strip). Open question flagged to Nabil: Team KPI is scoped to the CEO's own company.
- 2026-09-11T09:12:18Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-11T09:12:49Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-11T09:16:34Z PLAN: approved 6c01a1064102 — # PLAN — Nadi PWA: KPI page gains a CEO-only Team KPI view
- 2026-09-11T09:16:42Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-11T09:16:47Z COMMIT: 4df6b0f18 feat(pwa): the CEO can read the company's KPI scores by department → review+design dispatched
NEXT: Wait for the frappe-reviewer + design-reviewer verdicts on 4df6b0f18; fix anything Critical and
  re-commit (review re-triggers). Nothing pushed, nothing deployed. Open question for Nabil: Team KPI is
  scoped to the CEO's own Employee.company — drop the company filter if he must see every company on the hub.
- 2026-09-11T09:17:54Z COMMIT: 3e98896c3 docs(plans): record the Team KPI evidence and what the reviewers still owe → review dispatched
- 2026-09-11T09:28:23Z PLAN: approved 34adf6ee8615 — # PLAN — Nadi PWA: KPI page gains a CEO-only Team KPI view
- 2026-09-11 EVIDENCE: 2 correct — Team KPI probe on fresh.local (savepoint, rolled back): 35/35 PASS —
  both allowlists (CEO by designation, HR by role), System Manager still refused, both see across
  departments AND companies, company/department filters narrow, Company User Permission fences BOTH.
- 2026-09-11 EVIDENCE: 7 stays right — the cross-company leak the frappe-reviewer found is now an
  invariant test: the fence keys on Employee.company, proven RED by re-introducing the Appraisal.company
  fence (foreign employee re-admitted) and GREEN after.
- 2026-09-11 REPAIR: design review FIX_CRITICAL — GProgressRing prints its score verbatim into an 88px
  ring with no overflow clamp, so the raw sum/len mean (72.42857142857143) overflowed it and was read out
  in full to screen readers. Rounded at the API so ring, hero and table share one source.
NEXT: Nabil deploys, then check on the CEO's login AND an HR login: More -> "KPI" -> the
  [My KPI | Team KPI] strip appears, Team KPI lists every company, and Company/Department narrow it.
  BEFORE DEPLOY confirm the live Designation master is spelled exactly "Chief Executive Officer" and the
  CEO's Employee row carries it with status=Active — otherwise the tab silently never appears for him.
- 2026-09-11T09:28:57Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-11T09:28:59Z COMMIT: eb24a7c19 feat(pwa): HR reads Team KPI too, and both allowlists see every company → review+design dispatched
- 2026-09-11 EVIDENCE: 7 stays right — frappe-reviewer CRITICAL: `years`/`cycles` were derived from the
  UNFENCED appraisal read, so a company-fenced HR user was offered other companies' Appraisal Cycle NAMES
  (which carry company identity, and which Frappe's own Company UP hides from them in Desk). The fence now
  resolves the employee population BEFORE the appraisal read. Proven RED on HEAD, GREEN after; probe 41/41.
- 2026-09-11 EVIDENCE: 5 looks right — design-reviewer FIX_WARNINGS all closed: aria-live is now a mounted
  summary (was announcing the whole table, and unmounted itself on error), the hero holds its height across
  refetches, GDataTable's landmark is gated on a caption (an empty aria-label ships a nameless region),
  filters cannot widen the page, one decimal convention per hero, integer in the ring.
- 2026-09-11 REPAIR: frontend/tests/team-tabs-gated.test.mjs named ONE predicate (isApprover) and so was red
  for a view using a STRICTER gate. Widened to a named gate list. Frontend suite 160/1 -> 161/0.
BACKLOG (not this commit): hrms/hr/doctype/appraisal/appraisal.py `_hr_company_condition` and
  `has_permission` still fence on Appraisal.company, the field this work proves is never reconciled with
  Employee.company. The leak is closed on the PWA and OPEN on Desk: an HR user fenced to company A can read
  a company-B employee's appraisal through frappe.get_list. Re-key both to Employee.company via tabEmployee.
NEXT: Nabil deploys, then check on the CEO's login AND an HR login: More -> "KPI" -> the
  [My KPI | Team KPI] strip appears, Team KPI lists every company, Company/Department narrow it.
  BEFORE DEPLOY confirm the live Designation master is spelled exactly "Chief Executive Officer" and the
  CEO's Employee row carries it with status=Active — otherwise the tab silently never appears for him.
- 2026-09-11T09:41:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-11T09:41:39Z COMMIT: 984a8ace9 fix(kpi): the year and cycle selectors leaked other companies' cycle names → review+design dispatched
- 2026-09-11T09:53:33Z PLAN: approved b786d8ddf8b5 — # PLAN — Nadi PWA: KPI page gains a CEO-only Team KPI view
- 2026-09-11 RULING (Nabil): Team KPI is NOT company-fenced. Any HR sees every company; so does the CEO;
  non-HR sees nothing. This is the ONE place on the hub where an allow=Company User Permission (the fence
  behind the "HR (Company)"/"HR (Instance)" roles) does not narrow an HR user — everywhere else it still
  does. Pinned by test_a_company_user_permission_does_not_narrow_team_kpi; reverse it there first.
  WHY the CEO still needs the designation gate: in Desk/Verifica he holds no HR roles, so no role gate
  would ever reach him.
- 2026-09-11 EVIDENCE: 2 correct — probe on fresh.local (savepoint, rolled back) 38/38 PASS, including
  both allowlists unnarrowed by a Company User Permission and System Manager still refused.
- 2026-09-11 EVIDENCE: 5 looks right — design review's last open finding measured and fixed: `max-width:
  100%` on a filter select was a NO-OP (the flex wrapper is sized BY the select's min-content, so the
  percentage is circular). Chromium at 375px: scrollWidth 426 -> 375 with min-w-0 on the wrappers.
NEXT: Nabil deploys, then check THREE logins: (a) the CEO — More > "KPI" shows the [My KPI | Team KPI]
  strip; (b) any HR User/HR Manager — same strip, and the Company selector lists every company; (c) an
  ordinary employee — the KPI page looks exactly as it did, no strip.
  BEFORE DEPLOY confirm the live Designation master is spelled exactly "Chief Executive Officer" and the
  CEO's Employee row carries it with status=Active — otherwise the tab silently never appears for him.
- 2026-09-11T09:54:03Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-11T09:54:06Z COMMIT: 72ea9eb06 feat(kpi): Team KPI is group-level sight - any HR sees every company → review+design dispatched
- 2026-09-11 EVIDENCE: 5 looks right — design-reviewer VERDICT: DESIGN_APPROVED on 72ea9eb06, measured on
  real markup (committed template + real theme CSS + project Tailwind config in Chromium): 375px
  scrollWidth 427 -> 375 with min-w-0, skeleton resolves to exactly 36px in both themes, GDataTable emits
  no nameless landmark while keeping every caller's tab stop. Its one taken suggestion is this commit.
- 2026-09-11T10:05:20Z COMMIT: 8bcb764ea fix(pwa): an empty Team KPI still says what you filtered to → review+design dispatched
- 2026-09-11 EVIDENCE: 2 correct — frappe-reviewer VERDICT on 72ea9eb06: NEXT_ACTION: DEPLOY, no Critical.
  It proved read-only by instrumentation (DML spy on frappe.db.sql + transaction_writes flat across 6
  argument shapes), proved `company` is a strict subset of the unfiltered call for every value, and
  measured the whole-tabEmployee read (500 rows 3ms/0.3MB -> 25k rows ~100ms/15MB).
- 2026-09-11 REPAIR: its one actionable WARNING — test_api_employee_reads_are_fenced.py had been RED since
  before this work (3 offenders) with an EXEMPT set the docstring said must be argued into. A permanently
  red guard is not a guard. All three exempted WITH their arguments, plus a new
  test_every_exemption_is_still_a_reader so a stale exemption cannot silently pre-approve whatever later
  takes that name. Mutation-tested BOTH directions: an unfenced reader -> RED, a stale exemption -> RED.
BACKLOG (not this commit, both pre-existing and confirmed red on HEAD~1):
  - hrms/sync/checkin_recovery.py::recover_overwritten_checkins is hub-wide and role-checked only, with no
    require_unfenced — an "HR (Company)" user can recover punches outside their fence.
  - frontend/src/utils/__tests__/pushNotifications.test.js: 4 failures since 7d7ef6999 (8 Sep), a Node
    "cannot set navigator" environment issue, masking any real push regression.
NEXT: Nabil deploys, then check THREE logins: (a) the CEO — More > "KPI" shows the [My KPI | Team KPI]
  strip; (b) any HR User/HR Manager — same strip, Company selector lists every company; (c) an ordinary
  employee — the KPI page looks exactly as it did, no strip.
  BEFORE DEPLOY confirm the live Designation master is spelled exactly "Chief Executive Officer" and the
  CEO's Employee row carries it with status=Active — otherwise the tab silently never appears for him.
- 2026-09-11T10:07:20Z COMMIT: 320054e6a test(api): the Employee-fence guard was red, so it was not a guard → review dispatched
- 2026-09-11T10:13:51Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-11T10:13:54Z COMMIT: 320054e6a test(api): the Employee-fence guard was red, so it was not a guard → review dispatched
- 2026-09-11 EVIDENCE: 6 behaves — design-reviewer VERDICT DESIGN_APPROVED on 8bcb764ea; frappe-reviewer
  NEXT_ACTION: DEPLOY on 320054e6a. Between them they found one real hole I had opened: the fence guard's
  exemption set was keyed by BARE function name while offenders are reported as file.py:func, so exempting
  three readers pre-approved those names in every other file. Closed in 77a54c495, with the collision now
  a test rather than a hand-run mutant.
- 2026-09-11 REPAIR: design suggestions taken — the scope line is suppressed on an empty hub (no filter bar
  to read back), the "{n} appraised"/"Top" pair skeletons with the score instead of stating last fetch's
  answer under the new filter, and the screen-reader status line now names the scope, so two empty results
  in a row are distinguishable instead of both announcing "No appraisals here".
- 2026-09-11 EVIDENCE: 5 looks right — the mockup contract now records the empty, loading and error states
  it never depicted (state switcher in mockup-team-kpi.html), which is where those three rules had been
  living only in code.
- 2026-09-11T10:15:27Z COMMIT: 73229b4d2 fix(pwa): a filter change that finds nothing must still be legible → review+design dispatched
- 2026-09-11 REPAIR: design review FIX_WARNINGS on 73229b4d2, five findings, all real and three of them mine:
  (a) a FAILED REFETCH left the previous answer on screen beside the error alert — frappe-ui's handleError
  does `out.data = out.previousData`, so `v-if="resource.data"` stays TRUE after any successful first load;
  (b) the aria-live line was not gated on loading, so it announced the NEW scope beside the OLD numbers —
  the same defect the badge skeleton fixes visually, moved into the audio by my own scopeLabel change;
  (c) scopeLabel omitted the YEAR, the one filter always on screen, so two empty years announced identically.
- 2026-09-11 REPAIR: my mockup amendment was wrong in all three new states and the CODE was right each time:
  loading used visibility:hidden + insert (doubling the hero height, demonstrating the reflow the rule
  forbids), error kept the Scores eyebrow and note, empty replaced the whole table instead of keeping thead
  and filling one colspan cell. Fixed; the error rule is now stated as what is true — the ANSWER goes, the
  CONTROLS stay.
NEXT: Nabil deploys, then check THREE logins: (a) the CEO — More > "KPI" shows the [My KPI | Team KPI]
  strip; (b) any HR User/HR Manager — same strip, Company selector lists every company; (c) an ordinary
  employee — the KPI page looks exactly as it did, no strip.
  BEFORE DEPLOY confirm the live Designation master is spelled exactly "Chief Executive Officer" and the
  CEO's Employee row carries it with status=Active — otherwise the tab silently never appears for him.
- 2026-09-11T10:23:24Z COMMIT: 76d82d7e5 fix(pwa): a failed refetch left the old answer beside the error → review+design dispatched
- 2026-09-11T10:34:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T10:34:54Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 12 extra test file(s) ⟂ca1c1f300426
- 2026-09-11T10:35:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T10:35:36Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 12 extra test file(s) ⟂ca1c1f300426
- 2026-09-11T10:35:57Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T10:35:57Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 12 extra test file(s) ⟂ca1c1f300426
- 2026-09-11T10:36:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T10:36:21Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 12 extra test file(s) ⟂ca1c1f300426
- 2026-09-11T10:37:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T10:37:17Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 12 extra test file(s) ⟂ca1c1f300426
- 2026-09-11T10:37:18Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 6 call site(s) given verdicts, 4 same-root ⟂4180c4e5fcb6
- 2026-09-11T10:37:20Z COMMIT: 6c1f71efb fix(hr): approving a request is not filing it, so stop fencing it as one → review dispatched
- 2026-09-11T10:40:49Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T10:40:52Z COMMIT: 2ce8aa9c5 fix(checkin): a later check-in bounds a late check-out only if the session ended → review dispatched
TICKET: split hrms/hr/utils.py authorisation helpers (12 fixes/90d, 1548 lines) into
  hrms/hr/authorisation.py — validate_filing_for_self/_is_filing, validate_self_submission,
  validate_mandatory_attachment and the staff-lockdown approver guard (utils.py:1225-1250),
  re-exported from utils for compatibility. ONE module owns "who may act", and it DEFERS to the
  row scope for authority over an existing row; the module docstring states that invariant.
  Closes the two-fences-disagreeing class, not just this instance.
OPEN QUESTION (do not close HR-OTR-26-09-00009 without it): the approver saw TWO messages,
  "Could not load" AND the Approve refusal. Only the Approve half is proven fixed — reads never run
  validate. On a clean site the approver's open path is fine, so the toast is either a knock-on from
  the failed decide or a second live-site-only defect. Have the approver open one OT Request after
  deploy and say whether the toast is gone; if it persists it is a SEPARATE ticket.
- 2026-09-11T10:51:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-11T10:53:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-11T10:53:07Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 17 call site(s) given verdicts, 5 same-root ⟂d473b2b196be
- 2026-09-11T10:53:09Z COMMIT: 9ecc15b15 fix(checkin): the server decides IN or OUT, the phone only proposes → review+security+design dispatched
- 2026-09-11T10:58:39Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-11T10:58:40Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 13 call site(s) given verdicts, 5 same-root ⟂6e4c3857e480
- 2026-09-11 EVIDENCE: 6 behaves — security-reviewer on 9ecc15b15: VERDICT SECURE, BLOCKING no. It
  answered all five attack questions with evidence: the owner check runs BEFORE the new read (no
  enumeration), the coercion is one-directional and can only REDUCE the coercer's own hours (no pay
  manufacture), neither is_abandoned nor remote_approval_status is employee-writable, a stuck session
  stops coercing at the 06:00 cutoff (no lasting DoS), and the frozen sheet action cannot be replayed.
- 2026-09-11 REPAIR: its one WARNING was a real correctness bug in code I had just shipped —
  `order_by="time asc"` with a row limit keeps the OLDEST rows, so a busy log would truncate away the
  very open IN the rule depends on and silently stop coercing, for exactly the people punching most
  often. Fixed at both sites (punch + get_unresolved_stale_in); proven RED by reverting the order.
