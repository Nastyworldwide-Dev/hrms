CLASS: a form-row child rule outranking the row-modifier rule; and form state (loading/error) shown as a red field error and loose text

Instance: owner's live Overtime shots (25 Sep): "Could not check overtime…" wrapped one word per line inside the Hours value (row 43 -> 87 pt); "Checking overtime…" shown in red; the picked day asked again; "Paid as", the status line and "Try again" floating between groups.

Sites:
- frontend/src/theme/glass-components.css .g-form-row--error rule — same-root (now `.g-form-row.g-form-row--error > .g-field-error`, 0,3,0, later) — fixes EVERY form row that shows an error
- frontend/src/views/ot/OTRequestForm.vue inline error / saveError / floating lines — same-root
- frontend/src/views/ot/claimEmptyReason.js inlineClaimError — same-root (loading never red); summaryFailure (server reason)
- other forms' inline errors (leave dates, half day) — not-affected by the loading class: they set error_message only for real validation errors; they benefit from the CSS fix

Locked: grouped-form.test.js (error row rule), claimEmptyReason.test.js (+2), ot-request-state.test.mjs (+1). Verified in the browser with the summary forced to fail: error said once, rows 44 pt, retry is a row.
