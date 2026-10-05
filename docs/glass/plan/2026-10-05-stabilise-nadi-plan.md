# Stabilise Nadi, keep Desk in good hands (plan, 5 Oct 2026)

Plan only. No code in this document. Written after a coverage audit of every route, every request type and
the iOS/Android and Desk sides. **Not tested on a real phone.** Evidence is code reading, the app's own audit
baselines and probes on the test site. Where something is not proven it says UNVERIFIED.

Sources (all in the repo or /tmp/cov while this session lives): docs/glass/audit-2026-09-21.md (8 Critical,
26 High, 46 Medium, 40 Low, carried in, not re-found), the three hunts of 5 Oct, design/*-baseline.json,
and three coverage matrices (screens, flows, platform+Desk). The matrices are PARTIAL: about 60 flow cells and
12 Desk cells are UNVERIFIED (Shift Supervisor reach, per-type form-to-validate trace, back gesture, font scaling).

## 1. What "stable" means (the standard every screen is held to)

A person must always know four things: **what is happening, whether it worked, what happens next, how to get
out.** Every screen and request needs these states, with a plain sentence for each:

| State | Standard | Where Nadi stands |
|---|---|---|
| Loading | placeholder, never a blank | mostly yes |
| Empty | a sentence that says why and what to do | mostly yes |
| Error | "Try again" with a reason a person can act on | mostly yes; RequestActionSheet has no error line |
| Offline | banner AND a clear failure on submit | banner yes; a submit made offline has no clear failure, no queue |
| Expired session | one clear "you were signed out" | NO: the Submit tap does nothing (AU-2) |
| Slow / stale | pull-down refresh where data moves | on 6 screens; missing on 9 (below) |
| No access | a plain "you can't open this" with a way back | missing on detail views (KpiDetail shows nothing) |
| Double tap | guarded | yes on forms (pending button); no server key for Expense Claim / Comp Leave |

Request life: **Filed (Waiting) -> Approved or Rejected (with reason) -> Cancelled.** Each change must say who is
told, what the employee sees, and what attendance or balance moves. Nadi and Desk use the SAME word for each
(Waiting / Approved / Rejected / Cancelled; expense: Approved - unpaid / Paid). Done 5 Oct.

## 2. Already fixed on 5 Oct (do not reopen)

Rejection reason shown to the employee (feed and phone) · a request with no named approver reaches the line ·
leave reason read only by approvers/HR · System Manager cannot decide another company's check-in ·
push token handed back on logout (AU-1) · bulk approve · HR change shift from a date · half day on the team
line · overtime wording, claim box, half-hour rule + old claims cut · Desk wording for 8 request types ·
roster shift picker. Three of these are local and unpushed (Remote check-in, Expense Claim, pill filter).

## 3. The plan, in stages (one cause per commit, red test first, reviewed, never pushed without your word)

### Stage 0: land what is built
Push the 3 local commits; deploy; run the 3 after-deploy checks (Desk Leave list says Waiting; roster picker
lists every shift; a 1.37 overtime claim saves as 1.0). Check the live site for a Workflow on Leave/Expense that
would override the Desk wording.

### Stage 1: stop people being misled (highest harm, small each)
1. **AU-2 signed-out message.** A Submit after the session expired must say "You were signed out. Sign in
   again; your form is kept." Today it does nothing.
2. **Duplicate filing, Expense Claim only.** Comp Leave already refuses an overlap on its dates
   (compensatory_leave_request.py:46), Shift and Leave have overlap guards. Expense Claim has NO duplicate
   guard (nothing found in expense_claim.py), so a slow network plus a second tap can file the same claim
   twice, and a claim pays money. Needs a ruling: block or warn.
3. **Pull-down refresh on 9 screens:** Notifications, Team, Roster, Attendance dashboard, Leave dashboard,
   Issues, Helpdesk (Profile and More left alone). Same GPullRefresh Home already uses. This is the "pull down
   does nothing" report. Each screen needs its own reload step.
4. **Counts:** request_counts leaves out Compensatory Leave Request, so the employee's chips undercount.
5. **Stale-decision guard:** decide() skips the revision check when a client omits expected_modified
   (approval.py:625). Make it required.
6. **Inactive requester:** CLOSED, checked in code for all seven request types (Leave, Expense, Shift,
   Attendance Request, OT, Replacement Leave, Comp Leave): each calls validate_active_employee.
7. **Approver on leave:** requests wait silently. Needs a ruling (delegate, or skip to the next level).

### Stage 2: platform (iPhone and Android installed app)
1. **Update after a deploy.** A new build only takes over while the app is hidden, so an app left open stays on
   the old build. Add a quiet check on launch and on return to the app. Owner removed the "new version" bar, so
   no popup.
2. **AU-5 stale cached page** on slow networks (4 s timeout serves the last page and its CSRF token): clear it
   when the session ends, not only on login/logout.
3. **Offline submit:** a clear failure sentence at minimum; a queue only if you want one (ruling).
4. **Android gate.** The iOS gate runs in Safari's engine; there is no Android equivalent and no gate for push,
   deploy-update or expiry. Add them. Nothing here replaces testing on two real phones.
5. Back gesture and font scaling: UNVERIFIED, add to the gate.

### Stage 3: Desk in good hands (Shift Supervisor, HR)
1. **Verify Shift Supervisor reach** per Desk doctype (Employee Checkin, Attendance, Fix Day, request lists):
   no permission matrix exists. Build one, probe each as a real Supervisor account.
2. Wording is done for 8 types; confirm on the live site after deploy.
3. Remote Checkin list duplicates indicator logic (drift risk): fold into one rule.
4. The ~20 non-attendance reports are not role/row-scope audited. **You deferred this on 13 Sep.** Listed here
   so it is not forgotten; I will not open it without your word.
5. Keep Desk list-script ownership (one owner per doctype) and the "ship a patch with a JSON change" rule.

### Stage 4: the UX standard itself (measured debt, in this order)
1. **Accessibility, 32 axe findings on 9 screens:** 16 unlabelled form fields, 10 wrong ARIA attributes,
   2 unnamed buttons, 2 dialogs without a name, 2 small tap targets. Screen readers hit these first.
2. **Detail views with no "no access" screen**, RequestActionSheet with no error line, Item components with no
   truncation (long Malaysian names and reasons at 360px).
3. **25 hand-made controls** (16 buttons, 5 inputs, 4 selects) moved onto the shared components; Feather icons
   (1 file) onto Lucide.
4. **Token debt, 234 items** (120 hand-set sizes, 54 hex, 54 raw palette, 4 colour functions, 2 outlines),
   concentrated in theme/variables.css, SopList, Profile, SideNav, CheckInPanel. Lowest risk: the gate already
   blocks new ones.
5. **Forms keep no draft offline** (a long form lost on a dropped connection): ruling on scope.

### Stage 5: keep it stable
Extend the gates so these cannot come back: pull-refresh present on every live screen; every detail view has a
no-access state; submit-after-expiry shows the message; a screens-by-states test that fails when a new screen
lacks a state; an Android run beside the iOS one.

## 4. Rulings needed from you (nothing else is blocked)

1. Duplicate Expense Claim: block the second identical claim, or warn and let it through?
2. Approver on leave: requests wait, or go to the next level after N days?
3. Cancel after approval: nobody is notified for most types today. Who should be, and what does the balance do?
4. Offline submit: clear failure only, or a real queue?
5. Pull-down on Profile, More and Helpdesk: skip (recommended) or add?
6. Reports project (deferred 13 Sep): still deferred?

## 5. What this plan does not cover (honest limits)

- Real-device behaviour. I cannot see an iPhone or Android. Stage 2 is written from code, not observation.
- Amend-after-approval with attendance rebuild: traced for Leave only (works); NOT traced for OT, Attendance
  Request or Expense Claim. First task of Stage 1 if you want it.
- Cancel notifications per type: not traced beyond Leave (which notifies by email setting).
- Wording and flow problems no automated check can see. Most of today's real finds came from people, not gates.
  Expect more; keep a channel open for HR and your boss to report them.

## 6. Order of work if you only do three things

1. Stage 0 (land and verify what exists).
2. Stage 1 items 1, 3 and 4 (signed-out message, pull-down, counts): small, safe, the visible complaints.
3. Stage 2 item 1 (update after deploy): without it, no fix reaches people who never close the app.
