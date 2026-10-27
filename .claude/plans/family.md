CLASS: a per-person browser key (email in the key) kept after logout on a shared phone
frontend/src/data/session.js logout same-root — forgetAllHeights after clearPersonalCaches
frontend/src/utils/installPromptMemory.js not-affected — no person in its key, a device preference
frontend/src/data/employee.js:9 same-root — calls sessionEnded on a lost session; now also forgets the heights through it
frontend/src/data/employees.js:25 same-root — same, through sessionEnded
frontend/src/data/user.js:9 same-root — same, through sessionEnded
frontend/src/router/navigationGate.js:46 not-affected — a comment naming sessionEnded as the one owner
frontend/src/router/navigationGate.js:48 same-root — calls sessionEnded; covered by the one change
frontend/src/router/navigationGate.js:57 same-root — calls sessionEnded; covered by the one change
