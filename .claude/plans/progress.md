2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
- 2026-09-17T05:42:06Z PUSH: nz-glass @ 926e404ae
- 2026-09-17T05:42:07Z COMMIT: 926e404ae chore(plans): record the final review verdict → review dispatched
- 2026-09-17T05:42:21Z PUSH: nz-glass @ 559b9608a
- 2026-09-17T05:42:21Z COMMIT: 559b9608a docs(glass): handoff for the one-row-per-day work → review dispatched
- 2026-09-17T11:00:00Z REPAIR: geofence — the allowance was `accuracy` up to 250 m and ZERO beyond, so 251 m of reported error cost 250 m of tolerance. Measured before the fix: the same person 80 m from a 50 m fence was ALLOWED at 250 m and sent to remote approval at 251 m. Now min(accuracy, 250) for any reading inside the 2000 m trust cap; past the cap nothing changes.
- 2026-09-17T11:00:00Z EVIDENCE: rung 2 — 7 tests RED first, green after; the cross-language parity property test caught the frontend preview drifting the moment the server changed, and both sides now agree case for case. test_geofence_coordinate_contract's 5 subtest failures are pre-existing — identical count on HEAD's copies of both files.
- 2026-09-17T06:44:37Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-17T06:44:37Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 3 extra test file(s) ⟂17919a97fd02
- 2026-09-17T06:44:57Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-17T06:44:57Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 3 extra test file(s) ⟂17919a97fd02
- 2026-09-17T06:45:10Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-17T06:45:10Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 3 extra test file(s) ⟂17919a97fd02
- 2026-09-17T06:45:33Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-17T06:45:33Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 3 extra test file(s) ⟂17919a97fd02
- 2026-09-17T06:46:04Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-17T06:46:04Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 3 extra test file(s) ⟂17919a97fd02
- 2026-09-17T06:46:06Z EVIDENCE: 6 behaves — family hunt: class=a tolerance expressed as "up to X, then nothing", where the step lands; 2 call site(s) given verdicts, 5 same-root ⟂c74f27e58591
- 2026-09-17T06:46:23Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-17T06:46:23Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 3 extra test file(s) ⟂17919a97fd02
- 2026-09-17T06:46:25Z EVIDENCE: 6 behaves — family hunt: class=a tolerance expressed as "up to X, then nothing", where the step lands; 2 call site(s) given verdicts, 5 same-root ⟂c74f27e58591
- 2026-09-17T06:46:28Z COMMIT: 07a945371 fix(geofence): one metre more error stops costing 250 metres of tolerance → review dispatched
- 2026-09-17T06:54:00Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-17T06:54:30Z COMMIT: 5458850c7 docs(audit): the 8 Sep probe expects the reason the boundary now returns → review dispatched
- 2026-09-17T06:54:37Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-17T06:54:48Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-17T06:54:53Z COMMIT: 06e6f1466 fix(geofence): a coarse reading stops being announced as a precise distance → review+design dispatched
- 2026-09-17T12:00:00Z REPAIR: review Warnings on 06e6f1466 — the RemoteCheckinDialog HEADLINE and both StrictRejectionDialog strings still asserted the verdict in words over a card that had just refused to show the number; and the dialog read the panel's LIVE accuracy after two round trips instead of the reading the server judged. The punch now echoes accuracy_m, like check_geofence already did. `isReadingCoarse` is exported once — three hand-copies were what let this drift twice in a day — and a test fails if any surface re-derives it.
- 2026-09-17T12:00:00Z EVIDENCE: rung 2 — 7 dialog tests, 4 RED against HEAD's copies of both dialogs; every frontend suite green; 499 remote_checkin neighbour tests green (test_day_remark's one failure is the known batch-ordering pollution, green alone).
- 2026-09-17T12:00:00Z NEXT: owner to rule on WITHDRAWAL — every request type already reverses what it granted on cancel (leave ledger, allocation, replacement leave, attendance row, shift assignment), but his own 14 Sep ruling bars the EMPLOYEE from cancelling. Options put to him: (a) employee cancels outright, (b) withdrawal request the approver confirms, (c) self-service before it starts, approver after. Also open: whether strict geofence should stay harsh on coarse readings specifically.
- 2026-09-17T07:01:07Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-17T07:01:24Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-17T07:01:31Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-17T07:01:32Z EVIDENCE: 6 behaves — family hunt: class=a tolerance expressed as "up to X, then nothing", where the step lands; 37 call site(s) given verdicts, 15 same-root ⟂4ae4a89db443
- 2026-09-17T07:01:47Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-09-17T07:01:49Z EVIDENCE: 6 behaves — family hunt: class=a tolerance expressed as "up to X, then nothing", where the step lands; 37 call site(s) given verdicts, 15 same-root ⟂4ae4a89db443
- 2026-09-17T07:01:55Z PUSH: nz-glass @ 265d49afa
- 2026-09-17T07:01:55Z COMMIT: 265d49afa fix(geofence): the words match the number the dialog refuses to show → review+design dispatched
- 2026-09-17T13:00:00Z PLAN: current-plan.md approved — an employee may withdraw their own approved request. Owner answered "withdrawal. a." to the three shapes offered, reversing his own 14 Sep ruling.
- 2026-09-17T13:00:00Z REPAIR: the reverting half already worked for every request type (leave ledger, allocation, replacement leave, Attendance row, Shift Assignment). The DOOR was shut in three places, each with its own copy of "who may cancel": the guard, finalize, and the PWA's cancelRule.js — the last in a file whose own comment says it keeps no copy. may_cancel is now the one routing answer and all three ask it. Two money refusals stay: paid OT, and days inside a submitted salary slip (the employee is told to ask HR; HR is not stopped).
- 2026-09-17T13:00:00Z EVIDENCE: rung 2 — 10 new tests RED first; four suites that pinned the 14 Sep ruling AMENDED, each naming the ruling that replaced it; 126 guard/approval/cancel neighbour tests green, ruff clean, every frontend suite green.
- 2026-09-17T07:13:06Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 13 file(s) ⟂ad7bb4cb625b
- 2026-09-17T07:13:06Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-17T07:13:21Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 13 file(s) ⟂ad7bb4cb625b
- 2026-09-17T07:13:21Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 7 extra test file(s) ⟂aa35cf765c28
- 2026-09-17T07:13:26Z COMMIT: 96962182a feat(requests): an employee can withdraw their own approved request → review dispatched
- 2026-09-17T13:40:00Z REPAIR: review CRITICAL on 96962182a — REQUEST_PERIOD_FIELDS aimed Travel Request at `creation`, the row's save timestamp, so a trip filed after its pay period would have been withdrawable after it was paid. The doctype's dates live on its itinerary child table; it is out of the map on purpose, and absence now REFUSES the employee rather than waving them through. The helper returns the sentence, so "I cannot check" and "it is not paid" stop looking the same.
- 2026-09-17T13:40:00Z EVIDENCE: rung 2 — the new test reads each doctype's own JSON and fails a named field that is not a Date there; it is red against the `creation` entry. 120 guard/approval/withdrawal tests green, ruff clean.
- 2026-09-17T13:40:00Z NEXT: two open flags for the owner — (1) the review could not confirm what happens if a carry-forward expiry or an encashment ran against the allocation BETWEEN approval and withdrawal; worth a bench check before anyone withdraws an old leave. (2) whether strict geofence should stay harsh on coarse readings specifically.
- 2026-09-17T07:20:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T07:20:32Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:20:46Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T07:20:46Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:21:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T07:21:02Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:21:15Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T07:21:15Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:21:26Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T07:21:26Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:21:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T07:21:34Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:21:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T07:21:50Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:21:53Z COMMIT: 7e788e996 fix(requests): the payroll check reads the request's real dates → review dispatched
- 2026-09-17T07:22:13Z COMMIT: f09db725b docs(plans): ticket the approved-request guard hotspot → review dispatched
- 2026-09-17T14:05:00Z EVIDENCE: rung 2 — review of 7e788e996 NEXT_ACTION DEPLOY. It walked all nine decidable doctypes against their own JSON and confirmed no employee can withdraw days inside a submitted salary slip by any of them; Travel Request is refused outright. Its Warning — the JSON test skipped an unreadable doctype silently — is fixed: skips are collected and compared against an EXTERNAL set that is empty on purpose.
- 2026-09-17T07:26:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-17T07:26:53Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:27:09Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-17T07:27:09Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 3 extra test file(s) ⟂c121a8ab8901
- 2026-09-17T07:27:13Z COMMIT: 3f510070e fix(requests): a check that cannot read a doctype says so → review dispatched
- 2026-09-17T07:27:29Z PUSH: nz-glass @ 262f70acb
- 2026-09-17T07:27:29Z COMMIT: 262f70acb docs(glass): handoff for the withdrawal and geofence work → review dispatched
- 2026-09-17T07:48:04Z COMPACT: context compacted — read the last NEXT above before continuing

REPAIR: the "Fix day" (pair/relink) button was registered by fix_day.bundle.js
at boot into frappe.listview_settings["Employee Checkin"], and the doctype's own
list script — which Desk loads when the list opens — assigned that same key
again and threw it away. The owner stood on the page and could not find it.
EVIDENCE: 2 (mapped) — hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js
and hrms/hr/doctype/attendance/attendance_list.test.js now load bundle-then-list
in Desk's real order and ask the resulting onload what it registered; red on
HEAD (1 and 3 failures respectively), green after. 23/23 with the bundle suite.
NEXT: commit, review, then answer the owner's SOP question — his pairing SOP is
what Fix Day already does; it was unreachable from the page he uses.
- 2026-09-17T07:59:16Z EVIDENCE: 2 correct — mapped tests green (bun ) for 10 file(s) ⟂f3b86cf4d3e6
- 2026-09-17T07:59:20Z COMMIT: cba7c3f11 fix(attendance): the pairing screen is reachable from the pages HR uses → review dispatched
- 2026-09-17T08:00:44Z PUSH: nz-glass @ cba7c3f11
- 2026-09-17T08:01:26Z COMMIT: 3e24ccdf8 docs(glass): handoff for the Fix Day entry point → review dispatched
EVIDENCE: 7 (invariant + ticket) — review of cba7c3f11 returned DEPLOY with three
warnings, all closed here: the class invariant now reads hooks.app_include_js
instead of one flat directory and is scoped to the files that can actually lose
the race; the role gate is asserted by name (the harness records which role
string was asked); the attendance_list.js hotspot has a refactor ticket rather
than a seventh inline fix. Both new tests proven by mutation.
NEXT: deploy is the owner's. Open flags unchanged: the carry-forward/encashment
window between approval and withdrawal still wants a bench check.
- 2026-09-17T08:05:27Z COMMIT: ae106aecc test: the invariant watches what loads at boot, and names the roles → review dispatched
- 2026-09-17T08:08:32Z COMMIT: a800464b1 docs(glass): handoff points at the reviewed commit → review dispatched
- 2026-09-17T08:08:39Z PUSH: nz-glass @ a800464b1
EVIDENCE: 2 (prove red, by hand) — the prove-red gate chose the JS runner for a
Python test set and reported them green on HEAD. Proven properly instead: HEAD
extracted with `git archive` into the scratchpad, the three test files copied
in, `PYTHONPATH=. pytest` there -> 12 failed / 76 passed, including
`[{'attendance': 'ATT-1', 'owner': 'system'}, ...] is not an instance of str`,
which is the header's [object Object] verbatim. Green on the fix: 131 passed
across the six fix-day suites plus the duplicate backfill.
- 2026-09-17T08:51:06Z PUSH: nz-glass @ f45a0f593
REPAIR: the two-row rule shut the door its own sibling refusal points at — on a
punch-count TIE, remove_duplicate_row refuses with "Move a tap to the row it
belongs to first" and move_tap had just been blocked by the same rule. Both
escapes are waived now; the four rebuilding actions are not.
EVIDENCE: 2 (mapped) — 132 passed across the seven fix-day and duplicate suites;
the two new tests red before the waiver, green after.
NEXT: deploy is the owner's; he can already fix Norazlin today by removing the
duplicate row BEFORE pairing.
- 2026-09-17T08:57:02Z PUSH: nz-glass @ 5beef7501
EVIDENCE: 7 (invariant, behavioural) — review of 5beef7501 returned DEPLOY with
one warning: the escape invariant was an AST substring match, which a refactor
could keep while shutting the door. It is now driven end to end on a real
two-row day (TestATwoRowDayKeepsItsEscapesOpen). Proven by two mutations: the
waiver removed from move_tap fails the behavioural escape test; the rule itself
removed fails six tests including the notice. The mutation drill the reviewer
ran out of turns for was also run: both AST tests fail without the waiver.
- 2026-09-17T09:01:58Z PUSH: nz-glass @ 7a3d20bf0
- 2026-09-17T09:02:12Z PUSH: nz-glass @ 641fd4bdc
- 2026-09-17T09:02:12Z COMMIT: 641fd4bdc docs(glass): handoff for the two-row day → review dispatched
REPAIR: the Fix Day screen listed a day's attendance rows without naming them
- status, in, out, hours, OT and nothing else - so on a two-row day HR could
not tell which line was which row, or which shift it was on. The data was
already in row_view; only the line was missing it.
EVIDENCE: 2 (mapped) - fix_day.bundle.test.js red on HEAD, green after; 27 JS
and 109 Python tests across the fix-day suites.
NEXT: deploy; the ghost-row list is still on offer.
- 2026-09-17T09:05:40Z PUSH: nz-glass @ 01a4c79af
REPAIR: "Could not find Reference Name: HR-ATT-2026-15978" on live - _comment
hardcoded reference_doctype "Employee Checkin" and remove_duplicate_row handed
it an Attendance name, so the request threw and rolled back the cancel with it.
The one action that unblocks a two-row day could never complete. The store
harness stubbed _comment with a 2-arg lambda, which is why no test saw it.
EVIDENCE: 2 (mapped) - 4 new tests red on HEAD, green after; 117 passed across
the five fix-day suites; the stub now records the doctype and asserts on it.
NEXT: the owner says the flow has too many steps for one goal - propose the
one-screen "rebuild this day" plan/apply before building it.
- 2026-09-17T09:19:49Z PUSH: nz-glass @ 1295034e2
PLAN: .claude/plans/current-plan.md — one button rebuilds a day (risky tier: it
writes pay-affecting evidence in one press; the owner's rule, recorded with its
consequence — a real mid-day absence is now paid unless HR intervenes, and the
safeguard is that every dropped tap and every long gap is named on screen first).
EVIDENCE: 2 (mapped) — 20 new tests red on HEAD, green after; 147 Python and 27
JS across the seven fix-day suites and the three list/report doors.
NEXT: review, then the owner deploys.
- 2026-09-17T09:29:48Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-09-17T09:29:48Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-17T09:30:19Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-09-17T09:30:19Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-17T09:30:38Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-09-17T09:30:38Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-17T09:30:48Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-09-17T09:30:48Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-17T09:30:52Z COMMIT: d00b4de62 feat(attendance): one press rebuilds a day from its own evidence → review dispatched
- 2026-09-17T09:30:59Z PUSH: nz-glass @ d00b4de62
REPAIR: review of d00b4de62 returned FIX_CRITICAL. The planner had no session
length cap (a 24h "session" was writable in one press, while the manual pair
refuses anything over 20h); two rows both holding punches were merged as if one
were a ghost; and undo_fix only warned about un-cancel for remove_duplicate_row.
All three closed, plus a refactor ticket for the hotspot.
EVIDENCE: 2 (mapped) - 7 new tests red before, green after; 154 passed across
the seven fix-day suites.
NEXT: re-review, then the owner deploys.
REPAIR: the Fix Day rebuild would have left the complained-about days exactly
as they were. attendance_recovery.protected_reason holds any HR-owned row -
right for the nightly job, wrong for HR's own button - and Norazlin's row is
"Absent (HR)", so correcting every tap on it would still have ended in Absent,
0 hours, no OT. protected_reason now takes hr_asked and waives ONLY that hold.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 17 new tests red before, green after;
14 suites green including the recovery engine (96), day_remark (28), lone-in
closer (29) and the ownership classifier (40).
NEXT: review, then the owner deploys; after deploy, confirm on Norazlin's 4 Sep
that the day reads Present with hours and that the OT is claimable in Nadi.
- 2026-09-17T09:42:12Z PUSH: nz-glass @ b9794c65b
- 2026-09-17T09:46:05Z PUSH: nz-glass @ f369e51d4
REPAIR: review of b9794c65b, two Criticals. (1) a mirrored row reads as OWNER_HR
when a person wrote it on the ERP side - closed in f369e51d4 and now refused on
the screen by name too. (2) the never-worse guard is on attendance_recovery's
rebuild path and NOT on day_remark's, which is the one Fix Day uses; hr_asked
opened that door, so HR's press now goes through _rebuild_under_guard and a
rollback comes back as held, not as success.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 6 new tests red before, green after;
14 suites green (405 tests) including the recovery engine and day_remark.
DEAD END: putting the mirrored rule in protected_reason broke five tests of the
mirrored RELEASE plan, which asks that same function about mirrored rows on
purpose. It belongs to the waiver.
NEXT: re-review, then the owner deploys.
- 2026-09-17T09:48:32Z PUSH: nz-glass @ 944aeec7a
REPAIR: a rebuild the engine HELD (never-worse rollback, or a protection) showed
HR "The day came back unchanged" and nothing else - the engine's sentence was in
the answer and only reached the console. It is printed now.
EVIDENCE: 2 (mapped) - 1 new JS test red before, green after; 28 JS green. The
hr_asked branch was also proven by mutation: removing it fails 3 tests.
- 2026-09-17T09:51:28Z PUSH: nz-glass @ 723f79b25
EVIDENCE: 7 (invariant + tickets) - verification review of 944aeec7a executed
all 14 suites, ruff and the bundle test: 0 failures, no Critical, no Warning,
DEPLOY. It confirmed by reading the code that _rebuild_under_guard (not
guarded_rebuild) is the right inner call, that skipping _retire_unmarkable_rows
on the rollback path is REQUIRED - it reads the rolled-back result and would
cancel the very row the guard just protected - and that the held verdict reaches
the screen. Its one suggestion, an unread `rolled_back` flag, is removed rather
than kept: scaffolding rots.
NEXT: the owner deploys. Then: Norazlin 4 Sep must read Present with hours and
her OT must be claimable in Nadi. Open offer, not started: the ghost-row list
(rows holding times with zero punches) across all staff.
- 2026-09-17T09:53:14Z COMMIT: 956e9d22d refactor: drop a flag nothing reads → review dispatched
- 2026-09-17T09:53:32Z PUSH: nz-glass @ 956e9d22d
- 2026-09-17T09:53:45Z PUSH: nz-glass @ fb53ba256
- 2026-09-17T09:53:45Z COMMIT: fb53ba256 docs(glass): handoff for the day rebuild → review dispatched
REPAIR: the FOURTH door. After the ghost was cancelled, the session paired and
the strays ignored, HR-ATT-2026-15657 still read "Absent (HR) · in - · out -".
shift_type.get_automation_attendance filters auto_attendance: 1 and its own
docstring says a row HR marked by hand is "never rebuilt from punches" - so the
engine found no row to update, tried to CREATE one, hit DuplicateAttendanceError
and swallowed it. protected_reason was only the first gate.
release_to_automation hands the day's hand-marked rows back to the engine,
inside the guard's savepoint, only when HR asked. Never a leave, half-day leave,
On Leave, Attendance Request, mirrored or unsubmitted row.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 11 new tests red before, green after;
17 suites green.
NEXT: the owner deploys and re-runs Norazlin 4 Sep.
- 2026-09-17T10:21:21Z PUSH: nz-glass @ c82687052
REPAIR: review of c82687052 returned DEPLOY with two warnings, both about the
same thing: release_to_automation's docstring claimed its exclusions match
get_automation_attendance "exactly" and they do not - it is a deliberate
superset - and the two lists are hand-maintained in two files with nothing
holding them together. The claim is corrected and the dangerous direction is
locked by a drift test, proven by mutation: a new exclusion added to the lookup
alone fails it. The real fix, ONE declared field set all three owners build
from, is on the existing split ticket.
EVIDENCE: 7 (invariant) - 1 new test, red on a mutated lookup, green on HEAD;
9 suites green.
NEXT: the owner deploys and re-runs Norazlin 4 Sep.
- 2026-09-17T10:28:09Z PUSH: nz-glass @ 75c0055bf
- 2026-09-17T10:28:23Z PUSH: nz-glass @ 4cf17cc5b
- 2026-09-17T10:28:23Z COMMIT: 4cf17cc5b docs(glass): handoff for the fourth door → review dispatched
REPAIR: the fifth door, and the last one. The rebuild ran, both taps were
counted and linked, and the day still read "Half Day, in 09:03, out -, 0 h".
get_attendance cut the day into contiguous runs of counts_for_attendance, so the
three ignored taps BETWEEN the real IN and the real OUT left them in two one-tap
segments that never paired. "Not evidence" and "must not be bridged" were one
question; they are two now - splits_the_day names the walls (off-shift,
rejected, unapproved late check-out) and attendance_segments drops the rest.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 12 new tests red before, green after;
16 suites green, one pre-existing failure in test_ot_nonworking_hours confirmed
identical on a clean HEAD extract.
NEXT: the owner deploys and re-runs Norazlin 4 Sep; it should read Present.
