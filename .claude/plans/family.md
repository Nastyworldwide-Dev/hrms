CLASS: two words for one person on one day (review of 391ccefbb). The day
sheet line said "1 not marked"; the Team page showed that person Absent
("No punch · no leave filed").

Surfaces and verdicts:
frontend/src/utils/teamLine.js — same-root: past days count nobody-marked as absent (the Team page's word); today keeps "not in yet" (the Team page's word too).
frontend/src/views/team/TeamDashboard.vue — not-affected: its words are the reference.
