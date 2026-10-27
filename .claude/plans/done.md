GOAL: the notice page shows posted/until, the summary as a lead, the cover picture, and for an Event its When row (owner-approved mockup 27 Oct).
DONE WHEN: Detail.vue draws those; payload carries event_date; must-read flow unchanged.
CHECK: node --test frontend/src/views/announcements/__tests__/Detail.notice.test.js frontend/src/components/__tests__/must-read-tickbox.test.js; pytest hrms/api/test_announcement_payload_event_date.py
