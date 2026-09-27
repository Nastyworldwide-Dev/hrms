GOAL: the sheet check catches what the owner saw (a page-coloured box in a sheet, 12 pt row labels) in dark mode, and opens the request sheet from Requests and Time off.
DONE WHEN: sheet audit runs dark AND light in the iOS gate; new rules + 3 new openers; red on the old RequestActionSheet (5 sheets), 0 after the fix.
CHECK: SCHEME=dark node frontend/e2e/sheet-consistency-audit.mjs (old sheet: 5 issues; now 0); SCHEME=light 0
