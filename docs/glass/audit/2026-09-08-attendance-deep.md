# Attendance, OT and Replacement Leave: adversarial audit supplement

Audited `3ead59787`, 8 September 2026. Read-only source audit and synthetic production-function execution. No app edits, site connection, database writes, live approvals or payroll actions. This supplements `2026-09-08-attendance-ot-audit.md` rather than repeating its findings.

## Confirmed additional findings

### AD-01 — High: pending remote punches already qualify as verified OT and can become attendance

**Trigger:** an out-of-geofence or late punch is awaiting approval while auto-attendance or the OT form evaluates the day.

- `hrms/overrides/employee_checkin_override.py:249` sets `requires_remote_approval=1` and `remote_approval_status=Pending`, without setting `skip_auto_attendance`.
- `hrms/api/remote_checkin.py:490` creates a pending late OUT with the same omission.
- `hrms/hr/doctype/shift_type/shift_type.py:331` filters processing by `skip_auto_attendance=0`, but has no remote-status condition.
- `hrms/utils/ot_calculation.py:339` fetches raw punches without approval/skip/offshift/ownership filtering. `_pair_sessions` at line 631 excludes only Rejected.
- `hrms/overrides/remote_checkin_request_hooks.py:337` explicitly acknowledges that rejection after attendance marking does not correct that attendance.

**Executed evidence:** real `get_day_ot_breakdown` with a pending IN 09:00 and pending OUT 21:00 on a 09:00–18:00 shift returns **3 hours**, under the label “punch-verified.” This is not merely a preview discrepancy: OTRequest validation uses this function, and the payroll function uses the same underlying scan. Source inspection confirms auto-attendance inclusion; no scheduler/database transaction was executed.

**Impact:** a remote request can be rejected after a Present Attendance or separately approved OT/RL already exists. Rejection changes only that punch's flags, not linked Attendance, approved OT, previously granted leave or closed payroll. PWA and Desk can then disagree indefinitely.

**Proper fix:** define the admissible punch states in one shared policy, preserving accepted legacy NULL states and mirrored ownership. Defer final attendance and claim eligibility for Pending evidence. When evidence changes after processing, explicitly reconcile the affected whole shift/day and downstream grants/payroll, with controlled correction handling. Do not simply add a filter and strand already marked days or omit pending sessions from employee feedback. This requires an approved business/permission policy before implementation.

### AD-02 — High: late-checkout approval can erase earlier worked sessions from the day's Attendance

**Trigger:** employee has IN 09:00, OUT 12:00, IN 13:00; auto-attendance has already linked those rows to one shift Attendance. They later submit and receive approval for OUT 21:00.

`hrms/overrides/remote_checkin_request_hooks.py:382` selects only the latest IN, at 13:00. Lines 411–413 cancel the **entire** existing Attendance and unlink all its punches. Lines 436–441 fetch only the interval from that last IN to the new OUT. The rebuild at line 453 therefore excludes the morning work.

**Executed evidence:** unchanged `reprocess_late_checkout_attendance` with a synthetic four-row day and simulated cancellation selects only the 13:00 IN and 21:00 OUT for rebuilding. Expected all same-shift contributing rows. The actual query and rebuild function were executed; the database, cancellation and Attendance insert were seams.

**Impact:** approval intended to repair the day can remove worked hours, add a false late flag and reduce OT. The earlier now-unlinked logs may subsequently encounter duplicate Attendance rather than repair the incomplete replacement.

**Proper fix:** retain the original Attendance's full contributing set before cancellation; rebuild the entire employee/shift/work-date unit with eligible evidence and verified boundaries, not just the latest session. Preserve manual Attendance protection and mirrored-punch exclusion. Decide how an existing automation-owned draft should be updated: the current routine neither cancels that draft nor unlinks its logs, creating another duplicate/rebuild risk.

**Provenance:** this function was introduced in `7c9ed90d6` on 7 September. Preserve its useful single-session repair and the common shift calculator; extend its scope correctly. Do not revert it wholesale.

### AD-03 — High: a calendar-month OT cap changes when the caller changes the query range

`hrms/utils/ot_calculation.py:421` starts accumulated monthly hours at zero for every call; line 424 excludes dates outside that query before accumulation. Lines 451–455 then cap only the queried portion. `get_day_ot_breakdown` at line 524 queries one day; `get_ot_pay` at line 479 accepts arbitrary payroll intervals.

**Executed evidence:** September 3 = 3h and September 18 = 3h, with monthly cap 4h. One query over September produces **4h**; separate single-day queries produce **6h**. The existing calendar-boundary reset test passes while this property fails.

**Impact:** employees can be shown/approved separate claims beyond a shared calendar-month cap, and payroll periods splitting that month can each consume a fresh allowance. Different report ranges show different payable totals.

**Proper fix:** compute consumption from a canonical whole calendar month and consistently allocate the remaining cap to requested days; explicitly define whether consumption is approved-pay hours, raw worked hours or another agreed basis. Current payroll consumes approved hours while claim summaries consume raw hours. Preserve the existing month-boundary reset; fixing that bug did not address partial-month queries.

### AD-04 — Medium: editing a saved draft or changing an amendment's date bypasses the backdate rule

`OTRequest.validate_filing_window` (`hrms/hr/doctype/ot_request/ot_request.py:81`) returns immediately for every existing document and every amendment. It never compares the prior work date with the edited date. `ot_date` is editable in the Desk DocType.

**Executed evidence:** at fixed today 8 September 2026, the real validation method allows 1 January 2026 on both an existing draft and a new amendment with a changed date. New ordinary requests are checked against the two-cycle window.

**Framework cross-check:** local Frappe `Document.validate_amended_from` at `/home/nabil/verify-bench/apps/frappe/frappe/model/document.py:618` verifies only that the source is cancelled; it does not ensure the new work date matches the source. Other gates, including ownership, punch cap and duplicates, still apply. This is a date-policy bypass, not a demonstration of arbitrary unverified payout.

**Impact:** the current restriction already has an inconsistent exception, and implementing a four-month constant alone preserves that loophole.

**Proper fix:** allow routine handling of an unchanged, validly filed historical date, but apply filing rules whenever employee/work date changes. Validate amendment lineage and same-date exceptions explicitly. A future temporary grace needs an expiry and a reproducible policy date, not an unchecked `amended_from` exemption.

### AD-05 — High: Desk status edits leave Remote Checkin Request and punch state inconsistent

The PWA decision endpoint (`hrms/api/remote_checkin.py:216`) refuses a second decision. Desk exposes the ordinary editable `status` select (`hrms/hr/doctype/remote_checkin_request/remote_checkin_request.json:85`). The controller gate at `remote_checkin_request.py:25` checks who changes status but does not enforce allowed transitions; Pending always returns early.

The propagation hook at `hrms/overrides/remote_checkin_request_hooks.py:318` ignores transitions to Pending; approval at line 328 does not clear rejection's `skip_auto_attendance=1` from line 347. Existing `approved_at` is retained across Desk redecisions at line 321.

**Executed evidence:** real propagation on Rejected→Approved leaves `skip_auto_attendance=1`. Approved→Pending leaves linked punch `remote_approval_status=Approved`. The probe simulates DB writes in memory. Controller and schema tracing establish Desk reachability for an authorized writer; no authenticated Desk save was attempted.

**Impact:** “Approved” can still be excluded from attendance; “Pending” can still count as approved work. Desk has reversal behavior that PWA refuses, without reliable downstream correction or decision timestamps.

**Proper fix:** centralize the transition contract in the controller, used by both Desk and PWA. Either forbid direct reversal and provide an audited correction operation, or reconcile all related flags, timestamps and derived records atomically. Preserve assigned-approver and company checks, and do not allow resetting a request to evade the decision gate.

### AD-06 — Medium: an unrelated punch gap suppresses a fixed unpaid break

`ShiftType._deduct_unpaid_breaks` (`hrms/hr/doctype/shift_type/shift_type.py:408`) computes total gaps as elapsed span minus worked hours, then subtracts that total from configured break minutes at line 410. It has no information about where those gaps occurred.

**Executed evidence:** Thursday punches 09:00–10:00 and 11:00–19:00 total 9h, with a fixed unpaid 12:00–13:00 break. The real deduction method and real break-overlap helper return **9h**, although the separate 10:00–11:00 absence and 12:00–13:00 unpaid break should produce 8h. Shift lookup is mocked; the duration calculations are production code.

**Impact:** fixed break deductions and attendance thresholds can be wrong on split-punch days. This is separate from the OT late-arrival mismatch and matters when deciding what HR means by “all hours worked” on non-working days.

**Proper fix:** retain actual worked intervals and subtract the union of fixed unpaid windows intersecting those intervals. Handle flexible-duration breaks under their separate policy. Preserve the valid protection against double-deducting an actual lunch logout; total gap duration is insufficient to provide it.

## Strong prior finding reverified

### Inherited approved OUT refusal still holds under framework hook semantics

The earlier probe forced `has_value_changed=True`. This supplement also executes the **actual local Frappe** `has_value_changed` and `run_before_save_methods` bodies. A new inherited Approved request under the employee session still throws the assigned-approver error despite `ignore_permissions=True`.

Framework trace: `Document.insert:473` marks the document local; `check_if_latest:1095` loads no prior row and sets action save; `run_before_save_methods:1411` calls validate and before_save; `has_value_changed:701` returns true without a prior document. The `ignore_permissions` flag only bypasses permission checks, not these controller validators. Actual insert/naming/link validation/transaction rollback were **not** executed.

Do not weaken the gate globally to solve this. Trusted derivation must validate the owning IN/OUT/session relationship and approved parent on the server.

## Further coverage risks: source-established paths, not counted as reproduced incidents

- **Historical shift/rate drift:** `ot_calculation.py:105` reads current Shift Type configuration, and `_real_shift_end_for_session:197` anchors current start/end on historical dates. Editing shift start/end, enabling OT, or changing rates can change old claim caps and payroll recalculations. The existing “buffer edits do not change old OT” fix should remain. Work-date-effective configuration/snapshots and an explicit recalculation policy are needed for a four-month grace. Current employee OT eligibility (`ot_request.py:97`) also changes draft compensation at later save/approval; no historical entitlement policy is encoded.
- **Multi-shift same-date rates:** `_accumulate_range_by_day` (`ot_calculation.py:614`) overwrites the day's contributing shift with the last session. `_iter_day_ot` then applies that one shift's rate/divisors/caps to aggregated hours from all shifts. Preserve each contribution's rate context or define an explicit approved precedence rule; an arbitrary last shift is not a robust ledger.
- **Checkin edits after Attendance:** `EmployeeCheckin.validate_time_change` (`employee_checkin.py:61`) protects time only when Attendance is linked. Log type/employee edits have no equivalent controller guard, while shift snapshot refresh is skipped for linked Attendance. Review authenticated Desk edit behavior and guard the identity fields that produced a submitted Attendance.
- **Cross-request RL concurrency:** `approval.decide:222` correctly locks the individual request. `_existing_rl_allocation` (`hrms/hr/utils.py:672`) loads the shared allocation without a row lock; top-up at line 719 and reversal at line 801 write absolute totals. Two different requests affecting one allocation can read the same old total. Need DB concurrency tests for grant/grant and grant/cancel; same-request idempotency does not establish allocation safety.
- **Concurrent duplicate OT filing:** `OTRequest.validate_duplicate_request:144` is a read-before-insert existence check, with no employee/date composite uniqueness shown in the DocType or local method. Confirm installed DB indexes and race behavior before declaring duplicates impossible.
- **Late filing is not a payout schedule:** comments promise the next payroll, but `_approved_ot_pay_hours` (`ot_calculation.py:399`) selects by work date in the caller's period, without a settlement period or paid marker. Salary formula integrations may need arrears/adjustments for past claims. Actual payroll formulas/export process were not inspected; this is a gap to verify, not proof of a missed production payment.
- **Manual-skip and mirrored punches in OT:** the raw scan ignores `skip_auto_attendance`, `offshift` and `synced_from_instance`, unlike Attendance processing. Whether mirrored records are intentionally needed for a central report must be decided per consumer; blanket source exclusion could remove legitimate consolidated data.

## Verification and limits

Commands run, no application changes:

- `python3 docs/glass/audit/2026-09-08-attendance-deep-probes.py` — **exit 1**, nine acceptance violations covering six new findings and the inherited gate. This is intentional failing evidence, not a green application test suite.
- `PYTHONPATH=. python3 hrms/tests/test_ot_calculation_rules.py` — **11 passed**.
- `PYTHONPATH=. python3 hrms/tests/test_remote_checkin_request_hooks.py` — **6 passed**.
- `PYTHONPATH=. python3 hrms/api/test_approval.py` — **15 passed**.
- Break helper suite loaded with `_frappe_stub.install()` and `unittest.defaultTestLoader.loadTestsFromName("hrms.utils.test_break_calculation")` — **27 passed**. The direct `python3 -m unittest hrms.utils.test_break_calculation` attempt could not import the unavailable Frappe module in system Python; the stub loader resolves that environment requirement.

These existing tests use stubs or source assertions. Green results preserve known behavior but do not establish database transaction, locking, authentication, device GPS or production scheduler correctness. The new probes execute production functions with synthetic rows and explicit mocked DB boundaries. They must become proper regression/integration tests during authorized fixes.

No full bench tests were run because the task prohibits database mutation. Missing September dates still require affected punch/Attendance/approval/scheduler data. HR's 194-minute decimal-hours/rounding question remains unresolved. No code-only audit can guarantee absence of unknown regressions.
