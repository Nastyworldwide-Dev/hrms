# FAMILY — "You can only file requests for yourself." on an APPROVAL

CLASS: a FILING-time authorisation rule evaluated on EVERY save, so it also
judges approval saves — on doctypes where approval IS a save, because they
carry no approver field. The guard's exemption list (HR / self / Employee
writer) has never heard of the reporting manager, whom this app's own row
scope names "the natural approver". Two fences, disagreeing, and the narrower
one won.

ROOT CAUSE: hrms/hr/utils.py::validate_filing_for_self — no is_new /
employee-changed test. Fixed there, once, for every caller.

## validate_filing_for_self — the defective guard

hrms/hr/doctype/ot_request/ot_request.py:97 — same-root (fixed here)
  The reported symptom, HR-OTR-26-09-00009. Status Open/Approved/Rejected,
  no approver field, so approving is a save and the approver was refused.
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:38 — same-root (fixed here)
  Identical shape: Open/Approved/Rejected, no approver field, submittable.
  Its approvers hit the identical refusal; nobody had reported it yet.
hrms/hr/doctype/employee_issue/employee_issue.py:21 — same-root by construction
  (same function), NO REACHABLE INSTANCE. Corrected after review: the earlier
  wording claimed approvers were refused here, which is not reproducible.
  employee_issue_row_scope.has_permission denies every non-read ptype to
  non-HR users (READ_PTYPES, employee_issue_row_scope.py:78), and HR is exempt
  from the filing guard — so the guard's non-filing branch was dead code on
  this doctype. Probed with the guard instrumented: neither the reporting
  manager nor the subject employee ever reaches it (reached=[]); both get a
  PermissionError from the row scope first.
hrms/hr/utils.py:1060 — same-root (the fix itself)
  The new `_is_filing` gate, called once at the top of the guard.

## validate_self_submission — NOT the same class

Different question, different trigger: it fires only when the SUBMITTER IS
the employee named on the request, to stop self-approval. An approver is by
definition not that employee, so it never fires on the reported path and
cannot produce the reported message. Verified by reading each site; none
reference the filing rule or its exemption list.

hrms/hr/doctype/ot_request/ot_request.py:216 — not-affected — fires only when
  submitter == doc.employee; an approver is never the employee on the row.
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:94 — not-affected — same rule, same reason.
hrms/hr/doctype/shift_request/shift_request.py:51 — not-affected — same rule,
  and Shift Request additionally HAS an approver field, so its routing already
  names who may act; it never called the filing guard at all.

## LOCK THE CLASS

- Regression test for the instance AND the class:
  hrms/tests/test_filing_guard_is_filing_only.py — bench-free, 7 cases,
  proven RED on HEAD at the exact production message.
- Real-save evidence: verify-bench/sites/probe_ot_approval.py — 7/7, savepoint
  rolled back; RED on HEAD ("APPROVER REFUSED: You can only file requests for
  yourself."), GREEN after.
- The invariant pinned: authority over an EXISTING row is the row scope's
  question (ot_row_scope / employee_issue_row_scope). This guard may only ask
  who chose the subject, and only while the subject is being chosen.

---

# FAMILY — a punch's IN/OUT type taken on trust from the client

CLASS: `log_type` was decided by the browser and stored unverified, so a UI
race or a stale cache could write an IN where the person meant an OUT. Nothing
downstream ever re-checked that punches alternate, so one wrong type became
zero working hours, a Half Day, a day split across two shifts, and a late
check-out that could never be filed.

ROOT CAUSE: `hrms/api/remote_checkin.py::punch` accepted `log_type` after
checking only that it was one of ("IN","OUT"). Fixed by `resolve_punch_type`,
which the server applies before the row is built.
TRIGGER (removed too): `frontend/src/components/CheckInPanel.vue` recomputed
the action while the confirm sheet was open, and resolved to "IN" whenever the
log was mid-reload.

## same-root — fixed in this commit
hrms/api/remote_checkin.py:punch — resolves the type server-side.
frontend/src/components/CheckInPanel.vue:onModalPresent — the sheet commits to
  one action and holds it until dismissal.

## the machine's list — every one is a COMMENT or a LOG STRING, not a caller
The scan matches the words "punch"/"reject" in prose. None of these reference
`punch`, `resolve_punch_type` or `_session_is_live`; all verified by opening
the line.

frontend/src/composables/index.js:18 — not-affected — a comment about promise rejection.
frontend/src/composables/index.js:33 — not-affected — `reject(error)` of a JS Promise.
hrms/hr/doctype/vehicle_log/vehicle_log.js:44 — not-affected — Promise reject, unrelated doctype.
hrms/hr/doctype/vehicle_log/vehicle_log.js:50 — not-affected — same.
hrms/hr/doctype/employee_checkin/employee_checkin.py:333 — not-affected — docstring prose.
hrms/hr/doctype/employee_checkin/employee_checkin.py:735 — not-affected — a logger format string.
hrms/hr/doctype/employee_checkin/employee_checkin.py:769 — not-affected — a logger format string.
hrms/hr/doctype/shift_type/shift_type.py:431 — not-affected — a logger format string.
hrms/overrides/employee_checkin_override.py:143 — not-affected — docstring prose.
hrms/hr/report/attendance_day_audit/attendance_day_audit.js:102 — not-affected — a toast string.
hrms/utils/attendance_day_audit.py:114 — not-affected — a verdict message.
hrms/utils/attendance_day_audit.py:171 — not-affected — a verdict message.
hrms/utils/attendance_day_audit.py:195 — not-affected — a verdict message.
hrms/utils/attendance_day_audit.py:230 — not-affected — a verdict message.
hrms/utils/attendance_day_audit.py:620 — not-affected — a logger format string.
hrms/utils/attendance_day_audit.py:626 — not-affected — a logger format string.

hrms/utils/attendance_day_audit.py:192 — not-affected AS A CALLER. CORRECTED
  after review: I claimed this report was the existing DETECTOR for every day
  this defect produced. It is not, and the repair plan was leaning on that.
  `half-day-one-punch` sits behind `len(linked) == 1` nested inside a block
  already gated on `len(linked) == len(punches)`, so it fires only on a day
  with EXACTLY ONE punch in total. The shapes actually reported — IN 08:51 +
  IN 18:31, and IN 09:08 + IN 09:18 — are TWO punches and fall through to
  `_verdict("marked", ...)`, which reads as healthy. The night-shift split
  variant is missed too: `punches-split-across-shifts` needs
  `has_pair >= {"IN","OUT"}`, which two INs never satisfy.
  So the report detects the single-punch variant ONLY. Enumerating the damage
  needs its own query first — a day whose countable punches are all IN — and
  that must run BEFORE .claude/plans/checkin-root-cause.md step 5, which stays
  blocked on Nabil's explicit word because it touches historical data.

## LOCK THE CLASS
- 12 new cases in hrms/api/test_remote_checkin.py: 10 on the pure rule, 2 driving
  it through punch() so the wiring is proven and not just the rule.
- The live/stale boundary reuses the same 06:00 cutoff as
  `unresolved_stale_in`, so the forgot-to-check-out banner and the punch can
  never disagree about whether somebody is still on shift.
- frontend/tests/checkin-session-stale.test.mjs now asserts both of its source
  anchors instead of silently slicing to the end of the file.

---

# FAMILY — one question, answered in several places, with drifting arithmetic

CLASS: "who is this caller, and whose rows may they see" was derived more than
once. Each derivation was plausible; the DIFFERENCES between them were the
defect. Concretely here: `appraisal.get_allowed_appraisal_employees` seeds its
chain walk from a RAW, status-agnostic `user_id` match (every claimant), while
`identity.own_employees` is normalised, Active-only and empty on a duplicate.
Subtracting the second from the first closed Active-vs-Active and left
Active-vs-INACTIVE open — a leftover dead row with subordinates produced a
phantom "manager" chain.

ROOT CAUSE: hrms/api/kpi.py answered it in three places. Replaced by `_scope`,
which resolves identity FIRST, for every tier, and seeds the walk from it.

## same-root — fixed in this commit
hrms/api/kpi.py::_scope — the single resolver. Absorbs the tier check, the
  office test (which used to run its own user_id query AHEAD of the gate, so an
  ambiguous login got the WIDEST tier) and the manager chain.
hrms/api/kpi.py::_require_kpi_read — reads `_scope`, no second derivation.
hrms/api/kpi.py::get_team_kpi — same.
hrms/hr/doctype/appraisal/appraisal.py::get_allowed_appraisal_employees — gained
  an optional `seed`. Default is unchanged, so every existing caller keeps its
  behaviour exactly; callers that need IDENTITY rather than CLAIMS pass
  `own_employees`.

## the other callers — not-affected by THIS change, and why

hrms/hr/doctype/appraisal_cycle/appraisal_cycle.py:332 — not-affected — calls it with no seed, so behaviour is byte-identical; and it only tests `is not None` ("is this caller unrestricted?") without ever reading the list, so a wider or narrower chain cannot change its answer.

hrms/hr/report/appraisal_overview/appraisal_overview.py:78 — not-affected by
  this change, same reason: no seed, identical behaviour. It DOES read the list,
  so it shares the underlying class — a phantom chain would widen this report
  the same way. It is not fixed here deliberately: it is a Desk surface backed
  by Frappe's own User Permission layer (`has_permission` refuses the phantom
  rows there, measured during review), and changing the seed would alter Desk
  visibility for every existing user. That is a separate change with its own
  blast radius. TICKETED below rather than bundled.

TICKET: seed appraisal_overview (and audit every other reader of
  get_allowed_appraisal_employees) from `identity.own_employees`, after
  confirming on a real site that no legitimate manager loses rows. The Desk
  hook `get_permission_query_conditions` must be reviewed in the same pass —
  it is the one place where keeping the raw claimant seed may genuinely be
  right, because it answers for whatever rows exist rather than for a person.

## LOCK THE CLASS
- probe_kpi_manager_tier.py 27/27, carrying the phantom chain and the ambiguous
  login. Proven RED by reverting ONLY the seed.
- verify_appraisal_permission is ON again for the manager tier: the framework
  agrees there, and it independently held the DETAIL door while the seed was
  reverted and the LIST door leaked. Two layers, and they disagreed usefully.
- test_api_employee_reads_are_fenced pins that `_scope` reads only the caller's
  own resolved rows.

---

# FAMILY — standing down without closing your own rows

CLASS: `reconcile_employee_shift` has three branches that hand an employee over
to another owner. Two of them close the rule layer's own assignments on the way
out; the third returned without doing so. The rows it left behind are Active,
open-ended, and of a DIFFERENT shift type from the manual row now governing the
employee — which is the precondition for a day being split across two shifts.

ROOT CAUSE: hrms/hr/shift_rules.py::reconcile_employee_shift, the manual-wins
branch, returned "skipped-manual" without closing `auto_rows`.

REACHABILITY (measured, and it matters): the framework does normally refuse a
second overlapping assignment — `shift_assignment.validate_same_date_multiple_shifts`
throws MultipleShiftError. But that throw is skipped when HR Settings
`allow_multiple_shift_assignments` is on, and the remaining hard throw is left to
`has_overlapping_timings`, which a day shift and a night shift do NOT trigger. So
the pair is permitted exactly when a company runs two non-overlapping shifts —
which is the only way to assign two shifts at all, so any such company has it on.
On a site with the flag OFF this defect is unreachable. **Unanswered on
production: is `allow_multiple_shift_assignments` enabled on Verifica?** If it is
off, shape S6 must have another source and that source is still unfound.

## same-root — fixed in this commit
hrms/hr/shift_rules.py::reconcile_employee_shift (manual-wins branch) — closes
  `auto_rows` before returning, exactly as the two branches above it do.

## the other stand-down branches — not-affected, and why
hrms/hr/shift_rules.py:104 `skipped-roster` — not-affected — already closes every
  auto row before returning; it is one of the two branches this fix copies.
hrms/hr/shift_rules.py:115 `skipped-schedule` — not-affected — same, and its
  comment already states the rule ("the rule layer stands down and closes its
  own rows"). The defect was that the third branch did not honour it.
hrms/hr/shift_rules.py `skipped-no-rule` / `closed` — not-affected — reached only
  AFTER the stale loop, which closes every auto row that is not `matching`; and
  `matching` requires `desired`, which is falsy on this path. So nothing open is
  left behind.
hrms/hr/shift_rules.py `noop` — not-affected — `matching` is an open row of the
  DESIRED type; keeping it is the point.

## callers — not-affected
hrms/hr/shift_rules.py:194 sync_shift_assignments — not-affected — the daily
  scheduler; it only dispatches and counts actions. It now closes more rows than
  before, which is the intended repair, and its action vocabulary is unchanged.
hrms/hr/shift_rules.py:220 — not-affected — the Employee hook; same.
hrms/patches/v16_0/add_employee_roster_managed_field.py:5 — not-affected — a
  docstring mention, not a call.

## AMENDED AFTER REVIEW — the first fix was half a fix, and cost something else

Two defects in it, both measured on fresh.local and both now closed:

(a) THE HAND-OFF DAY SURVIVED. `_close_assignment` floors `end_date` at the row's
    own start date, so a rule row that STARTS TODAY closes to end_date == today —
    and every Shift Assignment date read in this app is inclusive of end_date, so
    it went on governing the very day it was meant to stop governing. Measured on
    1bb0a0414: shift types covering today = ['Half Day Test', 'NP Night 19-4'].
    The daily job creates the row at start=today and an Employee edit re-runs the
    reconcile the same day, so this was routine, not a corner. Such a row is now
    retired by STATUS instead — `validate_overlapping_shifts` returns early on
    Inactive, so it stops being a candidate at once.

(b) IT STRIPPED THE LAPSED-ROSTER CASE BARE. The branch fires on two disjuncts,
    and the second is a manual segment that ended recently and has NOT been
    replaced — so no manual row covers today to take over. Closing there left the
    employee with NO shift at all. Measured on 1bb0a0414: shift types covering
    today = []. Every punch that day is stamped off-shift, no attendance is
    auto-marked and no overtime is computed — shape S5 in this repo's own damage
    enumeration. The fix removed one kind of damage and created another. The
    closing loop now runs only on the FIRST disjunct, where a real manual row is
    actually covering the person; through a roster gap the rule's own row is the
    only coverage they have and it keeps it.

## LOCK THE CLASS
- The test asserted a PROXY, not the invariant, and was green with (a) live in
  its own fixture: `_open_autos()` filters on "no end date", so a row ending
  today is invisible to it. It now asserts that exactly ONE shift type governs
  today, which is what the docstring always claimed. Plus a second case for the
  roster gap.
- Regression test for the instance: hrms/hr/test_shift_rules.py::
  test_manual_takeover_closes_the_rules_own_open_rows — creates a rule row, then
  a manual one, and asserts no OPEN auto row survives the hand-off.
- Real-save evidence: verify-bench/sites/probe_shift_rules_manual.py, savepointed
  and rolled back. RED on HEAD ("left 1 open-ended auto row Active beside the
  manual row"), GREEN after. The probe sets the HR Settings flag inside the
  savepoint, because with it off the scenario cannot be constructed at all.
- The invariant pinned: a branch that hands an employee to another owner must
  close every assignment the rule layer created. There is no branch where
  standing down and leaving a live row is correct.

---

# FAMILY — a guard that judges evidence the walk will never read

CLASS: `resolve_punch_type` asks two questions about the same window — "is any
row untyped?" and "which rows does the pairing walk read?" — and asked them in
the wrong order. The untyped guard ran over the RAW window, the filter that
drops mirrored and rejected rows ran after it. So a row the walk had already
decided to ignore could still switch the whole correction off, silently, for
that employee's entire three-day window.

ROOT CAUSE: hrms/api/remote_checkin.py::resolve_punch_type — the guard read
`recent_rows`; it now reads `rows`, after the filter.

## same-root — fixed in this commit
hrms/api/remote_checkin.py::resolve_punch_type — the guard moved below the
  filter and now tests `rows`. No other behaviour changed: the filter, the
  tie-break and the walk are untouched.

## the other users of the same window — verdicts
hrms/api/remote_checkin.py::punch — not-affected as a caller (it supplies the
  rows and reads the returned type), but it is the ONLY caller, so this fix
  reaches every path that runs the correction at all. Which is the narrower
  problem recorded separately: the correction runs on the PWA path only.
hrms/utils/checkin_sweeper.py — not-affected — it excludes mirrored rows for the
  same single-writer reason, independently, and never consults this guard.
hrms/api/remote_checkin.py::_session_is_live — not-affected — the 06:00 cutoff is
  a different question (is the banner allowed to offer a repair) and is
  deliberately shared with `unresolved_stale_in`.

## LOCK THE CLASS
- hrms/api/test_remote_checkin.py gains three cases pinning BOTH sides of the
  boundary, so a future reordering cannot quietly widen the exemption:
  a mirrored untyped row must NOT stop the coercion; a LOCAL untyped row must;
  a rejected untyped OUT must not. Proven RED on HEAD ('IN' != 'OUT').
- The invariant: a guard may only judge the evidence the walk actually reads.

---

# FAMILY — "is the session open?" answered by the wrong question

CLASS: `resolve_punch_type` decided whether a session was open by scanning for
"an IN whose next row is not an OUT" and keeping the last such row. That is a
different question from "is the employee currently in", and it gives a different
answer on any log that already carries a duplicate IN — i.e. on exactly the
population the rule exists to protect. It returned a long-dead orphan as the
open session, so the next arrival was written as that orphan's check-out:
a block nobody worked, and the real session never opened.

ROOT CAUSE: hrms/api/remote_checkin.py::resolve_punch_type, the pairing walk.
The window is sorted; the newest row answers the question on its own. An OUT
last means the employee has left, whatever precedes it.

## same-root — fixed in this commit
hrms/api/remote_checkin.py::resolve_punch_type — the walk is replaced by
  `rows[-1] if rows[-1].log_type == "IN" else None`. The abandoned check and the
  staleness check that follow are untouched, and both still apply.

## the other readers of session state — verdicts
hrms/api/remote_checkin.py::_session_is_live — not-affected — it answers "has
  this open IN gone stale", taking the open IN as given. It is the SECOND gate
  and still runs; this change only corrects which row is handed to it.
hrms/overrides/employee_checkin_override.py::_open_in — not-affected AS A CALLER,
  but it is the same question asked a second time, for shift attribution. It
  already does it correctly: `order_by="time desc"`, limit 1, and it returns None
  unless that newest row is an IN — which is precisely the rule adopted here. The
  two now agree. TICKET: they should share one implementation; two answers to
  "is this employee currently in" is the defect class this repo keeps repeating.
hrms/utils/checkin_sweeper.py — not-affected — sweeps by age, not by pairing.

## LOCK THE CLASS
- hrms/api/test_remote_checkin.py gains three cases: the damaged log
  [IN 08:00, IN 09:00, OUT 12:00] must not reopen on a 14:00 arrival; three INs
  and a trailing OUT is closed; a trailing IN is open and names the NEWEST IN as
  the row being closed. Proven RED on HEAD ('OUT' != 'IN', twice).
- The invariant: session state is read from the newest row, never reconstructed
  by pairing a damaged log.

---

# FAMILY — a detector blind to the thing it detects

CLASS: a query written to FIND day-scoped damage, itself written day-scoped. The
unit of this damage is a SESSION — an IN and whatever closed it — and a session
is allowed to cross midnight. Every place the enumerator reached for a calendar
date instead, it lost the same population it exists to find, and it lost it
silently: the query still returns a number, and the number looks like an answer.

ROOT CAUSE: hrms/utils/checkin_damage_enumeration.py — S4 correlated a punch to
an attendance row with `DATE(i.time) = a.attendance_date`, and S6 compared a DATE
column against an end-of-day timestamp. Five smaller defects around them, all in
the same direction: a confident wrong count.

## same-root — fixed in this commit
S4 — correlates through `Employee Checkin.attendance`, the link the marking code
  itself writes. No date arithmetic at all, so a shift crossing midnight is one
  row and cannot be split or matched by coincidence.
S6 — `end_date >= DATE(%(to_date)s)`. MariaDB coerces a DATE to midnight, so the
  old form read an assignment ending on the last day of the window as closed.

## the other five, same commit, different mechanism
S1, S2 — the next-IN boundary subqueries had no Rejected filter, so a rejected
  remote check-in acted as a session boundary and put HEALTHY days into the
  repair-candidate list.
S2 — the derived table had no date predicate and self-joined the whole history
  per employee; on production it might never have returned. Adding the window is
  subset-preserving: rows outside it were never joined to the outer query.
S2 — now excludes mirrored and abandoned rows, because sync/write_block refuses
  writes to mirrored rows: a candidate that cannot be repaired is not a candidate.
S5 — `offshift = 0` added. shift IS NULL and offshift = 1 are written together,
  and OT ignores off-shift punches BY DESIGN, so without it the count was
  dominated by punches behaving correctly.
report() — counts rows AND people. Every decision taken off this is about people.

## not-affected — the other readers of the same damage
hrms/utils/attendance_day_audit.py — not-affected — a separate report with its own
  (documented, narrower) verdicts. It is blind to these shapes too, which is WHY
  this module exists; it is not being changed here.
hrms/sync/checkin_recovery.py — not-affected — infers types and writes; this
  module only reads. Its own fence defect is tracked separately.

## LOCK THE CLASS
- The first invariant test pinned ONE SPELLING (`GROUP BY ... DATE(time)`) and was
  GREEN with the other spelling shipped inside S4. It now also refuses
  `DATE(<alias>.time)` in any punch-walking shape. Mutation-checked without a
  bench: the assertion catches the old S4 form and passes the shipped one.
- Smoke-tested on fresh.local: all seven shapes execute, and S1 surfaces the
  Midnight Shift IN 00:30 -> IN 10:00 pair that a day-grouped query splits in two.

## AMENDED AFTER REVIEW — the link fix traded a loud wrong number for a quiet one

S4's move from DATE() to the `attendance` link is precise, and precision was not
the whole problem. `Employee Checkin.attendance` is written by ONE path
(update_attendance_in_checkins, two callers). HR's bulk Employee Attendance Tool,
mark_attendance() and Attendance Request never write it — and
mark_attendance_and_link_log DELIBERATELY leaves punches unlinked when it hits
DuplicateAttendanceError or OverlappingShiftAttendanceError, which IS the
contested, damaged day S4 exists to find. So S4 can return a clean-looking zero
while the damage sits in rows the link cannot speak for. Measured on fresh.local:
S4 = 0, and 22 Half-Day/0h rows carry no linked punch at all.

That is worse than the day-scoped version it replaced, which at least
over-reported. The answer is not to go back — it is to stop the report being able
to show a trustworthy zero:

S8 (new) — Half Day/0h rows with NO linked punch: the "cannot tell" denominator,
  printed directly under S4, with a line saying S4 is incomplete while S8 is
  non-zero.
S9 (new) — punches stamped offshift = 1. S5's new `offshift = 0` filter is right
  for keeping the anomalous population clean, but a punch gets that flag for two
  very different reasons — genuinely outside every window (by design), or NO
  ASSIGNMENT MATCHED (a lapsed or duplicated assignment, which is damage and is
  the S6 condition). Both yield 0.0h of overtime. Counted rather than dropped.
S6 — gained `start_date <= DATE(to_date)`. Without it an employee correctly
  scheduled onto a different shift NEXT MONTH counted as a duplicate-shift
  conflict, and S6 is the gate that tells the operator to stop.

## LOCK THE CLASS, second pass
- The day-scoping guard required a table alias (`DATE(i.time)`), and S5, S7 and S9
  are single-table and UNALIASED — so plain `DATE(time)`, the most natural way to
  break exactly those three, sailed through. Measured: 8 of 10 mutants missed.
  The guard now carries six spellings (DATE, DATEDIFF, CAST AS DATE, DATE_FORMAT,
  LEFT, and a bare range against a DATE column) and catches 8 of 8, while the
  shipped link form and an ordinary time window still pass.
- A renamed SELECT alias killed S6 at runtime the first time it executed
  ("Unknown column 'assignments_covering' in 'ORDER BY'") and every test stayed
  green, because these shapes only run on a bench. A new test now requires every
  bare identifier in ORDER BY or HAVING to be defined in that shape's SELECT.
  Proven red by reintroducing the mismatch.

## the machine's list — all four are the WORD "report" in prose, not a caller

The scan matches the symbol name `report`. None of these reference
`checkin_damage_enumeration.report` or `run_shape`; all verified by opening the line.

frontend/src/data/appLinks.js:26 — not-affected — a comment naming a payroll report file.
hrms/api/__init__.py:318 — not-affected — a comment about a manager reading a direct report (the person).
hrms/api/kpi.py:478 — not-affected — same, a comment about a manager reading a report (the person).
hrms/hr/utils.py:1126 — not-affected — a logger format string counting direct reports (people).

---

# FAMILY — a session boundary taken from the calendar instead of the shift

CLASS: "when is this work session over" was answered with calendar midnight.
That is correct for a shift living inside one date and wrong for every shift
that crosses one, where midnight falls in the MIDDLE of the session. Everything
downstream that asks "which later punch belongs to the NEXT session" then
mis-answers for exactly the people whose shift crosses midnight.

ROOT CAUSE: hrms/api/remote_checkin.py::submit_late_checkout computed
`next_day = midnight after the IN's date` and used it as the day-turnover
boundary. Its own `# ceiling:` comment named the defect and the upgrade; this is
that upgrade. The turnover now comes from the IN's own `shift_actual_end` when
it has one, floored at midnight so no shift inside one date changes behaviour.

## same-root — fixed in this commit
hrms/api/remote_checkin.py::submit_late_checkout — takes the boundary from
  `session_boundary` instead of computing it inline.
hrms/api/remote_checkin.py::session_boundary — NEW, pure, carries the rule and
  the reason. Not whitelisted: it is a helper, not an endpoint.

## the machine's list — no external call sites
`cs_callers` returns nothing outside this commit's own files for
`session_boundary`, `submit_late_checkout` or `get_unresolved_stale_in`. The
boundary was inline and is still reached only through `submit_late_checkout`.

## the other places that answer a NEIGHBOURING question — verdicts
hrms/api/remote_checkin.py::_session_is_live — not-affected — a different
  question (has an open IN gone stale, so may the banner offer a repair) with its
  own deliberately shared 06:00 cutoff. It does not bound a search.
hrms/api/remote_checkin.py::resolve_punch_type — not-affected — reads session
  state from the newest row; it never computes a day turnover.
hrms/utils/shift_resolution.py::SESSION_WINDOW — not-affected — a 20-hour
  DURATION used to decide whether an OUT still closes an IN. Different shape of
  answer (a length, not an instant) to a different question.
hrms/overrides/employee_checkin_override.py::_open_in — not-affected — bounds its
  lookback by SESSION_WINDOW, not by a calendar date, so it never had this bug.

## LOCK THE CLASS
- Real-save evidence: verify-bench/sites/probe_late_checkout_night.py, savepointed
  and rolled back. RED on 53c25a30e with the production message verbatim
  ("Check-out time must be before your next check-in ... at 2026-09-13 00:05:00"),
  GREEN after, same fixture and same night Shift Assignment in both runs.
- Six bench-free cases in hrms/api/test_remote_checkin.py pin the rule: a night
  shift turns over after it ends; a day shift keeps exactly the boundary it had;
  no shift stamp falls back to the calendar; a real OUT still wins; a stray later
  OUT does not widen the session (min, not max); and the shift close is accepted
  as a string, because that is how it arrives from the database.
- The invariant: a session's end is read from the shift it belongs to, and the
  calendar is only the fallback when there is no shift to read.

---

# FAMILY — a session boundary taken from the clock instead of the shift, again

CLASS: the same defect as the late check-out boundary, in the other direction.
`resolve_punch_type` exempted every punch between midnight and 06:00 outright, on
the reasoning that such a punch is ambiguous. It is ambiguous only when the open
session's shift has ENDED. For a shift still running through those hours the
punch is not ambiguous at all — it is the departure the rule exists to catch —
and the blanket exemption handed the two-IN shape straight back to the people
whose working hours live there.

ROOT CAUSE: hrms/api/remote_checkin.py::resolve_punch_type — `if now.hour < 6:
return requested, None` ran BEFORE the open session was known, so it could not
ask the only question that separates the two cases.

## same-root — fixed in this commit
hrms/api/remote_checkin.py::resolve_punch_type — the band moved BELOW the walk
  and now asks whether the open IN's own shift is still running at `now`. With no
  shift stamped the old behaviour stands, which is exactly the situation the band
  was right about.
hrms/api/remote_checkin.py::punch — `shift_actual_end` added to the recent-log
  fields, because the rule now needs it. Read-only widening of a SELECT.

## the machine's list — verdicts
hrms/api/remote_checkin.py::_session_is_live — not-affected — it also carries a
  06:00 cutoff, for a different question (may the BANNER offer a repair). A false
  "live" there costs a banner, not a row. It is deliberately shared with
  `unresolved_stale_in` so the banner and the punch cannot disagree about who is
  still on shift, and that is unchanged.
hrms/api/remote_checkin.py::session_boundary — not-affected — same family, fixed
  in 8d105985e. The two now answer the same question the same way: a session ends
  when its shift does.
hrms/overrides/employee_checkin_override.py::_open_in — not-affected — bounds by
  SESSION_WINDOW, never by an hour of the clock.
hrms/utils/checkin_sweeper.py — not-affected — sweeps by age.

## LOCK THE CLASS
- Four bench-free cases in hrms/api/test_remote_checkin.py: a night shift IS
  protected through its own small hours (RED on HEAD, 'IN' != 'OUT'); an early
  arrival after a shift that ENDED is still safe; no shift stamp keeps the old
  behaviour; and a daytime duplicate still needs no shift evidence at all.
- Real-save evidence: verify-bench/sites/probe_night_band.py (in the verify-bench
  tree, NOT in this repo), savepointed. Both halves measured on a real site: a
  19:00 shift closing 05:00 coerces the 02:00 double tap to OUT, and a day shift
  that closed at 13:00 leaves a 05:30 arrival as an arrival.
- The invariant: the small hours are decided on the open session's own shift
  window, never on the hour of the clock.

## AMENDED AFTER REVIEW — the widened boundary broke the invariant above it

The shift-aware boundary was right and it was applied in one place too many.
`submit_late_checkout` uses that boundary for TWO different questions, and only
one of them wanted it widened:

  * "is the time you typed still inside this session?" — its edge is the NEXT
    SESSION's arrival, and pushing that past midnight is the whole point.
  * "does an OUT already exist for this session?" — its edge must be the FIRST
    later arrival OF ANY KIND. Widening it let an OUT belonging to a later,
    COMPLETED session fall inside the search window.

PROVEN on fresh.local (verify-bench/sites/probe_buried_repair.py, savepointed):
night IN Mon 19:00 forgotten, a complete session IN Tue 01:00 / OUT Tue 02:00
after it, then a repair filed for Tue 00:30 — legal, before the new session
began. RED after 8d105985e ("A check-out for this session already exists."),
and ACCEPTED before it. A strict regression against HEAD~1, on exactly the
night-shift population the commit exists to unblock, leaving their hours
unrecorded. GREEN now, and the original night-shift repair is still GREEN.

`first_later_in` is computed separately and bounds the OUT-existence window only.

hrms/api/remote_checkin.py::submit_late_checkout — same-root (fixed here).

TICKET (W2, widened not introduced): a late check-out can still be written on top
of a genuinely new, still-open session opened between midnight and
`shift_actual_end`. The old code had the identical hole inside one calendar day
(IN 09:00 / IN 14:00 / OUT 16:00 was accepted), so this is a wider window on a
pre-existing class, not a new one — and A3b shrinks it further, because a
duplicate punch inside a live night shift is now recorded as an OUT rather than
an IN, so there is no stray IN left to step over. A true DOUBLE check-out is
still impossible (`later_out` blocks any second OUT) and the row lands Pending,
so a human sees it. Closing it properly wants the session-state supplier below.

TICKET (hotspot, 15 fixes in 90 days): extract
`hrms/utils/session_state.py::open_session(employee, at)` returning ONE object —
the open IN row, its session start, its turnover boundary, and whether it is live
— built from a single ordered recent-rows query. 27 of ~37 hunks in 90 days
landed in four functions (`submit_late_checkout` 9, `punch` 9,
`resolve_punch_type` 5, `get_unresolved_stale_in` 4) that all answer that one
question with three different rules: `_session_is_live`'s 06:00 cutoff,
`shift_resolution.SESSION_WINDOW`'s 20 hours, and `session_boundary`'s shift end.
Every fix in this file has been one of those three disagreeing with the other two.

CORRECTED: the claim "a day shift keeps exactly the boundary it had" is FALSE.
An evening shift ending 23:30 with the default hour of
`allow_check_out_after_shift_end_time` closes at 00:30, so its boundary moves by
that half hour — measured. That is the rule applied honestly, and it is now
pinned by its own case so nobody "restores" the day-shift behaviour by flooring
everything at midnight.

## AMENDED TWICE — no time edge separates the two shapes, so stop using one

The `first_later_in` edge fixed the buried repair and opened a DATA-CORRUPTION
hole in the other direction: `first_later_in` is always <= the old `next_in`, so
the OUT-existence window could only SHRINK, and the genuine OUT closing a session
fell outside it. A second check-out became creatable on a session that already
had one — on a plain DAY shift as well as at night, and
`get_unresolved_stale_in`'s "Forgot to check out?" banner OFFERS that session, so
an ordinary user was walked into it. Proven on fresh.local: two OUT rows on one
session, 12:08 Pending beside the real 18:00.

The two shapes are identical in time order — IN, IN, OUT — which is why two
attempts at a boundary traded places:

  REPAIR   IN 19:00 forgotten · IN 01:00 new session · OUT 02:00 closes it
           an OUT at 00:30 is correct and must be ALLOWED
  CORRUPT  IN 09:08 · stray IN 09:18 (a double tap) · OUT 18:00 closes it
           an OUT at 12:08 is the session's SECOND and must be REFUSED

What separates them is the sequence AFTERWARDS, not when the OUT lands. The
corrupting one leaves two departures adjacent with no arrival between — the exact
mirror of the rule `resolve_punch_type` already enforces at the other end of the
session. So the time edge is gone, replaced by `leaves_consecutive_outs`, pure and
bench-free.

hrms/api/remote_checkin.py::leaves_consecutive_outs — NEW, pure, not whitelisted.
hrms/api/remote_checkin.py::submit_late_checkout — same-root (fixed here). The
  `next_in` refusal is untouched; only the existence SEARCH changed.

MEASURED ON fresh.local, all four shapes, savepointed:
  buried night repair          ACCEPTED   (probe_buried_repair.py)
  day-shift duplicate          REFUSED    (probe_dayshift_double_out.py)
  night-shift duplicate        REFUSED    (probe_double_out.py)
  plain forgotten check-out    ACCEPTED   (probe_late_checkout_night.py)

## LOCK THE CLASS, third pass
- Eight bench-free cases in hrms/api/test_remote_checkin.py covering all four
  shapes plus the rejected-OUT exemption, an untyped row, and both same-instant
  tie-breaks. The suite was 50/50 GREEN with the corruption live, which is how it
  shipped — that is what these close.
- The invariant, stated once: a late check-out may never leave two departures in
  a row. Nobody leaves twice without arriving.

## AMENDED A THIRD TIME — the invariant was right, its scope and its reach were not

Two defects in the first statement of it, both measured on fresh.local:

(a) THE GUARD WENT BLIND PAST ROW 200. The sequence was fetched `time asc` with
    `limit=200`, and an ascending fetch with a row limit truncates the NEWEST
    rows — so the genuine closing OUT fell outside the window and the guard
    failed open with nothing in the log to say so. Measured: IN 09:00, 204 stray
    INs, real OUT 18:00; a second check-out at 13:00 was ACCEPTED. The sibling
    read in get_unresolved_stale_in already avoids this by fetching `time desc`
    and reversing. Now bounded by TIME, with no row limit.

(b) IT ASKED A GLOBAL QUESTION. `any(pair over the whole sequence)` is not "this
    row must not create an adjacency" — it refuses when the log ALREADY carries
    two adjacent OUTs anywhere in the window, which is exactly the damage the
    previous version of this function could produce, and also what the hub
    leaves behind when one punch is pulled twice. A legitimate repair of an
    EARLIER session was refused with a message about a check-out that had
    nothing to do with it. Now scoped to the inserted row's two neighbours.

hrms/api/remote_checkin.py::leaves_consecutive_outs — same-root (fixed here).
hrms/utils/checkin_sweeper.py:86 _has_matching_close — not-affected in BEHAVIOUR,
  but its docstring claimed to match submit_late_checkout's rule and no longer
  does. Corrected in place rather than left to be trusted again.

MEASURED, seven shapes, savepointed, all correct:
  204 stray INs then the real OUT      REFUSED   (probe_attack_consecutive.py A)
  stale OUT/OUT pair a day later       ACCEPTED  (B — the repair is unrelated)
  mirrored duplicate OUT pair          ACCEPTED  (C — same punch pulled twice)
  day-shift duplicate                  REFUSED
  night-shift duplicate                REFUSED
  buried night repair                  ACCEPTED
  plain forgotten check-out            ACCEPTED

Both mutants killed by the bench-free suite: inverting the same-instant tie-break
and restoring the global scan each turn exactly one test red.
