2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-13T16:57:20Z COMMIT: 9c6f41fa7 fix(checkin): a late check-out may never leave two departures in a row → review dispatched
- 2026-09-13 REPAIR: the consecutive-OUT invariant was right; its SCOPE and its REACH were not, and
  review measured both on fresh.local. (a) the sequence was fetched `time asc` with limit=200, and an
  ascending fetch with a row limit truncates the NEWEST rows — so past 200 punches the genuine closing
  OUT was invisible and the guard failed open silently (IN 09:00, 204 stray INs, real OUT 18:00 -> a
  second check-out at 13:00 ACCEPTED). Bounded by TIME now, no row limit. get_unresolved_stale_in
  already avoided this by fetching `time desc` and reversing. (b) `any(pair over the whole sequence)`
  is not "this row must not create an adjacency" — a log ALREADY carrying two adjacent OUTs anywhere in
  the window (the damage the previous version of this same function could produce, and what the hub
  leaves behind when one punch is pulled twice) refused the repair of an unrelated EARLIER session.
  Scoped to the inserted row's two neighbours.
- 2026-09-13 EVIDENCE(3): seven shapes measured, all correct — 204 stray INs REFUSED, stale OUT/OUT
  pair a day later ACCEPTED, mirrored duplicate pair ACCEPTED, day duplicate REFUSED, night duplicate
  REFUSED, buried repair ACCEPTED, plain forgotten check-out ACCEPTED. Both mutants killed bench-free:
  inverting the same-instant tie-break and restoring the global scan each turn exactly one test red.
- 2026-09-13 DEAD END: instrumenting a test with an inline `print(self.check(...))` made it report the
  WRONG verdict and cost a long detour chasing a phantom. Instrument the FUNCTION and write to a file,
  never the test body.
- 2026-09-13 LEARNING(fact): in this repo an ascending `frappe.get_all` with a row `limit` on a
  session-scoped question silently drops the NEWEST rows — the wrong axis entirely. Bound such fetches
  by time, or fetch `time desc` and reverse as get_unresolved_stale_in does.
NEXT: Nabil asked whether we even have a biometric device — the honest answer is that the code exposes
  the stock ERPNext ingestion endpoint (employee_checkin.py:143 add_log_based_on_employee_field, and it
  IS @frappe.whitelist()), nothing in this app calls it, and the bench proves nothing (12 rows, all
  Administrator). The production query is in the reply. If no device is in use, A2 shrinks to HR's Desk
  manual entry and drops below the OT wave. Start B1: the +/-1 day punch fetch window
  (ot_calculation.py:372-373) that makes four OT entry points disagree by 33 hours on one date.
- 2026-09-13T17:11:04Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T17:11:07Z COMMIT: cbb1295ff fix(checkin): the duplicate guard went blind past two hundred punches → review dispatched
- 2026-09-13 REPAIR: the two-day forward window I put in place of the row limit was the SAME defect on
  a new axis, and review proved it reachable. `next_in` cannot justify a forward bound because it
  searches for ARRIVALS while the row this guard must see is a DEPARTURE — nothing requires an arrival
  between them. A Friday-to-Monday weekend reaches it; so does the production double-tap whose close
  lands days later, and the banner OFFERS exactly those rows. The feature's own horizons disagree
  anyway (pairing looks back 14 days at employee_checkin_override.py:262, the stale-IN banner 10 at
  remote_checkin.py:573), so any number here was arbitrary. The bound is gone; `limit_page_length=0`
  stays. The `# ceiling:` marker went with it — removing a shortcut beats justifying it.
- 2026-09-13 LEARNING(gate): a test of the PURE rule stays green through BOTH versions of a
  fetch-window defect, because the rule was never wrong — what it got to SEE was. Two narrowings
  shipped that way. hrms/api/test_remote_checkin.py now reads the committed fetch out of the source and
  refuses any forward bound or row limit on it. Proven red by reintroducing the two-day window.
- 2026-09-13 TICKET: an invariant limited to "never two consecutive OUTs" does not notice a spurious
  extra SESSION manufactured between two stray INs — IN 09:00, IN 09:18, IN 10:00, OUT 18:00 with a
  filing at 09:30 is accepted, and attendance then pairs 09:00->09:30 and 10:00->18:00 instead of one
  session. NOT introduced by any of today's commits (the old global scan accepted it too). Decide on
  the session_state hotspot ticket whether the rule should also refuse to orphan a later departure's
  arrival.
- 2026-09-13T17:18:55Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
