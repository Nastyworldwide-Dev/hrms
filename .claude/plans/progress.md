2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-13T15:59:48Z COMMIT: cf3a923cf docs(plans): the live build already carries every fix, so the deploy is not the answer → review dispatched
- 2026-09-13 RULING (Nabil, in session, second round): (1) **AN APPROVED REQUEST IS NEVER CANCELLED.**
  So approval.py finalize:413-414, which elevates CANCEL on routing alone (`elif _is_routed_approver(doc):
  doc.flags.ignore_permissions = True`, with only _request_read_allowed ahead of it), is now a DEFECT to
  close, not an open question. A reports_to manager must not be able to cancel a settled decision.
  (2) Backdating: the CYCLE SHAPE STAYS 16th-15th; what changes is the DEPTH — four months back from the
  present day, and it applies to OT Request AND related requests such as expense claims. So filing_window
  keeps its cycle boundaries and widens from two cycles to four months' worth.
- 2026-09-13 REPAIR: acted on the doc reviewer's FIX_CRITICAL. The Critical was mine: the audit claimed
  the replaced-approver DocShare was dead code because "approval_row_scope grants the named approver
  submit". **A has_permission hook cannot GRANT a ptype in Frappe — the DocPerm is evaluated first and
  the hook can only subtract.** Verified from the doctype JSON: the Employee role carries submit=0 on
  Leave Application, Expense Claim and Shift Request, and hr/utils.py:986 shares exactly when
  has_permission(submit) is False — so for an Employee-role-only team lead the DocShare IS created, by
  live callers. Had that paragraph been believed, a later cleanup would have deleted the share and every
  Employee-role-only named approver would have lost sight of their queue. Also corrected seven anchor and
  count errors (26 of 32 Script Reports, not 27 of 33; 29 employee-owned doctypes, not 24; four off-by-a-
  few line references) and re-graded the REFUTED note: the "my team" table was measuring the CALLER's
  status where the defect is on the SUBORDINATE, so approval.py:85 reads caller=Active-yes / report=NO.
- 2026-09-13 LEARNING(fact): in Frappe a `has_permission` hook can only SUBTRACT a ptype, never grant
  one. Any claim of the form "the row scope grants role X permission Y" is false whenever the DocPerm
  for X lacks Y — check the doctype JSON before calling a share or a fallback dead.
NEXT: Wave A1 — hrms/hr/shift_rules.py:122-124 returns "skipped-manual" WITHOUT closing its own
  auto-created rows, while the sibling branch at :114-120 does close them. That is what keeps creating
  duplicate Active open-ended Shift Assignments of different shift types, which is the precondition for
  the split-day damage (shape S6). Red test first, then the fix, then the family ledger.
- 2026-09-13T16:03:56Z COMMIT: bd8bceee7 docs(plans): a permission hook cannot grant, so the approver share is not dead code → review dispatched
- 2026-09-13T16:07:55Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13 EVIDENCE(3): Wave A1 done. hrms/hr/shift_rules.py's manual-wins branch returned
  "skipped-manual" without closing its own auto rows, while the roster and schedule branches beside it
  both close theirs. Proven RED then GREEN on fresh.local through the real document API
  (verify-bench/sites/probe_shift_rules_manual.py, savepointed): before the fix the rule stood down and
  left an open-ended "NP Night 19-4" row Active beside the manual row; after it, none survive.
- 2026-09-13 EVIDENCE(2): the first probe attempt FAILED with MultipleShiftError, which turned out to
  be the more useful result. The framework does refuse a second overlapping assignment — unless HR
  Settings `allow_multiple_shift_assignments` is on, in which case the same-date case only WARNS and
  the hard throw is left to has_overlapping_timings, which a day shift and a night shift do not
  trigger. So this defect is reachable exactly on a site that runs two non-overlapping shifts, which is
  every site that assigns two shifts at all. On fresh.local the flag reads 0 and the probe sets it
  inside the savepoint.
- 2026-09-13 NEW PRODUCTION QUESTION (blocks the S6 count, ask Nabil or read the site):
  is HR Settings `allow_multiple_shift_assignments` enabled on Verifica? If YES, A1 is the source of
  the duplicate Active assignments and the S6 count should fall to zero once it has run. If NO, this
  defect was never reachable there and shape S6 has ANOTHER source that is still unfound — do not close
  the split-day investigation on the strength of A1 alone.
NEXT: Wave A2 — hrms/utils/shift_resolution.py:36 `choose_shift` applies the open-session rule only to
  OUT, so a check-IN never inherits the shift of the session it belongs to. Red test first (pure, no
  bench: choose_shift(punch, "IN", [day, night], open_in={shift: day}) must return the DAY shift).
- 2026-09-13T16:07:58Z COMMIT: 1bb0a0414 fix(shift): standing down means closing your own rows, in every branch → review dispatched
- 2026-09-13T16:10:04Z COMMIT: cb16e68ba docs(plans): a sweep fixed seven anchors and broke an eighth → review dispatched
- 2026-09-13 DEAD END: **Wave A2 as planned is WRONG and must not be built.** The audit said the fix
  was to make `choose_shift` apply the open-session rule to IN as well as OUT
  (hrms/utils/shift_resolution.py:36). Measured the real function on fresh.local
  (verify-bench/sites/probe_shift_in_inherit.py, pure, no writes), two assignments, day 09-18 and
  night 19-03:30:
      IN  18:31, day session open since 08:51   -> Night 19-0330   <- the reported split, CONFIRMED
      OUT 18:31, same open session              -> Day 09-18       <- already correct
      IN  08:51, nothing open                   -> Day 09-18       <- correct
      IN  19:00, day session STILL OPEN         -> Night 19-0330   <- correct, and the trap
      IN  19:00, nothing open                   -> Night 19-0330   <- correct
  The fourth row is why the planned fix is wrong: an unconditional "an IN inherits the open session's
  shift" would move a GENUINE 19:00 night arrival onto the day shift whenever the person forgot to
  check out that morning. It would trade the reported split for a silent misattribution of a whole
  night shift, which is worse — the split is at least visible as two rows.
  The 18:31 punch is only mis-attributed because it is mis-TYPED. Typed correctly it already resolves
  to the day shift. So the defect is not in shift attribution at all; it is that the type is still
  taken on trust everywhere except the PWA.
- 2026-09-13 REPAIR(plan): A2 re-scoped. The real gap is that `resolve_punch_type` is applied in
  `hrms/api/remote_checkin.py::punch` — ONE write path. `EmployeeCheckin.validate`
  (employee_checkin.py:35-41) enforces no alternation at all, so the biometric/device path
  (employee_checkin.py:143-211, log_type straight from the caller) and HR Desk manual entry still
  write an IN that contradicts a live session. The fix belongs in the document layer, not in
  shift_resolution. NOTE this changes what a BIOMETRIC DEVICE records, which is a different blast
  radius from a PWA button — flag it to Nabil before building, do not swap it in silently.
NEXT: A2 (re-scoped) — carry the server-side type resolution into the document layer so every write
  path alternates, not just the PWA. Needs Nabil's nod first because it changes biometric-recorded
  punches. If he defers, go to A3 (the three holes in resolve_punch_type) and A4 (the night-shift
  late-checkout boundary), which are self-contained and need nobody's permission.
- 2026-09-13T16:11:43Z COMMIT: c71a43907 docs(plans): the planned shift-attribution fix would have cost a whole night shift → review dispatched
- 2026-09-13T16:14:03Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-13T16:14:06Z COMMIT: d2b4191bf fix(checkin): the untyped guard judged rows the pairing walk never reads → review dispatched
- 2026-09-13T16:15:27Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T16:15:30Z COMMIT: f44b588c8 fix(checkin): a dead orphan was being read as the open session → review dispatched
- 2026-09-13T16:17:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13 REPAIR: A1 amended after review — it was half a fix and it cost something else. Measured
  both on fresh.local against commit 1bb0a0414 (verify-bench/sites/probe_shift_handoff_day.py,
  savepointed): (a) the HAND-OFF DAY survived, because _close_assignment floors end_date at the row's
  own start date and every Shift Assignment date read here is inclusive of end_date — a rule row
  starting today closed to today and went on governing it ("shift types covering today =
  ['Half Day Test', 'NP Night 19-4']"); such rows are now retired as Inactive instead. (b) the fix
  STRIPPED THE LAPSED-ROSTER CASE BARE — the branch's second disjunct is a manual segment that ended
  and was never replaced, so closing there left the employee with NO shift at all ("covering today =
  []"), which is shape S5 traded for shape S6. The closing loop now runs only when a real manual row
  actually covers the person. Both GREEN after.
- 2026-09-13 LEARNING(fact): in hrms, end-dating cannot close a Shift Assignment that STARTS TODAY —
  the floor is its own start date and every date-range read is inclusive of end_date. Use
  `status = "Inactive"`, which validate_overlapping_shifts short-circuits on.
- 2026-09-13 LEARNING(gate): an assertion about "open-ended rows" cannot see a row that ends today ->
  hrms/hr/test_shift_rules.py now asserts that exactly ONE shift type governs today. The old assertion
  was green with the defect live inside its own fixture.
- 2026-09-13T16:17:37Z COMMIT: b2ab6ce0f fix(shift): closing a row that starts today does not close it → review dispatched
- 2026-09-13T16:20:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13 REPAIR: the damage enumerator carried six SQL defects, every one of which would have
  produced a WRONG number on production — which is the exact failure the module was written to correct.
  Found by review, fixed and smoke-tested (all seven shapes now execute on fresh.local; S1 correctly
  surfaces the Midnight Shift IN 00:30 -> IN 10:00 pair that a day-grouped query splits):
  (1) S1/S2's next-IN boundary subqueries had no Rejected filter, so a rejected remote check-in acted
      as a session boundary and put HEALTHY days into the repair-candidate list;
  (2) S4 correlated punches by DATE(i.time) = a.attendance_date — re-introducing the night-shift
      blindness the module exists to remove, in BOTH directions (a broken night row unreported, a
      healthy one reported by coincidence). It now correlates through Employee Checkin.attendance, the
      link the marking code itself writes, with no date arithmetic at all;
  (3) S6 compared a DATE column against "<date> 23:59:59", which MariaDB coerces to midnight, so an
      assignment ending on the last day of the window read as closed — the PRECONDITION under-reported;
  (4) S5 counted every shift-less punch, but shift IS NULL and offshift = 1 are set together and OT
      ignores off-shift punches by design, so the count was dominated by punches behaving correctly;
  (5) S2's derived table had no date predicate and self-joined the whole history, quadratic per
      employee — on production it might never have returned;
  (6) counts were rows, not people. Every decision taken off this report is about people, so it now
      prints rows/employees, and trims the returned sample so the counts are not buried.
- 2026-09-13 LEARNING(gate): the first invariant test pinned ONE SPELLING of day-scoping
  (GROUP BY ... DATE(time)) and was green with the other spelling shipped inside S4
  (WHERE DATE(i.time) = a.attendance_date) -> hrms/tests/test_checkin_damage_enumeration.py now also
  refuses DATE(<alias>.time) in any punch-walking shape. Mutation-checked: catches the old S4 form,
  passes the shipped one.
- 2026-09-13 LEARNING(fact): in this app a check-in with shift IS NULL always also has offshift = 1
  (employee_checkin.py:79-80), and OT deliberately ignores off-shift punches — so "no shift stamp"
  alone is not evidence of damage.
NEXT: Wave A4 — the night-shift late-checkout boundary (hrms/api/remote_checkin.py:640, its own
  `# ceiling:` at :635-639). Take the session boundary from the IN's own shift window instead of
  calendar midnight. Red first: the probe that reproduced the production refusal verbatim
  (IN Mon 19:00, duplicate IN Tue 00:05, submit_late_checkout for Tue 03:30).
- 2026-09-13T16:20:39Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T16:21:46Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T16:22:35Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:23:23Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:23:24Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 4 call site(s) given verdicts, 10 same-root ⟂0dedd975f583
- 2026-09-13T16:23:26Z COMMIT: 53c25a30e fix(attendance): the damage query would have reported the wrong number → review dispatched
- 2026-09-13 EVIDENCE(3): Wave A4 done — the night-shift late check-out. The day-turnover half of the
  session boundary was calendar midnight, which on a 19:00-03:30 shift falls in the MIDDLE of the
  session, so a duplicate punch at 00:05 was read as the next session's arrival and bounded the window
  at itself. Reproduced on fresh.local with the production message verbatim
  (verify-bench/sites/probe_late_checkout_night.py, savepointed): RED on 53c25a30e, GREEN after, same
  fixture both runs. The turnover now comes from the IN's own shift_actual_end, floored at midnight so
  no shift living inside one date changes behaviour. Extracted as the pure `session_boundary` with six
  bench-free cases, because the rule was previously only reachable through a whitelisted endpoint.
- 2026-09-13 DEAD END: the first two probe runs were FALSE GREENS waiting to happen — the probe set
  shift_start/shift_end itself on insert, and fetch_shift overwrote them with the employee's REAL
  assignment (a 10:15-18:00 day shift), so shift_actual_end never crossed midnight and the fix looked
  inert. A late-check-out fix cannot be verified without giving the probe employee a real night Shift
  Assignment first. This also means the fix DEPENDS on shift_actual_end being stamped correctly — if
  shift attribution is wrong for a punch, its late check-out boundary is wrong too. The two are linked.
NEXT: Wave A3b — the 00:00-06:00 band in resolve_punch_type (hrms/api/remote_checkin.py:312-313)
  leaves night shifts unprotected for the back half of their shift, so a double tap after midnight
  still writes the two-IN shape. The band exists to protect an EARLY-SHIFT arrival at 05:30 from being
  read as yesterday's departure, so the fix must distinguish the two — likely by asking whether the
  open IN's own shift is still running, which session_boundary now makes expressible.
- 2026-09-13T16:29:51Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:29:55Z COMMIT: 8d105985e fix(checkin): a night shift's session does not end at midnight → review dispatched
- 2026-09-13 REPAIR: the enumerator's S4 fix was itself wrong, in the quietest possible way. Moving
  from DATE() to the `attendance` link is precise, but that link is written by ONE path
  (update_attendance_in_checkins); HR's bulk Employee Attendance Tool, mark_attendance() and Attendance
  Request never write it, and mark_attendance_and_link_log DELIBERATELY leaves punches unlinked on
  DuplicateAttendanceError / OverlappingShiftAttendanceError — which is exactly the contested day S4
  exists to find. Measured on fresh.local: S4 = 0 while 22 Half-Day/0h rows carry no linked punch at
  all. Added S8 as the "cannot tell" denominator, printed under S4 with a line saying S4 is incomplete
  while S8 is non-zero; S9 for the offshift=1 bucket S5 now excludes (a punch gets that flag either by
  design OR because no assignment matched, which is damage); and a start_date guard on S6, without
  which an employee correctly scheduled onto a different shift next month counted as a conflict.
- 2026-09-13 EVIDENCE(3): all NINE shapes execute on fresh.local. S6 died the first time it ran
  ("Unknown column 'assignments_covering' in 'ORDER BY'") — a renamed SELECT alias, with every test
  green, because these shapes only execute on a bench.
- 2026-09-13 LEARNING(gate): a renamed SQL alias is invisible to a repo that cannot run SQL ->
  hrms/tests/test_checkin_damage_enumeration.py now requires every bare identifier in ORDER BY or
  HAVING to be defined in that shape's SELECT. Proven red by reintroducing the mismatch.
- 2026-09-13 LEARNING(gate): the day-scoping guard required a table alias, and three shapes are
  single-table and unaliased, so plain DATE(time) passed — 8 of 10 mutants missed. It now carries six
  spellings and catches 8 of 8, while the shipped link form and an ordinary time window still pass.
- 2026-09-13 LEARNING(fact): Employee Checkin.attendance is written only by
  update_attendance_in_checkins. Any query correlating punches through that link UNDER-reports on
  exactly the contested days, because the marking code leaves them unlinked on purpose.
NEXT: Wave A3b — the 00:00-06:00 band in resolve_punch_type leaves night shifts unprotected for the
  back half of their shift. The band protects an EARLY-SHIFT 05:30 arrival from being read as
  yesterday's departure, so the fix must distinguish the two: ask whether the open IN's own shift is
  still running at `now`, which needs shift_actual_end on the rows punch() reads.
- 2026-09-13T16:34:10Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:34:11Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 4 call site(s) given verdicts, 11 same-root ⟂e41a025b743e
- 2026-09-13T16:34:13Z COMMIT: 73604c8a7 fix(attendance): a zero this report cannot justify must not look like good news → review dispatched
- 2026-09-13 EVIDENCE(3): Wave A3b done. resolve_punch_type exempted every punch between 00:00 and
  06:00 outright, which handed the two-IN shape back to night workers through the back half of their
  own shift. The band now sits BELOW the walk and asks whether the open IN's own shift is still running
  — the only question that separates a night worker's 02:00 double tap from an early-shift 05:30
  arrival after yesterday's forgotten check-out. With no shift stamped the old behaviour stands.
  RED then GREEN bench-free (4 cases), and both halves measured on fresh.local through real saves
  (verify-bench/sites/probe_night_band.py): 19:00 shift closing 05:00 -> 02:00 tap becomes OUT;
  day shift closed 13:00 -> 05:30 arrival stays IN.
NEXT: A4 came back from review with TWO REGRESSIONS IT INTRODUCED, both proven on fresh.local, both
  in hrms/api/remote_checkin.py::submit_late_checkout. (W1) the widened boundary lets an OUT belonging
  to a LATER COMPLETED session fall inside out_time_filter and trip `later_out`, so a buried repair is
  now REFUSED that HEAD~1 ACCEPTED — a strict regression on the very population A4 exists to unblock.
  (W2) a late check-out can be written on top of a genuinely new, still-open session opened between
  midnight and shift_actual_end. Fix for both is the same: compute `first_later_in` (time > in_dt,
  name != in_doc.name) separately from `next_in`, and use min(next_in, first_later_in) as the upper
  edge of the `later_out` existence window ONLY — the "must be before your next check-in" refusal stays
  keyed on next_in, which is what A4 widened on purpose. A3b shrinks W2's exposure (a 00:05 duplicate
  is now an OUT, so there is no stray IN to step over) but does not close it.
  Also (W3) the claim "a day shift keeps exactly the boundary it had" is FALSE for an evening shift
  whose grace window crosses midnight — measured, session_boundary(Mon 14:00, Tue 00:30) -> Tue 00:30.
  Reword, and pin the crossing-grace shape with its own case.
- 2026-09-13T16:38:18Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:38:46Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:39:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:39:13Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:39:28Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:39:37Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:39:45Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:40:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:40:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:40:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:41:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
