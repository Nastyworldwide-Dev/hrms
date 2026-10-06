# Release 2.0.0-alpha.37 "Clear Screens" (planned and approved 6 Oct 2026)

Owner, 6 Oct: "plan for next release". Scope: Stage 4 of docs/glass/plan/2026-10-05-stabilise-nadi-plan.md
(the screens' own standard), the hotspot ticket that is small enough to do safely, and the one gate
problem that keeps costing time. Nothing that needs a ruling.

## FLOW
Same as alpha.35/36: Opus orchestrator briefs -> Sonnet implementer (xhigh) builds test-first, commits
nothing -> orchestrator reviews, proves red/green (live browser for UI), commits one cause per commit ->
reviewer -> next. Max 3 agents. Then bump + changelog, full suites, push branch, scripts/release.sh.

## SLICES
B1  **Screen readers: the 16 serious findings on 9 screens** (design/a11y-baseline.json, counted once, not
    light+dark): 8 form fields with no label, 5 wrong ARIA attributes, 1 unnamed button, 1 dialog with no
    name, 1 tap target under 24 px. Screens: attendance-requests, expense-claims, leave-applications,
    shift-assignments and issues detail; expense-claims, OT and replacement-leave new; invalid-employee.
    Fix in the shared component where the finding comes from (one fix, many screens), not per screen.
    DONE WHEN: design/gates/a11y.mjs on fresh.local reports 0 serious/critical on those screens and the
    baseline file shrinks to empty for them; no visual change (screenshot diff on the 9 screens).
B2  **"You can't open this" instead of a blank screen.** A detail page the person may not open (KPI detail
    today renders nothing on a 403) says so in plain words with a way back. ResourceError learns the
    no-access case once; every detail view already using it gets it free; KpiDetail starts using it.
    DONE WHEN: unit test: a 403 resource -> "You can't open this." + Back; live: a staff user opening
    another person's KPI sees the sentence (Playwright).
B3  **Long names and reasons don't break rows at 360 px.** List item components truncate with an ellipsis
    and keep the full text for screen readers. DONE WHEN: a 60-character Malaysian name renders on one line
    in the request, approval and team rows at 360 px (Playwright screenshot), full text in aria-label.
R1  **One owner for "the session ended"** (ticket docs/glass/tickets/2026-10-06-session-identity-hotspot.md):
    five places decide it today. One function marks, clears the offline page and reloads; user.js,
    employees.js, navigationGate.js and logout call it. DONE WHEN: grep finds `name: "Login"` only in the
    router and that function; a test per caller; the alpha.35 live probe (session killed, tap) still shows
    the banner.

## NEEDS OWNER YES
P1  **The commit hook keeps sweeping other files into a commit** (3 times this week, each undone by hand,
    nothing lost). Find where (pre-commit-lint stages `git add -u` on the commit's files; something else
    adds the rest) and make a commit hold only the files it names. Pipeline repo change, test-first, like G1.
T1  **Test-site accounts** on fresh.local only (never the live site): (a) set a password on the existing
    test HR persona to check HR screens live; (b) make one test employee a Shift Supervisor with 2 reports,
    so the Desk supervisor check (V1 from alpha.36) can finally run. Both were refused without your word.

## NOT IN THIS RELEASE
Rulings 1-5 (duplicate expense, approver on leave, cancel notices, offline queue, reports). Token debt
(234) and hand-made controls (25): big, low harm, next. Android gate. hrms/api/__init__.py split (ticket).

## MOCKUP: NOT NEEDED (no new screen; B2 is one sentence in the existing error block, B3 is an ellipsis)

## EXPECTED OUTPUT
4 app commits (B1 may be 2-3: one per shared component), P1 in the pipeline repo, V1 report if T1 is yes;
chore(release): 2.0.0-alpha.37. Suites green, a11y gate 0 serious on the 9 screens.

## RISKS
- B1 touches shared form components: the visual gate must show no change.
- R1 touches the session path (hotspot): behaviour must stay exactly as alpha.36; the live probe is the proof.
