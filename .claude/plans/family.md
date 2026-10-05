CLASS: a rule the server enforces silently, so the person sees their typed figure change and reads it as a bug. The half-hour cut (66f0ed539) turned a typed 1.37 into a saved 1.0 with no word about it anywhere on the form.
frontend/src/views/ot/OTRequestForm.vue:dayFooter same-root (fixed here: the footer under the day list now ends with the half-hour sentence, for Overtime Pay only)
frontend/src/views/ot/halfHourNote.js same-root (new: the sentence, and halfHourClaim which mirrors the server rule)
frontend/src/views/ot/OTRequestForm.vue:claimed_hours box not-affected — keeps its own prefill and error; the note sits in the footer where "how it is paid" already lives
hrms/hr/doctype/ot_request/ot_request.py:band_typed_claim not-affected — the server rule is unchanged; this only says it out loud
frontend/src/views/ot/OTRequestList.vue not-affected — a saved claim already shows the cut figure
