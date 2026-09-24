# OT form: "Could not check overtime" — findings (24 Sep 2026)

## Problem A — the summary call fails on the live site

### Where the text comes from (verified)
- frontend/src/views/ot/OTRequestForm.vue:406-414 `saveError`:
  - 408: `otSummary.error` -> "Could not check overtime. Try again before saving."
  - 409-410: loading / no data -> "Checking overtime for this date…"
  - 412-413: cap not a finite number -> the same "Could not check" text
- otSummary = summaryRequest.value.resource (196-198), built in loadSummary (349-400):
  POST hrms.api.get_ot_claim_summary, params {employee, date}.
  The date is `d.date` from the list = `str(work_date)` = "YYYY-MM-DD" (hrms/api/__init__.py:727). No Date object.
- The request re-runs on summaryKey change, via a sync watcher (401-404). pickDay (241-244) only sets ot_date, and that changes the key.
  One fetch per pick. A stale response is ignored (the check on line 385). No race was seen.
- The resource's `transform` (373-381) THROWS "Invalid overtime summary" when punch_ot_hours is not a finite number >= 0,
  or when compensation is not "Overtime Pay" / "Replacement Leave". That thrown error also becomes otSummary.error.
- The error reaches the Hours row through inlineError (418-424) -> watch sets field.error_message on claimed_hours (439-446).
  The "Try again" button (127-134) calls loadSummary.

### Backend (verified by reading)
- get_ot_claim_summary (hrms/api/__init__.py:596-636) and get_claimable_ot_summary (638+) use the SAME fence
  (_ensure_own_employee_or_permitted) and the SAME engine (get_ot_claim_capacity).
- Only difference: the summary passes explain=True. That flag is used only on the zero-hours path (ot_calculation.py:904-909).
  A 1h day never takes that path.
- So for the same employee and date, the summary should succeed whenever the list does.
- No backend or OT-form change since v2.0.0-alpha.6. `git diff v2.0.0-alpha.6 HEAD` on hrms/api, ot_calculation.py and views/ot is empty.

### Reproduction on fresh.local (verified)
- Direct call as W0 (HR-EMP-00009): list = [{date 2026-09-15, hours 2.0}].
  get_ot_claim_summary(employee, "2026-09-15") -> {"shift": null, "punch_ot_hours": 2.0, "eligible_for_overtime_pay": 1, "compensation": "Overtime Pay"}.
- Sweep of every active employee x every claimable day: 1 pair, 1 OK, 0 failures, 0 mismatches.
- Real browser (Playwright, served bundle, 390x844). Tapping the day sends
  POST {"employee":"HR-EMP-00009","date":"2026-09-15"}. Answer: 200 with the payload above.
  "2h 00m to claim" shows. No error.
- **The live failure did NOT reproduce locally.** The exact exception on the live site is UNVERIFIED.

### What is left, and how to settle it
- The code has no path where the list succeeds and the summary throws for the same day.
  The live cause must therefore be one of:
  1. a live-data exception in a branch local data never reaches, or
  2. a failed or timed-out request (network, deploy restart), or
  3. the transform throw at 373-381.
- Unverified candidates on the capacity path:
  - `hours > 0`, so the summary runs the monthly-cap code.
  - That code is _approved_reservations -> _per_day_ot_hours / _classify_day (ot_calculation.py:926-957).
  - The list runs the same code, so it cannot differ, unless the data changed between the two calls.
- **Next step (needs the live site):** read the Error Log / request log for hrms.api.get_ot_claim_summary on 23-24 Sep,
  or replay the call as the owner's employee for 2026-09-23 in the live console.
  This needs Nabil or Frappe Cloud access. It is the one missing fact.
- Neither capAsTime nor the redesign (002b76507) is to blame:
  - capAsTime is display-only (OTRequestForm.vue:224, 232). It never touches params or the cap.
  - pickDay sets ot_date to the same string the old date field set.

### Smallest fix, whatever the cause
- **Make the error say what failed.** The resource has no onError. The real exc_type / message is thrown away,
  and the UI shows one generic line. Add `onError(e) { console.warn("[OTRequestForm] summary failed", e.exc_type, e.messages) }`,
  and show `e.messages[0]` when it exists. The next live report then names the cause.
- A one-off network failure already recovers through "Try again".
- Do not patch around this further until the live log names the exception.

## Problem B — red text one word per line inside the Hours row (verified, CSS cause exact)

- FormField.vue:4-8 puts `g-form-row--error` on the row. Line 206 renders `<p class="g-field-error">` as a direct flex child.
- glass-components.css:3613-3620 intends: row wraps, and the error takes a full line (`flex-basis: 100%`).
- It loses to glass-components.css:3526-3529:
  `.g-form-row > :not(.g-form-row__label):not(.g-form-row__switch) { flex: 1 1 0; min-width: 0; }`
  - Specificity: that rule is (0,3,0), because each :not(.class) counts as a class.
    `.g-form-row--error .g-field-error` is only (0,2,0).
  - So flex-basis stays 0. A basis-0 item always "fits", so the wrap never happens.
    The error shares the line with the label and the input and gets squeezed.
- Measured in Chromium with the summary call forced to 500:
  - `.g-field-error`: flex-basis 0px, width 21.9px, height 139px.
  - Row: 358px wide, flex-wrap: wrap. Children: label 79px, field 201px, error 22px.
  - Result: one word per line.
- **Fix (one rule, more specific, placed after the old one):**
  `.g-form-row.g-form-row--error > .g-field-error { flex: 0 0 100%; text-align: right; }`
  - That is (0,3,0) and comes later in the file, so it wins. Or replace 3617-3620 with it.
  - The same bug hits EVERY FormField row with an error, not just Hours. One fix covers all.
- Screenshots: /tmp/alpha7/ot-probe.png (happy path), /tmp/alpha7/ot-probe-error.png (forced error, squeezed text).
