CLASS: display-only field computed by a caller's list transform, missing when the same view loads the raw document

Instance: RequestActionSheet showed no date for Fix a day / Shift change / Time off when opened from Approvals (attendance_dates, shift_dates, leave_dates are set only by data/attendance.js and data/leaves.js list transforms).

Call sites of RequestActionSheet:
- frontend/src/views/Approvals.vue:159 — same-root (raw doc: dates were missing; fixed by the header date line)
- frontend/src/components/RequestList.vue:70 — same-root (same sheet; the header line now shows there too)
- frontend/src/components/ListView.vue:138 — same-root (same sheet)
- frontend/src/components/FormView.vue:300 — same-root (same sheet)

Other computed-by-transform fields in requestSummaryFields.js:
- total_attendance_days / total_shift_days — ticket alpha6-B (the sheet redesign replaces the field list; no wrong value is shown, the row is simply absent)

Locked: utils/__tests__/requestDates.test.js (instance), RequestActionSheet.reject-reason.test.js "the sheet says which day(s)" (the sheet reads the document, not a transform).
