GOAL: on a shared phone, nobody can open the previous person's /hrms page from the offline copy.
DONE WHEN: the "nadi-pages" cache is deleted at logout and at login; browser proof: /hrms/home copy gone after logout.
CHECK: node --test frontend/src/utils/__tests__/cachedPages.test.js; Chromium: before [/hrms/home], after logout only a Guest-rendered page
