GOAL: every section-header link looks the same, set in .g-seclink; in-sentence links share .g-backlink (design audit 27 Oct, finding 5).
DONE WHEN: no screen adds style classes to .g-seclink; computed style identical on Leave, Expense, Team; in-sentence links keep a 44 px target.
CHECK: node --test frontend/src/components/__tests__/section-link-one-look.test.js; Playwright measure on /dashboard/leaves, /dashboard/expense-claims, /team.
