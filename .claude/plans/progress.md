2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-13T16:41:09Z COMMIT: 36b4ddad8 fix(checkin): the small hours belong to whoever is still on shift → review dispatched
- 2026-09-13 REPAIR: A4 introduced a STRICT REGRESSION and review caught it. submit_late_checkout uses
  the session boundary for two different questions, and only one wanted widening: the refusal ("is the
  time you typed still inside this session") is keyed on the NEXT SESSION's arrival and was meant to
  move past midnight; the search ("does an OUT already exist for this session") must be bounded by the
  FIRST later arrival of any kind. Widening both let an OUT belonging to a later COMPLETED session fall
  inside the search window. PROVEN on fresh.local (verify-bench/sites/probe_buried_repair.py): night IN
  Mon 19:00 forgotten, a complete session Tue 01:00-02:00 after it, repair filed for Tue 00:30 — RED
  after 8d105985e ("A check-out for this session already exists"), ACCEPTED before it. GREEN now, and
  the original night-shift repair is still GREEN.
- 2026-09-13 DEAD END: "a day shift keeps exactly the boundary it had" was FALSE, and the test that
  asserted it picked the one shape that cannot exercise the claim. An evening shift ending 23:30 with
  the default hour of allow_check_out_after_shift_end_time closes at 00:30, so its boundary moves by
  that half hour — measured, session_boundary(Mon 14:00, Tue 00:30) -> Tue 00:30. Reworded and pinned
  with its own case.
- 2026-09-13 TICKET (hotspot, remote_checkin.py, 15 fixes/90d): extract
  hrms/utils/session_state.py::open_session(employee, at) returning ONE object — the open IN row, its
  session start, its turnover boundary, and whether it is live — from a single ordered query. 27 of ~37
  hunks in 90 days landed in four functions that all answer that one question with three different
  rules (_session_is_live's 06:00 cutoff, SESSION_WINDOW's 20 hours, session_boundary's shift end).
  Every fix in this file has been one of those three disagreeing with the other two.
NEXT: the enumerator came back with two more. (1) S8 is NOT the logical complement of S4 — S4 needs
  EXISTS(IN) AND EXISTS(OUT), S8 needs NOT EXISTS(any punch), so a row with ONE linked punch is in
  neither bucket and the "unearned zero" caveat never fires. attendance_day_audit.py:600 unlinks
  punches ONE AT A TIME, so that partial state is reachable. Make S8 `NOT (EXISTS(IN) AND EXISTS(OUT))`.
  (2) the caveat only prints when both shapes ran, so `report(shapes="S4")` shows a bare zero — the
  exact read the commit forbids. Auto-append the denominator, or say it was not run.
- 2026-09-13T16:43:24Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T16:43:28Z COMMIT: 96228853f fix(checkin): widening the session boundary buried the repair it was meant to free → review dispatched
- 2026-09-13 REPAIR: the enumerator's denominator was not a denominator. S4 needs EXISTS(IN) AND
  EXISTS(OUT); S8 asked for NOT EXISTS(any punch) — which is not the negation of that, so a row with
  exactly ONE linked punch fell out of both buckets and the "unearned zero" caveat never fired for it.
  That state is reachable: attendance_day_audit.py:600 unlinks punches ONE NAME AT A TIME, and this
  repo's own audit already has a verdict for a Half Day with a single linked punch. S8 is now
  NOT (EXISTS(IN) AND EXISTS(OUT)) — the exact complement. Measured on fresh.local for 1-14 Sep:
  total Half-Day/0h = 22, S4 = 0, S8 = 22, S4+S8 = 22, partition holds.
- 2026-09-13 REPAIR: the caveat only printed when both shapes happened to run, so `report(shapes="S4")`
  showed a bare zero — the exact reading the pairing exists to forbid, reachable through the documented
  subset form. `report` now drags a denominator in whenever its shape is asked for. Verified: asking
  for S4 alone prints S4, S8 and the caveat.
- 2026-09-13 REPAIR: three more day-scoping spellings the guard missed, named by review and now covered
  — SUBSTRING/SUBSTR/CONVERT over a time column, TIMESTAMPDIFF(DAY, ...) (MINUTE stays legal, S2 uses
  it), and BETWEEN against a DATE column alongside the >= that was already there.
NEXT: A2 (re-scoped) — carry the server-side punch-type resolution into the document layer so every
  write path alternates, not just the PWA. This changes what a BIOMETRIC DEVICE records, so it is the
  one remaining item with a blast radius beyond the phone app. After that: the OT wave (B1 the +/-1 day
  fetch window disagreement, B2 the unguarded Shift Type end_time, B3 the silent-zero messages,
  B4 the missing holiday list), then the leak wave (C1 employee_issue_row_scope fails open, C2 the
  hub-wide recovery endpoint, C3 ot_row_scope, C4 the leave-allocation pointer).
- 2026-09-13T16:44:43Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T16:44:47Z COMMIT: 98c64cb99 fix(attendance): the denominator was not the complement of what it counted → review dispatched
- 2026-09-13 REPAIR: the `first_later_in` edge introduced DATA CORRUPTION and review caught it.
  first_later_in is always <= next_in by construction, so the OUT-existence window could only SHRINK —
  and the genuine OUT closing the session fell outside it. A SECOND check-out became creatable on a
  session that already had one, on a plain DAY shift as well as at night, and get_unresolved_stale_in's
  banner OFFERS that session so an ordinary user is walked into it. Two OUT rows on one session,
  measured.
- 2026-09-13 LEARNING(fact): a buried-session repair and a duplicate-check-out corruption are
  INDISTINGUISHABLE by any time boundary — both read IN, IN, OUT in time order. That is why two
  successive fixes each got one of them wrong. The invariant that separates them is "never leave two
  consecutive OUTs", the mirror of resolve_punch_type's "nobody arrives twice without leaving".
  Replaced the edge with hrms/api/remote_checkin.py::leaves_consecutive_outs, pure and bench-free.
  All four shapes measured on fresh.local: buried repair ACCEPTED, day duplicate REFUSED, night
  duplicate REFUSED, plain forgotten check-out ACCEPTED.
- 2026-09-13 LEARNING(gate): the bench-free suite was 50/50 GREEN with that corruption live, because
  nothing exercised the OUT-existence search against a duplicate IN inside a CLOSED session -> eight
  cases added covering all four shapes plus the rejected-OUT exemption and both same-instant tie-breaks.
- 2026-09-13 TICKET: hrms/tests/test_checkin_timezone.py has two tests permanently RED under the bench
  interpreter (test_punch_stamps_employee_timezone_not_site_timezone errors, leaving frappe.get_all
  unpatched; test_closed_sessions_are_not_flagged fails on row ordering that does not survive the
  list(reversed(...)) in get_unresolved_stale_in). They are the ONLY bench-level coverage of punch()
  and of the banner that hands users into the path above. Repair or delete — a permanently red test
  protects nothing and masks the next regression.
NEXT: A2 (re-scoped) — carry the server-side punch-type resolution into the document layer so every
  write path alternates, not just the PWA. Changes what a BIOMETRIC DEVICE records. Then the OT wave
  (B1 the +/-1 day fetch window, B2 the unguarded Shift Type end_time, B3 the silent zeros, B4 the
  missing holiday list), then the leak wave (C1 employee_issue_row_scope fails open, C2 the hub-wide
  recovery endpoint, C3 ot_row_scope, C4 the leave-allocation pointer).
- 2026-09-13T16:57:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
