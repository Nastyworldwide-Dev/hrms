2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-09-17T11:19:56Z PUSH: nz-glass @ d643e66d2
REPAIR: review of 672a4b1df, two more. (1) the backfill pooled `refs` from every
Fix Day entry, and a rebuild's refs name the session taps it KEPT as well as the
ones it dropped - so a kept tap that something later skipped for a real reason
would have been ticked noise, a wall mislabelled, the inverse of the defect.
It reads after_state.plan.drop for a rebuild and refs only for an ignore_tap,
and chunks the IN clause. (2) attendance_master_edit has its OWN punch writer
(_update_punch does a plain doc.update/save), which Fix Day's choke point cannot
reach; its shift stamp carries the clear now.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 16 suites green; the one failure in
test_ot_nonworking_hours is pre-existing and identical on a clean HEAD extract.
NEXT: the owner deploys.
- 2026-09-17T11:23:55Z PUSH: nz-glass @ 5d5282203
REPAIR: my own sweep (told the reviewer to assume the list is still wrong) found
the sixth: attendance_day_audit's `unskip` repair cleared skip_auto_attendance
and left the verdict. Fixed, and added to both the census and the clearers test.
Also confirmed by reading: master_edit's second "skip_auto_attendance": 0 is an
in-memory PREVIEW stamp for a what-if calculation, not a write; and there is
exactly one _finish(..., "rebuild_day", ...) call and it passes plan=plan, so no
rebuild entry is invisible to the backfill.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 14 suites green.
NEXT: the owner deploys once the verification comes back.
- 2026-09-17T11:26:46Z PUSH: nz-glass @ 951af8d8a
- 2026-09-17T11:28:48Z PUSH: nz-glass @ 5735179cf
- 2026-09-17T11:28:49Z COMMIT: 5735179cf docs(glass): handoff for the wall-vs-noise rule → review dispatched
REPAIR: 18 Sep, live. Remote Approvals showed a BROKEN IMAGE for every pending
selfie. The 17 Sep crash was gone - the photo uploaded - but upload_selfie stored
the File public, and the S3 hook addresses a public file as the bucket object
itself ({endpoint}/{bucket}/{key}), which is readable only with a public-read
ACL this bucket does not grant. Selfies are private now and attached to their
punch, so File.is_downloadable grants exactly the people who can read that
Employee Checkin - the approver included. The `# ceiling:` on that function had
named this upgrade already; it arrived for a different reason than expected.
EVIDENCE: 2 (mapped) - 13 new tests red before, green after; 176 passed across
remote_checkin and the fix-day suites.
NEXT: deploy; the patch repairs the photos already taken.
- 2026-09-18T03:12:18Z PUSH: nz-glass @ 8c2f4c6eb
REPAIR: the selfie url parser treated any http(s) url as a bucket url. An
ABSOLUTE url to this site's own generate_file endpoint would have been split on
slashes, read "api" as the bucket, and rewritten a good photo's address to
nonsense - on a patch that runs once and is hard to undo. It refuses anything
containing /api/method/ now.
EVIDENCE: 2 (mapped) - 1 new test red before, green after; 87 passed.
NEXT: the owner's ruling on whether Employee master still comes from the ERP,
then the cutover hold-back for shift/location data.
- 2026-09-18T03:17:49Z PUSH: nz-glass @ 96e0df238
REPAIR: live employees had shift and location reverted to the source's values.
No scheduler runs a sync - HRMS Sync Run logs every press - but the sync was
ALLOWED to: unlock_mirrored_writes held back Attendance alone, and every other
mirrored doctype was still pulled and UPDATED, including Employee
(default_shift, branch, holiday_list), Shift Assignment and Shift Schedule
Assignment. Owner ruling: after cutover, add what is absent, never overwrite
what exists. One pure rule, asked where the create-only question was already
asked.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 23 tests red before, green after; 18
sync suites green (400+ tests).
NEXT: review, then the owner deploys. The rows already reverted are a SEPARATE
repair - Frappe Version history holds the previous shift and branch values.
- 2026-09-18T03:22:43Z PUSH: nz-glass @ 5baf3c99a
EVIDENCE: 7 (invariant + a ruling surfaced) - review of 5baf3c99a returned
DEPLOY. Its parity warning was checked and is not a defect: parity compares row
COUNTS and this stops only updates. Its second warning is real and is the
owner's call, not mine: after cutover the source can no longer disable a hub
login for somebody marked Left on the ERP, because the Employee row is skipped
before _reconcile_user_status. Recorded in cutover.py and raised with him.
NEXT: the owner deploys 5baf3c99a and rules on whether a leaver marked only on
the old ERP should still lose their Verifica login.
- 2026-09-18T03:27:02Z PUSH: nz-glass @ f08b27f70
- 2026-09-18T03:27:02Z COMMIT: f08b27f70 docs(sync): name the one thing the insert-only rule gives up → review dispatched
REPAIR: the planner was stricter than the engine it plans for. Norazlin's 3 Sep
holds two taps the device both recorded as IN; the shift pairs ALTERNATING
entries, so the engine read them as in 08:48 / out 18:02 and marked her Present
with 8.04 h - and "Rebuild this day" refused with "Nothing closes this day",
sending HR to hunt a fault that was not there. day_plan takes the shift's own
pairing rule now, read per day from the taps' shift, and the strict reading stays
the default for a caller that says nothing.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 8 new tests red before, green after;
10 suites green.
NEXT: the owner deploys; an IN-IN day then rebuilds with one press like any other.
- 2026-09-18T03:38:02Z PUSH: nz-glass @ da5fa456c
REPAIR: the rebuild got 3 Sep right in Attendance and the report and left the
check-in list showing two INs. Owner: "check in must show correct in and out
despite it was in in or anything". The rebuild relabels the two taps that ARE
the session - and nothing else - through a narrow, explicit exception in
_write_tap. Shown in the plan before Apply, commented on the punch, restored by
the undo (log_type is already in TAP_FIELDS).
EVIDENCE: 2 (mapped) + 3 (blast radius) - 10 new tests red before, green after;
11 Python suites and 20 JS green.
NEXT: the owner deploys; an IN-IN day then reads IN/OUT on all four pages.
- 2026-09-18T03:58:40Z PUSH: nz-glass @ e1f4165b7
REPAIR: review of e1f4165b7. (1) undo_fix refused an ENTIRE rebuild when it had
also cancelled a ghost row - so the relabel my commit called reversible was not.
A remove_duplicate_row IS its cancel and is still refused; a rebuild restores its
taps and says the cancelled row stays cancelled. (2) session_is_open reads
log_type != "OUT", so relabelling a closing tap makes the session read CLOSED -
the relabel is a CORRECTNESS improvement there, not a risk: an IN-IN day used to
leave its session reading open. (3) the checkin_import worry was checked and does
not corrupt anything - drop_already_imported matches on the SOURCE key, so no
duplicate and no revert; the real effect is a permanent type_mismatch line on the
import report. Ticketed, not touched: the owner has had one bad sync day already.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 4 new tests red before, green after;
179 passed across five fix-day suites.
NEXT: the owner deploys.
