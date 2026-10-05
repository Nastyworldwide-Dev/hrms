CLASS: a form box prefilled from a raw stored float, so the nine decimals the database keeps ("8.876944444") sit in the box a person is about to edit, and a rounded-UP figure would offer time the cap check refuses. Replacement Leave days carry the raw punch time as the cap; Overtime Pay caps are already in 30-minute bands.
frontend/src/views/ot/OTRequestForm.vue:onSuccess same-root (fixed here: prefill through prefillClaim, rounded DOWN to two decimals)
frontend/src/views/ot/claimPrefill.js:prefillClaim same-root (new: the one place that cuts a cap for the box)
frontend/src/views/ot/OTRequestForm.vue:capAsTime ticket ot-decimals — floors to the minute while the lists round to the nearest (OD3, "8h 52m" vs "8h 53m"): a separate wording decision, next
frontend/src/components/RequestActionSheet.vue:formatHours ticket ot-decimals — sent-request sheet shows "8.88" while the list says "8h 53m" (OD4)
hrms/api/__init__.py:get_ot_claim_summary not-affected — returns the raw cap to the form on purpose; the form is where it is cut
frontend/src/utils/formatters.js:formatHoursCap not-affected — display of a cap, already rounds down
