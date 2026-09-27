GOAL: a request once sent is read-only in the app, even while waiting; the sheet offers Withdraw, not Edit; no Save on a sent request.
DONE WHEN: FormView.isFormReadOnly = Boolean(props.id); formButton Save only when new; RequestActionSheet has no Edit.
CHECK: node --test frontend/src/components/__tests__/sent-is-read-only.test.js; WebKit: waiting OT 0 editable fields, no Save; approver still sees Review request; new request still editable
