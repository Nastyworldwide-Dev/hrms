CLASS: a status collapsed to one word that drops the detail that changes its meaning. The team view maps Attendance "Half Day" to "Present" (someone worked), and the line under the name never said the day was a half, so a boss read a full day where HR had marked a half (2 Oct 2026). A half-day LEAVE already said "(Half day)" in the expanded row; a half day marked on the attendance did not.
hrms/api/team.py:member_statuses same-root (fixed here: row carries half_day_marked from the Attendance status)
frontend/src/utils/team.js:memberLine same-root (fixed here: the line ends with "Half day" when HR marked it; the Team page row and the Calendar day sheet both read this one function)
hrms/api/calendar.py:get_day not-affected — builds its rows from member_statuses, so it carries the field; the sheet renders through memberLine
hrms/utils/team_status.py:derive_member_status not-affected — the CHIP stays Present on purpose (someone worked); only the line gains the detail
frontend/src/views/team/TeamDashboard.vue:expanded row not-affected — already prints "(Half day)" for a half-day LEAVE; the HR-marked half now shows in the line above it
hrms/api/calendar.py:attendance month view not-affected — reads Attendance.status directly and already shows Half Day (calendar legend)
