GOAL: no loose lines on Notifications, Who to ask, You (alpha.9 D3, D4, D9)
DONE WHEN: ios-consistency-audit loose-text rule clean on /notifications /hr-contacts /profile /settings
CHECK: node --test frontend/src/components/__tests__/nothing-loose.test.js
