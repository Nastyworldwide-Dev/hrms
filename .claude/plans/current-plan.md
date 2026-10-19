# alpha.57: bug fixes and quality of life (19 Oct 2026)

APPROVED: owner, 19 Oct 2026: "defer the question, proceed the rest"
Full list: docs/glass/plan/NADI_2.0.0-alpha.57_PLAN.md (items 1-9; the two owner questions deferred).

GOAL: fix the open follow-ups from alpha.48-56. No new features, no rule changes.

## FLOW
1. Check-in placeholder sized like the button it stands for (no jump at large text).
2. Compact buttons may wrap at large text; nowrap kept at the default size.
3. Login with no Employee: viewer-role holders start on More; others the existing not-linked page.
4. Announcements company: reproduce first; fix only if red.
5. File row: tick + "Tap to replace" after upload.
6. Time slip: late hint for a night shift after midnight.
7. Status pills role="status".
8. Prettier on AttendanceDownload.vue. 9. SOP document test identity stub.

MOCKUP: NOT NEEDED (no new screen; each change restyles or re-words an existing control in the Glass kit, checked by before/after screenshots)

## EXPECTED OUTPUT
- Default text size: screens unchanged except the file row (tick) and the no-Employee start page.
- Large text: no placeholder jump on Home, no clipped compact button.
- Tests: one red-then-green test per cause; lint 0; frontend tests per file.
- Ships as 2.0.0-alpha.57, no migrate expected.

## Amendment (owner, 19 Oct 2026): announcements in the same release
Owner rulings: nudge on each new announcement; scroll + tickbox only when HR ticks
"Acknowledge required"; audience stays Everyone/Company/Department/Branch (no schema).
10. A notice published with a future Publish From is pushed on that day, not at publish time
    (daily job; on_update pushes only when it is already live).
11. People with notifications off see a "Turn on notifications" line on the board and on a notice.
12. Must-read: a tickbox "I have read and understood this", tickable only after the end is
    reached, then Confirm. Same gate on a notice opened from the board (it had none).
EXPECTED OUTPUT (amendment): no migrate; HR's Desk reach / remind unchanged.

## All balances as rings (owner, 19 Oct 2026)
APPROVED: owner, 19 Oct 2026: "B, build it" (after "mockup, all balance sheet. need a better visual info rather than simple linear text")
MOCKUP: mockups/mockup-nadi-all-balances.html, option B (rings)

FLOW
1. Server: leave rows also carry `allocated` and `taken` (ledger leaves_taken via get_leave_balance_map).
2. All balances sheet: one ring per type, two across; lime = left, grey = taken, bare track = never given/expired; number + "of N" inside; expiry or "N taken" under.
3. One sentence per ring for VoiceOver; the drawing is aria-hidden.

EXPECTED OUTPUT
- Requests page unchanged (two tiles + All balances row); the sheet shows rings instead of text rows.
- Tests: ring-arcs.test.js (runs the maths), balances-rings.test.js, server test for allocated/taken.
