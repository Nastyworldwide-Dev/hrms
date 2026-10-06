CLASS: a list row whose name or reason wraps onto several lines on a small phone, pushing the row tall and breaking the list's rhythm (long Malaysian names, long reasons at 360 px).
frontend/src/components/glass/GListRow.vue same-root (label truncates with min-w-0, full text in title; `wrap` prop for sentence rows)
frontend/src/components/ListItem.vue same-root
frontend/src/components/{AttendanceRequest,ExpenseClaim,LeaveRequest,OTRequest,ReplacementLeaveClaim,ShiftAssignment,ShiftRequest}Item.vue same-root (the 7 request rows)
frontend/src/views/team/TeamDashboard.vue same-root (name carries title=)
frontend/src/views/Approvals.vue, components/DaySheet.vue, HolidayList.vue, WhoToAsk.vue same-root (`wrap` on rows that are sentences, not names)
frontend/src/views/Notifications.vue, More.vue, Profile.vue not-affected — use GListRow; truncate by default now, checked by eye before release
