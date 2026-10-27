GOAL: the announcement board draws each notice like Home (tile, summary, badge, age), To confirm then Latest (owner-approved mockup 27 Oct).
DONE WHEN: List.vue and Home share utils/announcementRow.js; board sections "To confirm · N" / "Latest", urgent first; Home output unchanged.
CHECK: node --test frontend/src/utils/__tests__/announcementRow.test.js frontend/src/views/announcements/__tests__/List.board.test.js frontend/src/components/__tests__/announcement-cards-a7.test.js
