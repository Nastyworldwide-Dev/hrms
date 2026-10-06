# Release 2.0.0-alpha.35 "Steady Nadi" (6 Oct 2026)

Owner, 6 Oct: "plan for next release to cover optimisation, tech debt and bug fixes; this will be the release
I deploy, including the past ones. Once planned, execute with a Sonnet implementer."

The release ships everything since alpha.34 (57 commits already on origin: approvals bulk + filter, HR shift
change, access fixes, rejection reasons, half day, OT wording + half-hour rule + cleanup patch, Desk wording for
8 request types + expense pill patch, roster picker, check-in status line, pull-down/scroll) PLUS the slices
below. Source of truth for scope: docs/glass/plan/2026-10-05-stabilise-nadi-plan.md (Stages 1, 2, 4) and the
owner's rulings of 5-6 Oct. Nothing that needs a new owner ruling is in scope.

## FLOW

Orchestrator (this session, Opus) writes each slice brief -> `implementer` (Sonnet, xhigh) builds it test-first,
commits nothing -> orchestrator reviews the diff, runs the gates, proves red/green (live browser for UI
behaviour), commits one cause per commit -> reviewers (Sonnet/Haiku) -> next slice. At most 3 agents at once.
After the last slice: version bump + changelog, full unit suites + the e2e gates on the test site, push the
branch, scripts/release.sh (tag v2.0.0-alpha.35 + GitHub Release). Deploy is the owner's (Frappe Cloud).

## SLICES (ordered by user harm; each one commit, red test first)

### Bugs people hit
S1  **Signed out mid-form says so.** A Submit/decision after the session expired does nothing today
    (loudRequest SILENT_EXCEPTIONS hides SessionExpired/AuthenticationError and no navigation follows).
    Fix: on the FIRST session-lost failure of a WRITE (POST) the app shows one message "You were signed out.
    Sign in again to continue." with a Sign in action that keeps the URL to come back to; the form's typed
    values stay on screen until the person leaves. Read-only background failures stay silent (a burst of them
    must give ONE message, not N). Files: frontend/src/utils/loudRequest.js (+test), maybe utils/sessionLost.js.
    DONE WHEN: a unit test feeds loudRequest a SessionExpired on a POST -> exactly one notice with the sign-in
    action; a GET -> no notice; two in a row -> one notice. Live: on fresh.local, expire the session cookie,
    tap Submit on a leave form -> the message shows (Playwright).
S2  **Pull-down on the screens that lack it:** Notifications, Team, Roster, Attendance dashboard, Leave
    dashboard, Issues list, Helpdesk hub. Same GPullRefresh, each screen reloads ITS resources and completes
    the refresher. Profile and More left alone (plan ruling 5 recommended skip). Files: those 7 views.
    DONE WHEN: e2e/pull-refresh.spec.js SCREENS grows to the 11 screens and passes on fresh.local; each new
    screen's assertion names a request that screen really makes.
S3  **Counts include Compensatory Leave** (request_counts DECISION_FIELD omits it; the employee's chips
    undercount). File: hrms/api/request_counts.py (+test). DONE WHEN: a stub test counts a Comp Leave row in
    waiting/approved/rejected; the list in request_counts equals approval.DECIDE_THEN_SUBMIT's keys (one rule:
    the test derives one from the other, not a hand list).
S4  **A decision always carries the revision the approver saw.** decide() skips the stale check when
    expected_modified is missing (approval.py:625). Every caller already sends it (PWA sheet, FormView, Desk
    request_approval.js, approved_request_cancel.js, decide_many). Make it required: a missing value is
    refused with "Reload and try again." Files: hrms/api/approval.py (+test). DONE WHEN: a test calls decide
    without it -> ValidationError; with a stale one -> refused; with the right one -> decided. Grep proves
    every caller sends it (list them in family.md).

### Optimisation
O1  **Leave list N+1.** get_leave_applications calls may_read_leave_reason per row: one Employee->company
    get_value per row for HR, one routing check per row for approvers (50 rows = 50+ queries). Batch: read the
    companies of the distinct employees once, and decide per distinct (employee) not per row. Same answers.
    File: hrms/api/__init__.py and/or approval.may_read_leave_reason (+test). DONE WHEN: a test with 50 rows
    for 3 employees counts at most 3 company reads (patched frappe.db.get_value / get_all call count), and the
    blanked/kept descriptions are identical to the per-row version for the same fixtures (owner, HR, approver,
    stranger).
O2  **Update after a deploy reaches an app left open.** A waiting build applies only while the app is hidden;
    an app kept in the foreground never updates. Add: registration.update() on launch and when the app returns
    to the foreground (visibilitychange -> visible, at most once per 30 min), so a new build is FOUND; it
    still APPLIES only while hidden (owner: no update popup, never under a half-written form). File:
    frontend/src/data/swRegistration.js (+test). DONE WHEN: a unit test with a fake registration: becoming
    visible calls update() once, twice within 30 min calls it once; the skip-waiting-only-while-hidden rule is
    unchanged (existing test stays green).

### Tech debt
D1  **Repo hygiene.** Delete the 13 throw-away probe scripts frontend/e2e/live-*.mjs (their findings are in
    progress.md and the two real gates). Commit the two untracked, passing tests from 5 Oct
    (src/utils/__tests__/countWords.test.js, src/views/__tests__/notifications-reason.test.js) after reading
    them. Fix the pre-existing red test no-jump-placeholders ("an empty queue..."): it expects single quotes,
    Approvals.vue renders double: assert the words, not the quote style. DONE WHEN: `git status` shows no
    untracked source/test files outside .claude; the components test suite is fully green.
D2  **One icon library.** Feather is left in 2 files (main.js, GIconButton.vue); everything else uses Lucide.
    Move them to Lucide and drop the Feather import if nothing else uses it. DONE WHEN: grep finds no
    feather-icons/FeatherIcon in frontend/src (except comments); the app builds; GIconButton's test green.
    (Roster app untouched: it uses frappe-ui's own FeatherIcon.)
D3  **Ceiling markers without an upgrade trigger** (27 found by the pipeline). For each in files this release
    touches, add the `upgrade:` trigger or delete the shortcut. Others listed in a ticket, not touched (no
    drive-by refactors). DONE WHEN: grep of touched files shows no `ceiling:` without `upgrade:`.

## NOT IN THIS RELEASE (need a ruling, or too big; listed so they are not forgotten)
Duplicate Expense Claim guard (ruling 1), approver on leave (2), cancel notices (3), offline queue (4), reports
fencing (6, deferred 13 Sep), Android/real-device gate, AU-5 stale cached page (needs a design: when to clear),
amend+rebuild trace for OT/Attendance Request/Expense, the 32 a11y + 234 token debt items, realtime fan-out for
the other useListUpdate callers (ticket), list second-page gate (ticket).

## MOCKUP: NOT NEEDED (no new screen or layout: one notice in an existing component, an existing pull indicator on 7 more screens)
No new screen. Two visible changes, both using existing components and copy rules:
- S1: one GBanner/gToast-style notice: "You were signed out." / "Sign in again to continue." + a "Sign in"
  action (same component the app uses for "Something didn't load").
- S2: the existing pull indicator ("Pull to refresh" / "Refreshing...") on 7 more screens. Nothing else moves.

## EXPECTED OUTPUT
- 9 commits (S1-S4, O1-O2, D1-D3), each reviewed, each with its family.md entry; then `chore(release):
  2.0.0-alpha.35` with the changelog entry naming every change since alpha.34 in plain words.
- frontend unit suites green (node --test), python stub tests green per file, ruff clean, vite build OK.
- e2e on fresh.local: pull-refresh (11 screens) + list-scroll + a session-expiry spec green.
- origin/nz-glass at the release commit; tag v2.0.0-alpha.35 + GitHub Release; safety tag stays local.
- A HANDOFF.md per the project CLAUDE.md, and a deploy checklist for the owner (what to check on the phone).

## RISKS
- S1 touches the one request seam every call goes through: only POSTs + session-lost errors change behaviour;
  a test pins that a normal error still toasts once and a GET still stays silent.
- S4 refuses decisions without a revision: any caller that does not send it breaks. Mitigation: grep every
  caller (done in planning: 6 senders), the Desk test request_approval.test.js stays green.
- O2 must not reintroduce the "update bar" or apply a build under a form.
