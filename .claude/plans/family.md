CLASS: a read-only select drops a saved value that is not in the viewer's option list, drawing a blank row (UX review F6)
frontend/src/components/FormField.vue:340 same-root — selectionList now appends the saved value; every documentList row routes here
frontend/src/views/leave/Form.vue:446 same-root — leave_approver list holds only the viewer's own approver; fixed via FormField
frontend/src/views/expense_claim/Form.vue:252 same-root — same for expense_approver; fixed via FormField
frontend/src/views/leave/Form.vue:313 not-affected — half_day_session options are a fixed AM/PM pair, value always inside
