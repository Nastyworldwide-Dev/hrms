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
