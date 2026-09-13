2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-13T18:13:51Z COMMIT: fa8565990 fix(approval): being the approver is not permission to undo an approval → review dispatched
- 2026-09-13T18:14:32Z COMMIT: f2e8dd05f feat(overtime): backdated filing reaches four months instead of two → review dispatched
- 2026-09-13 DEAD END (twice now, same trap): a commit message written with `cat > $GD/MSG` inside a
  command that a PreToolUse gate BLOCKS never runs, so the following `git commit -F` silently reuses
  the PREVIOUS message. 616d6b119 and fa8565990 both landed with the wrong subject and had to be
  amended. ALWAYS write the message file in its own command, then commit in the next.
NEXT: every defect on the ranked plan is CLOSED. What remains is the report project (26 Script Reports
  with no company fence + 4 that read past one), the tickets filed today (C-routing, C-mayread,
  C-roster, C-appraisal, C-ctc, C-1on1, C-fence, the session_state refactor, the two permanently-red
  timezone tests, the spurious-extra-session invariant, KPI route state DSN-16, the provenance Recover
  button), and Nabil's three production questions (is a biometric device in use; is HR Settings
  allow_multiple_shift_assignments on; did the OT precision patches ever run on Verifica). Historical
  data repair still needs his explicit word for that exact change. NOTHING IS PUSHED.
- 2026-09-13T18:15:25Z COMMIT: 7472b03ef docs(plans): every defect on the ranked plan is closed → review dispatched
- 2026-09-13 RULING (Nabil): **THE SCRIPT REPORT PROJECT IS DEFERRED. DO NOT OPEN IT.** That covers all
  three steps proposed today — the role patch stripping Accounts User / Projects User / Manufacturing
  User / Expense Approver / Leave Approver / System Manager off the pay reports, the company guard on
  frappe.desk.query_report.run, and the per-report self-scoping. No commits, no patches, no probes
  against it until he says otherwise, in those words.
  The exposure is recorded and understood: those roles can read gross pay, employer contributions,
  whole-company leave balances and full CTC today, and 26 of 32 Script Reports accept any company typed
  into the filter. It is written down in .claude/plans/audit-2026-09-13-approver.md. Leaving it open is
  HIS CALL, made with the facts in front of him — not an oversight for a later session to "helpfully"
  correct.
  The two policy questions that would gate the work if it resumes: should Accounts see gross pay (they
  may have a legitimate cost-allocation reason), and should a Leave Approver see whole-company balances
  or only their team.
NEXT: nothing is queued. Every defect on the ranked plan is closed and committed; the reports project
  is DEFERRED by ruling; historical data repair still needs Nabil's explicit word for that exact
  change. 50 commits sit unpushed on nz-glass ahead of the live build a741f3e. Do not push, deploy or
  repair anything without him saying so.
- 2026-09-13T18:21:43Z COMMIT: ffcfcc52b docs(plans): the reports project is deferred, by decision not by oversight → review dispatched
- 2026-09-13 REPAIR: acted on the ruling review's four spec warnings. (a) test_ot_discovery_window still
  hardcoded the fence — the exact rot its sibling had just been fixed for — so it DERIVES it now; that
  file's question ("discovery offers exactly what filing accepts, never wider") is policy-independent
  and must not need editing when the policy moves. (b) the comment in approval.py claimed the else is
  "reachable only on a CANCEL": finalize is whitelisted with no doctype allow-list, so a submit of any
  other submittable doctype lands there too, which is why the "not routed to you" refusal is still live
  and must not be deleted as dead. (c) the backfill patch's docstring still quoted "repair last 2
  months" while its code now follows the four-cycle filing window. (d) the empty-range early return
  omitted keys the calling patch reads and would have raised KeyError inside after_migrate.
- 2026-09-13 **DEPLOY RISK, READ BEFORE PUSHING**: widening the filing window silently re-scoped the
  deploy-time OT repair from at most 92 days to at most 153, and it runs on EVERY deploy via
  hooks.py after_migrate. _repair_financial_dependency is per-day rather than per-range so it is no
  weaker across the wider window — but under the parallel-run setup a month settled on the SOURCE
  instance may have no Salary Slip HERE to protect it. Dry-run the newly reachable slice first:
    bench --site <site> execute hrms.hr.doctype.attendance.attendance.recompute_ot_backfill \
      --kwargs "{'from_date':'2026-04-16','to_date':'2026-06-15','dry_run':1}"
  Read `changed` against `locked`. If changed > locked, settle it with Nabil BEFORE deploying.
  Recorded in the patch docstring too, where whoever deploys will meet it.
- 2026-09-13 OPEN DECISION for Nabil (the cancel ruling is narrower than it reads): it is a NO-OP on
  Leave Application, Expense Claim and Shift Request. patches/v15_106_3/allow_staff_cancel_own_requests
  grants Employee/ESS the cancel flag on those three, and employee_master auto-grants the Leave/Expense
  Approver roles which carry cancel — so the routed approver passes the framework check anyway. The
  ruling bites only on OT Request, Attendance Request and Replacement Leave Claim. Either "an approved
  request is never cancelled" means those roles lose cancel on approved rows (a DocPerm + patch change),
  or it means "routing is not a cancel right", which is what shipped. HIS CALL.
- 2026-09-13 OPEN DECISION for Nabil (a consequence of the four-month window): ot_request's
  validate_duplicate_request checks only for another OT REQUEST on the same employee+date — nothing
  consults Overtime Details, Overtime Slip or a submitted Salary Slip. At two cycles the reachable
  window stayed near the open payroll cycle; at four it reaches five calendar months, into closed and
  PAID periods. So an employee can file for an April day whose overtime was already paid without an OT
  Request on record, and the only thing between that and a second payout is an approver recognising a
  five-month-old date. Either accept it explicitly (every OT Request is human-approved) or add an
  already-paid check. HIS CALL.
- 2026-09-13 LEARNING(fact): the live cancel matrix is NOT what the doctype JSON says.
  patches/v15_106_3/allow_staff_cancel_own_requests grants cancel to Employee/ESS on Leave Application,
  Expense Claim and Shift Request via update_permission_property, and employee_master's
  update_approver_user_roles auto-grants the Leave/Expense Approver roles. Any permission analysis on
  those three must read the patch and that hook as well as the JSON.
- 2026-09-13T18:26:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-13T18:26:53Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 5 extra test file(s) ⟂2da7a836b075
