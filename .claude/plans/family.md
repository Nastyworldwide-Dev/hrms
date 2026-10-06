CLASS: a pull that completes before the data it promised has loaded (refresh not awaited).
frontend/src/views/attendance/Dashboard.vue same-root (calendar refresh now inside the awaited list)
frontend/src/components/AttendanceCalendar.vue same-root (refresh() returns its reload; failures still logged and resolved)
frontend/src/components/AttendanceCalendar.vue:useListUpdate not-affected — ignores the return value
frontend/src/views/Notifications.vue, team/*, leave/Dashboard.vue, issues/*, helpdesk/HelpdeskHub.vue not-affected — every reload is inside Promise.allSettled (alpha.35 review)
