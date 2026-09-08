# Nonworking hours: computational review checkpoint

The frozen slice preserves actual eligible worked intervals on listed rest/off/public holidays, bypasses weekday thresholds/caps/rounding, and records valid pairs as Present without flags. Configured rate bands remain authoritative. It preserves the integrated whole-shift `repair_attendance` forwarding.

## Review paths

- `hrms/utils/ot_calculation.py`: 163 added/74 removed lines against current root.
- `hrms/hr/doctype/shift_type/shift_type.py`: 53 added/8 removed; holiday pair/status/checkbox gate, retained invalid query boundaries and eligible-only linking.
- `hrms/api/__init__.py`: copy only the four-line nonworking choice branch in `get_claimable_ot_summary`.
- `hrms/tests/test_ot_nonworking_hours.py`: 17 tests; actual calculator, controller and selected public API/native method source, explicit DB/persistence boundaries.
- `hrms/utils/test_ot_calculation.py`: existing rest/off tests now create explicit holiday calendars; retained rate assertions.

## Evidence

System Python command:

```
python3 -m pytest -q hrms/tests/test_ot_nonworking_hours.py hrms/tests/test_ot_holiday_classification.py hrms/tests/test_ot_claim_monthly_capacity.py hrms/tests/test_ot_monthly_range.py hrms/tests/test_ot_calculation_rules.py hrms/tests/test_ot_filing_edits.py hrms/utils/test_filing_window.py hrms/tests/test_frappe_stub_time.py
```

Result: **80 passed, 33 subtests**. Includes 50 generated minute durations, exact194/60 hours, PH9h8@2+1@3, strict duplicate IN, alternating entries, explicit OUT/IN gaps, pending/rejected exclusion, midnight split, weekday minimum and split-session lateness, claim/payroll/discovery pool separation, Present/no flags and incomplete holiday evidence. Ruff check and git diff check pass.

Native verify-bench Python imported this worktree. Four existing OT test methods passed with unique synthetic Shift/Holiday fixtures. Native `ShiftType.get_attendance` returned Present,194/60,False,False; native `Attendance.set_overtime` retained194/60 in hours and band assignments. Transactions rolled back. TestCase class setup was not invoked because it commits dependencies. This is native calculation composition, not a complete scheduler transaction test.

## Explicit remaining dependencies

1. **Persistence precision**: real physical decimal(21,2) loses exact entitlement; one-minute reloaded request0.02 fails actual submit against1/60. User has now authorized the separate exact six-field9dp/pre-model guard/post-model verifier/Decimal-boundary slice; none is implemented here. See precision proposal and native probe.
2. **OT-MULTI**: same-day multiple shifts still collapse to the last shift's classification/rates. `2026-09-08-ot-multishift-probe.py` is intentionally RED:1h normal@1.5 plus1h rest@2 returns weighted4 instead3.5. This is an immediate next bounded slice, not claimed fixed here.
3. Weekday scheduled-break overlap, expired calendar assignment resolution, discovery of raw-punch dates and effective filing window, approved employee serialization/index remain separate authorized work. No four-month policy assumed.
4. Source-based punch precision remains canonical; this slice does not repair historical records, perform migration, or claim end-to-end persisted acceptance.

## Fresh-review correction: real scheduler evidence

Fresh review refuted the first checkpoint: the scheduler query dropped skipped rows and omitted remote status fields, so its input disagreed with raw OT. The query now retains invalid boundary evidence; the shared predicate excludes it from work and linking. Weekday calculations preserve the configured native policy within each contiguous eligible segment, so a rejected boundary cannot join a first-IN/last-OUT span. Entirely eligible weekday streams retain native behavior.

Additional review path: `hrms/tests/test_rejected_punch_attendance.py`. Its old static query-filter assertion conflicted with retaining boundary evidence; it now executes the actual eligibility function and asserts rejected, pending, skipped, approval-required and offshift rows are ineligible. Query-to-mark behavior has stronger dynamic coverage in the new nonworking tests.

Reproducible native command (cwd `/home/nabil/verify-bench/sites`):

```
/home/nabil/verify-bench/env/bin/python /home/nabil/nadi-fix-overtime/docs/glass/audit/2026-09-08-ot-allhours-native-probe.py
```

Result: four native existing OT methods, exact194-minute native ShiftType/Attendance calculation, and five actual database query→mark→Attendance save/submit→checkin-link scenarios PASS. The rejected/pending/skipped/approval-required/offshift boundary remains unlinked. A later valid13:00–14:00 pair creates Present1h without flags. All fixtures roll back; no mocked Attendance persistence or linking. Add `--old-fetch` to use the actual query body pinned at090091e06: RED because the skipped boundary is removed (2 fetched rows vs3), with current calculation unchanged.

Dependent suites: `test_remote_checkin_request_hooks.py`6passed; `test_rejected_punch_attendance.py test_leave_rules.py`4passed5subtests. No `employee_checkin.py` edit belongs to this slice: that path was only synchronized from root to make the existing reviewed helper available in the worktree.

Precision implementation/local tests are **authorized** by the user's “proceed”; awaiting implementation after this frozen review, not awaiting permission.
