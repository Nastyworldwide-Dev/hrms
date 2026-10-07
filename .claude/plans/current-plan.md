# Release 2.0.0-alpha.41 "Clean Glass" (approved 7 Oct 2026: owner "Approve as written", E1a, E2a)

Owner, 7 Oct: "plan the release and i think we should cater all, as these are frontend ui ux engineering works."
Scope = every UI/UX debt item in the 7 Oct list (14 items). Frontend + Desk list scripts only; no pay or
attendance rule changes. One release, built in slices, one deploy at the end.

## Facts measured 7 Oct (not assumed)
- `yarn gates` (CI "Glass gates") fails for two reasons:
  (a) REAL failures: tokens — 4 NEW colour collapses (--g-on-badge equals 4 other tokens);
      scale — 23 off-grid sizes in theme/glass-components.css; motion — 1 duration off the scale, and
      Approvals.vue:700-717 uses var(--g-ink-3), var(--g-accent), var(--g-ink-2): DEFINED NOWHERE, so the
      browser drops those colours today (a live defect hidden by the red check).
  (b) 4 gates (a11y, visual, coherence, ios) "measured nothing": CI has no served site / AUDIT_PW.
- Request detail (FormView.vue) is mostly Glass already: only frappe-ui ErrorMessage is left
  (ticket-formview-restructure.md is out of date).
- GSelect already takes [{label, value}] — the filter-word fix is small (ticket-waiting-word-in-filters).
- design/lint-baseline.json: 234 hard-coded values in 39 files (arbitrary 120, raw palette 54, hex 54,
  colour fn 4, outline 2). Top: theme/variables.css 47, SOP screens 39, Profile 17, CheckInPanel 16.
- design/token-collapse-baseline.json: 15 accepted collapses (+4 new above).
- Android Back with a sheet open closes the sheet AND goes back (router/sheetGuard.js ceiling). Blocked
  upstream in @ionic/vue-router 7.4 (pending pop not cleared on a cancelled navigation).

## SLICES (one cause per commit; tests first; live check per slice)
S1 Gates go green honestly (item 11)
   - Approvals.vue: map --g-ink-3/--g-accent/--g-ink-2 to real tokens (the dropped colours come back).
   - --g-on-badge: give it its own value or fold it into the token it equals; update the baseline only for
     collapses that are by design, with a reason per entry.
   - 23 off-grid sizes onto the 4 pt grid; 200ms -> a motion-scale step.
   - CI: the 4 site gates are marked "needs a site" and SKIPPED with a visible line, not failed, so the
     board is green only when the measurable gates pass. They run locally before release (step R).
S2 One word for waiting (item 1): Leave and Shift Request filters show Waiting/Approved/Rejected, send the
   stored value ({label, value} through FormField -> GSelect).
S3 Desk words (item 2): Remote Checkin Request list says Waiting, not Pending (a *_list.js indicator).
   Expense Claim: Desk states follow Nadi ("Approved · unpaid", "Paid") via the doctype states with a
   guarded patch (Property Setter trap). NEEDS RULING E1 below.
S4 Request detail finished (item 3): ErrorMessage -> the Glass error line; drop the allow-list entry and
   the stale ticket.
S5 Android Back (item 4): Back with a sheet open closes only the sheet. Try a router-side fix that does not
   cancel the popstate (re-push the current route after dismiss); if Ionic's pop state still breaks the
   next animation, keep today's behaviour and record why (ceiling stays, upgrade trigger named).
S6 Help search (item 5): search asks the server, not only the loaded rows.
S7 Partial loads say so (item 6): RequestPanel shows "Some details didn't load. Pull to refresh." when a
   part fails but rows exist.
S8 Hard-coded styles -> tokens (item 7): the 234 values in 39 files, worst first (variables.css, SOP,
   Profile, CheckInPanel, then the rest). Lint baseline shrinks per commit; target 0 or a named reason each.
   Visual gate before/after per screen (no visible change unless it fixes a dark/light mismatch).
S9 Light/dark collapses (item 8): review the 15 accepted pairs; keep by-design ones with a reason, split
   the rest.
S10 Infinite scroll proven (item 9): seed > 1 page for the audit user; e2e asserts start=50 is requested
   and rows grow.
S11 Desk roster live (item 10): Playwright on Desk: month view shows O/R/PH, drag-swap keeps Day Type.
S12 Hotspots (items 12-14), behaviour-neutral refactors with their own tests:
    main.js service-worker block -> utils/serviceWorker.js; approvalToast -> one outcome table;
    attendance_list.js onload -> the Mark Attendance dialog in its own module.

## RULINGS (7 Oct 2026: E1a Expense words same as Nadi; E2a keep Back behaviour if unsafe, note it)
E1 Expense Claim words on Desk: (a) RECOMMENDED: same as Nadi — Waiting / Approved · unpaid / Paid /
   Rejected; (b) keep Desk's own (Draft, Submitted, Unpaid, Paid).
E2 Android Back: if S5 cannot be done safely on Ionic 7.4, (a) RECOMMENDED: keep today's behaviour,
   note it, revisit on the Ionic upgrade; (b) upgrade Ionic in this release (bigger, separate risk).

## AMENDMENTS (7 Oct, plan review)
P1 S1 Approvals mapping (exact): --g-ink-3 -> --g-ink3; --g-accent -> --g-brand (GCheckbox's checked colour;
   tick text --g-on-brand contrasts in both themes); --g-ink-2 -> --g-ink2. Theme names have no hyphen
   before the digit.
P2 S3 mechanism corrected: expense_claim.json has `"states": []` and Doctype States only drive form badges;
   the Desk LIST pill comes from expense_claim_list.js get_indicator. S3 changes get_indicator (with a test
   that executes it, load-order aware — desk-listview-settings-one-owner), plus a Remote Checkin Request
   *_list.js. No doctype JSON change, so no Property Setter patch.
P3 Step R is a HARD release precondition: `yarn gates` with a served site and AUDIT_PW, all 11 gates
   measured, output saved as an EVIDENCE line. CI skipping the 4 site gates is not a pass.
P4 S8: each value maps to the EXACT equal token (not the nearest); the visual gate runs locally on a served
   site before and after each S8 commit; baseline updates ride in the same commit as the tokens.
P5 S2 test asserts the request payload carries the stored value ("Open"/"Draft"), not the label.
P6 S6 server search: permission-scoped (get_list, never get_all), query escaped / parameterised.
P7 S12: each refactor names its existing test file first (no empty stubs).

## EXPECTED OUTPUT:
- UI: Approvals checkboxes/labels get their colours back; list filters say Waiting; Desk says the same
  words as Nadi; request errors in the Glass style; Help search finds any ticket; a partly loaded request
  says so; light/dark match; Android Back closes only the sheet (or a recorded reason).
- Code: tokens instead of hard-coded values (lint baseline toward 0), gates green in CI, three hotspot
  splits, two new e2e proofs (second page, Desk roster).
- Ships: slices committed one cause each, reviewed; full gates run locally with a served site + AUDIT_PW
  before release (R); release alpha.41 with tag + GitHub Release; owner deploys.

## MOCKUP: NOT NEEDED (no new screens; restyle keeps today's look, the visual gate guards it)

## FLOW
Opus orchestrator briefs -> Sonnet implementer per slice (tests first) -> orchestrator reviews, proves red,
live check -> commit -> reviewer -> next slice. Up to 3 workers in parallel on slices that touch different
files (S1 | S2+S3 | S8 split by file). R: `yarn gates` locally with the site served, then release.

## NOT IN THIS RELEASE
New screens or features; pay/attendance rules; the server-side roster.py / team.py refactors (backend).
