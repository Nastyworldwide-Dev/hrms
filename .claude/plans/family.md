CLASS: a list row that predates alpha.6 (bold time as the title, In/Out as coloured chips, the day repeated on every row)

Instance: plan §2 0.8 — Your check-ins list.

Sites:
- frontend/src/components/EmployeeCheckinItem.vue — same-root (a grouped row: In/Out leading, time trailing grey, chevron)
- frontend/src/components/ListView.vue Employee Checkin branch — same-root (groups by site day under Today/Yesterday/Tue 22 Sep headings)
- frontend/src/utils/dayGroups.js — new (groupByDay keeps server order; dayHeading)
- the other ListView doctypes — not-affected: they keep GListPanel rows; their redesign is Phase 3 (lists)
- the filter as a glass bar button — ticket Phase 1 (every bar button changes there, not one screen alone)

Locked: utils/__tests__/dayGroups.test.js (3). Verified in WebKit: headings by day, rows 44 pt, tap opens the check-in sheet, no page errors.
