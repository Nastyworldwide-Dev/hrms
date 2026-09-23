CLASS: `.fetch().catch()` on a frappe-ui resource. fetch() returns undefined
when frappe-ui skips a request (already loading, cached), so `.catch` throws a
TypeError instead of catching. Live audit 23 Sep: Help threw on every open.

Call sites (every one found by grep) — all same-root, fixed here with `?.catch?.`:
frontend/src/views/helpdesk/HelpdeskHub.vue (two, the reported one)
frontend/src/components/AttendanceCalendar.vue:191
frontend/src/views/announcements/List.vue:124
frontend/src/views/ot/OTRequestForm.vue:142
frontend/src/composables/approvedCancel.js:25
frontend/src/data/announcements.js:50-51
Guard: src/utils/__tests__/fetch-may-return-nothing.test.js fails if the pattern returns.
