CLASS: a sent (waiting) request editable in the app because Frappe allows its owner to edit an unsubmitted document
frontend/src/components/FormView.vue:1069 same-root — every request form (leave, OT, fix a day, shift, expense, issue) read-only once sent
frontend/src/components/FormView.vue:839 same-root — Save only for a new request
frontend/src/components/RequestActionSheet.vue:86 same-root — Edit removed; Withdraw stays
frontend/src/views/ot/OTRequestForm.vue:342 not-affected — canEditClaim still gates its own summary reload; the form is read-only above it
