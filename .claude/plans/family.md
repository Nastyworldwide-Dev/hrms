CLASS: review follow-ups on the UX batch — a reason hidden behind another line; a fix applied to editable selects it was not meant for; a cached read never refreshed
frontend/src/components/FormView.vue:277 same-root — reason line is its own v-if; describedby points at whichever line is drawn
frontend/src/components/FormField.vue:350 same-root — out-of-list value appended on read-only rows only
frontend/src/utils/missingFields.js:16 same-root — takes the form's read-only rule, so line and rows agree on edit
frontend/src/views/Profile.vue:374 same-root — reload, with the failure logged
frontend/src/views/leave/Form.vue:457 not-affected — editable leave_type now drops a stale pick again (pre-batch behaviour)
