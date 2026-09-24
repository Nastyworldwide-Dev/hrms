CLASS: a duration written as a unit abbreviation ("1d", "0.5d") instead of words

Instance: plan §5.3 A16/B4 — list rows read "15 Sep · 1d".

Sites:
- frontend/src/components/LeaveRequestItem.vue — same-root
- frontend/src/components/AttendanceRequestItem.vue — same-root
- frontend/src/components/ShiftRequestItem.vue — same-root
- frontend/src/components/ShiftAssignmentItem.vue — same-root
- frontend/src/utils/countWords.js countOf — not-affected: already words; daysWords added beside it

Locked: utils/__tests__/daysWords.test.js (3).
