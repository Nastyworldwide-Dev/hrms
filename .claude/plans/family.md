CLASS: a blocked-Send message names fields in database words, not the labels on screen (UX review F2)
frontend/src/components/FormView.vue:974 same-root — the only builder of the "fields are mandatory" line; fixed via utils/missingFields.js
frontend/src/utils/addItemHint.js:23 not-affected — already plain (plainLabel + __), the expense item sheet's own hint
frontend/src/views/ot/OTRequestForm.vue:498 not-affected — sets error_message, a plain sentence already
