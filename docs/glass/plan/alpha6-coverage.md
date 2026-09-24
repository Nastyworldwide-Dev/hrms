# alpha.6 coverage — is it 100%?

The owner asked (24 Sep): "are you sure? 100%? small, medium to big, back and
forth, top to down?" This is the answer as a list, not a feeling. Every row is
**measured** (with the tool that measured it), **n/a** (and why), or
**missing** (and why it could not be measured here).

Tools: `frontend/e2e/alpha6-audit.mjs` (every route: type, colour, controls,
words, targets, overflow), `frontend/e2e/alpha6-sheets.mjs` (opens every sheet),
`frontend/e2e/alpha6-journey.mjs` (staff files, approver decides, through the
screens), `scripts/journey_every_request.py` (the same, server rules, 87 checks),
the design gates (`design/gates/run.mjs`), the motion/sheet e2e specs, and the
unit suite (1231 tests). Site: fresh.local, 25 Sep 2026.

## 1. Every route (52 in the router)

| Route | Status | By |
|---|---|---|
| /home, /requests, /dashboard/attendance, /dashboard/leaves, /dashboard/expense-claims, /dashboard/kpi, /more, /profile, /notifications, /change-password, /hr-contacts, /approvals, /remote-approvals, /support (help hub), /team, /team/roster, /announcements, /sop, /invalid-employee | measured | audit (phone dark + light, desktop) |
| every list: /leave-applications, /attendance-requests, /shift-requests, /expense-claims, /ot-requests, /shift-assignments, /employee-checkins | measured | audit |
| every new form: /leave-applications/new, /attendance-requests/new, /shift-requests/new, /expense-claims/new, /ot-requests/new, /issues/new, /helpdesk/new | measured | audit + screen journey (5 request types filed) |
| every detail: /leave-applications/:id, /attendance-requests/:id, /shift-requests/:id, /expense-claims/:id, /shift-assignments/:id, /issues/:id | measured | audit |
| /ot-requests/:id, /sop/:id, /announcements/:id, /helpdesk/:id | measured when the site has one; the journey creates an OT request each run | audit resolves ids from the site |
| /login | measured | alpha.5 capture (anon); login is outside the signed-in audit |
| / , /form , /settings , /issues , /hr/issues , /replacement-leave/* , /:pathMatch(.*)* | n/a | redirects (to /home, /profile, /support, /requests) or the 404 page; no screen of their own |
| /design | n/a | the design specimen for developers, not in any menu |

## 2. Every sheet a person reaches

| Sheet | Status |
|---|---|
| New request, All balances, Check in, Public holidays, Your details, Who to ask, New expense item, Approval, Answered | measured: alpha6-sheets.mjs 9/9 clean (Close leading, titled, no jargon/email/heavy, fits, closes) |
| Calendar day sheet | measured: sheet-is-tappable + sheet-leaves-with-page specs (passed) |
| Link search picker (people, types) | measured through forms: title-only labels (forms-native-kit test) |
| Reject reason confirm | measured: journey declines with a reason on every type |
| Delete / Cancel confirm (GConfirm) | measured by unit tests; not tapped in a journey |
| "⋯" menu on a sent request (frappe-ui Dropdown) | **partly**: target is 44px now; the menu itself is still frappe-ui — ticket `.claude/plans/ticket-formview-restructure.md` |
| Install prompt, push prompt, late check-out, strict-rejection, remote check-in dialogs | **missing**: need a phone state (install eligibility, a real out-of-area punch, notification permission) the headless browser cannot produce; unit-tested only |

## 3. Every person

| Person | Status |
|---|---|
| Staff | measured: audit, sheets, journeys |
| Approver (named leave approver) | measured: audit, sheets, journeys |
| Manager up the chain | measured: server journey (sees and may decide) |
| HR | measured: server journey (sees the queue) |
| Someone with no shift / no approver / new joiner | measured on the server side (readiness checks, "No shift today" rule tests); not walked through the screens |

## 4. Sizes, themes, engines

| | Status |
|---|---|
| 390 phone, dark and light | measured (audit) |
| 1280 desktop, dark | measured (audit) |
| 320 narrowest phone | measured for Calendar, Time off, Fix a day (no sideways scroll); reflow-320 spec exists |
| 430 large phone, tablet | **missing** from the audit's loop; layouts are single-column fluid below 1024 |
| Real Safari (WebKit) | **missing**: the machine lacks WebKit's system libraries (`sudo npx playwright install-deps webkit`). The iPhone-only date-field drag is fixed from documented evidence; confirm on the phone after deploy |

## 5. Motion (back and forth)

| | Status |
|---|---|
| Push / back / tab switch / desktop section switch | measured: nav-motion.spec.js 3/3 |
| Sheet open / close / dim area / leaving with Back | measured: sheet-closes 5/5, sheet-leaves-with-page 3/3, sheet-is-tappable 3/3 |
| Back then navigate before it lands | measured: back-race (passes alone at 7 rounds; failed once under full parallel load) |

## 6. Every request, both sides

| | Status |
|---|---|
| Time off, Fix a day, Shift change, Expense, Overtime — staff files, approver approves / rejects, staff sees it | measured: server 87/87, screens 10/10 |
| Time off in lieu (filed in Desk) — approver decides | measured: server |
| Check-in outside the area — approver decides | measured: server |
| Replacement leave claim | n/a — retired by owner ruling 23 Sep (no banked overtime) |
| Employee Advance | n/a — hidden by owner ruling 15 Sep |
