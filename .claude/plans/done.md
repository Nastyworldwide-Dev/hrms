GOAL: a sent request's status is the first line of its page, whole, at body size; the bar keeps Back, the title and the menu. A sent reason is as tall as its text.
DONE WHEN: no GStatusChip in FormView's bar; .g-form-status before the fields; decided leave shows "Rejected" 17pt; reason 22pt tall.
CHECK: node --test frontend/src/components/__tests__/status-in-content.test.js frontend/src/theme/__tests__/row-control-fit.test.js; WebKit decided leave screenshot
