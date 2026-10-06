# Release 2.0.0-alpha.36 "Loose Ends" (planned 6 Oct 2026)

Owner, 6 Oct: "plan alpha.36 with the small leftovers and any part can be inside it."
Scope: the alpha.35 leftovers plus small, safe parts of the stabilise plan
(docs/glass/plan/2026-10-05-stabilise-nadi-plan.md). Nothing that needs a ruling.

## FLOW
Orchestrator (Opus) writes each slice brief -> implementer (Sonnet, xhigh) builds it test-first, commits
nothing -> orchestrator reviews, runs gates, proves red/green (live browser for UI), commits one cause per
commit -> reviewer -> next slice. Max 3 agents. Then bump + changelog, full suites, push branch,
scripts/release.sh. Owner deploys.

## SLICES
A1  **HR's issue board gets pull-down.** HRIssueBoard.vue (HR users on Help -> HR pill) reloads `issues`
    (+ `detail` if open). Same lazy GPullRefresh. DONE WHEN: unit test pins the wiring; live pull as an HR
    user reloads the board list (Playwright, real request named).
A2  **Attendance pull waits for the month.** AttendanceCalendar.refresh() returns its reload promise;
    attendance/Dashboard awaits it, so "Refreshing..." closes after the days load. DONE WHEN: unit test:
    complete() is called only after the calendar reload resolves.
A3  **A failed Log out cannot hide a later "signed out" banner.** session.logout resets the logging-out mark
    on error. DONE WHEN: test: logout fails -> session ends on its own -> mark is set.
A4  **Saved pages cleared when a session ends on its own (AU-5).** Login clears the offline page copy when
    it shows the "signed out" banner (it is already cleared on login/logout). DONE WHEN: test: banner shown
    -> clearCachedPages called once; plain visit -> not called.
O1  **Approvals list reads leave reasons in one batch.** approvals_list uses may_read_leave_reasons (built
    in alpha.35) instead of one check per row. DONE WHEN: same answers for owner/HR/approver/stranger; read
    count no longer grows per row (test counts calls).
D1  **Shortcut notes name their trigger.** 22 `ceiling:` notes with no `upgrade:` get one, or the note is
    removed if the shortcut is gone. Comments only. DONE WHEN: grep finds none without `upgrade:`.
D2  **Hotspot tickets filed:** session.js + personalCache.js (5 and 3 fixes in 90 days) and
    hrms/api/__init__.py. Tickets only, no refactor. DONE WHEN: two ticket files under docs/glass/tickets.
V1  **Shift Supervisor Desk check (report only).** Probe as a real Supervisor on fresh.local: Employee
    Checkin, Attendance, Fix Day, Roster, each request list: open / create / edit / delete. Output a table in
    docs/glass/audit/. Fixes go to alpha.37. DONE WHEN: table with every cell filled, each from a real request.

## NEEDS OWNER YES (pipeline, not app code)
G1  The commit gate runs Playwright e2e specs with bun, so they always fail. Change: skip frontend/e2e/*.spec.js
    in the bun runner (Playwright runs them on the test site instead). Then land the 7-screen pull-refresh spec
    (copy at /tmp/wip_s2spec/). Harness change -> measured with evals/ab.sh per CLAUDE.md.
G2  Add .claude/.no-release-gate in this repo so the release check stops asking to push the local safety tag.

## NOT IN THIS RELEASE
Rulings 1-5 (duplicate expense, approver on leave, cancel notices, offline queue, reports). Screen-reader
fixes (32), token debt (234), hand-made controls (25), "no access" screens, Android gate, amend-after-approval
trace. Remote check-in list: checked 6 Oct, one indicator rule only, nothing to merge.

## MOCKUP: NOT NEEDED (no new screen: one existing pull indicator on one more screen)

## EXPECTED OUTPUT
8 commits (A1-A4, O1, D1, D2, V1 report), each reviewed; then chore(release): 2.0.0-alpha.36 with a plain
changelog. Frontend + Python stub suites green, build OK, pull-refresh live on the HR board.

## RISKS
- A4 touches the login path: clear runs only when the banner shows; a failed clear never blocks sign-in.
- O1 changes who reads leave reasons in the approvals list: the test compares old vs new answers.
