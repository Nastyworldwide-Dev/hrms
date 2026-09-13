2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-13T15:13:55Z COMMIT: c57410e6b feat(kpi): one level of the department tree, with its roll-up → review dispatched
- 2026-09-13T15:14:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-09-13T15:14:11Z COMMIT: 8058cd68b feat(pwa): the department tree, walked → review+design dispatched
- 2026-09-13 REPAIR: design review FIX_CRITICAL on the tree, THREE Criticals, all mine.
  (a) THE HERO WAS INVISIBLE FOR CEO/HR. It was still gated on teamKpi, which fetchTeam never submits
  for the tree tier — so the score, badge and ring vanished for exactly the tier this was built for, and
  the screen read as controls, then tables, no number. Same class as the tab-fetch regression: a binding
  left pointing at the wrong source after a split.
  (b) The live region announced a FALSE scope. scopeLabel read teamDepartment, which the tree never
  writes, so at every depth it said "All departments" while the user stood in Sales East — asserting a
  scope the tables underneath did not show, under a comment of mine claiming that drift was impossible.
  (c) Focus was destroyed on every drill: the activated button unmounts with its block (a leaf has no
  Departments table; the root crumb is not a button). Same class as the list->detail swap I had already
  fixed and did not extend to the walk.
- 2026-09-13 LEARNING(gate): two resources behind one set of chrome drift silently ->
  frontend/tests/kpi-shared-payload.test.mjs refuses ANY direct teamKpi/departmentKpi binding in the
  template. Proven RED 2/3 by re-binding the hero.
- 2026-09-13 REPAIR: its warnings too — the breadcrumb is an ordered list with aria-current and renders
  at every depth (it is also the only element that survives a drill, so it is what focus lands on); the
  Department SELECT is gone for the tier that walks instead; the root no longer shows an empty "People
  here" under a hero counting the whole company; both tables name their node; the eyebrows are headings.
TICKET (DSN-16): the walk has no route state. Browser Back and the Android back gesture exit KPI
  entirely instead of going up a level, and "look at Sales East" cannot be sent to anyone. Drive
  treeNode from a query param with router.push and a route watcher — Back, deep links and a
  route-change announcement all come for free. Tolerable for the one-level drill-down that shipped
  earlier; a tree of arbitrary depth is a different proposition.
- 2026-09-13T15:23:18Z COMMIT: 49996b767 fix(kpi): the CEO's own score was missing from the CEO's own page → review+design dispatched
- 2026-09-13T15:43:24Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-13 EVIDENCE(2): clock in/out audit complete — .claude/plans/audit-2026-09-13-clockinout.md.
  Independently re-verified three load-bearing claims: (a) `python3 -m unittest
  test_sync_endpoints_are_fenced` is RED on HEAD at checkin_recovery.py:recover_overwritten_checkins
  ("hub-wide but only role-checked"); (b) remote_checkin.py:635 carries a `# ceiling:` comment that
  admits the late-checkout boundary is calendar-date based and therefore wrong for any shift crossing
  midnight — the fix the ledger records as DONE is done for DAY SHIFTS ONLY; (c) shift_resolution.py:36
  still reads `if log_type == "OUT"`, so an IN never inherits the open session's shift, and
  shift_rules.py:123 returns "skipped-manual" WITHOUT closing its own auto rows (contrast :114-120,
  which closes them) — duplicate Active assignments are still being created today.
- 2026-09-13 DEAD END: the enumeration query in .claude/plans/checkin-root-cause.md is unsound.
  `HAVING outs = 0 AND ins >= 2` is day-grouped, so it misses the `IN, IN, OUT` day (outs=1) and every
  night shift, whose two INs straddle midnight into different DATE(time) groups. Attendance Day Audit is
  blind to both as well. Any damage count taken from it so far is an undercount. The session-scoped
  replacement (S1-S7) is specified in the audit doc; the script itself lived under /tmp and is gone.
NEXT: two audits still running (approver acafee3f79ead71e2, OT a3991044134607724) plus the Script Report
  family hunt (a47a18fba0b9015aa). When all three report, reconcile their verdicts with the clock audit
  above and lay ONE ranked plan for Nabil in the 6-lens format. Do not repair historical data, change a
  schema or a policy, push or deploy without his explicit word for that exact change.
- 2026-09-13 EVIDENCE(2): OT audit complete — .claude/plans/audit-2026-09-13-ot.md. Re-verified four
  anchors by reading source: ot_calculation.py:372-373 (the +/-1 day fetch window, O1),
  shift_type.py:275 (guards start_time only, end_time not at all, O2), ot_calculation.py:300-302
  (missing holiday list returns "normal" with a warning only, O5), hr/utils.py:774 (bare get_doc on
  Leave Allocation with no existence or docstatus guard, O7).
- 2026-09-13 DEAD END: the ledger's "OT hour persistence precision" row is FALSE. The columns are
  decimal(21,9), not (21,2); 9dp works end to end and one minute does NOT become 0.02. The surviving
  symptom — a one-minute claim refused — comes from round_ot_pay_hours (ot_calculation.py:63-79)
  applying HR's 30-minute pay band, reported to the employee as an EVIDENCE failure ("your check-outs
  prove at most 0.0 hours"). Rewrite the row as a wrong-message defect. Still unconfirmed on
  PRODUCTION: patches check_ot_hour_precision_capacity and verify_ot_hour_precision (patches.txt:2,8)
  may never have run on Verifica.
- 2026-09-13T15:48:27Z COMMIT: 87434be6e docs(plans): the 8 Sep ledger was not settled — two audits say where → review dispatched
- 2026-09-13 EVIDENCE(2): approver audit complete — .claude/plans/audit-2026-09-13-approver.md.
  Re-verified five anchors by reading source: employee_issue_row_scope.py:106 uses a raw
  get_value("user_id") == user while the file's OWN canonical _own_employees() sits at line 28 — it
  FAILS OPEN for an offboarded or duplicate-claimed login; `grep -c -i company hrms/overrides/ot_row_scope.py`
  returns 0; ot_row_scope._reporting_employees resolves identity canonically but queries the reports
  with no status and no company filter; salary_payments_via_ecs.py:76 makes `company` OPTIONAL, so an
  empty filter returns every company; employee_leave_balance.py:146-165 is a raw frappe.qb Employee
  query with optional unvalidated filters and no Active default.
- 2026-09-13 REPAIR(ledger): four rows on 360-status.md are wrong in the SAFE direction and two in the
  DANGEROUS one. Safe: N02 and N03 are recorded OPEN and are CLOSED in code (d479e4c05 / 686e4aa0d /
  981c1cbe7, one landing AFTER the row was written). Dangerous: Employee Leave Balance is recorded as a
  FENCED report and was never touched; and "PWA/Desk approval capability settled" is true of STATE and
  false of AUTHORITY.
- 2026-09-13 DEAD END: the approver audit's own (c)A table row #3 is wrong. It claims
  approval.py:85 _is_routed_approver has no Active filter. It calls hrms.utils.identity.own_employees —
  the canonical, normalized, Active-only, fail-closed primitive. Its real gap is only the missing
  company fence on the REPORT. Corrected in the audit doc under REFUTED; do not quote that column.
NEXT: all three audits are in and committed. Lay ONE ranked plan for Nabil in the 6-lens format from
  the three audit docs, ordered by impact on pay, separating (i) what we may fix on our own authority,
  (ii) what needs a production query first, (iii) what is HIS ruling and not a code change. Do not
  repair historical data, change a schema or a policy, push or deploy without his explicit word.
- 2026-09-13T15:52:45Z COMMIT: aa29a8aec docs(plans): the approver audit — sight and action are decided by different code → review dispatched
- 2026-09-13T15:59:11Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-13T15:59:14Z COMMIT: 2af3351e3 feat(attendance): count the check-in damage with a query that can see it → review dispatched
- 2026-09-13 EVIDENCE(4): **THE PRODUCTION BUILD IS NOT STALE.** Nabil states the live build is
  a741f3e. It is an ancestor of HEAD, 17 commits behind, and every one of those 17 is KPI work or
  docs — NOT ONE attendance, OT or approver fix. Verified by merge-base against sixteen named fix
  commits: 6c1f71efb (the approver filing guard), ce5ff48dd, e6eb09a35, 090091e06 (late checkout),
  a741f3e itself (the punch-type correction), 09e29ae5d, 7548588c0, 6be841a6e, d479e4c05, 981c1cbe7,
  ffce088ec, 3aaeffb30, 5353b5e9f, f83c201dd, 54327f689, 275c0f6f5 — ALL IN PRODUCTION. So the
  standing question "two rows at 18:30:25 -> the fixes are the answer; one row typed OUT on the night
  shift -> the deploy is the answer" is ANSWERED: the deploy is not the answer. The symptoms that
  persist are the defects the three audits found, running on code that already carries every fix.
- 2026-09-13 RULING (Nabil, in session): (1) the holiday-absorbs-shift-hours rate rule stays AS IS —
  ot_calculation.py:459-463 is confirmed intentional, close O4 as a decision, not a defect.
  (2) THE APPROVER IS ALWAYS THE reports_to MANAGER, transitively up the chain (his example: Nabil ->
  Hafiz -> Hafiz's superior); HR maintains the link on Employee. So approval.py::_is_routed_approver
  is CORRECT and approval_row_scope.py:15-18's "direct manager, READ ONLY" docstring is what is wrong.
  Re-scope (c)B from "unreviewed authority" to "the row scope contradicts the ruling". Still
  unaddressed by the ruling: whether a manager may CANCEL (finalize:410-416) — ask before touching.
  (3) Backdating window is FOUR MONTHS BEFORE THE CURRENT DATE — not the two 16th-15th cycles
  filing_window.py implements. That is a real policy change with its own blast radius.
- 2026-09-13 REPAIR: acted on the doc reviewer's four warnings. Corrected two load-bearing anchors in
  the clock audit (the `# ceiling:` block is :635-639 not :628-632; the untyped guard is :315-323 and
  its filter :330-342, not :325-328/:334-344) plus three minor ones; amended the WRONG ROW OF
  360-status.md IN PLACE (the precision row now reads REFUTED with a pointer) and headed that file
  with the three 13 Sep audits, so the index stops being quotable as false evidence; and committed the
  S1-S7 enumerator as hrms/utils/checkin_damage_enumeration.py (2af3351e3) so the sole evidence for
  "historical damage unrepaired" is no longer a script in /tmp.
NEXT: Wave A of the plan — stop the bleeding, in this order, one commit each with its own red test
  first: A1 shift_rules.py:122-124 (close the auto rows before returning "skipped-manual"),
  A2 shift_resolution.py:36 (a check-IN must inherit the open session's shift too),
  A3 the three holes in resolve_punch_type, A4 remote_checkin.py:635-639 (take the session boundary
  from the IN's own shift window, not calendar midnight). Do NOT repair historical data, push or
  deploy without Nabil's explicit word.
