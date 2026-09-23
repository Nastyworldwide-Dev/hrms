CLASS: the same team summary drawn twice (AUDIT-PLAN "Team line", ruling 1:
the day sheet's line is the door, the Team page is the room, no repeat).

Surfaces and verdicts:
frontend/src/components/DaySheet.vue — same-root: names list + four-tile coverage grid replaced by ONE line (utils/teamLine.js) that opens Team for that date.
frontend/src/views/team/TeamDashboard.vue — same-root: opens on ?date= (dateFromRoute), and its four-tile strip is cut; the page starts with the names.
frontend/src/utils/teamLine.js — new, pure; words per the plan's table (past / today / future / all in), non-zero parts only.
