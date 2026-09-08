# OT precision implementation review checkpoint

User authorization: “proceed” after the exact six-field proposal. Implementation and local schema testing are authorized. No production migration, historical recalculation or unrelated policy change is included.

## Exact review paths

1. `hrms/hr/doctype/attendance/attendance.json`: working_hours, ot_hours, ot_rate_weighted_hours precision2→9.
2. `hrms/hr/doctype/attendance_overtime_band/attendance_overtime_band.json`: hours precision2→9.
3. `hrms/hr/doctype/ot_request/ot_request.json`: claimed_hours and punch_ot_hours precision2→9.
4. `hrms/patches.txt`: pre-model capacity guard and post-model verifier registrations.
5. `hrms/patches/v16_0/check_ot_hour_precision_capacity.py`: refuse old-width values outside the new12-digit integer capacity before native model sync.
6. `hrms/patches/v16_0/verify_ot_hour_precision.py`: verify physical decimal(21,9) and effective DocField precision9; clear metadata caches.
7. `hrms/utils/ot_precision.py`: shared fixed field manifest and Decimal9ROUND_HALF_UP storage representation.
8. `hrms/utils/ot_calculation.py`: only claim-capacity return values normalize to saved representation; raw worked durations/bands remain unchanged.
9. `hrms/hr/doctype/ot_request/ot_request.py`: compare positive claimed hours and verified cap at that same documented representation.
10. `hrms/tests/test_ot_storage_precision.py`: nine tests,60 generated durations and six metadata assertions.

The previous reviewed computation/attendance source snapshot is at `/tmp/nadi-allhours-reviewed-snapshot`. No new ShiftType or Attendance Python edit belongs to this precision slice. No API source edit belongs to it; existing summary functions call shared capacity directly.

## Red and green evidence

Before implementation: one-minute reload representation was rejected by actual controller; generated duration1second failed; subquantum positive claim wrongly passed; all six metadata assertions failed. The public-capacity assertion separately failed raw1/60 vs representable0.016666667. Missing preflight failed its new test. Existing3.24 rejection stayed green.

```
python3 -m pytest -q hrms/tests/test_ot_storage_precision.py hrms/tests/test_ot_nonworking_hours.py hrms/tests/test_ot_holiday_classification.py hrms/tests/test_ot_claim_monthly_capacity.py hrms/tests/test_ot_monthly_range.py hrms/tests/test_ot_calculation_rules.py hrms/tests/test_ot_filing_edits.py hrms/utils/test_filing_window.py hrms/tests/test_frappe_stub_time.py hrms/tests/test_rejected_punch_attendance.py hrms/tests/test_leave_rules.py
```

Result: **93passed44subtests**. Ruff and diff check pass. New tests include physical/effective verification failure and idempotent capacity scanning.

Native artifact: `docs/glass/audit/2026-09-08-ot-precision-native-test.py`.
Run from `/home/nabil/verify-bench/sites`:

```
/home/nabil/verify-bench/env/bin/python /home/nabil/nadi-fix-overtime/docs/glass/audit/2026-09-08-ot-precision-native-test.py
```

Passes actual punch/calendar/config→claim capacity→OTRequest.insert→reload→submit→approved payroll for60seconds,194minutes and60.125seconds. Native Attendance insert/reload checks working_hours, ot_hours, weighted hours and child band hours; OT Request checks both remaining fields. All synthetic records roll back. Only clock/notification boundaries are patched during initial filing; financial calculation/validation, persistence and native submit run.

`--sync` performs the separately authorized LOCAL native model import of the three DocTypes, never full production migration. Initial real old-width fixture10^12 was refused by preflight and rolled back before any DDL. Initial sync emitted4 native DDL statements; second pass emitted0. Effective metadata/physical six columns now9dp on fresh.local. The local schema remains widened, as authorized; synthetic financial records are rolled back. Subsequent verification without `--sync` emits no DDL or commits. The original first-pass DDL count was recorded, not its SQL text; the artifact now logs any future DDL explicitly.

Observed stored values and approved amounts with hourly rate10/rest rate2:

| Duration | Stored hours | Payroll amount |
|---|---:|---:|
| 1minute | 0.016666667 | 0.33 |
| 194minutes | 3.233333333 | 64.67 |
| 60.125seconds | 0.016701389 | 0.33 |

`3.24` against194minutes is refused. No epsilon or arbitrary business rounding rule.

Desk artifact: `node docs/glass/audit/2026-09-08-ot-precision-desk-probe.mjs` executes installed native ControlFloat/ControlInt and number-format implementation using the actual changed metadata; parse/reparse and JSON model values retain both caps. Counterfactual precision2 loses them, proving the metadata dependency. DOM rendering is outside this probe. The PWA owner independently pins actual FormView save payloads; those tests are in their separate slice.

## Precise caller manifest for root family ledger

CLASS: loss of canonical OT entitlement at fixed-scale storage and mismatched raw-vs-persisted comparison.

- `OTRequest.validate_claimed_hours` ← `OTRequest.validate`: **same-root**. Native insert/save/submit all use positive Decimal9comparison. Existing saved Rejected branch still skips financial validation; no reversal/ownership/mandatory check removed.
- `get_ot_claim_capacity` ← `OTRequest.set_punch_verified_cap`: **same-root**. Persisted cap matches server summary representation.
- `get_ot_claim_capacity` ← API `get_ot_claim_summary`: **same-root**. PWA and Desk receive representable capacity, so no separate client epsilon/rounding.
- `get_ot_claim_capacity` ← API `get_claimable_ot_summary`: **same-root**. Each choice and shared remaining budget use the same decimal scale; existing chronological allocation policy remains.
- `stored_ot_hours` ← the two functions above: **same-root**, only comparison/public claim capacity boundary. Source punch durations stay canonical.
- `check_ot_hour_precision_capacity.execute` ← pre_model_sync patch runner: **same-root**. Must run before sync, including on legacy installations with missing fields; no values are rewritten.
- `verify_ot_hour_precision.execute` ← post_model_sync runner: **same-root**. Fails mismatched physical/effective precision; idempotent verifier only.
- Changed metadata ← native model sync and Desk ControlFloat parsing: **same-root**, tested via native schema import and installed JS parser.
- Changed persisted Attendance fields ← `Attendance.set_overtime` and native insert/save: **same-root through storage**, source assignments unchanged, six-field reload coverage.
- Stored claimed_hours ← `_approved_ot_pay_hours` → `get_ot_pay` → Salary Slip formula: **same-root through storage**, approved payroll exercised; currency rounding remains unchanged.
- Raw `get_day_ot_breakdown`, `get_shift_ot_breakdown`, rate-band builder and `replacement_leave_days`: **not-affected by new numerical policy**. Raw duration remains exact; existing RL blocks and rate bands unchanged. Their persisted hour fields use the approved representation.
- Multiple-shift contribution ownership: **ticket OT-MULTI**, separate immediate correction already has a concrete red reproducer; precision does not resolve it.

## Limits and next action

Fresh review required before commit/integration. This slice does not deploy or repair historical values already rounded away. Keep widened columns on code rollback; a blind precision2 down-migration would lose new values. Approved index/serialization, mixed-shift contribution pricing, dated holiday expiry, raw-punch discovery/window and weekday scheduled-break overlap remain separate next slices. Four-month grace policy is still unresolved.

LEARNING(fact): Public claim capacity should use the same documented representation as persisted claims; raw punch durations should remain untouched until their own storage boundary.
