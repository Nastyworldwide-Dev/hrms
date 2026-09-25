GOAL: request details say the person's name, and drop Company on your own request (alpha.9 D10, D11)
DONE WHEN: approver sees "Who W0 employee" on all 5 request types; employee sees no Company row
CHECK: node --test frontend/src/components/__tests__/request-detail-names.test.js
