GOAL: TruTrip (business travel) is one tap away on More, with its own icon, for every employee.
DONE WHEN: More shows a "Travel" group with a TruTrip row (plane icon, arrow-out badge) that opens https://app.trutrip.co/v2/login in a new tab with noopener, through an https host allowlist kept apart from the same-origin app list.
CHECK: node --test frontend/src/data/__tests__/externalLinks.test.js; live on fresh.local as an employee: tap opened app.trutrip.co/v2/login in a new tab, window.opener null, the app stayed on /hrms/more.
