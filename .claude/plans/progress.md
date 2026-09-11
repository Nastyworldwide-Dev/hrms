2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
2026-09-10T09:20Z COMMIT: 2fc1db148 fix(ot) round before the minimum; cf4cb2fe4 fix(attendance) typed correction deducts the break.
  EVIDENCE: 2 correct — red proved for both (ImportError on ot_minutes_qualify; TypeError on the third arg), then 6/6 and 24/24 green.
  EVIDENCE: 3 works — bench hrms.tests.test_ot_nonworking_hours 17/17; bench-free suite diffed against a 174-failure baseline, no new failures;
    reviewer independently killed 4 mutants (raw-compare and always-true on the helper, raw-compare at both gate call sites).
  EVIDENCE: 6 behaves — frappe-reviewer on 2fc1db148: NEXT_ACTION DEPLOY, no Critical. Property sweep over min_minutes 1..180 x 1..720 min:
    the OLD gate produced 435 "qualifies but pays 0" mismatches, the NEW gate produces 0. Double-rounding proven idempotent.
TICKET: refactor hrms/utils/ot_calculation.py — split the policy ladder (round/qualify/cap) from the pricing and capacity-replay layers.
  Hotspot, 18 fixes/90d, 950 lines. Cause of the churn: day classification, band pricing, capacity replay and monthly-cap accounting all live
  in one module, so every policy change touches the same file. This commit reduced pressure slightly (two duplicated inline gate expressions
  collapsed into one named rule) but did not address the cause.
TICKET: break-aware OT window — hrms/utils/ot_calculation.py has zero break awareness (grep 'break' -> only Python keywords). Harmless while
  every configured break sits inside the normal shift; a break configured to overlap the OT window would be paid as overtime. Needs Nabil's
  ruling because it changes money; today's figures do not move.
DEAD END: `git stash push -u -- <paths>` then `git stash apply <sha>` in this worktree silently REVERTED an already-committed file
  (hrms/utils/ot_calculation.py, back to the pre-fix body) and truncated .claude/plans/progress.md from 321 to 211 lines. Caught by reading
  `git diff --stat` before committing; recovered with `git checkout HEAD -- <both paths>`. Class: STASH-IN-SHARED-WORKTREE. Do not use stash to
  take a baseline measurement here — commit first and measure against the parent commit instead.
NEXT: Nabil rules on the OT backfill (below); then doors and permissions — OT Request menu link, Employee permlevel-1 rows,
  HR User on Overtime Type, HR Manager on Overtime Slip.
DECISION NEEDED: the rounding fix changes what Attendance.ot_hours SHOULD hold for every historical weekday in the 50-59 minute band.
  The record still reads 0 while get_claimable_ot_summary recomputes from punches and offers the day as 1.0 h — record and claim card disagree
  on the employee's screen. The only remedy is recompute_ot_backfill, which rewrites SUBMITTED rows in a range with no financial-dependency
  guard (current-plan.md risk 5c). NOT run and NOT patched in: mass-rewriting submitted pay rows needs Nabil's explicit word for that exact range.
- 2026-09-10T11:29:57Z COMMIT: 7020a4f87 test(patches): make the masters test runnable and give it something to fail on → review dispatched
2026-09-10T09:35Z REPAIR: review of cf4cb2fe4 (frappe-reviewer, NEXT_ACTION DEPLOY, no Critical) found a SECOND live member of the same
  class, larger than the one fixed. The hourly job applies three rules to produce working_hours — unpaid break, unpaid early arrival
  (paid_intervals_from, shift_type.py:551), and hours-from-worked-intervals-not-span. cf4cb2fe4 unified the break only.
  Verified: shift 09:00-18:00, punch in 07:30 out 18:00 -> job writes 8.00h. HR corrects the out time by five minutes -> typed path
  recomputes 07:30-18:05 = 10.58h less 60m = 9.58h against the job's 8.08h. +1.50h to payroll per correction, permanent because
  on_update_after_submit (attendance.py:396-398) sets auto_attendance = 0 so the job never revisits the row.
  Recorded in .claude/plans/family.md as the second live member; NOT patched (class: spec -> ruling first).
  EVIDENCE: 6 behaves — reviewer killed both wiring mutants independently (each call site turned a different test red), and probed the two
  likeliest wrong answers: a fixed break the employee punched out for is NOT double-deducted (job 8.00h vs typed 8.00h), and an overnight
  Thu 22:00 -> Fri 06:00 correctly takes 0 break minutes while Fri 08:00 -> Sat 02:00 takes the 105-minute Friday prayer break.
TICKET: one paid-hours rule shared by both writers — extract "paid hours for these times on this shift" so shift_type._process and the typed
  correction path cannot diverge again. Closes the early-arrival divergence above AND the attendance.py hotspot obligation (10 fixes/90d) in
  one move. Blocked on the decision below.
DECISION NEEDED: does an HR correction re-apply the early-arrival rule (hours start at shift start), or is the span HR typed authoritative?
  HR ruled on the job's behaviour only, 10 Sep 2026: "early clock in didnt counted as paid".
NEXT: Nabil rules on (a) the OT backfill range and (b) early arrival on typed corrections. Meanwhile: doors and permissions —
  OT Request menu link, Employee permlevel-1 rows, HR User on Overtime Type, HR Manager on Overtime Slip.
- 2026-09-10T11:34:22Z COMMIT: 143fc391c docs(plans): the paid-hours class has a second live member, larger than the first → review dispatched
- 2026-09-11T03:14:42Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:14:42Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-11T03:14:46Z COMMIT: 33d286691 fix(perms): restore restricted-field permission rows on every migrate, not once → review+cross-app dispatched
- 2026-09-11T03:21:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:21:44Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:21:57Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:21:57Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:22:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:22:17Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:22:23Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:22:23Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:22:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-11T03:22:50Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-11T03:22:54Z COMMIT: 6032d0749 fix(hr): two select comparisons matched values their fields never declared → review dispatched
- 2026-09-11T03:25:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-11T03:25:12Z COMMIT: 861d9be54 fix(perms): a restored permlevel row has to write, not only read → review dispatched
- 2026-09-11T03:34:10Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-11T03:34:14Z COMMIT: 4c181eeb3 fix(perms): keep the guard inside the doctypes the lockdown owns → review dispatched
- 2026-09-11T03:39:43Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-11T03:39:47Z COMMIT: 239ad87b5 feat(hr): restrict bank, IBAN and passport on Employee, reversibly → review dispatched
2026-09-11T03:40Z COMMIT: 33d286691 -> 4c181eeb3 permlevel guard (3 iterations, 2 of them fixing defects review found in my own work);
  6032d0749 two dead select branches + a class gate; 239ad87b5 reversible sensitive-field lock.
  EVIDENCE: 3 works — every permission claim grounded on the verify bench, not by reading rows: the write defect was proved with a real
  HR Manager doc.save() reading back 0 (red) then 1 (green); the sensitive lock was proved BOTH directions, 0->1 on migrate with the box
  ticked and 1->0 on the migrate after unticking it.
REPAIR: my first permlevel guard granted read without write, so the checkbox rendered and every tick was silently reverted — WORSE than the
  missing row, because HR would believe the grant landed. Caught by review. Second defect found while fixing it: the guard keyed on row
  EXISTENCE, so a read-only row stayed read-only for ever. Third: unfiltered doctype scan + rows_needing_write had no level-0 gate, so one
  permlevel-1 Custom Field on Appraisal would have granted HR write on appraisee_comments / appraisee_agreement / appraisee_sign_date —
  the employee's own sign-off, read-only for HR by design. Not live; closed anyway. Scope is now GUARDED_DOCTYPES, pinned equal to the
  lockdown patch's L1_HR_DOCTYPES by test.
LEARNING(fact): frappe.permissions.add_permission grants READ only. Without update_permission_property(..., "write", 1) the field renders and
  Document.reset_values_if_no_permlevel_access reverts every edit with no error. Proving the ROWS are right is not proving a SAVE persists.
LEARNING(fact): Frappe does not apply a new field's `default` to an EXISTING Single — HR Settings read 0 straight after the migrate that
  introduced the field, indistinguishable from a deliberate untick. A defaulted setting needs a one-time patch, written only when the field
  has never been stored so an existing choice survives.
LEARNING(how): the shared git stash is unsafe in this worktree — `git stash push -- <paths>` then `apply` silently reverted an already-committed
  file and truncated progress.md by 110 lines. Measure a baseline against the parent COMMIT, never by stashing.
TICKET: refactor hrms/utils/ot_calculation.py (18 fixes/90d) — split the policy ladder from pricing and capacity replay.
TICKET: one shared paid-hours rule for both writers (attendance hotspot, 10 fixes/90d) — closes the early-arrival divergence too.
NEXT: (1) sweep 4 finding #20 — Shift Request approval builds a Shift Assignment with NO shift_location, and employee_checkin.py returns early
  when no assignment has one, so anyone approved that way checks in from anywhere with the geofence silently off. Verify, then fix.
  (2) Nabil rules on the OT backfill range and on early arrival for typed corrections. (3) OT Request Desk menu link + the 4 select-only
  permission rows + HR Manager on Overtime Slip.
- 2026-09-11T03:40:19Z COMMIT: 7d7326508 docs(plans): evidence, three self-inflicted repairs, and the stash dead end → review dispatched
- 2026-09-11T03:43:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-11T03:43:09Z COMMIT: 5e61fc7ff fix(perms): one discovery source, one warning per loop, and a loud conversion → review dispatched
2026-09-11T03:45Z CIRCUIT: hrms/utils/permlevel_guard.py has taken FOUR fix: commits in a row with no push
  (33d286691 -> 4c181eeb3 -> 861d9be54 -> 5e61fc7ff). Per CLAUDE.md that opens the circuit: no more reviewers on this file,
  park it, ask a human. Parked. Each fix was found by the review of the one before it, and each was real — read without write,
  row-existence not row-capability, an unscoped scan that could have granted HR write on an employee's own appraisal sign-off,
  and a log line I said I had moved when I had copied it. The file is converging (three different LAYERS, not the same line
  three times) but four rounds on one file is the signal the rule exists for.
TICKET: hrms/utils/permlevel_guard.py now holds two responsibilities — granting permission ROWS (ensure_permlevel_rows) and
  setting field PERMLEVELS (apply_sensitive_field_lock). Split when a fifth change lands. Also: the source-contract tests assert
  on literal source text and file ordering (.index()); they are the right tool for a wiring defect and the most brittle thing in
  the file — any rename breaks them with a confusing message.
NEXT: NOT more work on permlevel_guard.py. Next is sweep-4 finding #20 (Shift Request approval creates a Shift Assignment with no
  shift_location, and employee_checkin returns early when no assignment has one -> geofence silently off for anyone approved that
  way). Verify first, then fix. Nabil still owes a ruling on the OT backfill range and on early arrival for typed corrections.
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
