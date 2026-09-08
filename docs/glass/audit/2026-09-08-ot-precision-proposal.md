# Preserve overtime minutes through storage

Status: concrete proposal for schema approval. No precision metadata, physical column or migration has been changed. The separately approved OT index does not include this proposal.

## Confirmed physical loss

Native local metadata and `SHOW COLUMNS` agree on all six fields:

| DocType | Field | Current physical type | Proposed physical type |
|---|---|---|---|
| Attendance | working_hours | decimal(21,2) | decimal(21,9) |
| Attendance | ot_hours | decimal(21,2) | decimal(21,9) |
| Attendance | ot_rate_weighted_hours | decimal(21,2) | decimal(21,9) |
| Attendance Overtime Band | hours | decimal(21,2) | decimal(21,9) |
| OT Request | claimed_hours | decimal(21,2) | decimal(21,9) |
| OT Request | punch_ot_hours | decimal(21,2) | decimal(21,9) |

Their DocField precision is `2`. Native `BaseDocument.get_valid_dict()` preserves the original float; the database loses the digits:

- 194 minutes: serialized `3.2333333333333334`, reloaded `3.23`.
- One minute: serialized `0.016666666666666666`, reloaded `0.02`.
- After reloading that one-minute claim, native `Document.submit()` reaches the real claimed-hours validator and refuses it: the stored `0.02` exceeds the freshly verified `1/60` cap.

The runnable `2026-09-08-ot-precision-probe.py` proves this with two synthetic rows, always rolled back, no DDL or commit. Identity, links and filing are explicit synthetic boundaries; native submission and the real financial validator run. This is local persistence evidence, not an authenticated production workflow test.

## Exact change

The attached `2026-09-08-ot-precision-metadata.patch` changes only these six JSON `precision` values from `2` to `9`, in the three listed DocType files. Native Frappe `database/schema.py:get_definition` uses that precision to generate the physical decimal scale. Merely changing UI formatting would not repair the columns.

Source punch timestamps remain the canonical evidence. Duration and band calculations retain their actual intervals. Nine decimal places are an hour-storage representation (one storage quantum is 3.6 microseconds), not a new overtime rounding rule.

At the persisted claim comparison boundary, use `Decimal(str(value)).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_UP)` for both the claimed value and verified cap. This models the documented physical representation, with no epsilon or arbitrary tolerance. It makes a stored one-minute representation stable on reload; `3.24` still exceeds a 194-minute cap and must be refused. Weekday pay-band policy remains unchanged and is applied before this storage representation.

## Migration and rollback

1. Add `hrms.patches.v16_0.check_ot_hour_precision_capacity` under the existing `[pre_model_sync]` section of `hrms/patches.txt`. Preflight the six columns BEFORE any model/schema synchronization: reject values outside the new 12-digit integer capacity (absolute value at least `10**12`) and report them for review. Increasing decimal scale from 2 to 9 reduces the integer part of a fixed-width decimal(21,scale); no silent truncation is acceptable.
2. Ship the three metadata changes with an idempotent verifier `hrms.patches.v16_0.verify_ot_hour_precision` under `[post_model_sync]`. Native `frappe/migrate.py:run_schema_updates` explicitly runs pre-model patches, then `frappe.model.sync.sync_all()`, then post-model patches. The sync applies the three table alterations only after the preflight passed; the post-model patch verifies the intended physical precision and clears affected metadata caches. It is not the capacity preflight. Re-running must leave schema and values unchanged.
3. Do not recalculate historical Attendance or approved claims inside this migration. Widening preserves existing values with added zeros; it cannot reconstruct minutes already rounded away. Any historical repair needs a separate reviewed candidate set and payroll/leave dependency checks.
4. Application rollback may retain the wider columns. Blindly reverting the metadata to precision 2 and running migration would destroy newly stored precision. A physical downgrade is safe only before higher-precision values exist, or after an explicitly approved conversion/backup restoration. This is not a universally lossless down-migration.
5. Table alterations may take metadata locks; measure on the local verification site after approval and plan deployment through the normal admin release gates. No production migrate is included in this approval request.

## Consumers and display

- `Attendance.set_overtime` copies the calculator's hours and bands into these fields. Its current Python assignments do not round them; the six physical columns are the loss boundary.
- `_approved_ot_pay_hours` reads stored claimed hours. `get_ot_pay` limits pricing to that approval, so the current `3.23` storage loses payable work even if the raw scanner correctly found 194 minutes. Money can still round to currency precision at the final amount boundary.
- Salary Slip exposes `get_ot_pay` to salary formulas. Rate-weighted Attendance hours and child bands are export-facing quantities; their numeric payloads must keep the new precision. No exporter should format a display string and then reuse it as the numeric value.
- PWA `OTRequestForm.vue` currently copies `data.punch_ot_hours` directly into the model. `FormField.vue` forwards numeric input values, and its default parser uses `parseFloat`; neither is inherently a two-decimal storage rule. Pin request payloads when the summary loads, the date changes, an existing draft opens, and an unrelated field is edited.
- Native Desk `ControlFloat.parse` calls `flt(value, df.precision)`. Keeping its metadata at 2 would round an edited claim back down, so the metadata change is necessary alongside the physical type. A concise read-only display can format two decimals or exact hours/minutes, but must never overwrite the underlying model with that display value. A two-decimal display is not the claim's value.

## Acceptance before release

- Native serialize → insert → reload → approve for 1 and 194 minutes, plus fractional-second examples; verify numeric storage at nine decimals, stable validation and expected final payroll amounts.
- New and existing `3.24` claims against 194 minutes are refused. No invented epsilon.
- The six metadata fields and physical columns match; a second migration changes nothing. Preflight refuses an out-of-range numeric fixture rather than truncating it.
- PWA and Desk submit the preserved cap after display and unrelated edits. Export payloads retain numeric precision; display formatting remains separate.
- Weekday rounding, monthly pools, rejection, cancellation and existing approved-payment preservation remain green.

The computational all-hours/status slice can be reviewed separately, but the complete nonworking-hours feature must not be declared finished or deployed without resolving this storage dependency and the remaining multi-shift calculation defect.
