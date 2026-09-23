CLASS: a server time cut at five characters. The server sends "9:00:00" for
a one-digit hour; `.slice(0, 5)` leaves "9:00:" (live audit 23 Sep: day
sheet "9:00:–18:00").

Call sites (grep `.slice(0, 5)` across frontend/src and hrms/api):
frontend/src/components/DaySheet.vue trimSeconds — same-root, fixed (clockTime).
frontend/src/views/team/TeamDashboard.vue formatTime — same-root, fixed (clockTime).
No other time is cut by position.
