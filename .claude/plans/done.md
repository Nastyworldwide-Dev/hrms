GOAL: the check-in screen measures against the site the server will judge by — for someone HR lets check in at more than one site, the one they are inside, else the nearest.
DONE WHEN: CheckInPanel reads activeShiftLocation through nearestSite(payload with other_sites, current fix); one site behaves exactly as before.
CHECK: node --test frontend/src/utils/__tests__/nearestSite.test.js; yarn --cwd frontend test (1545 pass, incl. the CheckInPanel location harness).
