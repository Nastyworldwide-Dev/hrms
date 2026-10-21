GOAL: close the batch review's Important findings (dangling describedby, stale editable pick, cached shift) on the UX fixes.
DONE WHEN: Send's reason line always renders with its id; editable selects drop an out-of-list pick; You reloads today's shift.
CHECK: node --test frontend/src/utils/__tests__/sendBlock.test.js frontend/src/utils/__tests__/missingFields.test.js frontend/src/components/__tests__/FormField.saved-approver.test.js frontend/src/views/__tests__/you-plan.test.js
