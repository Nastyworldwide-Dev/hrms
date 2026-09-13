2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-11T10:58:42Z COMMIT: 474539b65 fix(checkin): a busy log must not truncate away the open session → review dispatched
TICKET: split hrms/api/remote_checkin.py (10 fixes/90d, ~700 lines) — it now owns four distinct
  jobs: the punch write path, the geofence/approval routing, the late-checkout resolution, and the
  session-state reads the PWA banner depends on. Extract the SESSION-STATE rules
  (_session_is_live, resolve_punch_type, the open-session walk in get_unresolved_stale_in, and the
  late-checkout boundary) into hrms/utils/punch_session.py. ONE module answers "is this employee on
  shift, and what does this punch mean". The recurring defect class in this file is two places
  computing the same session question and drifting — the 06:00 cutoff was inline in two functions,
  and the newest-row truncation was duplicated in both log reads. A single owner closes the class.
NEXT: Nabil deploys (or first runs the production query in .claude/plans/checkin-root-cause.md to
  confirm the build is not simply stale), then checks: (a) an approver can approve an OT Request;
  (b) a late check-out submits for someone carrying a duplicate IN; (c) a check-out at 18:3x is
  recorded as OUT and does not open a second attendance row on the 7PM shift.
  STILL BLOCKED ON NABIL'S WORD: repairing the attendance days already split, and closing the stale
  night-shift assignments. Enumerate first with the Attendance Day Audit report for 03-09..10-09.
- 2026-09-11T11:06:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-11T11:06:07Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 13 call site(s) given verdicts, 5 same-root ⟂6e4c3857e480
- 2026-09-11T11:06:09Z CIRCUIT: open after 4 fix cycles on nz-glass — parked for a human
- 2026-09-11T11:19:23Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T11:19:23Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 0 extra test file(s) ⟂f14a25999045
- 2026-09-11T11:19:26Z COMMIT: a741f3e46 feat(checkin): one flag turns the punch-type correction off → review dispatched
- 2026-09-11T11:19:41Z PUSH: nz-glass @ a741f3e46
- 2026-09-11T11:20:41Z PUSH: nz-glass @ 3fccd9d64
- 2026-09-13T14:05:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13 EVIDENCE: 2 correct — My Team tier probe on fresh.local (savepoint, rolled back) 11/11 PASS:
  a manager with no HR role and no office gets mode "manager", sees their direct report AND the report's
  report (the chain is transitive), sees neither an outsider nor themselves, an employee managing nobody
  gets NO tier and is refused, and a CEO who also manages people keeps the company view.
- 2026-09-13 EVIDENCE: 7 stays right — the manager tier BORROWS
  appraisal.get_allowed_appraisal_employees rather than re-deriving who reports to whom. A manager could
  already read those appraisals in Desk; this only surfaces it. A second implementation of "whose
  appraisals may I see" is exactly how the filing guard and the row scope came to disagree (family.md).
NEXT: step 2 of the KPI tree work — the per-person drill-down endpoint and its fence (KRA detail is a
  personnel file, not a league-table row, so it needs its own check, not the list's). Then step 3, the
  department-tree navigation for CEO/HR, rolled up as the average over PEOPLE in the subtree.
- 2026-09-13T14:05:36Z COMMIT: c9a8034c0 feat(kpi): a manager sees their own team, by the rule that already governs it → review+design dispatched
- 2026-09-13 REPAIR: frappe-reviewer FIX_CRITICAL on c9a8034c0, TWO Criticals, both mine.
  (a) I renamed the second tab per tier and the first-fetch watch still compared against the LABEL
  `TEAM` — so for the CEO and HR it never fired. Their tab would have been permanently empty, with no
  other trigger (fetchTeam is otherwise reachable only from the filter bar, which renders only after a
  fetch returns). The feature would have shipped broken for the two tiers it exists to serve.
  (b) The tier check mixed TWO definitions of "my own Employee row": get_allowed_appraisal_employees
  seeds from a raw user_id match (every claimant), identity.own_employees is Active-only and fails
  closed to [] on duplicates. Subtracting one from the other turned that disagreement into "people who
  report to me", and a duplicate-identity login was handed the OTHER claimant's score — which the
  framework's own has_permission refuses them everywhere else. Now: no resolvable identity, no tier.
- 2026-09-13 EVIDENCE: 2 correct — probe 14/14 on fresh.local (savepoint, rolled back), now covering the
  duplicate-identity login and the offboarded leaver. Frontend 164/0 with a new per-tier fetch test,
  proven RED (3/3) against the label comparison.
- 2026-09-13 LEARNING(gate): a tab-label refactor breaks the first-fetch watch silently ->
  frontend/tests/kpi-tab-fetch-per-tier.test.mjs executes the committed watch body for every tier and
  refuses a trigger that compares against a label constant.
- 2026-09-13 EVIDENCE: 2 correct — drill-down probe on fresh.local (savepoint, rolled back) 23/23,
  now covering the fence from every side: you can open your own; a manager can open a report AND the
  report's report; a manager CANNOT open an outsider; a colleague CANNOT open a colleague; the CEO can
  open anyone; a duplicate-identity login can open nobody. Plus the payload equality check — the
  drill-down returns byte-identical keys to get_my_kpi_dashboard, so the shared layout cannot
  half-render.
- 2026-09-13 EVIDENCE: 7 stays right — ONE renderer, two doors. _kpi_dashboard is shared;
  get_my_kpi_dashboard is safe BY CONSTRUCTION (takes no employee), get_employee_kpi is safe BY CHECK
  (_require_kpi_read runs first). The frontend mirrors it: KpiDetail.vue renders both "my KPI" and
  "their KPI", so the two cannot drift into disagreeing about somebody's review.
  Recorded: the framework's appraisal has_permission CANNOT be used on the team path — the CEO tier is
  granted by DESIGNATION, which appraisal.py has never heard of, so it would refuse the CEO their own
  feature. The tier fence is the authority there, checked before a row is read.
NEXT: step 3 — the department-tree navigation for CEO/HR (Department is a real Frappe tree:
  parent_department + is_group), rolled up as the average over PEOPLE in the subtree. Then the final
  review of everything before the push.
- 2026-09-13T14:24:42Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 9 file(s) ⟂79474414be21
- 2026-09-13T14:25:41Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 9 file(s) ⟂79474414be21
- 2026-09-13T14:25:45Z COMMIT: e4b16bc16 feat(kpi): open a person and see their KPI in the layout you see your own → review+design dispatched
- 2026-09-13 REPAIR: final design review FIX_CRITICAL on the unpushed range. DSN-01 is the worst defect
  of the session: employeeKpi is a MODULE SINGLETON and frappe-ui does not clear `.data` when a new
  submit starts, so "open A -> Back -> open B" rendered B's NAME above A's ENTIRE performance review —
  A's score, grade, ring, KRA targets and feedback — solid, with no spinner, because the loading branch
  sits after the gate and was unreachable once any payload existed. Now gated on WHO THE PAYLOAD IS
  ABOUT (data.employee.name === the person opened), taken from the payload itself.
  DSN-02: the list<->detail swap moved no focus and announced nothing (no route change), so a keyboard
  user landed on <body> and a screen-reader user was told nothing while still "inside" a table that had
  unmounted. Focus now lands on the person's name opening, and on the Scores heading closing.
  DSN-06: "My KRAs" and "You can only see your own scores" rendered over somebody else's record. The
  second is FALSE on the screen it appeared on, and it is the one line there that states an access rule.
- 2026-09-13 LEARNING(gate): a singleton resource reused for a second subject renders the FIRST
  subject's payload during the second fetch -> frontend/tests/kpi-detail-identity.test.mjs executes the
  committed computed and refuses a truthiness gate. Proven RED 3/4 against it.
- 2026-09-13T14:35:22Z COMMIT: f7048be95 fix(kpi): the drill-down showed one person's review under another's name → review+design dispatched
- 2026-09-13 REPAIR: final frappe review FIX_CRITICAL. My earlier duplicate-identity fix closed only HALF
  the hole. appraisal.get_allowed_appraisal_employees SEEDS its walk from a RAW, status-agnostic user_id
  match; subtracting identity.own_employees from the result closed Active-vs-Active but NOT
  Active-vs-INACTIVE. One login holding an Active row PLUS a leftover inactive row that still has
  subordinates passed the fail-closed gate and got a phantom "manager" chain — the caller could read the
  full KRA detail of people they manage nobody in, while the framework's own has_permission refused them
  the very same document. The security reviewer independently ran out of turns chasing the identical edge.
- 2026-09-13 REPAIR: the office was decided BEFORE the identity gate and re-derived identity with its own
  user_id query, so an AMBIGUOUS login — the case this hub documents as fail-closed — was handed the
  WIDEST tier. Identity now runs first for every tier.
- 2026-09-13 REPAIR: the root of both was ONE question answered in THREE places with slightly different
  arithmetic (the tier check, the detail fence, the list). Replaced by `_scope(user) -> (tier, admitted)`,
  the single resolver; get_allowed_appraisal_employees gained an optional `seed` so the Desk hook is
  unchanged while callers that need IDENTITY rather than CLAIMS pass own_employees.
  Also: verify_appraisal_permission is back ON for the manager tier — the framework agrees there
  (measured), and it independently held the detail door when the seed was reverted.
- 2026-09-13 EVIDENCE: 2 correct — probe 27/27 on fresh.local, now covering the phantom chain and the
  ambiguous login. Proven RED by reverting ONLY the seed: tier became "manager" and get_team_kpi returned
  a stranger's row.
- 2026-09-13 LEARNING(gate): one question answered in three places drifts -> hrms/api/kpi.py::_scope is
  the single resolver, and test_api_employee_reads_are_fenced pins that it reads only the caller's own
  resolved rows.
TICKET: hrms/api/kpi.py is 667 lines carrying three tiers, two doors and a shared renderer. _scope closed
  the recombination that leaked; the remaining split is presentational (the list, the detail, the
  renderer) and is worth doing before the department-tree work lands on top of it.
- 2026-09-13T14:41:40Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T14:41:40Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 5 extra test file(s) ⟂b91eb133f40c
- 2026-09-13T14:42:43Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T14:42:43Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 5 extra test file(s) ⟂b91eb133f40c
- 2026-09-13T14:43:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T14:43:21Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 5 extra test file(s) ⟂b91eb133f40c
- 2026-09-13T14:43:48Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 2 call site(s) given verdicts, 6 same-root ⟂6c69f0b459ca
- 2026-09-13T14:44:07Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T14:44:07Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 5 extra test file(s) ⟂b91eb133f40c
- 2026-09-13T14:44:08Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 2 call site(s) given verdicts, 6 same-root ⟂6c69f0b459ca
- 2026-09-13T14:44:11Z COMMIT: 191b70965 fix(kpi): a dead employee row must not make you somebody's manager → review dispatched
- 2026-09-13 EVIDENCE: 6 behaves — re-verification NEXT_ACTION: DEPLOY, no Critical. It confirmed the
  phantom chain closed on BOTH doors, reproduced my revert exactly, and tried four further ways to defeat
  it (dead row Inactive / Suspended / Left, and a second Active row whose user_id differs by case and
  whitespace) — all failed closed. It also proved the `seed` default is byte-identical for every existing
  caller, and that a legitimate manager still opens a report who has LEFT, a cross-company report and a
  SUBMITTED appraisal.
- 2026-09-13 REPAIR: its W1. Identity-first had started gating the HR tier too, so an HR account with no
  Employee row — a new HR hire not yet mirrored, a shared HR login, Administrator during support — lost
  Team KPI entirely. HR is decided by ROLE and only by role: identity buys nothing there (a role cannot be
  forged with a duplicate Employee row) and cost the feature. HR is answered before the gate now; the two
  tiers that READ Employee rows to decide themselves keep it, fail-closed.
- 2026-09-13 REPAIR: its W3. The phantom chain had NO repo-runnable guard — the only red was an
  out-of-repo probe on a personal bench, so someone could simplify `seed=` away and nothing versioned
  would notice. TestTeamKPI now carries the phantom chain, the ambiguous login and the HR-without-an-
  Employee case, so they travel with the code.
TICKET (W2, fails CLOSED so not blocking): for a manager who carries an allow=Company User Permission,
  the LIST shows a cross-company report and the DETAIL refuses it — the framework check fences on
  Appraisal.company, the list does not. Clicking a row the page just showed you says "not permitted".
  Make the two doors agree, and add a probe case so the pair cannot drift. Do NOT fix it by fencing the
  list on Appraisal.company: that field is copied from the Appraisal Cycle and never reconciled, which is
  the bug test_an_appraisal_stamped_with_the_wrong_company_does_not_move_its_owner already pins.
- 2026-09-13 RULING (Nabil, restated): HR MANAGES THE ENTIRE GROUP AND IS NOT LIMITED TO A COMPANY.
  That covers the personnel file, not only the list — an allow=Company User Permission, including the
  one the "HR (Company)" role auto-provisions, does not narrow HR anywhere on the KPI page. This is the
  ONE place on the hub with that exemption; everywhere else the fence still binds. Verified on a real
  site: a company-fenced HR user still lists every company AND still opens another company's KRA detail.
  Recorded in hrms/api/kpi.py::_scope and pinned by two tests, so a future reader meets the decision
  rather than re-deriving it — and knows exactly where to reverse it if the policy ever changes.
  This closes the last open question before the push.
- 2026-09-13T15:00:19Z COMMIT: 683d53017 docs(kpi): HR manages the entire group, and the code now says so → review dispatched
- 2026-09-13T15:01:07Z PUSH: nz-glass @ 6c6ce6b2d
- 2026-09-13T15:01:34Z PUSH: nz-glass @ 84b057733
- 2026-09-13T15:13:10Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 6 file(s) ⟂c4997bca2a0e
- 2026-09-13T15:13:52Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
