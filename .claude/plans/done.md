GOAL: screens use plain, non-repeating words and lists sort by when a request was sent
DONE WHEN: own request hides Who/Company; list titles drop "Your"; posting date reads "Sent on"; lists default to creation desc
CHECK: cd frontend && node --test src/components/__tests__/request-detail-names.test.js src/components/__tests__/list-failure-is-not-empty.test.js
