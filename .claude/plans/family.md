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
