2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
  session. CORRECTED after measurement: this WAS introduced by today's stack, at 9c6f41fa7, and is
  unpushed. Measured through the real function at five revisions — origin/nz-glass (DEPLOYED) REFUSES
  it, 96228853f REFUSES it, and 9c6f41fa7 / cbb1295ff / HEAD all ACCEPT it. The earlier note here said
  "not introduced by any of today's commits" because the old GLOBAL scan also found no adjacent OUT
  pair; that is true and irrelevant — the deployed code refuses the shape for a different reason.
  It is the deliberate price of freeing the buried repair: the same change also, on purpose, allows a
  far-out buried repair and a far-out rejected OUT that the deployed code refuses. THIS IS A TRADE TO
  PUT TO NABIL BEFORE THE PUSH, not an inherited limitation to shrug at.
- 2026-09-13T17:18:55Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T17:18:59Z COMMIT: 4015d50d1 fix(checkin): the forward window was the same failure on a different axis → review dispatched
- 2026-09-13 DEAD END: **B1 IS NOT REPRODUCIBLE AS STATED — do not build it.** The OT audit's headline
  finding was that the +/-1 day punch fetch makes four entry points disagree by 33 hours on one date.
  Measured on fresh.local through the real functions (verify-bench/sites/probe_ot_window.py,
  savepointed): on an ORDINARY overtime day (IN 10:00, OUT 22:00, four hours past an 18:00 shift end)
  get_ot_claim_capacity, get_day_ot_breakdown, get_ot_breakdown(month) and get_shift_ot_breakdown ALL
  RETURN 4.0. They agree. And on the long session the finding rests on (IN 3 Sep 09:00, OUT 5 Sep
  03:00) every path returns 0.0 or no entry — but NOT because of the window: the closing punch is
  stamped shift=None, offshift=1, because an OUT two days later falls inside no shift window, so the
  session never PAIRS anywhere. There is nothing to disagree about.
- 2026-09-13 REPAIR(audit): corrected O1 in .claude/plans/audit-2026-09-13-ot.md in place, with the
  measurement, rather than leaving a refuted number on the board to be quoted. The original text is
  struck through beneath it so nobody re-derives it.
- 2026-09-13 EVIDENCE(2): what IS real on that shape is the SILENT ZERO — 33 worked hours reported as
  0.0 on every surface with no cause named, exactly O3/S8. That is the OT defect worth fixing, and the
  probe above is its red.
NEXT: OT wave re-ordered on evidence. B1 is struck. Take B2 first (hrms/hr/doctype/shift_type/
  shift_type.py:275 guards only start_time and only while punches are UNLINKED, so editing a shift's
  end_time re-prices closed months and moves an already-APPROVED claim's punch_ot_hours — measured
  3.0 -> 6.0 -> 4.0 through the real document API), then B3 (make the silent zeros legible: 15 sites,
  one message, no cause ever named), then B4 (a missing holiday list prices a public holiday as a
  normal day, silent underpay).
- 2026-09-13T17:23:07Z COMMIT: 0280a495a docs(plans): the headline overtime finding does not reproduce → review dispatched
- 2026-09-13T17:26:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T17:26:59Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 5 extra test file(s) ⟂7ec4f73e96a2
- 2026-09-13T17:27:37Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T17:27:37Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 5 extra test file(s) ⟂7ec4f73e96a2
- 2026-09-13T17:27:38Z EVIDENCE: 6 behaves — family hunt: class=a FILING-time authorisation rule evaluated on EVERY save, so it also; 2 call site(s) given verdicts, 16 same-root ⟂9cfe6fa24e18
- 2026-09-13T17:27:40Z COMMIT: 79511b581 fix(overtime): a closed month must not be re-priced by an edit made today → review dispatched
- 2026-09-13 EVIDENCE(3): B3 done. Fifteen situations ended in "no overtime" and all fifteen said the
  same sentence, which states a conclusion and hides the cause — and only one of the fifteen is the
  employee's own to answer. `_explain_no_overtime` now asks the punches why and says so: no check-ins ·
  punches attached to no shift (ask HR) · overtime not enabled on the shift, named · off-shift ·
  skip-attendance · awaiting approval · no check-out · no check-in. It returns "" when the punches look
  fine and the hours really are zero, because inventing a cause there is worse than silence. Surfaced
  in the PWA hint and appended to the save-time refusal. Seven bench-free cases.
- 2026-09-13 LEARNING(fact): hrms/api/__init__.py's OT summary functions are AST-EXTRACTED by
  test_ot_claim_monthly_capacity.py and test_ot_nonworking_hours.py — only the named FunctionDefs are
  exec'd, so a new module-level helper is invisible to them and raises NameError. Nest the helper, or
  add it to the extraction list.
- 2026-09-13 LEARNING(fact): frappe.bold is a MagicMock under the bench-free stub, so any assertion on
  a message built with it cannot see the content. These sentences are shown in the PWA as TEXT anyway,
  where markup would appear literally — plain strings are both more testable and more correct.
NEXT: B4 — a missing holiday list prices a public holiday as a normal day (ot_calculation.py:300-302
  returns "normal" with a logger.warning only), so 4 Sep 2026 was measured at 1.5x instead of 3.0x.
  Silent UNDERPAY, config-dependent. Then the leak wave: C1 employee_issue_row_scope.py:106 fails OPEN
  (three characters of intent — the canonical _own_employees() is 80 lines above it), C2 the hub-wide
  recovery endpoint whose own test is already red, C3 ot_row_scope's status-and-company-free reports,
  C4 the leave-allocation pointer with no existence guard. Then the two ruling items: stop managers
  cancelling a settled decision (approval.py:413-414), and the four-month filing window.
- 2026-09-13T17:33:51Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-13T17:33:51Z EVIDENCE: 3 works — blast radius green: 11 dependent(s), 7 extra test file(s) ⟂f36332fee993
- 2026-09-13T17:33:58Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-13T17:33:58Z EVIDENCE: 3 works — blast radius green: 11 dependent(s), 7 extra test file(s) ⟂f36332fee993
- 2026-09-13T17:34:03Z COMMIT: 616d6b119 fix(overtime): a closed month must not be re-priced by an edit made today → review+design dispatched
- 2026-09-13T17:34:31Z COMMIT: 63a473ef9 fix(overtime): a zero that names no cause is not an answer → review+design dispatched
- 2026-09-13 REPAIR: B2 fixed ONE of the two pricing paths, and one fixed is worse than none — review
  caught it. get_shift_ot_breakdown's own field list did not fetch `shift_end`, so every session IT
  built fell back to the live Shift Type. That is the path Attendance.set_overtime uses to WRITE the
  stored ot_hours, and hrms/patches/v16_0/backfill_ot_after_rounding_rule.after_migrate re-runs it
  across historical Attendance on EVERY DEPLOY — armed on a timer, no HR or user action needed. And the
  losing direction does not misprice visibly, it HIDES the day: api/__init__.py gates the claimable
  card on ot_hours > 0. Measured with the column absent: end 18:00->15:00 gave claim 4.0 / attendance
  7.0; end 18:00->22:00 gave claim 4.0 / attendance 0.0. Both directions hold at 4.0 now on both paths.
- 2026-09-13 REPAIR: the no-punch fallback session set `shift_end` to the CONFIGURED end, contradicting
  the invariant recorded hours earlier. Right number by accident only, and anything reading that key as
  the grace value it is named for would understate OT by the whole grace window. Both keys now hold
  what their names say.
- 2026-09-13 LEARNING(gate): a missing COLUMN in a caller's field list is invisible to any test of the
  rule -> hrms/tests/test_ot_calculation_rules.py now asserts both punch-reading paths fetch
  `shift_end`, read off the committed source. Proven red by removing it.
- 2026-09-13 LEARNING(fact): a commit message written with `cat > $GD/MSG` inside a command that the
  PreToolUse gate BLOCKS never runs, so the next `git commit -F` silently reuses the PREVIOUS message.
  616d6b119 landed with B2's message on B3's content and had to be amended. Write the message file in
  its own command, then commit in the next.
- 2026-09-13T17:36:38Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T17:36:38Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 5 extra test file(s) ⟂7ec4f73e96a2
- 2026-09-13T17:36:41Z COMMIT: 45656e87d fix(overtime): fixing one pricing path and not the other was worse than neither → review dispatched
- 2026-09-13 REPAIR: two more holes of the same shape, both found by review AFTER the ledger had
  written "LOCK THE CLASS" — which is exactly why that phrase is dangerous. (a) the START was taking
  only the DATE off the punch and re-deriving the time of day from the live Shift Type, so moving a
  shift's start 10:00 -> 07:00 dropped a settled day from 4.0h to 1.0h — and CROSS-PATH AGREEMENT
  CANNOT SEE IT, because both pricing paths agree on the wrong number. Carried now as
  `configured_start`, from `shift_start` only and never the early-arrival-extended
  `shift_actual_start`. (b) a PUNCHLESS day has no snapshot at all, so recomputing it necessarily uses
  live config — and recompute_ot_backfill runs on EVERY deploy, so it rewrote every manually entered
  settled day whenever anybody edited a shift, writing a ZERO in the losing direction which removes the
  day from the claimable card. It now leaves punchless days alone.
- 2026-09-13 EVIDENCE(3): measured on fresh.local with the punches LINKED to an Attendance row — the
  only state in which shift_type's start_time guard stands down, and therefore the only state where the
  defect is reachable. All four edits hold at 4.0 on both paths; without configured_start the
  start 10:00->07:00 case is RED at 1.0 on both.
- 2026-09-13 LEARNING(gate): a source-text guard built from str.index + regex counts quoted words
  inside COMMENTS, and this work had planted a ten-line comment inside the very span it matched — so
  deleting the column and leaving `# TODO: fetch "shift_end" here one day` made it pass with the defect
  live. Parsed with `ast` now (FunctionDef -> get_all -> fields keyword -> Constant elements).
  Mutation-checked both ways.
- 2026-09-13 LEARNING(fact): shift_type.py's start_time guard fires only while check-ins are UNLINKED,
  so a probe whose punches are not linked to an Attendance row CANNOT reach the defect — it gets
  "Mark attendance for existing check-in/out logs" instead. Link the punches first.
NEXT: B4 — a missing holiday list prices a public holiday as a normal day (ot_calculation.py:300-302
  returns "normal" with a logger.warning only): silent UNDERPAY, 1.5x instead of 3.0x. Then C1
  employee_issue_row_scope.py:106 fails OPEN, C2 the hub-wide recovery endpoint, C3 ot_row_scope,
  C4 the leave-allocation pointer. Then the two rulings: stop managers cancelling a settled decision,
  and the four-month filing window.
- 2026-09-13T17:46:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T17:46:59Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 9 extra test file(s) ⟂8fecdc10bd87
