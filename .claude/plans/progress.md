2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-17T10:55:55Z PUSH: nz-glass @ ff1493e85
REPAIR: review of ff1493e85 found a Critical I missed and it was right. The
financial-guard refusal path (handle_attendance_exception ->
skip_attendance_in_checkins) skip-stamps punches so a blocked batch is not
retried - that means "the system deferred this", not "HR judged this noise" -
and my inverted reading would have bridged across them and paid the time. The
rule is fail-safe now: every skipped punch is a WALL unless it carries the new
Employee Checkin.skipped_as_noise tick, which only Fix Day's ignore/rebuild and
the burst stutter set. Default 0 = exactly the behaviour before this branch.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 16 suites green incl. remote_checkin
(67) and master edit (54); the one failure in test_ot_nonworking_hours is
pre-existing and identical on a clean HEAD extract.
DEAD END: classifying writers by reading them was wrong twice (I missed the
master editor's two, then the deferral path). The default had to change, not
the list.
- 2026-09-17T11:05:54Z PUSH: nz-glass @ 8c06af285
REPAIR: naming skipped_as_noise in CHECKIN_FIELDS would have put an unmigrated
column in a live SELECT - the "Unknown column" class this fork has already been
burned by (ensure_extension_custom_fields, the OT suite on
remote_approval_status). checkin_fields() asks frappe.db.has_column once per
request and leaves the field out when it is absent; a row without the key reads
as 0, which splits_the_day treats as a WALL - the conservative answer, so that
window behaves exactly like the code did before the field existed.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 17 suites green (600+ tests); the one
failure in test_ot_nonworking_hours is pre-existing and identical on a clean
HEAD extract. Two AST harnesses updated to see the new module-level names.
NEXT: re-review, then the owner deploys (this one needs the migrate to create
the column; until it exists every skipped punch simply stays a wall).
- 2026-09-17T11:11:53Z PUSH: nz-glass @ 3e02ec548
REPAIR: two places cleared skip_auto_attendance without clearing the new noise
verdict (attendance_recovery's unskip, the master edit's hand-back). Harmless
while the tap counts - splits_the_day answers on counted first - but the tick
would have survived onto the NEXT skip and made a deferral read as noise. Both
clear it now, and a test anchors on each definition (all three names are also
called earlier in their own files, which is how the first version of that test
found the wrong line).
EVIDENCE: 2 (mapped) + 3 (blast radius) - 13 suites green; the single failure in
test_ot_nonworking_hours is pre-existing and identical on a clean HEAD extract.
NEXT: the owner deploys; the day's column is created by the patch on migrate,
and until it exists every skipped punch simply stays a wall.
- 2026-09-17T11:13:24Z PUSH: nz-glass @ c4a0fca32
REPAIR: review of c4a0fca32 found a third set of un-skippers I had missed -
pair_taps and the rebuild's session keep both set skip_auto_attendance 0 and
left the noise tick behind. Fixed at the CHOKE POINT instead of the call sites:
_write_tap clears the verdict whenever the skip is written as 0, so none of the
five callers can forget it. Its Warning is closed too: taps HR ignored before
the field existed are backfilled from the HR Day Fix Log (action ignore_tap or
rebuild_day, not undone, and only those still skipped) - the app's own audit
record rather than a guess from comment text.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 17 suites green; the one failure in
test_ot_nonworking_hours is pre-existing and identical on a clean HEAD extract.
NEXT: the owner deploys.
- 2026-09-17T11:16:36Z PUSH: nz-glass @ 672a4b1df
REPAIR: the undo's writer bypasses _write_tap on purpose (it reverses an action
rather than inventing evidence), so the choke point does not cover it. It
restores every TAP_FIELD, which now carries the verdict, so a new snapshot round
trips - but a snapshot taken TODAY, before the field existed, has no such key
and would have written NULL into a Check column. It lands as 0 now: the wall,
which is how that tap read when the snapshot was taken.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 13 suites green.
