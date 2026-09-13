2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-13T17:47:08Z COMMIT: f3e647b9c fix(overtime): the shift's start moves a settled day too, and both paths agree wrongly → review dispatched
- 2026-09-13 EVIDENCE(2): B4 done. With no applicable holiday list a date cannot be told from an
  ordinary weekday, so it is priced as one — 1.5x where a public holiday pays 3.0x. That default is
  right (nobody is overpaid, and refusing to price the day would cost the employee their ordinary pay
  too); what was wrong is that it was SILENT. The only trace was a logger line, which is read neither
  by the person whose holiday pay just halved nor by the HR user who could fix the config in a minute.
  It goes to the Error Log now, naming the date, the employee, the shift and the three places a
  covering list can be attached. Proven RED by restoring the logger-only line.
NEXT: the leak wave. C1 hrms/overrides/employee_issue_row_scope.py:106 fails OPEN — has_permission does
  a raw get_value("user_id") == user while the file's OWN canonical _own_employees() sits at line 28, so
  an offboarded login or either of two duplicate claimants reads HR tickets, including another person's.
  Smallest fix in the whole plan. Then C2 the hub-wide recover_overwritten_checkins (its guard test is
  ALREADY RED), C3 ot_row_scope's status-and-company-free reports query, C4 hr/utils.py:774's bare
  get_doc on a Leave Allocation with no existence or docstatus guard.
- 2026-09-13T17:48:52Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T17:48:52Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 5 extra test file(s) ⟂7ec4f73e96a2
- 2026-09-13T17:48:58Z COMMIT: 8dce0426a fix(overtime): a halved holiday rate should not be invisible → review dispatched
- 2026-09-13 EVIDENCE(2): C1 done, and it was the smallest fix in the whole plan.
  employee_issue_row_scope.has_permission compared a raw user_id while the LIST query twelve lines
  above resolved through the file's OWN canonical _own_employees (line 28). It FAILS OPEN both ways
  that resolver exists to close: an offboarded login keeps reading its old tickets after the list has
  stopped showing them, and where two Active Employees claim one login — which the resolver refuses
  outright — the raw compare says yes to BOTH people's rows. Employee Issue carries grievances and
  disciplinary records. Two AST cases pin the SHAPE (must call _own_employees; must never read
  "user_id"), proven red by restoring the compare.
- 2026-09-13 DEAD END: the family gate's machine list for this commit is 40 unrelated
  `frappe.has_permission(...)` call sites — it matches the SYMBOL NAME, and this hook is called
  has_permission, the same name as the framework function every app calls constantly. None of them
  call this hook; the framework calls it. Committed with PIPELINE_SKIP_FAMILY=1 rather than writing
  forty untrue verdict lines, with the reason recorded in family.md and the REAL family captured as
  four tickets (appraisal.py:887 seed, employee_one_on_one.py:19, employee_ctc_break_up.py:359,
  company_fence.py:237).
- 2026-09-13 LEARNING(fact): appending a test class to a file that already ends with
  `if __name__ == "__main__": unittest.main()` defines the class AFTER main() has run, so it never
  executes and the suite reports the old count as OK. Insert above the guard.
NEXT: C2 — recover_overwritten_checkins is hub-wide and validation-free (frappe.only_for("System
  Manager") only, no company fence), and hrms/tests/test_sync_endpoints_are_fenced.py is ALREADY RED on
  it. Call hrms.overrides.company_scope.require_unfenced. Then C3 ot_row_scope's reports query (no
  status, no company), C4 hr/utils.py:774's bare get_doc on a Leave Allocation. Then the two rulings.
- 2026-09-13 EVIDENCE(2): C2 done. recover_overwritten_checkins was role-checked only while collect()
  deliberately applies no company filter, so a company-fenced HR user could have written punches for
  every company on the hub — with ignore_permissions AND ignore_validate, so no geofence, no
  duplicate-time check and no approval routing between the insert and payroll. It calls
  require_unfenced now. NO NEW TEST WAS NEEDED: hrms/tests/test_sync_endpoints_are_fenced.py already
  encoded the invariant, already named this endpoint and the remedy in its assertion message, and was
  RED on HEAD at the start of this session. The gate existed and was being ignored.
NEXT: C3 — hrms/overrides/ot_row_scope.py:38 `_reporting_employees` queries reports with no status and
  no company filter (the file contains the word "company" zero times), so a manager sees the OT and
  replacement-leave rows of INACTIVE and CROSS-COMPANY reports. hr/utils.py:1108 get_direct_report_employees
  is the canonical answer and is Active-only and fenced. Then C4 hr/utils.py:774's bare
  get_doc("Leave Allocation") with no existence or docstatus guard — a cancel after the allocation was
  cancelled or re-pulled by sync either throws DoesNotExistError or writes onto a cancelled document.
  Then the two rulings: approval.py:413-414 must stop elevating CANCEL on routing alone, and the
  filing window widens to four months while keeping its 16th-to-15th cycle shape.
- 2026-09-13T17:52:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T17:52:29Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-13T17:52:32Z COMMIT: 958152380 fix(sync): a role is not a fence, and the test said so already → review dispatched
- 2026-09-13 REPAIR: the punchless-day guard asked the WRONG QUESTION and review caught it. I tested
  the `Employee Checkin.attendance` link; the pricer finds punches by employee + shift + time window
  and never by that link. A day can hold punches with no link at all — mark_attendance_and_link_log
  leaves them unlinked ON PURPOSE on an overlapping-shift error, and the bulk tool never writes one.
  Those days have a full snapshot, so skipping them STRANDED their overtime at zero, which hides them
  from the claimable card entirely. Silent underpay, and the version before mine repaired them.
  `get_shift_ot_breakdown` now reports `priced_from_punches` and the repair asks that — one source of
  truth. Measured on fresh.local: punches present but UNLINKED -> scanned 2, changed 1 (repaired);
  no punches at all -> changed 0 (left alone).
- 2026-09-13 REPAIR: `if not names: return` before the link probe. Frappe rewrites `["in", []]` into
  `IN ("")` rather than raising, so an empty list matched every row with a NULL or blank column and,
  with no page limit, pulled the whole table — on every deploy.
- 2026-09-13 LEARNING(gate): an ast source guard storing ONE field set per function is last-write-wins
  — adding any later get_all that happens to name the columns masks the punch query having lost one,
  exactly as a comment defeated the regex version. It now matches on the DOCTYPE argument, keeps EVERY
  matching call, and expands a starred module constant so a legitimate `fields=[*_COLUMNS, "time"]`
  refactor is not reported as the bug. Both mutations measured.
- 2026-09-13T17:58:58Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T17:58:58Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 9 extra test file(s) ⟂8fecdc10bd87
- 2026-09-13T17:59:02Z COMMIT: aa747dae3 fix(overtime): ask the pricer whether it used punches, not the attendance link → review dispatched
- 2026-09-13 EVIDENCE(3): C-provenance done. Review found — and proved live — that fencing the recovery
  ENDPOINT left the READ door beside it wide open: the Checkin Provenance Audit report reaches the same
  hub-wide `collect()` with no fence of its own, and its role list includes HR Manager. frappe.get_all
  bypasses User Permissions as well as DocPerms, so a correct-looking role list on a report is not a row
  fence. Measured on fresh.local: a user restricted to one company saw 12 of 12 punches before the fix
  and 10 of 12 after (an earlier richer fixture showed 14 rows across THREE companies). Fenced at the
  COLLECTOR so both surfaces close in one place, applied on the TRUE employee after classification —
  an overwritten punch carries somebody else's name in the column, so an SQL filter would hide the very
  rows the function exists to surface.
- 2026-09-13 LEARNING(fact): `frappe.get_all` bypasses User Permissions AND DocPerms, so any Script
  Report calling a hub-wide collector through it leaks cross-company rows even when the Report's own
  `roles` list looks correctly scoped.
- 2026-09-13 TICKET: checkin_provenance_audit.js still renders the "Recover" button for a company-fenced
  user, who now sees the right rows but meets a PermissionError on pressing it. Cosmetic; the refusal
  is correct.
NEXT: C3 — hrms/overrides/ot_row_scope.py:38 `_reporting_employees` queries reports with no status and
  no company filter (the file contains "company" zero times), so a manager sees OT and replacement-leave
  rows of INACTIVE and CROSS-COMPANY reports. hr/utils.py:1095 get_direct_report_employees is the
  canonical answer and is Active-only and company-fenced. Then C4 hr/utils.py:774. Then the two rulings.
- 2026-09-13T18:04:47Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-13T18:04:47Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-13T18:04:51Z COMMIT: 2e5df9c9b fix(sync): closing the write door left the read door beside it open → review dispatched
- 2026-09-13 EVIDENCE(2): C3 done. ot_row_scope._reporting_employees was the SEVENTH derivation of "who
  reports to me", and it proved the canonical helper's own docstring right — "duplicating it would let
  the fences drift apart". It asked `reports_to in (mine)` with no status filter and no company
  predicate (the word "company" did not appear in the file), so a manager saw the OT and
  replacement-leave rows of people who had LEFT and of people in a company they cannot otherwise reach.
  Delegates to get_direct_report_employees now. Two AST cases, proven red by restoring the local query.
- 2026-09-13 TICKETS from the same family, each its own slice because each changes what a different
  group can do: C-routing (approval.py:85 resolves the caller canonically but reads the SUBORDINATE
  with no status or company filter, so an inactive employee's request still routes for elevated
  submit — it governs who may ACT, not who may see); C-mayread (api/__init__.py:320, same raw shape);
  C-roster (roster.py:54 has no status filter but IS company fenced, while team.py:158 deliberately
  does NOT fence a manager's own team — two OPPOSITE company rules, each in a comment claiming to be
  right, so the ticket is to DECIDE which); C-appraisal (appraisal.py:939, transitive and unfenced).
NEXT: C4 — hrms/hr/utils.py:774 reverse_replacement_leave does a bare
  frappe.get_doc("Leave Allocation", allocation_name) with no existence and no docstatus guard, so a
  cancel after the allocation was itself cancelled or re-pulled by sync either throws
  DoesNotExistError mid-transaction or writes a negative ledger entry onto a cancelled document.
  Then the two rulings: approval.py:413-414 must stop elevating CANCEL on routing alone (an approved
  request is never cancelled), and the filing window widens to four months keeping its 16th-to-15th
  cycle shape.
- 2026-09-13T18:07:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T18:07:05Z COMMIT: bdcb02fcb fix(hr): a manager's team was re-derived here, and the fences drifted → review dispatched
- 2026-09-13 EVIDENCE(2): C4 done. reverse_replacement_leave fetched the Leave Allocation with a bare
  get_doc while running INSIDE A CANCEL, so an allocation that HR had cancelled or that the sync had
  re-pulled under a new name froze the employee's own withdrawal with DoesNotExistError. And a
  CANCELLED allocation is worse than a missing one — decrementing it writes a negative ledger entry
  onto a document no longer in force. Existence and docstatus are both checked now; it returns cleanly
  and records the skip in the Error Log rather than throwing, because the person's cancellation
  succeeded and the allocation's fate is not theirs to fix. Four AST cases (the module cannot be
  imported without a bench — pypika), proven red by restoring the bare get_doc.
NEXT: the two rulings, both from Nabil in this session. (1) "an approved request is never cancelled" —
  hrms/api/approval.py:413-414 elevates CANCEL on routing alone (`elif _is_routed_approver(doc):
  doc.flags.ignore_permissions = True`), with only _request_read_allowed ahead of it, and the guard at
  :400 means the else branch is reachable ONLY on cancel. Close it. (2) the filing window widens to
  four months from the present day while KEEPING its 16th-to-15th cycle shape, and covers OT Request
  and expense-shaped requests alongside it — hrms/utils/filing_window.py currently implements two
  cycles.
- 2026-09-13T18:08:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-13T18:08:50Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 12 extra test file(s) ⟂ca1c1f300426
- 2026-09-13T18:08:53Z COMMIT: d2f9602b3 fix(hr): withdrawing a request must not freeze on an allocation that moved on → review dispatched
- 2026-09-13 EVIDENCE(2): RULING 1 implemented. "An approved request is never cancelled" — Nabil, this
  session. approval.py::finalize's else branch is reachable ONLY on a cancel (the first branch catches
  every submit of a decide-then-submit doctype, and every request doctype is in that set), and it
  elevated on ROUTING alone with only _request_read_allowed ahead of it — so a settled approval could
  be withdrawn with the framework's own cancel right bypassed. The elevation is gone; cancelling needs
  the cancel right. The refusal also names cancellation instead of saying "not routed to you for
  approval", which sent the reader looking for the wrong thing. Three AST cases, including one pinning
  that `decide` STILL elevates — so a future narrowing of cancellation cannot quietly take approval
  away. Proven red by restoring the elevation.
NEXT: RULING 2 — the filing window widens to FOUR MONTHS from the present day while KEEPING its
  16th-to-15th cycle shape, covering OT Request and expense-shaped requests alongside it.
  hrms/utils/filing_window.py currently implements two cycles. Read it, widen it, and check every
  caller: filing, discovery and validation all consult it and must move together.
- 2026-09-13T18:10:49Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T18:10:49Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-13T18:10:52Z COMMIT: 9fbd5085f fix(approval): being the approver is not permission to undo an approval → review dispatched
- 2026-09-13 EVIDENCE(2): RULING 2 implemented. Backdated OT filing widens from two cycles to FOUR
  (Nabil, this session: "4 month before the current date", and separately "still 16th to 15th" — so the
  cycle shape is untouched and only the depth changes). hrms/utils/filing_window.py BACKDATE_CYCLES
  2 -> 4. Anchoring to the 16th means four cycles back from the CURRENT cycle's start reaches a little
  beyond four calendar months for most of a cycle; that is the anchoring the module was built around,
  not a rounding error, and it errs towards letting somebody file.
- 2026-09-13 EVIDENCE(3): every consumer moves together because they all read the same function —
  filing (ot_request.validate_filing_window), discovery (api/__init__.py:636) and the deploy-time
  backfill (backfill_ot_after_rounding_rule:63) all call earliest_filable_date. Verified by grep; no
  second copy of the rule exists.
- 2026-09-13 SCOPE NOTE on ruling 2: it names "OT request and related requests like expenses". Expense
  Claim enforces NO filing window at all — there is nothing to widen there, and nothing was invented.
  Recorded so the next reader does not go looking for the expense half of this change.
- 2026-09-13 LEARNING(gate): test_ot_filing_edits.py hardcoded CUTOFF as a literal date, so a policy
  change broke a test that was only ever meant to say "an edit gets the same window as a new filing" —
  true whatever the window is. It DERIVES the cutoff from the module now (loaded by path, because
  importing through the package pulls hrms/__init__.py and needs a bench), so the next policy change
  moves the fence and the test keeps asking its own question.
- 2026-09-13T18:13:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T18:13:48Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 2 extra test file(s) ⟂a5801cfef452
