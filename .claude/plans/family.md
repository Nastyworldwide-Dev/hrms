CLASS: a doctype depends_on that the PWA form ignores, so a conditional row always shows (UX review F7)
frontend/src/views/attendance/AttendanceRequestForm.vue:83 same-root — time_slip_reason now follows reason == Time Slip
frontend/src/views/attendance/AttendanceRequestForm.vue:76 not-affected — half_day_date already hidden on !half_day by hand
frontend/src/views/leave/Form.vue:313 not-affected — half-day rows already follow half_day by hand
frontend/src/utils/visibleSections.js:20 ticket ux-depends-on — FormView reads no depends_on at all; a generic eval is a bigger change, left as a ticket
