CLASS: `.fetch()/.reload()/.submit()` then `.catch` on a result that may be undefined (follow-up to 1344b7cb7).

The guard now covers reload/submit and multi-line chains; it found two:
frontend/src/components/AttendanceCalendar.vue (.reload() / .catch on two lines) — same-root, fixed.
frontend/src/views/ot/OTRequestForm.vue (.fetch() / .catch on two lines) — same-root, fixed.
