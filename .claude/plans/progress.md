2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
- 2026-09-17T03:23:52Z PUSH: nz-glass @ 07c824401
- 2026-09-17T03:23:52Z COMMIT: 07c824401 docs(glass): handoff for the selfie, self-approval and gloss fixes → review dispatched
- 2026-09-17T05:05:00Z REPAIR: "Leave Type is required" blocked HR from saving ANY hours-based Half Day (HR-ATT-2026-15978, Norazlin, 4 Sep). Attendance.leave_type was mandatory for both On Leave and Half Day — upstream's assumption that a Half Day is always leave — while this app's own check_leave_record writes leave-less Half Days deliberately. Mandatory for On Leave only; still offered on a Half Day.
- 2026-09-17T05:05:00Z EVIDENCE: rung 2 — 1 test RED on HEAD first, 4 green after; 186 mapped/neighbour tests green (test_day_remark's single failure is the known batch-ordering pollution, green alone).
- 2026-09-17T04:00:18Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:11:37Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T04:11:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T04:11:53Z COMMIT: 2ed460509 fix(attendance): a half day earned by hours stops demanding a leave type → review dispatched
- 2026-09-17T05:40:00Z EVIDENCE: rung 2 — review of 2ed460509 NEXT_ACTION DEPLOY, no Critical: no other server or client rule requires leave_type on a Half Day (attendance.js has none at all), and every consumer guards — salary_slip.get_half_absent_days prices hours-based half days by half_day_status == "Absent" and never reads leave_type, the LWP branch is falsy-guarded, the Monthly Attendance Sheet filters empty types out, and shift_attendance.mark_hr_owned already uses "no leave_type" as its HR-editable signal. check_leave_record still backfills the type for a genuine leave half day before the mandatory check runs.
- 2026-09-17T05:40:00Z REPAIR: the review's one Warning — a site Property Setter on Attendance.leave_type.mandatory_depends_on would outrank the JSON and keep refusing the save. Patch added so the release self-heals instead of asking anyone to check a site.
- 2026-09-17T04:18:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:19:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:19:33Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:19:34Z EVIDENCE: 6 behaves — family hunt: class=upstream metadata that models "Half Day" as a leave state, inside an app; 1 call site(s) given verdicts, 1 same-root ⟂0c35df7d632a
- 2026-09-17T04:19:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:19:45Z EVIDENCE: 6 behaves — family hunt: class=upstream metadata that models "Half Day" as a leave state, inside an app; 1 call site(s) given verdicts, 1 same-root ⟂0c35df7d632a
- 2026-09-17T04:19:48Z COMMIT: a84b89973 fix(attendance): the half day fix lands even on a site with its own override → review dispatched
- 2026-09-17T04:20:22Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:20:36Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-17T04:20:40Z COMMIT: d4494a658 fix(attendance): an on-duty request stops being unapprovable forever → review dispatched
- 2026-09-17T06:10:00Z REPAIR: review Critical on d4494a658 — the overlapping-shift fallback could silently repurpose a STALE leave row, because should_mark_attendance guards on the Leave Application while the fallback reads the row, and create_or_update_attendance writes with db_set (no validation). A candidate with leave_type or status On Leave is now skipped and logged; the framework's overlap refusal stands, which is the right answer for a day that still says leave.
- 2026-09-17T06:10:00Z EVIDENCE: rung 2 — 2 more tests RED first, 13 green after; 397 attendance-request neighbour tests green. Hotspot ticket opened (.claude/plans/ticket-attendance-request-refactor.md): six methods now re-derive the same day state, which is why this fix had to be written twice.
- 2026-09-17T04:26:47Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-09-17T04:27:00Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T04:27:16Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T04:27:17Z EVIDENCE: 6 behaves — family hunt: class=Attendance is keyed by (employee, date, shift), but a request is about; 1 call site(s) given verdicts, 5 same-root ⟂f0de8b38c48e
- 2026-09-17T04:27:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 10 file(s) ⟂28ecefc53753
- 2026-09-17T04:27:32Z EVIDENCE: 6 behaves — family hunt: class=Attendance is keyed by (employee, date, shift), but a request is about; 1 call site(s) given verdicts, 5 same-root ⟂f0de8b38c48e
- 2026-09-17T04:27:35Z COMMIT: f27a0e402 fix(attendance): a leave row is never repurposed by an on-duty request → review dispatched
- 2026-09-17T04:30:41Z PUSH: nz-glass @ 783d241c5
- 2026-09-17T04:30:41Z COMMIT: 783d241c5 chore(plans): record the review verdicts on the attendance fixes → review dispatched
- 2026-09-17T04:45:11Z COMMIT: 05b42c583 test(checkin): drive the selfie timing tests where the upload now happens → review dispatched
- 2026-09-17T07:00:00Z REPAIR: the owner's report that a staff member's clock-in "goes missing" and the app shows Check In when it should show Check Out. Not a cache and not a lost punch: lastLog answered {} for the whole of any list reload and liveAction reads {} as "no open session". The server still decided the type, so the punch stored was a correct check-OUT — the label was the only thing wrong, and it is what makes people tap again.
- 2026-09-17T07:00:00Z EVIDENCE: rung 2 — 1 test RED first, green after; CheckInPanel + location suites 32/32, including the two selfie-timing tests that b8af8c241 had silently detached from the code (fixed in the commit before this one).
- 2026-09-17T04:45:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-09-17T04:45:50Z COMMIT: 995abacbb fix(checkin): the button stops saying Check In to somebody who is checked in → review+design dispatched
- 2026-09-17T04:50:14Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-17T07:20:00Z REPAIR: review Warning on 995abacbb — the held-over row left the label stale in the OTHER direction after a check-out, until the reload landed. The punch response sets it now; the reload stays the authority. The dead { immediate: true } option dropped.
- 2026-09-17T07:20:00Z EVIDENCE: rung 2 — 1 test RED first, 33/33 green after across both CheckInPanel suites. The reviewer verified in node_modules that frappe-ui's createListResource reassigns .data on every fetch, so the non-deep watch cannot miss a reload.
- 2026-09-17T04:50:19Z COMMIT: e86ae521c fix(checkin): the label is right the moment the punch lands, both ways → review+design dispatched
- 2026-09-17T07:45:00Z EVIDENCE: rung 2 — re-review of e86ae521c NEXT_ACTION DEPLOY. It verified from the server source that punch() returns name/employee/employee_name/log_type/time/requires_remote_approval/remote_approval_status and nothing else, and that every reader of lastLog touches only log_type, time and name — is_abandoned is read off the separate unresolvedStaleIn resource and matched by name, so the optimistic row cannot mislead anything today. Dropping { immediate: true } confirmed dead-code removal.
- 2026-09-17T07:45:00Z NEXT: owner to say go on Phase 1 (settle row ownership) and Phase 2 (wire the duplicate resolver that already exists in hrms/sync/erp_backfill.py and is called by nothing). Its one Warning — an out-of-order reload can drag the label back for one round trip — is on record as a ceiling marker with its upgrade trigger rather than fixed, because the window closes on the next reload and the counter machinery is not worth it unless anyone reports it.
- 2026-09-17T04:54:56Z COMMIT: f0412ebc4 docs(checkin): mark what the held-over row does not promise → review+design dispatched
- 2026-09-17T04:55:14Z PUSH: nz-glass @ 21541e304
- 2026-09-17T04:55:14Z COMMIT: 21541e304 docs(glass): handoff for the attendance pipeline fixes → review dispatched
- 2026-09-17T08:20:00Z PLAN: current-plan.md approved (hash 097aeb7619dd) — one day, one attendance row; the owner's three-item list, with "no on gap" ruled out of scope.
- 2026-09-17T08:20:00Z REPAIR: item 3 — Fix Day gains remove_duplicate_row. A day carrying two rows could not be reduced to one anywhere: the report shows one, the Attendance list shows two, the master edit refuses the day outright. Cancels, never deletes; keeps the row the punches are linked to; the day is re-marked from its punches.
- 2026-09-17T08:20:00Z EVIDENCE: rung 2 — 14 tests RED on HEAD first (7 pure refusal cases + 7 contract), green after; 132 fix-day tests green including the two existing suites that pin "five actions" and now pin six.
- 2026-09-17T05:18:18Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-17T05:18:18Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-17T05:18:31Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 10 file(s) ⟂b0f3c69c66bb
- 2026-09-17T05:18:31Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-17T05:18:34Z COMMIT: 58f475c6b feat(attendance): HR can take a day back to one attendance row → review dispatched
- 2026-09-17T08:45:00Z REPAIR: item 2 — resolve_duplicate_rows existed, tested, with NO caller. Wired in as the endgame's `duplicates` step between recovery and ot, with a re-mark queued for each day it changed and a line in HR's summary. This is the specific reason the last release did not finish the job.
- 2026-09-17T08:45:00Z EVIDENCE: rung 2 — 10 tests RED first, green after; 207 endgame + backfill tests green.
- 2026-09-17T05:21:19Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:21:19Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-17T05:21:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:21:32Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-09-17T05:21:37Z COMMIT: 22f5541cb feat(attendance): the repair takes a two-row day back to one → review dispatched
- 2026-09-17T09:05:00Z REPAIR: item 1 — a burst of taps seconds apart wrote a twelve-second session (Norazlin 18:09:14/26/30). A punch within 45s of the previous one is now stored and skip-stamped with a comment, never refused: the old 60-second SAME_PUNCH_WINDOW refused real punches too, which is why it was removed.
- 2026-09-17T09:05:00Z EVIDENCE: rung 2 — 11 tests RED first, green after; 497 remote_checkin neighbour tests green.
- 2026-09-17T05:24:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:24:56Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:25:07Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:25:08Z EVIDENCE: 6 behaves — family hunt: class=every punch is treated as a deliberate act, however close it lands to; 37 call site(s) given verdicts, 2 same-root ⟂0e7de744fe27
- 2026-09-17T05:25:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:25:22Z EVIDENCE: 6 behaves — family hunt: class=every punch is treated as a deliberate act, however close it lands to; 37 call site(s) given verdicts, 2 same-root ⟂0e7de744fe27
- 2026-09-17T05:25:24Z COMMIT: 960ed4c16 fix(checkin): a stutter of taps is one tap, not a session → review dispatched
- 2026-09-17T09:25:00Z EVIDENCE: rung 2 — review of 58f475c6b NEXT_ACTION DEPLOY. It traced the re-link by hand: after the cancel, _finish -> _rebuild -> day_remark.remark_day -> attendance_recovery re-points every checkin's `attendance` field at the surviving row (7 assignment sites), in the same request, so nothing is left pointing at a cancelled row; and if the rebuild threw, the whole request rolls back and the cancel with it.
- 2026-09-17T09:25:00Z REPAIR: its one Warning — a DRAFT attendance row was treated as live, and doc.cancel() answers a draft with a raw framework error. Refused in the pure guard with a sentence naming Desk. Also refused: a target that is no longer on the day (stale screen), which was falling back to a row with no punch count.
- 2026-09-17T09:25:00Z NEXT: the bench probe for the sixth action is the one thing left undone, ticketed at the foot of .claude/plans/ticket-attendance-request-refactor.md — it is what would catch the unit stub diverging from a real site.
- 2026-09-17T05:26:28Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T05:26:28Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-17T05:26:41Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T05:26:41Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-17T05:26:45Z COMMIT: b05a4afb7 fix(attendance): the duplicate-row action refuses in sentences, not traces → review dispatched
- 2026-09-17T09:50:00Z EVIDENCE: rung 2 — review of 22f5541cb..b05a4afb7 NEXT_ACTION DEPLOY, no Critical. It verified by reading that remark_day_after_commit registers on frappe.db.after_commit, so the cancel and its re-mark ride the SAME commit the endgame loop makes; and that the duplicates step is idempotent on resume, because a cancelled row carries docstatus 2 and duplicate_days reads docstatus 1 only.
- 2026-09-17T09:50:00Z REPAIR: its Warning — a burst-skipped punch was invisible to HR. The comment now carries the Attendance Day Audit's own SKIP_PREFIX and "Tapped again" joins REPAIRABLE_SKIP_REASONS, so the existing detector lists it with the way back. No new report was built.
- 2026-09-17T05:32:49Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T05:32:49Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 5 extra test file(s) ⟂2da7a836b075
- 2026-09-17T05:33:07Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T05:33:07Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 5 extra test file(s) ⟂2da7a836b075
- 2026-09-17T05:33:14Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T05:33:14Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 5 extra test file(s) ⟂2da7a836b075
- 2026-09-17T05:33:15Z EVIDENCE: 6 behaves — family hunt: class=a guard that reasons about rows without asking whether the write it; 29 call site(s) given verdicts, 5 same-root ⟂f8dbc7841a1e
- 2026-09-17T05:33:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-17T05:33:29Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 5 extra test file(s) ⟂2da7a836b075
- 2026-09-17T05:33:30Z EVIDENCE: 6 behaves — family hunt: class=a guard that reasons about rows without asking whether the write it; 29 call site(s) given verdicts, 5 same-root ⟂f8dbc7841a1e
- 2026-09-17T05:33:32Z COMMIT: 2f969afd0 fix(checkin): a tap the system stops counting reaches HR's list → review dispatched
- 2026-09-17T10:15:00Z REPAIR: review CRITICAL on 2f969afd0 — the burst comment was written with add_comment("Info", ...), and every skip-reason reader filters comment_type == "Comment". The row was never seen, so the "reaches HR's list" fix did nothing while all its tests passed: they checked that the marker STRINGS agreed, not that the writer and the reader agreed on the row type. Now "Comment", and the new test reads the type out of both sides.
- 2026-09-17T10:15:00Z EVIDENCE: rung 2 — 1 test RED first, 14 green after; 596 remote_checkin + audit neighbour tests green; module import checked on verify-bench python (no cycle, SKIP_PREFIX identical on both sides).
- 2026-09-17T10:15:00Z LEARNING(gate): a marker string shared by a writer and a reader is not the whole contract — add_comment's first argument is the stored comment_type, and a test that only compares constants will pass while the feature does nothing.
- 2026-09-17T05:38:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:38:47Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:39:04Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:39:14Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:39:15Z EVIDENCE: 6 behaves — family hunt: class=a writer and a reader agreeing on the TEXT of a marker while disagreeing; 37 call site(s) given verdicts, 1 same-root ⟂3cf557ee1323
- 2026-09-17T05:39:25Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-17T05:39:26Z EVIDENCE: 6 behaves — family hunt: class=a writer and a reader agreeing on the TEXT of a marker while disagreeing; 37 call site(s) given verdicts, 1 same-root ⟂3cf557ee1323
- 2026-09-17T05:39:29Z COMMIT: a9519ef65 fix(checkin): the skip reason is written where the readers look for it → review dispatched
- 2026-09-17T10:35:00Z EVIDENCE: rung 2 — review of a9519ef65 NEXT_ACTION DEPLOY, no Critical, no Warning. It confirmed end to end that a burst-skipped punch is now found by BOTH skip-reason readers and offered "unskip", that the module-scope import has no cycle on the real interpreter, that the resolved-type trace is untouched, and that the new test reads BOTH sides from source so reverting the fix would fail it.
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
